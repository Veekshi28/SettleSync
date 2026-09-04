"""
Close Pack PDF export — a single-page executive summary of a month-end close.
Pure deterministic formatting of already-computed data. No LLM involvement,
no network access, works fully offline.
"""
import time
from typing import Optional

from fpdf import FPDF


def _rupees(paise: int) -> str:
    return f"Rs {paise / 100:,.2f}"


def _safe(text) -> str:
    """The core PDF fonts are latin-1 only. Any dynamic text (free-typed
    justifications, upstream data) is sanitized so PDF generation never
    crashes on an unsupported character."""
    return str(text).encode("latin-1", errors="replace").decode("latin-1")


def build_close_pack(
    merchant_gstin: str,
    score: int,
    status: str,                 # "CLOSED" | "CONDITIONALLY CLOSED"
    total_records: int,
    resolved_count: int,
    human_reviewed: int,
    exceptions_remaining: int,
    total_itc_risk_paise: int,
    gate_results: list,          # list of core.close_gate.GateResult
    exception_classes: dict,     # {class: count}
    itc_at_risk_by_class: dict,  # {class: paise}
    ledger_event_count: int,
    chain_intact: bool,
    final_hash: str,
    authorized_at: Optional[str] = None,
    override_justification: Optional[str] = None,
) -> bytes:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Courier", "B", 16)
    pdf.cell(0, 8, "SETTLESYNC FINANCE CONTROLLER", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Courier", "B", 13)
    pdf.cell(0, 8, "MONTH-END CLOSE REPORT", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Courier", "", 10)
    pdf.cell(0, 6, f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Merchant GSTIN: {_safe(merchant_gstin)}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Courier", "B", 14)
    pdf.cell(0, 8, f"CLOSE READINESS SCORE: {score} / 100", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"STATUS: {status}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    resolved_pct = (resolved_count / total_records * 100) if total_records else 0
    pdf.set_font("Courier", "B", 12)
    pdf.cell(0, 7, "BATCH SUMMARY", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Courier", "", 10)
    pdf.cell(0, 6, f"Total records:        {total_records}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Auto-resolved:        {resolved_count} ({resolved_pct:.1f}%)", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Human reviewed:       {human_reviewed}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Exceptions remaining: {exceptions_remaining}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Total ITC at risk:    {_rupees(total_itc_risk_paise)}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Courier", "B", 12)
    pdf.cell(0, 7, "GATE RESULTS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Courier", "", 10)
    for g in gate_results:
        verdict = "PASS" if g.passed else "FAIL"
        pdf.cell(0, 6, f"{_safe(g.label):<24s} ... {verdict}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Courier", "B", 12)
    pdf.cell(0, 7, "EXCEPTION SUMMARY BY CLASS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Courier", "", 10)
    for cls in sorted(exception_classes):
        count = exception_classes[cls]
        risk = itc_at_risk_by_class.get(cls, 0)
        pdf.cell(0, 6, f"{cls:<18s} ... {count:>3d} ... {_rupees(risk)}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Courier", "B", 12)
    pdf.cell(0, 7, "AUDIT TRAIL", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Courier", "", 10)
    pdf.cell(0, 6, f"Total events:    {ledger_event_count}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Chain integrity: {'VERIFIED' if chain_intact else 'BROKEN'}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Final hash:      {_safe(final_hash)[:16]}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Courier", "B", 12)
    pdf.cell(0, 7, "AUTHORIZATION", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Courier", "", 10)
    pdf.cell(0, 6, "Authorized by:   Finance Controller", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Authorization:   {authorized_at or time.strftime('%Y-%m-%d %H:%M:%S')}", new_x="LMARGIN", new_y="NEXT")
    if override_justification:
        pdf.ln(2)
        pdf.set_font("Courier", "B", 10)
        pdf.cell(0, 6, "Override justification:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Courier", "", 10)
        pdf.multi_cell(0, 6, _safe(override_justification))

    return bytes(pdf.output())
