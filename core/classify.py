"""
Exception classifier — ICAI-cited mismatch taxonomy.
All logic is deterministic. NO LLM calls here.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional


# ITC Section 16(4): must avail ITC by November 30 of following FY, or GSTR-9 date.
# FY2024-25 deadline: 2025-11-30
# FY2025-26 deadline: 2026-11-30
ITC_DEADLINES: dict[int, date] = {
    2024: date(2025, 11, 30),
    2025: date(2026, 11, 30),
    2026: date(2027, 11, 30),
}

TDS_RATES = {
    "194C":           0.010,   # contractor payments
    "194C_transport": 0.020,
    "194J":           0.100,   # professional services
}
TDS_TOLERANCE_PAISE = 200   # ₹2 rounding tolerance


@dataclass
class ExceptionResult:
    exception_class: str       # one of the 5 canonical classes
    confidence: float          # 0.0–1.0
    explanation: str           # human-readable cause
    icai_citation: str         # exact rule reference
    resolution_hint: str       # what to do about it


def get_fy_start(d: date) -> int:
    """Return financial year start year: Apr 2025 → 2025, Jan 2025 → 2024."""
    return d.year - 1 if d.month <= 3 else d.year


def classify(
    record_id: str,
    settlement_amount_paise: Optional[int],
    books_amount_paise: Optional[int],
    gstr_amount_paise: Optional[int],
    invoice_date: Optional[date],
    settlement_date: Optional[date],
    vendor_gstin_settlement: Optional[str],
    vendor_gstin_books: Optional[str],
    supplier_filed: bool = True,
    run_date: Optional[date] = None,
) -> ExceptionResult:

    run_date = run_date or date.today()

    # ── Rule 1: Supplier hasn't filed GSTR-3B → mandatory Rule 37A reversal ──
    if not supplier_filed:
        return ExceptionResult(
            exception_class="RULE_37A",
            confidence=0.98,
            explanation=(
                f"Supplier (GSTIN: {vendor_gstin_settlement}) has not filed GSTR-3B. "
                "ITC on this invoice is not reflected in GSTR-2B and must be reversed."
            ),
            icai_citation=(
                "CGST Rule 37A (inserted w.e.f. 26 Dec 2022) — ITC reversal mandatory "
                "when supplier fails to file GSTR-3B within 2 months of the due date for "
                "that return period. Cited in ICAI GSTR-9C Technical Guide (Dec 2025), "
                "para on 'Rule 37A Compliance Checks'."
            ),
            resolution_hint=(
                "Reverse ITC in the current GSTR-3B. Re-avail if supplier files within "
                "Section 16(4) time limit. Flag in GSTR-9C Part II reconciliation."
            ),
        )

    # ── Rule 2: ITC time-bar (Section 16(4)) ─────────────────────────────────
    if invoice_date is not None:
        fy = get_fy_start(invoice_date)
        deadline = ITC_DEADLINES.get(fy)
        if deadline and run_date > deadline:
            return ExceptionResult(
                exception_class="ITC_TIME_BAR",
                confidence=0.99,
                explanation=(
                    f"Invoice dated {invoice_date} belongs to FY{fy}-{fy + 1}. "
                    f"The ITC claim deadline was {deadline} and has passed. "
                    "ITC on this invoice is permanently lapsed."
                ),
                icai_citation=(
                    "CGST Act Section 16(4) — ITC must be availed by 30 November "
                    "following the financial year end, or the date of filing GSTR-9, "
                    "whichever is earlier. ICAI GSTR-9C Technical Guide (Dec 2025), "
                    "Part V: 'Reconciliation of ITC — Time-barred Credits'."
                ),
                resolution_hint=(
                    "Do NOT re-avail this ITC. Disclose the lapsed credit in "
                    "GSTR-9 Part V. If liability has crystallised, file DRC-03. "
                    "Consult CA before closing."
                ),
            )

    # ── Rule 3: Amount mismatch (check for TDS pattern) ──────────────────────
    if (settlement_amount_paise is not None and
            books_amount_paise is not None and
            books_amount_paise > 0):

        diff = books_amount_paise - settlement_amount_paise  # positive = books > settlement
        diff_pct = abs(diff) / books_amount_paise

        if diff_pct > 0.001:   # > 0.1% after rounding noise
            # Check if diff matches a known TDS rate
            tds_match = None
            for tds_name, rate in TDS_RATES.items():
                expected_tds = int(books_amount_paise * rate)
                if abs(diff - expected_tds) <= TDS_TOLERANCE_PAISE:
                    tds_match = tds_name
                    break

            return ExceptionResult(
                exception_class="AMOUNT_MISMATCH",
                confidence=0.92 if tds_match else 0.72,
                explanation=(
                    f"Settlement ₹{settlement_amount_paise/100:.2f} vs "
                    f"Books ₹{books_amount_paise/100:.2f} — "
                    f"difference of ₹{diff/100:.2f} ({diff_pct:.1%}). "
                    + (
                        f"Difference is consistent with TDS deduction at "
                        f"{TDS_RATES[tds_match]:.0%} (Section {tds_match})."
                        if tds_match else
                        "Cause unclear — may be refund, dispute credit, or adjustment."
                    )
                ),
                icai_citation=(
                    "ICAI Handbook on Finalisation of Accounts with GST Perspective "
                    "(Jun 2026) — Section on 'Electronic Cash Ledger vs Books "
                    "Reconciliation'. TDS deductions appear in books at gross invoice "
                    "value but settlements are net of TDS; reconcile against "
                    "Form 26AS / AIS."
                ),
                resolution_hint=(
                    "Download Form 16A / 26AS from TRACES. Verify TDS certificate "
                    "matches deduction. For non-TDS cases: check Razorpay dispute "
                    "dashboard for credit notes or refunds applied to this invoice."
                ),
            )

    # ── Rule 4: Timing difference (cross-period) ──────────────────────────────
    if invoice_date is not None and settlement_date is not None:
        gap_days = abs((settlement_date - invoice_date).days)
        different_gst_period = (invoice_date.year, invoice_date.month) != (
            settlement_date.year, settlement_date.month
        )
        if gap_days > 30 or different_gst_period:
            return ExceptionResult(
                exception_class="TIMING_DIFF",
                confidence=0.87,
                explanation=(
                    f"Invoice date {invoice_date} vs settlement date {settlement_date} "
                    f"({gap_days} days gap). Invoice falls in one GST period, "
                    "settlement in another — books and Razorpay data come from "
                    "different reporting cycles."
                ),
                icai_citation=(
                    "ICAI GSTR-9C Technical Guide (Dec 2025) — 'Common Areas of "
                    "Mismatch' para: Timing differences between invoice date and "
                    "settlement date are the most frequent source of Books vs GST "
                    "discrepancy and are typically not a compliance issue. "
                    "Declare in GSTR-9C Part IV reconciliation column."
                ),
                resolution_hint=(
                    "No immediate action needed if amounts agree. "
                    "Mark as timing difference in GSTR-9C Part IV. "
                    "Verify the invoice appears in the correct GST period return."
                ),
            )

    # ── Rule 5: Missing entry in books ───────────────────────────────────────
    if books_amount_paise is None or books_amount_paise == 0:
        return ExceptionResult(
            exception_class="MISSING_ENTRY",
            confidence=0.82,
            explanation=(
                "Transaction is present in Razorpay settlement report and/or GSTR-2B "
                "but has no corresponding entry in the merchant's books of accounts."
            ),
            icai_citation=(
                "CGST Act Section 35 — every registered person must maintain records "
                "of all inward supplies. ICAI guidance (GSTR-9C Technical Guide, "
                "Dec 2025): unrecorded transactions must be traced and entered in "
                "books before GSTR-9 filing to avoid mismatch at audit."
            ),
            resolution_hint=(
                "Locate the source document (invoice, receipt, or delivery challan). "
                "Record the transaction in books for the correct period. "
                "If legitimately not a purchase, raise with vendor for credit note."
            ),
        )

    # ── Fallback ──────────────────────────────────────────────────────────────
    return ExceptionResult(
        exception_class="MISSING_ENTRY",
        confidence=0.45,
        explanation=(
            "Record could not be matched and does not meet any known exception "
            "classification criteria. Manual investigation required."
        ),
        icai_citation="ICAI GSTR-9C Technical Guide — general guidance on unresolved items.",
        resolution_hint="Do not close batch until this record is reviewed and classified manually.",
    )