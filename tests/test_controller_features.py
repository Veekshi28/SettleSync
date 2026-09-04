"""
Tests for the 5 controller-intelligence features: Ask the Controller,
pre-flight scan, resolution playbooks, confidence calibration, and the
GSTR-2B pending state.
"""
from datetime import date

from fastapi.testclient import TestClient

from core.classify import classify
from core.close_gate import run_close_gates
from core.playbook import get_playbook
from core.state import BatchState, RecordState
from audit.ledger import AuditLedger


# ── Feature 1: Ask the Controller ───────────────────────────────────────────

def test_ask_controller_no_batch():
    from api.main import app
    from api import state as api_state

    api_state.batch = None
    client = TestClient(app)
    resp = client.post("/api/query", json={"question": "What's blocking close?"})

    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["answer"], str)
    assert body["used_llm"] is False


# ── Feature 3: Resolution playbooks ──────────────────────────────────────────

def test_playbook_rule_37a_has_4_steps():
    steps = get_playbook("RULE_37A")
    assert len(steps) == 4
    assert all("action" in s and "mandatory" in s for s in steps)


def test_playbook_unknown_class_returns_empty():
    assert get_playbook("NOT_A_REAL_CLASS") == []


# ── Feature 5: GSTR-2B pending state ─────────────────────────────────────────

def test_gstr2b_pending_before_14th():
    result = classify(
        record_id="TEST-PENDING",
        settlement_amount_paise=100000,
        books_amount_paise=100000,
        gstr_amount_paise=100000,
        invoice_date=date(2026, 3, 5),
        settlement_date=date(2026, 3, 6),
        vendor_gstin_settlement="27AADCT2765Q1ZO",
        vendor_gstin_books="27AADCT2765Q1ZO",
        supplier_filed=True,
        run_date=date(2026, 3, 5),   # same month as invoice, day < 14
    )
    assert result.exception_class == "GSTR2B_PENDING"
    assert result.itc_risk_paise == 0


def test_gstr2b_pending_not_triggered_after_14th():
    result = classify(
        record_id="TEST-NOT-PENDING",
        settlement_amount_paise=100000,
        books_amount_paise=100000,
        gstr_amount_paise=100000,
        invoice_date=date(2026, 3, 5),
        settlement_date=date(2026, 3, 6),
        vendor_gstin_settlement="27AADCT2765Q1ZO",
        vendor_gstin_books="27AADCT2765Q1ZO",
        supplier_filed=True,
        run_date=date(2026, 3, 20),  # same month, but past the 14th
    )
    assert result.exception_class != "GSTR2B_PENDING"


def test_gstr2b_pending_not_high_risk():
    batch = BatchState()
    entry = batch.add("pay_pending_1", raw={"settlement_amount_paise": 50000})
    entry.exception_class = "GSTR2B_PENDING"
    entry.state = RecordState.HUMAN_REQUIRED

    ledger = AuditLedger(path="audit/_test_ledger_pending.jsonl")
    try:
        gates = run_close_gates(batch=batch, ledger=ledger, thresholds={"max_open_high_risk": 0})
        high_risk_gate = next(g for g in gates if g.name == "HIGH_RISK_EXCEPTIONS")
        assert high_risk_gate.passed is True
        assert high_risk_gate.detail["open_count"] == 0
    finally:
        import os
        if os.path.exists("audit/_test_ledger_pending.jsonl"):
            os.remove("audit/_test_ledger_pending.jsonl")


# ── Feature 4: Confidence calibration ────────────────────────────────────────

def test_calibration_in_evaluation_report():
    from evaluation.run import evaluate

    result = evaluate()
    assert "confidence_calibration" in result
    assert len(result["confidence_calibration"]) == 4
    assert "calibration_quality" in result
    for bucket in result["confidence_calibration"]:
        assert "bucket" in bucket and "count" in bucket and "precision" in bucket
