"""Close authorization, override (with mandatory justification), and PDF export."""
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from core.close_gate import run_close_gates, compute_readiness_score, can_close
from core.pdf_export import build_close_pack
from audit import batch_history
from api import state

router = APIRouter()


def _current_gates():
    return run_close_gates(
        batch=state.batch, ledger=state.ledger, thresholds=state.thresholds,
        sources_loaded={"settlements": True, "books": True, "gstr2b": True},
    )


@router.post("/api/close/authorize")
def authorize_close():
    if state.batch is None:
        raise HTTPException(404, "No batch loaded")
    gates = _current_gates()
    score = compute_readiness_score(gates)
    ready, _blockers = can_close(gates)
    if not ready:
        raise HTTPException(400, "Close gates are not all passing — cannot authorize")

    ev = state.ledger.append("CLOSE_AUTHORIZED", detail={"score": score, "actor": "human"})
    batch_history.mark_closed(state.current_run_id)
    state.close_authorized = True
    state.close_override_justification = None

    return {"ok": True, "ledger_seq": ev.seq}


class OverrideBody(BaseModel):
    justification: str


@router.post("/api/close/override")
def override_close(body: OverrideBody):
    if state.batch is None:
        raise HTTPException(404, "No batch loaded")
    if not body.justification.strip():
        raise HTTPException(400, "Justification is required to override a gate")

    gates = _current_gates()
    score = compute_readiness_score(gates)
    ready, blockers = can_close(gates)
    if ready:
        raise HTTPException(400, "All gates already pass — use authorize instead of override")

    absolute_blockers = [b for b in blockers if not b.overridable]
    if absolute_blockers:
        raise HTTPException(
            400,
            f"Cannot override: {', '.join(b.label for b in absolute_blockers)} "
            "require direct resolution (see POLICY.md).",
        )

    overridable_blockers = [b for b in blockers if b.overridable]
    ev = state.ledger.append(
        "CLOSE_OVERRIDE",
        detail={
            "score": score,
            "blockers": [b.name for b in overridable_blockers],
            "justification": body.justification,
            "actor": "finance_controller",
        },
    )
    batch_history.mark_override_used(state.current_run_id)
    state.close_authorized = True
    state.close_override_justification = body.justification

    return {"ok": True, "ledger_seq": ev.seq}


@router.get("/api/pdf/export")
def export_pdf():
    if state.batch is None:
        raise HTTPException(404, "No batch loaded")

    batch = state.batch
    exception_entries = [e for e in batch.records.values() if e.exception_class is not None]
    gates = _current_gates()
    score = compute_readiness_score(gates)
    ready, _blockers = can_close(gates)
    s = batch.summary()
    total_itc_risk = sum(e.itc_risk_paise for e in batch.records.values())

    itc_by_class: dict = {}
    for e in exception_entries:
        itc_by_class[e.exception_class] = itc_by_class.get(e.exception_class, 0) + e.itc_risk_paise

    intact, _broken = state.ledger.verify()
    final_hash = state.ledger.recent(1)[0].current_hash if len(state.ledger) else "N/A"
    merchant_gstin = next(
        (e.raw.get("merchant_gstin") for e in batch.records.values() if e.raw.get("merchant_gstin")),
        "N/A",
    )

    pdf_bytes = build_close_pack(
        merchant_gstin=merchant_gstin,
        score=score,
        status="CLOSED" if ready else "CONDITIONALLY CLOSED",
        total_records=s["total"],
        resolved_count=s["resolved"],
        human_reviewed=s["human_required"] + s["approved"] + s["rejected"] + s["escalated"],
        exceptions_remaining=len(exception_entries),
        total_itc_risk_paise=total_itc_risk,
        gate_results=gates,
        exception_classes=s["exception_classes"],
        itc_at_risk_by_class=itc_by_class,
        ledger_event_count=len(state.ledger),
        chain_intact=intact,
        final_hash=final_hash,
        override_justification=state.close_override_justification,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=settlesync_close.pdf"},
    )
