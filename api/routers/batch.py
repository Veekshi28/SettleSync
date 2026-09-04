"""
Batch reconciliation endpoints. Runs the existing deterministic pipeline
(core/ingest → core/normalize → core/match → core/classify → agent/narrator)
in a background thread so GET /api/batch/status can be polled for live
progress, mirroring the old Streamlit activity feed.
"""
import threading
import time
import uuid

from fastapi import APIRouter

from core.state import BatchState, RecordState
from core.ingest import load_all
from core.normalize import normalize_all
from core.match import run_three_way_match
from core.classify import classify
from core.close_gate import run_close_gates, compute_readiness_score
from agent.narrator import explain_exception
from audit import batch_history

from api import state

router = APIRouter()

SETTLEMENTS_PATH = "data/synthetic/settlements.csv"
BOOKS_PATH = "data/synthetic/books.csv"
GSTR_PATH = "data/synthetic/gstr2b.csv"


def _run_pipeline(batch: BatchState) -> None:
    state.ledger.append("BATCH_START")
    try:
        raw = load_all(SETTLEMENTS_PATH, BOOKS_PATH, GSTR_PATH)
        normalized = normalize_all(raw)
        state.ledger.append("INGESTED", detail={"count": len(normalized)})

        for r in normalized:
            rid = r["record_id"]
            entry = batch.add(rid, raw=r)
            entry.transition(RecordState.INGESTED)
            entry.transition(RecordState.NORMALIZED)
            entry.transition(RecordState.MATCHING)

            match = run_three_way_match(r)
            state.ledger.append(
                "match_attempt", rid,
                match_type=match.get("type"), confidence=match.get("confidence", 0),
            )

            if match["matched"]:
                entry.match_type = match["type"]
                entry.match_confidence = match["confidence"]
                entry.transition(RecordState.RESOLVED)
                state.ledger.append("resolved", rid, match_type=match["type"])
                batch.log(rid, "resolved", f"{match['type']} match @ {match['confidence']:.0%}")
            else:
                entry.transition(RecordState.EXCEPTION)
                exc = classify(
                    record_id=rid,
                    settlement_amount_paise=r.get("settlement_amount_paise"),
                    books_amount_paise=r.get("books_total_paise"),
                    gstr_amount_paise=r.get("gstr_total_paise"),
                    invoice_date=r.get("books_invoice_date"),
                    settlement_date=r.get("settlement_date"),
                    vendor_gstin_settlement=r.get("vendor_gstin_settlement"),
                    vendor_gstin_books=r.get("vendor_gstin_books"),
                    supplier_filed=r.get("gstr_supplier_filed", True),
                )
                entry.exception_class = exc.exception_class
                entry.exception_rule = exc.icai_citation
                entry.exception_confidence = exc.confidence
                entry.exception_hint = exc.resolution_hint
                entry.itc_risk_paise = exc.itc_risk_paise
                entry.itc_risk_label = exc.itc_risk_label
                state.ledger.append(
                    "classified", rid,
                    exception_class=exc.exception_class, itc_risk_paise=exc.itc_risk_paise,
                )

                narrative, used_llm = explain_exception(
                    r, exc.exception_class, exc.explanation, exc.icai_citation, exc.resolution_hint,
                )
                entry.exception_narrative = narrative
                entry.transition(RecordState.AI_REVIEW)
                entry.transition(RecordState.HUMAN_REQUIRED)
                state.ledger.append(
                    "human_required", rid,
                    exception_class=exc.exception_class, llm_used=used_llm,
                )
                batch.log(rid, "exception", f"{exc.exception_class} ({exc.confidence:.0%})")

            time.sleep(0.01)  # small pacing so the activity feed reads as live

        state.ledger.append("BATCH_COMPLETE", detail=batch.summary())

        run_id = str(uuid.uuid4())
        state.current_run_id = run_id
        gates = run_close_gates(
            batch=batch, ledger=state.ledger, thresholds=state.thresholds,
            sources_loaded={"settlements": True, "books": True, "gstr2b": True},
        )
        score = compute_readiness_score(gates)
        s = batch.summary()
        total_risk = sum(e.itc_risk_paise for e in batch.records.values())
        batch_history.save_run(
            run_id=run_id,
            total_records=s["total"],
            resolved_count=s["resolved"],
            exception_count=sum(s["exception_classes"].values()),
            human_reviews=s["human_required"],
            close_readiness_score=score,
            total_itc_risk_paise=total_risk,
            match_rate=round(s["resolved"] / max(s["total"], 1) * 100, 2),
        )
    finally:
        with state.lock:
            state.running = False


