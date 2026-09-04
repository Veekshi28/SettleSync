"""
Record listing, human review actions, and exception grouping.
All state changes go through RecordEntry.transition() and the audit ledger —
this layer never mutates state directly.
"""
import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.state import RecordState
from core.grouping import group_exceptions
from core.playbook import get_playbook
from api import state

router = APIRouter()


def _iso(d):
    return d.isoformat() if d else None


def _serialize(entry) -> dict:
    r = entry.raw
    return {
        "record_id": entry.record_id,
        "match_type": entry.match_type,
        "confidence": entry.match_confidence,
        "exception_class": entry.exception_class,
        "exception_narrative": entry.exception_narrative,
        "itc_risk_paise": entry.itc_risk_paise,
        "itc_risk_label": entry.itc_risk_label,
        "state": entry.state.value,
        "status_label": entry.status_label,
        "settlement_amount_paise": r.get("settlement_amount_paise"),
        "books_amount_paise": r.get("books_total_paise"),
        "gstr_amount_paise": r.get("gstr_total_paise"),
        "vendor_name": r.get("vendor_name_books") or "",
        "vendor_gstin": r.get("vendor_gstin_settlement") or "",
        "invoice_date": _iso(r.get("books_invoice_date")),
        "settlement_date": _iso(r.get("settlement_date")),
        "human_action": entry.human_action,
        "exception_rule": entry.exception_rule,
        "exception_hint": entry.exception_hint,
    }


STATUS_FILTERS = {
    "resolved": {RecordState.RESOLVED},
    "exception": {
        RecordState.EXCEPTION, RecordState.AI_REVIEW, RecordState.HUMAN_REQUIRED,
        RecordState.APPROVED, RecordState.REJECTED, RecordState.ESCALATED,
    },
    "human_required": {RecordState.HUMAN_REQUIRED},
}


@router.get("/api/records")
def list_records(status: str = "all", exc_class: Optional[str] = None):
    if state.batch is None:
        return []
    entries = list(state.batch.records.values())
    allowed = STATUS_FILTERS.get(status)
    if allowed is not None:
        entries = [e for e in entries if e.state in allowed]
    if exc_class:
        entries = [e for e in entries if e.exception_class == exc_class]
    return [_serialize(e) for e in entries]


GROUP_TYPE_LABELS = {
    "vendor_class": "vendor",
    "date_cluster": "temporal",
    "tds_cluster": "tds_rate",
}


@router.get("/api/exceptions")
def list_exceptions(grouped: bool = False, exc_class: Optional[str] = None):
    if state.batch is None:
        return []
    entries = [e for e in state.batch.records.values() if e.exception_class is not None]
    if exc_class:
        entries = [e for e in entries if e.exception_class == exc_class]

    if not grouped:
        return [_serialize(e) for e in entries]

    groups, ungrouped = group_exceptions(entries)
    result = []
    for g in groups:
        members = [state.batch.records[rid] for rid in g.record_ids]
        result.append({
            "group_type": GROUP_TYPE_LABELS.get(g.group_type, g.group_type),
            "label": g.title,
            "record_count": g.count,
            "total_risk_paise": g.total_itc_risk_paise,
            "recommended_action": g.recommended_action,
            "records": [_serialize(e) for e in members],
        })
    if ungrouped:
        result.append({
            "group_type": "ungrouped",
            "label": f"{len(ungrouped)} exception(s) with no matching pattern",
            "record_count": len(ungrouped),
            "total_risk_paise": sum(e.itc_risk_paise for e in ungrouped),
            "recommended_action": "No shared pattern detected — review individually.",
            "records": [_serialize(e) for e in ungrouped],
        })
    return result


class ActionBody(BaseModel):
    action: str
    note: str = ""


ACTION_MAP = {
    "approve": (RecordState.APPROVED, "approved", "human_approved"),
    "reject": (RecordState.REJECTED, "rejected", "human_rejected"),
    "escalate": (RecordState.ESCALATED, "escalated", "human_escalated"),
}


@router.post("/api/records/{record_id}/action")
def record_action(record_id: str, body: ActionBody):
    if state.batch is None:
        raise HTTPException(404, "No batch loaded")
    entry = state.batch.records.get(record_id)
    if entry is None:
        raise HTTPException(404, "Record not found")
    if body.action not in ACTION_MAP:
        raise HTTPException(400, "Invalid action — must be approve, reject, or escalate")

    new_state, human_action_label, ledger_action = ACTION_MAP[body.action]
    try:
        entry.transition(new_state, actor="human")
    except ValueError as e:
        raise HTTPException(400, str(e))

    entry.human_action = human_action_label
    entry.human_note = body.note
    ev = state.ledger.append(ledger_action, record_id, actor="human", note=body.note)

    return {"ok": True, "new_state": new_state.value, "ledger_seq": ev.seq}


@router.get("/api/records/{record_id}/playbook")
def record_playbook(record_id: str):
    if state.batch is None:
        raise HTTPException(404, "No batch loaded")
    entry = state.batch.records.get(record_id)
    if entry is None:
        raise HTTPException(404, "Record not found")

    return {
        "exception_class": entry.exception_class,
        "steps": get_playbook(entry.exception_class),
        "completed_steps": sorted(entry.playbook_completed.keys()),
        "completed_details": entry.playbook_completed,
    }


class PlaybookStepBody(BaseModel):
    note: str = ""


@router.post("/api/records/{record_id}/playbook/{step_number}/complete")
def complete_playbook_step(record_id: str, step_number: int, body: PlaybookStepBody):
    if state.batch is None:
        raise HTTPException(404, "No batch loaded")
    entry = state.batch.records.get(record_id)
    if entry is None:
        raise HTTPException(404, "Record not found")

    steps = get_playbook(entry.exception_class)
    if not any(s["step"] == step_number for s in steps):
        raise HTTPException(400, f"Step {step_number} does not exist for {entry.exception_class}")

    state.ledger.append(
        "playbook_step_complete", record_id,
        step=step_number, exception_class=entry.exception_class, note=body.note,
    )
    entry.playbook_completed[step_number] = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "note": body.note,
    }

    return {"ok": True, "completed_steps": sorted(entry.playbook_completed.keys())}
