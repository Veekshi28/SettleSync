"""
Shared in-memory singletons for the API layer.

No business logic lives here — only wiring to the existing core/ and audit/
modules. `batch` and the threshold/close flags are per-process, in-memory
state, acceptable for this single-user demo (per CLAUDE.md: this is a
working demo, not production software).

Note: audit/batch_history.py exposes a function-based API (save_run,
mark_closed, mark_override_used, recent_runs) against a fixed DB path,
not a BatchHistory class — that module's business logic is frozen, so
this layer calls its functions directly rather than wrapping it in a
class that doesn't exist.
"""
import threading
from typing import Optional

from core.state import BatchState
from audit.ledger import AuditLedger

batch: Optional[BatchState] = None
running: bool = False
current_run_id: Optional[str] = None
close_authorized: bool = False
close_override_justification: Optional[str] = None

ledger = AuditLedger("audit/ledger.jsonl")

thresholds: dict = {
    "min_match_rate": 0.85,
    "max_variance_paise": 1_000_000,
    "max_open_high_risk": 0,
}

# Guards writes to `batch`/`running` from the background reconciliation thread
# against concurrent request handlers. Reads are not locked — acceptable for
# a single-user demo where staleness is at most one poll interval.
lock = threading.Lock()
