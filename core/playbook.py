"""
Deterministic resolution checklists, one per exception class. No LLM
involvement — these are fixed, ICAI/CGST-grounded action lists, not
generated text. Checking a step is a human action recorded on the audit
ledger (see api/routers/records.py).
"""

PLAYBOOKS = {
    "RULE_37A": [
        {
            "step": 1,
            "action": "Verify supplier GSTIN is active on GSTN portal",
            "detail": "Search https://www.gstn.gov.in with the supplier GSTIN. Confirm they are registered and active.",
            "mandatory": True,
        },
        {
            "step": 2,
            "action": "Contact supplier to file pending GSTR-3B",
            "detail": "Supplier must file GSTR-3B for the relevant period. Share the filing deadline under Section 16(4).",
            "mandatory": True,
        },
        {
            "step": 3,
            "action": "Reverse ITC in current GSTR-3B",
            "detail": "File ITC reversal in GSTR-3B Table 4(B)(2) immediately. Rule 37A is self-operative — you cannot wait.",
            "mandatory": True,
        },
        {
            "step": 4,
            "action": "Set follow-up for next period",
            "detail": "If supplier files within the Section 16(4) window, you may re-avail the reversed ITC in that period's return.",
            "mandatory": False,
        },
    ],
    "ITC_TIME_BAR": [
        {
            "step": 1,
            "action": "Confirm invoice date and financial year with CA",
            "detail": "Verify the invoice belongs to the financial year identified by the classifier. Lapse under Section 16(4) is permanent.",
            "mandatory": True,
        },
        {
            "step": 2,
            "action": "Write off lapsed ITC as expense in books",
            "detail": "Debit P&L (ITC Lapsed Account), credit Electronic Credit Ledger. Do NOT reclassify as a current asset.",
            "mandatory": True,
        },
        {
            "step": 3,
            "action": "Disclose in GSTR-9 Part V",
            "detail": "Lapsed ITC must be disclosed in the annual return. Do not attempt to re-avail in any subsequent period.",
            "mandatory": True,
        },
    ],
    "AMOUNT_MISMATCH": [
        {
            "step": 1,
            "action": "Download Form 16A from TRACES",
            "detail": "Login to traces.gov.in, download TDS certificate for this vendor for the relevant quarter.",
            "mandatory": True,
        },
        {
            "step": 2,
            "action": "Verify TDS deduction matches settlement variance",
            "detail": "Compare Form 16A deduction amount with the settlement shortfall. Tolerance: ₹2 for rounding.",
            "mandatory": True,
        },
        {
            "step": 3,
            "action": "Update books entry to reflect gross invoice amount",
            "detail": "Books should record gross invoice value (before TDS). TDS appears separately as a receivable (TDS Receivable a/c Dr).",
            "mandatory": False,
        },
        {
            "step": 4,
            "action": "Reconcile with 26AS/AIS",
            "detail": "Confirm TDS appears in the merchant's Form 26AS (Annual Information Statement) to avoid mismatch at ITR filing.",
            "mandatory": False,
        },
    ],
    "TIMING_DIFF": [
        {
            "step": 1,
            "action": "Verify the invoice appears in the correct GST period",
            "detail": "The invoice date determines which GSTR-3B period it belongs to — not the settlement date. Confirm it is in the correct return.",
            "mandatory": True,
        },
        {
            "step": 2,
            "action": "Confirm ITC is availed in the invoice period, not settlement period",
            "detail": "Timing differences are not a compliance issue, but ITC must be availed in the period of the invoice, not when Razorpay settles.",
            "mandatory": True,
        },
        {
            "step": 3,
            "action": "Declare in GSTR-9C Part IV reconciliation",
            "detail": "Mark as timing difference in the annual reconciliation. No adjustment needed if amounts agree.",
            "mandatory": False,
        },
    ],
    "MISSING_ENTRY": [
        {
            "step": 1,
            "action": "Locate original invoice or delivery challan",
            "detail": "Contact vendor for invoice copy. Check email, WhatsApp, or vendor portal for the original document.",
            "mandatory": True,
        },
        {
            "step": 2,
            "action": "Record transaction in books for the correct period",
            "detail": "Entry must be recorded in the period of supply, not the date you found it missing.",
            "mandatory": True,
        },
        {
            "step": 3,
            "action": "Verify ITC availability in GSTR-2B",
            "detail": "Check if GSTR-2B shows this invoice from the supplier. ITC can only be availed if shown in GSTR-2B.",
            "mandatory": False,
        },
    ],
}


def get_playbook(exception_class: str) -> list[dict]:
    return PLAYBOOKS.get(exception_class, [])
