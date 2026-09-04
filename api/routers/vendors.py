"""
Per-vendor compliance scorecard — pure Python groupby, no LLM, no pandas.
Grouped strictly by GSTIN (the real vendor identity); vendor *name*
formatting varies by source record and must never be used as the group key
(see WHATBROKE.md / CLAUDE.md "Common mistakes to avoid").
"""
from collections import Counter

from fastapi import APIRouter

from api import state

router = APIRouter()


@router.get("/api/vendors")
def list_vendors():
    if state.batch is None:
        return []

    buckets: dict[str, list] = {}
    for e in state.batch.records.values():
        gstin = e.raw.get("vendor_gstin_settlement") or "UNKNOWN"
        buckets.setdefault(gstin, []).append(e)

    result = []
    for gstin, entries in buckets.items():
        total = len(entries)
        matched = sum(1 for e in entries if e.state.value in ("RESOLVED", "APPROVED"))
        exceptions = sum(1 for e in entries if e.exception_class is not None)
        pending = sum(1 for e in entries if e.exception_class == "GSTR2B_PENDING")
        real_exceptions = exceptions - pending
        match_rate = matched / total * 100 if total else 0.0
        rule_37a = sum(1 for e in entries if e.exception_class == "RULE_37A")
        itc_timebarred = sum(1 for e in entries if e.exception_class == "ITC_TIME_BAR")
        amount_mismatch = sum(1 for e in entries if e.exception_class == "AMOUNT_MISMATCH")
        itc_risk = sum(e.itc_risk_paise for e in entries)

        filed_flags = [e.raw.get("gstr_supplier_filed", True) for e in entries]
        supplier_filed_pct = (
            sum(1 for f in filed_flags if f) / len(filed_flags) * 100 if filed_flags else 100.0
        )

        names = [e.raw.get("vendor_name_books") for e in entries if e.raw.get("vendor_name_books")]
        name = Counter(names).most_common(1)[0][0] if names else "(name unavailable)"

        if rule_37a > 0 or itc_timebarred > 0 or match_rate < 50:
            status = "Critical"
        elif match_rate < 80 or amount_mismatch > 0:
            status = "Watch"
        else:
            status = "Clean"

        # GSTR2B_PENDING is a timing state, not a violation — if the only reason
        # this vendor isn't Clean is pending records sitting in review, surface
        # that as "Pending" rather than a false compliance flag.
        if real_exceptions == 0 and pending > 0 and status != "Clean":
            status = "Pending"

        result.append({
            "gstin": gstin,
            "name": name,
            "total": total,
            "matched": matched,
            "exceptions": exceptions,
            "pending": pending,
            "match_rate": round(match_rate, 1),
            "rule_37a": rule_37a,
            "itc_timebarred": itc_timebarred,
            "itc_risk_paise": itc_risk,
            "supplier_filed_pct": round(supplier_filed_pct, 1),
            "status": status,
        })

    result.sort(key=lambda v: v["itc_risk_paise"], reverse=True)
    return result
