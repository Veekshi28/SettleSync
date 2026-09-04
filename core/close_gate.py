"""
Close Gates and Close Readiness Score.

Six deterministic gates determine whether a merchant's books are safe to close.
Any blocker caps the readiness score at 65.
The controller refuses to close until all blockers are resolved or overridden
by a human with a documented justification.

NO LLM has authority to pass or fail a gate.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from core.state import BatchState, RecordState
from audit.ledger import AuditLedger


@dataclass
class GateResult:
    name: str
    label: str           # human-readable name
    passed: bool
    message: str         # one-line status
    detail: dict = field(default_factory=dict)
    severity: str = "blocker"   # "blocker" | "warning"
    overridable: bool = True    # per POLICY.md — some gates are absolute constraints

    @property
    def icon(self) -> str:
        if self.passed:
            return "✅"
        return "❌" if self.severity == "blocker" else "⚠️"


GATE_WEIGHTS = {
    "DATA_INTEGRITY":       15,
    "RECONCILIATION":       25,
    "MATERIAL_VARIANCE":    20,
    "HIGH_RISK_EXCEPTIONS": 20,
    "COMPLIANCE":           10,
    "AUDIT_INTEGRITY":      10,
}

DEFAULT_THRESHOLDS = {
    "min_match_rate":        0.85,   # 85% of records must be auto-resolved
    "max_variance_paise":    1_000_000,  # ₹10,000 — unresolved amount ceiling
    "max_open_high_risk":    0,      # zero tolerance for open RULE_37A / ITC_TIME_BAR
}


def run_close_gates(
    batch: BatchState,
    ledger: AuditLedger,
    thresholds: dict = None,
    sources_loaded: dict = None,
) -> list[GateResult]:
    """
    Run all six close gates against current batch state.
    Returns gates in order — first blocker is the stop-the-close reason.
    """
    t = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    sources = sources_loaded or {"settlements": True, "books": True, "gstr2b": True}
    summary = batch.summary()
    records = list(batch.records.values())
    total = max(summary["total"], 1)

    gates = []

    # ── GATE 1: Data Integrity ────────────────────────────────────────────
    all_loaded = all(sources.values())
    missing = [k for k, v in sources.items() if not v]
    gates.append(GateResult(
        name="DATA_INTEGRITY",
        label="Data integrity",
        passed=all_loaded,
        message="All data sources loaded and validated" if all_loaded
                else f"Missing sources: {', '.join(missing)}",
        detail={"sources": sources},
        severity="blocker",
        overridable=False,
    ))

    # ── GATE 2: Reconciliation Rate ───────────────────────────────────────
    closed_states = {RecordState.RESOLVED, RecordState.APPROVED}
    resolved = sum(1 for r in records if r.state in closed_states)
    match_rate = resolved / total
    required = t["min_match_rate"]
    gates.append(GateResult(
        name="RECONCILIATION",
        label="Reconciliation rate",
        passed=match_rate >= required,
        message=(
            f"{resolved}/{total} records resolved ({match_rate:.1%})"
            + (f" — meets {required:.0%} threshold" if match_rate >= required
               else f" — below {required:.0%} threshold")
        ),
        detail={"resolved": resolved, "total": total,
                "match_rate": round(match_rate, 4), "threshold": required},
        severity="blocker",
    ))

    # ── GATE 3: Material Variance ─────────────────────────────────────────
    open_states = {RecordState.EXCEPTION, RecordState.AI_REVIEW, RecordState.HUMAN_REQUIRED}
    unresolved_paise = sum(
        r.raw.get("settlement_amount_paise", 0)
        for r in records if r.state in open_states
    )
    variance_ceiling = t["max_variance_paise"]
    gates.append(GateResult(
        name="MATERIAL_VARIANCE",
        label="Material variance",
        passed=unresolved_paise <= variance_ceiling,
        message=(
            f"₹{unresolved_paise / 100:,.2f} unresolved"
            + (" — within tolerance" if unresolved_paise <= variance_ceiling
               else f" — exceeds ₹{variance_ceiling / 100:,.0f} threshold")
        ),
        detail={"unresolved_paise": unresolved_paise,
                "ceiling_paise": variance_ceiling,
                "unresolved_count": sum(1 for r in records if r.state in open_states)},
        severity="blocker",
    ))

    # ── GATE 4: High-Risk Exceptions ─────────────────────────────────────
    # RULE_37A and ITC_TIME_BAR are legal compliance issues — zero tolerance
    high_risk_classes = {"RULE_37A", "ITC_TIME_BAR"}
    terminal = {RecordState.APPROVED, RecordState.REJECTED, RecordState.ESCALATED}
    open_high_risk = [
        r for r in records
        if r.exception_class in high_risk_classes and r.state not in terminal
    ]
    max_open = t["max_open_high_risk"]
    gates.append(GateResult(
        name="HIGH_RISK_EXCEPTIONS",
        label="Compliance exceptions",
        passed=len(open_high_risk) <= max_open,
        message=(
            "No open RULE_37A / ITC_TIME_BAR exceptions" if not open_high_risk
            else f"{len(open_high_risk)} compliance exceptions require human decision"
        ),
        detail={
            "open_count": len(open_high_risk),
            "records": [r.record_id for r in open_high_risk],
        },
        severity="blocker",
    ))

    # ── GATE 5: Compliance (Rule 37A resolved) ────────────────────────────
    # Specifically RULE_37A: must be acknowledged by a human, not just AI-reviewed
    rule37a_unreviewed = [
        r for r in records
        if r.exception_class == "RULE_37A"
        and r.human_action is None
    ]
    gates.append(GateResult(
        name="COMPLIANCE",
        label="Rule 37A review",
        passed=len(rule37a_unreviewed) == 0,
        message=(
            "All Rule 37A exceptions reviewed" if not rule37a_unreviewed
            else f"{len(rule37a_unreviewed)} Rule 37A record(s) need human sign-off"
        ),
        detail={"count": len(rule37a_unreviewed)},
        severity="blocker",
        overridable=False,
    ))

    # ── GATE 6: Audit Integrity ───────────────────────────────────────────
    intact, broken_at = ledger.verify()
    gates.append(GateResult(
        name="AUDIT_INTEGRITY",
        label="Audit chain",
        passed=intact,
        message=(
            f"{len(ledger)} events verified — chain intact"
            if intact else f"Chain broken at event #{broken_at}"
        ),
        detail={"intact": intact, "broken_at": broken_at, "event_count": len(ledger)},
        severity="blocker",
        overridable=False,
    ))

    return gates


def compute_readiness_score(gates: list[GateResult]) -> int:
    """
    Close Readiness Score: 0–100.

    - Each gate contributes its weight when passing.
    - Any blocker caps the score at 65 (not closeable regardless of other gates).
    - Score of 100 means all gates pass — books are ready to close.
    """
    score = sum(GATE_WEIGHTS.get(g.name, 10) for g in gates if g.passed)
    has_blocker = any(not g.passed and g.severity == "blocker" for g in gates)
    if has_blocker:
        score = min(score, 65)
    return score


def can_close(gates: list[GateResult]) -> tuple[bool, list[GateResult]]:
    """
    Returns (ready: bool, blockers: list[GateResult]).
    The controller refuses to close if any blocker gate fails.
    """
    blockers = [g for g in gates if not g.passed and g.severity == "blocker"]
    return len(blockers) == 0, blockers