"""
Finite State Machine for SettleSync batch records.
NO LLM is allowed to call .transition() directly.
Only deterministic tools and human actions may change state.
"""
from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import time


class RecordState(Enum):
    UPLOADED       = "UPLOADED"
    INGESTED       = "INGESTED"
    NORMALIZED     = "NORMALIZED"
    MATCHING       = "MATCHING"
    RESOLVED       = "RESOLVED"        # terminal: auto-matched
    EXCEPTION      = "EXCEPTION"
    AI_REVIEW      = "AI_REVIEW"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    APPROVED       = "APPROVED"        # terminal: human approved
    REJECTED       = "REJECTED"        # terminal: human rejected
    ESCALATED      = "ESCALATED"       # terminal: needs senior review


TERMINAL = {
    RecordState.RESOLVED,
    RecordState.APPROVED,
    RecordState.REJECTED,
    RecordState.ESCALATED,
}

VALID_TRANSITIONS: dict[RecordState, set[RecordState]] = {
    RecordState.UPLOADED:       {RecordState.INGESTED},
    RecordState.INGESTED:       {RecordState.NORMALIZED},
    RecordState.NORMALIZED:     {RecordState.MATCHING},
    RecordState.MATCHING:       {RecordState.RESOLVED, RecordState.EXCEPTION},
    RecordState.EXCEPTION:      {RecordState.AI_REVIEW},
    RecordState.AI_REVIEW:      {RecordState.HUMAN_REQUIRED},
    RecordState.HUMAN_REQUIRED: {RecordState.APPROVED, RecordState.REJECTED, RecordState.ESCALATED},
    RecordState.RESOLVED:       set(),
    RecordState.APPROVED:       set(),
    RecordState.REJECTED:       set(),
    RecordState.ESCALATED:      set(),
}


@dataclass
class RecordEntry:
    record_id: str
    state: RecordState = RecordState.UPLOADED
    # Match results
    match_type: Optional[str] = None       # "exact" | "fuzzy" | "timing"
    match_confidence: float = 0.0
    # Exception details
    exception_class: Optional[str] = None
    exception_narrative: Optional[str] = None
    exception_rule: Optional[str] = None
    exception_hint: Optional[str] = None
    exception_confidence: float = 0.0
    itc_risk_paise: int = 0
    itc_risk_label: str = ""
    playbook_completed: dict = field(default_factory=dict)  # {step_number: {"ts": str, "note": str}}
    # Human action
    human_action: Optional[str] = None    # "approved" | "rejected" | "escalated"
    human_note: Optional[str] = None
    # Raw data (set during ingestion)
    raw: dict = field(default_factory=dict)
    history: list = field(default_factory=list)

    def transition(self, to: RecordState, actor: str = "system") -> None:
        allowed = VALID_TRANSITIONS.get(self.state, set())
        if to not in allowed:
            raise ValueError(
                f"[FSM] Invalid transition for {self.record_id}: "
                f"{self.state.value} → {to.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )
        self.history.append({
            "from": self.state.value,
            "to": to.value,
            "actor": actor,
            "ts": time.strftime("%H:%M:%S"),
        })
        self.state = to

    def is_terminal(self) -> bool:
        return self.state in TERMINAL

    @property
    def status_label(self) -> str:
        labels = {
            RecordState.RESOLVED:       "✅ Resolved",
            RecordState.APPROVED:       "✅ Approved",
            RecordState.REJECTED:       "❌ Rejected",
            RecordState.ESCALATED:      "🔺 Escalated",
            RecordState.HUMAN_REQUIRED: "⏳ Needs review",
            RecordState.AI_REVIEW:      "🤖 AI reviewing",
            RecordState.MATCHING:       "🔄 Matching",
            RecordState.NORMALIZED:     "🔄 Normalized",
            RecordState.INGESTED:       "🔄 Ingested",
            RecordState.UPLOADED:       "📥 Uploaded",
            RecordState.EXCEPTION:      "⚠️ Exception",
        }
        return labels.get(self.state, self.state.value)


class BatchState:
    def __init__(self):
        self.records: dict[str, RecordEntry] = {}
        self.activity: list[dict] = []   # observable tool-call log for UI

    def add(self, record_id: str, raw: dict = None) -> RecordEntry:
        e = RecordEntry(record_id=record_id, raw=raw or {})
        self.records[record_id] = e
        return e

    def log(self, record_id: str, action: str, detail: str = "") -> None:
        self.activity.append({
            "ts": time.strftime("%H:%M:%S"),
            "record_id": record_id,
            "action": action,
            "detail": detail,
        })

    def summary(self) -> dict:
        all_entries = list(self.records.values())
        match_types = [e.match_type for e in all_entries if e.match_type]
        exc_classes  = [e.exception_class for e in all_entries if e.exception_class]
        return {
            "total":           len(all_entries),
            "resolved":        sum(1 for e in all_entries if e.state == RecordState.RESOLVED),
            "approved":        sum(1 for e in all_entries if e.state == RecordState.APPROVED),
            "human_required":  sum(1 for e in all_entries if e.state == RecordState.HUMAN_REQUIRED),
            "escalated":       sum(1 for e in all_entries if e.state == RecordState.ESCALATED),
            "rejected":        sum(1 for e in all_entries if e.state == RecordState.REJECTED),
            "match_types":     {t: match_types.count(t) for t in set(match_types)},
            "exception_classes": {c: exc_classes.count(c) for c in set(exc_classes)},
        }