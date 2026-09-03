"""
AI narration layer — Claude explains exception records in plain English.
Falls back to deterministic templates if API unavailable.
The LLM explains. It does NOT classify, match, or approve anything.
"""
import os
from typing import Optional

try:
    import anthropic
    _client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    _HAS_API = bool(os.environ.get("ANTHROPIC_API_KEY"))
except Exception:
    _client = None
    _HAS_API = False


TEMPLATES = {
    "RULE_37A": (
        "This invoice cannot have its Input Tax Credit (ITC) claimed because the supplier "
        "has not filed their GSTR-3B return. Under Rule 37A, you must reverse this ITC "
        "immediately. If the supplier files within the time allowed under Section 16(4), "
        "you may re-avail the credit."
    ),
    "ITC_TIME_BAR": (
        "The ITC window for this invoice has permanently closed. Under Section 16(4) of "
        "the CGST Act, Input Tax Credit must be claimed by 30 November following the "
        "financial year end. This deadline has passed and the credit is lapsed. "
        "Do not attempt to re-avail it — disclose the lapsed amount in GSTR-9 Part V."
    ),
    "AMOUNT_MISMATCH": (
        "The amount in the Razorpay settlement differs from what your books show. "
        "The most common cause is a TDS (Tax Deducted at Source) deduction that was "
        "applied to the settlement but not reflected in your accounting entry. "
        "Check Form 16A from TRACES and verify against the Razorpay payment details."
    ),
    "TIMING_DIFF": (
        "This transaction appears in two different accounting periods — the invoice was "
        "raised in one GST period but settled by Razorpay in the next. This is a "
        "common, typically harmless mismatch. No ITC reversal is needed, but "
        "declare this in GSTR-9C Part IV reconciliation column."
    ),
    "MISSING_ENTRY": (
        "This transaction exists in your Razorpay settlement data and/or GST records "
        "but has no matching entry in your books of accounts. Before closing the "
        "period, locate the original invoice or receipt and record the transaction. "
        "If you did not receive this service or goods, request a credit note from the vendor."
    ),
}


def explain_exception(
    record: dict,
    exception_class: str,
    exception_explanation: str,
    icai_citation: str,
    resolution_hint: str,
) -> tuple[str, bool]:
    """
    Returns (narrative: str, used_llm: bool).
    Falls back gracefully if LLM unavailable.
    """
    if not _HAS_API or _client is None:
        return TEMPLATES.get(exception_class, TEMPLATES["MISSING_ENTRY"]), False

    try:
        prompt = f"""You are a GST compliance assistant helping a finance controller
understand a reconciliation exception.

Record ID: {record.get("record_id")}
Exception class: {exception_class}
Technical explanation: {exception_explanation}
ICAI rule reference: {icai_citation}
Resolution hint: {resolution_hint}

Write a 2-3 sentence plain-English explanation for a finance controller who is not a
tax expert. Be specific about the amounts if known. Do NOT mention ICAI or cite rules
— just explain what happened and what they should do next. Keep it under 80 words."""

        response = _client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip(), True

    except Exception as e:
        # Graceful degradation — batch continues
        fallback = TEMPLATES.get(exception_class, TEMPLATES["MISSING_ENTRY"])
        return fallback + f" [AI narration unavailable: {type(e).__name__}]", False