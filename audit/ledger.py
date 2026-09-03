"""
Hash-chained append-only audit ledger.
Every state transition and human action is recorded here.
sha256(seq || prev_hash || canonical(event)) — tamper-evident.
"""
import hashlib
import json
import time
from dataclasses import dataclass, asdict
from typing import Optional
from pathlib import Path


@dataclass
class LedgerEvent:
    seq: int
    timestamp: str
    action: str
    record_id: Optional[str]
    detail: dict
    prev_hash: str
    current_hash: str = ""   # filled in by append()


def _canonical(e: LedgerEvent) -> str:
    """Deterministic serialization — excludes current_hash."""
    return json.dumps({
        "seq":       e.seq,
        "timestamp": e.timestamp,
        "action":    e.action,
        "record_id": e.record_id,
        "detail":    e.detail,
        "prev_hash": e.prev_hash,
    }, sort_keys=True, ensure_ascii=True)


class AuditLedger:
    GENESIS = "0" * 64

    def __init__(self, path: str = "audit/ledger.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._events: list[LedgerEvent] = []
        self._prev_hash = self.GENESIS

        if self.path.exists():
            self._load()

    def _load(self):
        with open(self.path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                e = LedgerEvent(**json.loads(line))
                self._events.append(e)
        if self._events:
            self._prev_hash = self._events[-1].current_hash

    def append(
        self,
        action: str,
        record_id: Optional[str] = None,
        **detail,
    ) -> LedgerEvent:
        e = LedgerEvent(
            seq=len(self._events),
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            action=action,
            record_id=record_id,
            detail=detail,
            prev_hash=self._prev_hash,
        )
        e.current_hash = hashlib.sha256(_canonical(e).encode()).hexdigest()
        self._prev_hash = e.current_hash
        self._events.append(e)

        with open(self.path, "a") as f:
            f.write(json.dumps(asdict(e)) + "\n")

        return e

    def verify(self) -> tuple[bool, Optional[int]]:
        """
        Returns (intact: bool, broken_at_seq: Optional[int]).
        Checks both link integrity (prev_hash chain) and hash correctness.
        """
        prev = self.GENESIS
        for e in self._events:
            if e.prev_hash != prev:
                return False, e.seq
            expected = hashlib.sha256(_canonical(e).encode()).hexdigest()
            if e.current_hash != expected:
                return False, e.seq
            prev = e.current_hash
        return True, None

    def recent(self, n: int = 25) -> list[LedgerEvent]:
        return self._events[-n:]

    def __len__(self) -> int:
        return len(self._events)