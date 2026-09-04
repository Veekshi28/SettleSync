"""
Batch run history — SQLite-backed, so the Control Tower can show
month-over-month trends across reconciliation runs.

Every operation is wrapped in try/except: history is a convenience feature,
never a blocker. If SQLite is unavailable for any reason, callers get an
empty list / no-op rather than a crash.
"""
import sqlite3
import time
from pathlib import Path
from typing import Optional

DB_PATH = Path("audit/batch_history.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS batch_runs (
    run_id TEXT PRIMARY KEY,
    run_date TEXT,
    total_records INT,
    resolved_count INT,
    exception_count INT,
    human_reviews INT,
    close_readiness_score INT,
    total_itc_risk_paise INT,
    match_rate REAL,
    unsafe_closure_rate REAL,
    closed_at TEXT,
    override_used INT DEFAULT 0
)
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(_SCHEMA)
    return conn


def save_run(
    run_id: str,
    total_records: int,
    resolved_count: int,
    exception_count: int,
    human_reviews: int,
    close_readiness_score: int,
    total_itc_risk_paise: int,
    match_rate: float,
    unsafe_closure_rate: float = 0.0,
) -> None:
    try:
        conn = _connect()
        conn.execute(
            """INSERT OR REPLACE INTO batch_runs
               (run_id, run_date, total_records, resolved_count, exception_count,
                human_reviews, close_readiness_score, total_itc_risk_paise,
                match_rate, unsafe_closure_rate, closed_at, override_used)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                       COALESCE((SELECT closed_at FROM batch_runs WHERE run_id = ?), NULL),
                       COALESCE((SELECT override_used FROM batch_runs WHERE run_id = ?), 0))""",
            (run_id, time.strftime("%Y-%m-%dT%H:%M:%S"), total_records, resolved_count,
             exception_count, human_reviews, close_readiness_score, total_itc_risk_paise,
             match_rate, unsafe_closure_rate, run_id, run_id),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def mark_closed(run_id: Optional[str]) -> None:
    if not run_id:
        return
    try:
        conn = _connect()
        conn.execute(
            "UPDATE batch_runs SET closed_at = ? WHERE run_id = ?",
            (time.strftime("%Y-%m-%dT%H:%M:%S"), run_id),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def mark_override_used(run_id: Optional[str]) -> None:
    if not run_id:
        return
    try:
        conn = _connect()
        conn.execute("UPDATE batch_runs SET override_used = 1 WHERE run_id = ?", (run_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass


def recent_runs(n: int = 6) -> list[dict]:
    try:
        conn = _connect()
        cur = conn.execute(
            "SELECT * FROM batch_runs ORDER BY run_date DESC LIMIT ?", (n,)
        )
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        conn.close()
        return list(reversed(rows))  # oldest → newest, for trend charts
    except Exception:
        return []
