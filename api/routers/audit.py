"""Ledger inspection, chain verification, evaluation results, and batch history."""
import json
from pathlib import Path

from fastapi import APIRouter

from audit import batch_history
from api import state

router = APIRouter()


@router.get("/api/audit/events")
def audit_events(n: int = 25):
    events = state.ledger.recent(n)
    return [
        {
            "seq": e.seq, "timestamp": e.timestamp, "action": e.action,
            "record_id": e.record_id, "detail": e.detail, "current_hash": e.current_hash,
        }
        for e in reversed(events)
    ]


@router.get("/api/audit/verify")
def audit_verify():
    intact, broken_at = state.ledger.verify()
    return {"intact": intact, "broken_at": broken_at, "event_count": len(state.ledger)}


@router.get("/api/evaluation")
def get_evaluation():
    path = Path("evaluation/results/latest.json")
    if not path.exists():
        return {"error": "Run python -m evaluation.run first"}
    with open(path) as f:
        return json.load(f)


@router.get("/api/history")
def get_history(n: int = 12):
    return batch_history.recent_runs(n)
