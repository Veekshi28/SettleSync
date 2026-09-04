"""Close-gate evaluation against configurable, session-persisted thresholds."""
from typing import Optional

from fastapi import APIRouter

from core.close_gate import run_close_gates, compute_readiness_score, can_close
from api import state

router = APIRouter()


@router.get("/api/gates")
def get_gates(
    min_match_rate: Optional[float] = None,
    max_variance: Optional[float] = None,
    max_high_risk: Optional[int] = None,
):
    if min_match_rate is not None:
        state.thresholds["min_match_rate"] = min_match_rate
    if max_variance is not None:
        state.thresholds["max_variance_paise"] = int(max_variance * 100)
    if max_high_risk is not None:
        state.thresholds["max_open_high_risk"] = max_high_risk

    if state.batch is None:
        return {"score": 0, "can_close": False, "gates": [], "blockers": []}

    gates = run_close_gates(
        batch=state.batch, ledger=state.ledger, thresholds=state.thresholds,
        sources_loaded={"settlements": True, "books": True, "gstr2b": True},
    )
    score = compute_readiness_score(gates)
    ready, blockers = can_close(gates)

    return {
        "score": score,
        "can_close": ready,
        "gates": [
            {
                "name": g.name, "label": g.label, "passed": g.passed,
                "message": g.message, "detail": g.detail, "severity": g.severity,
                "overridable": g.overridable,
            }
            for g in gates
        ],
        "blockers": [b.name for b in blockers],
    }
