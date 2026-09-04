"""
Tests for the 6 controller features added on top of the core pipeline.
"""
import tempfile
from datetime import date

import pytest

from core.classify import classify
from core.grouping import group_exceptions
from core.state import BatchState, RecordState
from core.close_gate import run_close_gates
from core.pdf_export import build_close_pack
from audit.ledger import AuditLedger


# ── Feature 1: ITC risk computation ─────────────────────────────────────────

@pytest.mark.parametrize(
    "exception_class,supplier_filed,invoice_date,run_date,settlement_amount,books_amount,"
    "gstr_amount,expected_risk_paise",
    [
        # RULE_37A: full ITC (gstr amount) at risk
        ("RULE_37A", False, date(2025, 6, 15), None, 100000, 100000, 100000, 100000),
        # ITC_TIME_BAR: full ITC (gstr amount) permanently lapsed
        ("ITC_TIME_BAR", True, date(2024, 8, 10), date(2025, 12, 5), 200000, 200000, 200000, 200000),
        # AMOUNT_MISMATCH: risk = abs(settlement - books)
        ("AMOUNT_MISMATCH", True, date(2025, 5, 1), None, 99000, 100000, 100000, 1000),
        # TIMING_DIFF: zero risk
        ("TIMING_DIFF", True, date(2025, 3, 31), date(2025, 4, 10), 150000, 150000, 150000, 0),
        # MISSING_ENTRY: risk = full settlement amount (unbooked exposure)
        ("MISSING_ENTRY", True, None, None, 80000, None, 80000, 80000),
    ],
)
def test_itc_risk_computation(
    exception_class, supplier_filed, invoice_date, run_date,
    settlement_amount, books_amount, gstr_amount, expected_risk_paise,
):
    result = classify(
        record_id="TEST-RISK",
        settlement_amount_paise=settlement_amount,
        books_amount_paise=books_amount,
        gstr_amount_paise=gstr_amount,
        invoice_date=invoice_date,
        settlement_date=date(2025, 7, 1),
        vendor_gstin_settlement="27AADCT2765Q1ZO",
        vendor_gstin_books="27AADCT2765Q1ZO",
        supplier_filed=supplier_filed,
        run_date=run_date,
    )
    assert result.exception_class == exception_class
    assert result.itc_risk_paise == expected_risk_paise
    assert result.itc_risk_label  # never empty


# ── Feature 4: Smart exception grouping ─────────────────────────────────────

def _make_entry(record_id, exception_class, raw, itc_risk_paise=0):
    entry = BatchState().add(record_id, raw=raw)
    entry.exception_class = exception_class
    entry.itc_risk_paise = itc_risk_paise
    return entry


def test_grouping_same_vendor_rule37a_forms_one_cluster():
    gstin = "27AADCT2765Q1ZO"
    entries = [
        _make_entry(f"pay_{i}", "RULE_37A", {
            "vendor_gstin_settlement": gstin,
            "vendor_name_books": "Tata Consultancy Services Ltd",
        }, itc_risk_paise=10000)
        for i in range(3)
    ]

    groups, ungrouped = group_exceptions(entries)

    assert len(groups) == 1
    assert groups[0].group_type == "vendor_class"
    assert groups[0].count == 3
    assert groups[0].total_itc_risk_paise == 30000
    assert ungrouped == []


def test_grouping_leaves_singleton_ungrouped():
    entries = [_make_entry("pay_1", "RULE_37A", {
        "vendor_gstin_settlement": "27AADCT2765Q1ZO",
        "vendor_name_books": "Solo Vendor",
    })]
    groups, ungrouped = group_exceptions(entries)
    assert groups == []
    assert len(ungrouped) == 1


# ── Feature 2: Configurable close gate thresholds ───────────────────────────

def test_lowering_min_match_rate_passes_reconciliation_gate():
    from core.ingest import load_all
    from core.normalize import normalize_all
    from core.match import run_three_way_match

    raw = load_all(
        "data/synthetic/settlements.csv",
        "data/synthetic/books.csv",
        "data/synthetic/gstr2b.csv",
    )
    normalized = normalize_all(raw)

    batch = BatchState()
    for r in normalized:
        entry = batch.add(r["record_id"], raw=r)
        match = run_three_way_match(r, run_date=date(2025, 10, 1))
        if match["matched"]:
            entry.transition(RecordState.INGESTED)
            entry.transition(RecordState.NORMALIZED)
            entry.transition(RecordState.MATCHING)
            entry.transition(RecordState.RESOLVED)

    ledger = AuditLedger(path=tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False).name)

    gates_default = run_close_gates(batch=batch, ledger=ledger, thresholds={"min_match_rate": 0.85})
    reconciliation_default = next(g for g in gates_default if g.name == "RECONCILIATION")
    assert reconciliation_default.passed is False   # ~52% match rate < 85%

    gates_lowered = run_close_gates(batch=batch, ledger=ledger, thresholds={"min_match_rate": 0.50})
    reconciliation_lowered = next(g for g in gates_lowered if g.name == "RECONCILIATION")
    assert reconciliation_lowered.passed is True     # ~52% match rate >= 50%


# ── Feature 6: PDF close pack export ────────────────────────────────────────

def test_pdf_close_pack_generates_and_has_content():
    ledger = AuditLedger(path=tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False).name)
    ledger.append("BATCH_START")
    ledger.append("BATCH_COMPLETE", detail={"total": 77})
    intact, _ = ledger.verify()

    from core.close_gate import GateResult
    gates = [
        GateResult(name="DATA_INTEGRITY", label="Data integrity", passed=True, message="ok"),
        GateResult(name="RECONCILIATION", label="Reconciliation rate", passed=False, message="52%"),
    ]

    pdf_bytes = build_close_pack(
        merchant_gstin="27AADCM9876R1ZX",
        score=65,
        status="CONDITIONALLY CLOSED",
        total_records=77,
        resolved_count=40,
        human_reviewed=37,
        exceptions_remaining=37,
        total_itc_risk_paise=1_234_500,
        gate_results=gates,
        exception_classes={"RULE_37A": 8, "AMOUNT_MISMATCH": 12},
        itc_at_risk_by_class={"RULE_37A": 800000, "AMOUNT_MISMATCH": 120000},
        ledger_event_count=len(ledger),
        chain_intact=intact,
        final_hash=ledger.recent(1)[0].current_hash,
        override_justification="Variance confirmed against bank statement.",
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1024
    assert pdf_bytes[:4] == b"%PDF"
