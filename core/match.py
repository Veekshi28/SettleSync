"""
Three-way match engine — settlements vs books vs GSTR-2B.
Fully deterministic. NO LLM calls here.

A record is only "matched" (auto-resolvable) when amounts reconcile AND
GSTR-2B shows no compliance blocker. A RULE_37A or ITC_TIME_BAR record can
have identical invoice ID, GSTIN, and amount across all three sources and
still must NOT auto-close — that is the entire point of a three-way match
over a two-way (settlement vs books) one.
"""
from __future__ import annotations
from datetime import date
from typing import Optional

from core.classify import get_fy_start, ITC_DEADLINES

AMOUNT_TOLERANCE_PAISE = 100          # ₹1
FUZZY_NAME_THRESHOLD = 85
FUZZY_AMOUNT_TOLERANCE_PCT = 0.05     # 5%
FUZZY_DATE_WINDOW_DAYS = 90
TIMING_MIN_GAP_DAYS = 30


def _is_compliant(record: dict, run_date: date) -> bool:
    """GSTR-2B compliance gate: unfiled supplier or lapsed ITC blocks auto-match."""
    if not record.get("gstr_supplier_filed", True):
        return False
    invoice_date = record.get("books_invoice_date")
    if invoice_date is not None:
        fy = get_fy_start(invoice_date)
        deadline = ITC_DEADLINES.get(fy)
        if deadline and run_date > deadline:
            return False
    return True


def _date_gap_days(record: dict) -> Optional[int]:
    inv = record.get("books_invoice_date")
    settle = record.get("settlement_date")
    if inv is None or settle is None:
        return None
    return abs((settle - inv).days)


def run_three_way_match(record: dict, run_date: date = None) -> dict:
    """
    Returns {"matched": bool, "type": Optional[str], "confidence": float, "detail": str}.
    type is one of "exact", "fuzzy", "timing" when matched.
    """
    run_date = run_date or date.today()

    books_amount = record.get("books_total_paise")
    settlement_amount = record.get("settlement_amount_paise")
    gstin_settlement = record.get("vendor_gstin_settlement")
    gstin_books = record.get("vendor_gstin_books")

    no_match = {"matched": False, "type": None, "confidence": 0.0, "detail": ""}

    if books_amount is None or gstin_books is None:
        return {**no_match, "detail": "No corresponding books entry found for this invoice"}

    # GSTIN invariant (WHATBROKE Incident 001): never auto-match across
    # conflicting GSTINs, even when vendor names look identical.
    if gstin_settlement != gstin_books:
        return {**no_match, "detail":
                f"GSTIN mismatch ({gstin_settlement} vs {gstin_books}) — refusing to auto-match"}

    compliant = _is_compliant(record, run_date)

    # ── Pass 1: Exact ────────────────────────────────────────────────────
    if settlement_amount is not None and abs(settlement_amount - books_amount) <= AMOUNT_TOLERANCE_PAISE:
        if not compliant:
            return {**no_match, "detail":
                    "Invoice, GSTIN, and amount reconcile, but GSTR-2B compliance blocker present"}
        return {"matched": True, "type": "exact", "confidence": 0.99,
                "detail": "Invoice ID, GSTIN, and amount agree across settlement and books"}

    # ── Pass 2: Fuzzy vendor-name match ─────────────────────────────────
    name_settlement = record.get("vendor_name_settlement", "")
    name_books = record.get("vendor_name_books", "")
    if name_settlement and name_books and settlement_amount is not None and books_amount:
        from rapidfuzz import fuzz
        score = fuzz.token_sort_ratio(name_settlement, name_books)
        diff_pct = abs(settlement_amount - books_amount) / books_amount
        gap = _date_gap_days(record)
        if (score >= FUZZY_NAME_THRESHOLD and diff_pct < FUZZY_AMOUNT_TOLERANCE_PCT
                and gap is not None and gap <= FUZZY_DATE_WINDOW_DAYS):
            if not compliant:
                return {**no_match, "detail":
                        "Vendor name and amount reconcile, but GSTR-2B compliance blocker present"}
            return {"matched": True, "type": "fuzzy", "confidence": 0.85,
                    "detail": f"Vendor name match ({score:.0f}%), amount within tolerance"}

    # ── Pass 3: Timing-adjusted (cross-period settlement) ────────────────
    if (name_settlement and name_books and settlement_amount is not None
            and books_amount is not None
            and abs(settlement_amount - books_amount) <= AMOUNT_TOLERANCE_PAISE):
        from rapidfuzz import fuzz
        score = fuzz.token_sort_ratio(name_settlement, name_books)
        gap = _date_gap_days(record)
        if score >= FUZZY_NAME_THRESHOLD and gap is not None and gap > TIMING_MIN_GAP_DAYS:
            if not compliant:
                return {**no_match, "detail":
                        "Amount matches exactly, but GSTR-2B compliance blocker present"}
            return {"matched": True, "type": "timing", "confidence": 0.90,
                    "detail": f"Amount matches exactly, {gap}-day cross-period settlement gap"}

    return {**no_match, "detail": "No matching pass succeeded — amounts or identity do not reconcile"}