@router.post("/api/batch/run")
def run_batch():
    with state.lock:
        if state.running:
            return {"ok": False, "total": 0}
        raw = load_all(SETTLEMENTS_PATH, BOOKS_PATH, GSTR_PATH)
        total = len(raw["settlements"])

        batch = BatchState()
        state.batch = batch
        state.running = True
        state.close_authorized = False
        state.close_override_justification = None

    thread = threading.Thread(target=_run_pipeline, args=(batch,), daemon=True)
    thread.start()

    return {"ok": True, "total": total}


@router.post("/api/batch/preflight")
def batch_preflight():
    """
    Scans ONLY the settlement CSV — before books/GSTR-2B are even consulted —
    and predicts what reconciliation will likely find. Purely deterministic
    heuristics over settlement data; no LLM, no books/GSTR-2B read here.
    """
    import pandas as pd

    df = pd.read_csv(SETTLEMENTS_PATH)
    df["settlement_date"] = pd.to_datetime(df["settlement_date"])
    df["amount_paise"] = df["amount_paise"].astype(int)
    total = len(df)

    if total == 0:
        return {
            "total_settlements": 0,
            "predicted": {
                "timing_diff_risk": 0, "amount_mismatch_risk": 0,
                "large_amounts": 0, "duplicate_refs": 0,
                "estimated_exceptions": 0, "estimated_auto_resolution_rate": 0,
            },
            "recommendation": "No settlement records found.",
        }

    # 1. Cross-period timing risk: early-month settlements often correspond
    # to invoices from the previous month.
    timing_risk = int((df["settlement_date"].dt.day <= 10).sum())

    # 2. TDS amount pattern detection: does this amount look like a gross
    # invoice value net of a common TDS rate (1%, 2%, 10%)? Reconstructing
    # gross = net / (1 - rate) and checking it lands within a few paise of a
    # whole rupee is the discriminating test — round(x, -2) is *always*
    # within 50 paise of x by construction, so a raw "< 50" tolerance against
    # it is tautological and matches almost every amount.
    TDS_FACTORS = [0.99, 0.98, 0.90]

    def looks_like_tds(amount):
        for f in TDS_FACTORS:
            gross = amount / f
            remainder = gross % 100
            distance_to_whole_rupee = min(remainder, 100 - remainder)
            if distance_to_whole_rupee < 5:
                return True
        return False

    tds_risk = int(df["amount_paise"].apply(looks_like_tds).sum())

    # 3. Large amounts (above 95th percentile) — higher manual-review risk.
    p95 = df["amount_paise"].quantile(0.95)
    large_amount_count = int((df["amount_paise"] > p95).sum())

    # 4. Duplicate invoice references.
    dup_refs = int(df["invoice_ref"].duplicated().sum())

    # 5. Expected auto-resolution estimate. timing_risk is overestimated by
    # this heuristic (most timing differences still auto-match), so weight
    # it down relative to the others.
    estimated_exceptions = int(timing_risk * 0.5 + tds_risk * 0.7 + dup_refs * 1.0)
    estimated_resolution = max(0, total - estimated_exceptions)
    estimated_rate = round(estimated_resolution / total * 100, 1)

    return {
        "total_settlements": total,
        "predicted": {
            "timing_diff_risk": timing_risk,
            "amount_mismatch_risk": tds_risk,
            "large_amounts": large_amount_count,
            "duplicate_refs": dup_refs,
            "estimated_exceptions": estimated_exceptions,
            "estimated_auto_resolution_rate": estimated_rate,
        },
        "recommendation": (
            "Batch looks clean — expect high auto-resolution."
            if estimated_exceptions < total * 0.15
            else "Multiple risk signals detected — expect manual review items."
        ),
    }


@router.get("/api/batch/status")
def batch_status():
    batch = state.batch
    if batch is None:
        return {
            "has_batch": False, "running": False, "total": 0, "resolved": 0,
            "human_required": 0, "escalated": 0, "approved": 0,
            "close_readiness_score": 0, "unresolved_variance_paise": 0,
            "total_itc_risk_paise": 0, "activity": [], "summary": {},
        }

    s = batch.summary()
    total_itc_risk = sum(e.itc_risk_paise for e in batch.records.values())
    unresolved_variance = sum(
        e.raw.get("settlement_amount_paise", 0)
        for e in batch.records.values()
        if e.state.value in ("HUMAN_REQUIRED", "EXCEPTION", "AI_REVIEW")
    )
    gates = run_close_gates(
        batch=batch, ledger=state.ledger, thresholds=state.thresholds,
        sources_loaded={"settlements": True, "books": True, "gstr2b": True},
    )
    score = compute_readiness_score(gates)

    return {
        "has_batch": True,
        "running": state.running,
        "total": s["total"],
        "resolved": s["resolved"],
        "human_required": s["human_required"],
        "escalated": s["escalated"],
        "approved": s["approved"],
        "close_readiness_score": score,
        "unresolved_variance_paise": unresolved_variance,
        "total_itc_risk_paise": total_itc_risk,
        "activity": batch.activity[-50:],
        "summary": s,
    }
