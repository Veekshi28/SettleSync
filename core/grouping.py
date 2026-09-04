"""
Smart exception grouping — clusters exception records into review clusters
so a CA reviews K clusters instead of N individual records.

Fully deterministic. No LLM calls. No state transitions — this only
produces a display grouping over already-classified RecordEntry objects.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from core.classify import TDS_RATES, TDS_TOLERANCE_PAISE

DATE_CLUSTER_WINDOW_DAYS = 7
MIN_CLUSTER_SIZE = 2

VENDOR_CLASS_ACTIONS = {
    "RULE_37A": (
        "Reverse ITC for all {n} invoices from this vendor; request updated "
        "GSTR-3B filing confirmation before re-availing."
    ),
    "ITC_TIME_BAR": (
        "Disclose lapsed ITC for all {n} invoices in GSTR-9 Part V — "
        "no recovery is possible for any of them."
    ),
    "MISSING_ENTRY": (
        "Trace and book all {n} missing invoices from this vendor before close."
    ),
}


@dataclass
class ExceptionGroup:
    group_type: str          # "vendor_class" | "date_cluster" | "tds_cluster"
    title: str
    record_ids: list[str] = field(default_factory=list)
    total_itc_risk_paise: int = 0
    recommended_action: str = ""

    @property
    def count(self) -> int:
        return len(self.record_ids)


def _vendor_class_groups(entries: list) -> list[ExceptionGroup]:
    """Rule 1: same vendor GSTIN + same exception class."""
    buckets: dict[tuple, list] = {}
    for e in entries:
        if e.exception_class not in VENDOR_CLASS_ACTIONS:
            continue
        gstin = e.raw.get("vendor_gstin_settlement")
        key = (gstin, e.exception_class)
        buckets.setdefault(key, []).append(e)

    groups = []
    for (gstin, exc_class), members in buckets.items():
        if len(members) < MIN_CLUSTER_SIZE:
            continue
        vendor_name = members[0].raw.get("vendor_name_books") or "Unknown vendor"
        gstin_label = f"{gstin[:9]}..." if gstin and len(gstin) > 9 else (gstin or "—")
        total_risk = sum(m.itc_risk_paise for m in members)
        action = VENDOR_CLASS_ACTIONS[exc_class].format(n=len(members))
        groups.append(ExceptionGroup(
            group_type="vendor_class",
            title=f"{len(members)} {exc_class} exceptions — {vendor_name} (GSTIN: {gstin_label})",
            record_ids=[m.record_id for m in members],
            total_itc_risk_paise=total_risk,
            recommended_action=action,
        ))
    return groups


def _date_clusters(entries: list) -> list[ExceptionGroup]:
    """Rule 2: TIMING_DIFF records whose invoice dates fall within a 7-day window."""
    timing_entries = [
        e for e in entries
        if e.exception_class == "TIMING_DIFF" and e.raw.get("books_invoice_date")
    ]
    timing_entries.sort(key=lambda e: e.raw["books_invoice_date"])

    groups = []
    cluster: list = []
    cluster_start: Optional[date] = None

    def flush():
        if len(cluster) >= MIN_CLUSTER_SIZE:
            start = cluster[0].raw["books_invoice_date"]
            end = cluster[-1].raw["books_invoice_date"]
            if start.month == end.month:
                span = f"{start:%B %d}–{end:%d}"
            else:
                span = f"{start:%b %d}–{end:%b %d}"
            total_risk = sum(m.itc_risk_paise for m in cluster)
            groups.append(ExceptionGroup(
                group_type="date_cluster",
                title=f"{len(cluster)} cross-period settlements — {span} batch",
                record_ids=[m.record_id for m in cluster],
                total_itc_risk_paise=total_risk,
                recommended_action=(
                    f"Verify all {len(cluster)} invoices are declared in the correct "
                    "GST period (GSTR-9C Part IV)."
                ),
            ))

    for e in timing_entries:
        inv_date = e.raw["books_invoice_date"]
        if cluster_start is None or (inv_date - cluster_start).days > DATE_CLUSTER_WINDOW_DAYS:
            flush()
            cluster = [e]
            cluster_start = inv_date
        else:
            cluster.append(e)
    flush()

    return groups


def _tds_clusters(entries: list) -> list[ExceptionGroup]:
    """Rule 3: AMOUNT_MISMATCH records whose variance matches a known TDS rate."""
    buckets: dict[str, list] = {}
    for e in entries:
        if e.exception_class != "AMOUNT_MISMATCH":
            continue
        books = e.raw.get("books_total_paise")
        settlement = e.raw.get("settlement_amount_paise")
        if not books or settlement is None:
            continue
        diff = books - settlement
        for tds_name, rate in TDS_RATES.items():
            expected = int(books * rate)
            if abs(diff - expected) <= TDS_TOLERANCE_PAISE:
                buckets.setdefault(tds_name, []).append(e)
                break

    groups = []
    for tds_name, members in buckets.items():
        if len(members) < MIN_CLUSTER_SIZE:
            continue
        rate = TDS_RATES[tds_name]
        section = tds_name.split("_")[0]
        total_risk = sum(m.itc_risk_paise for m in members)
        groups.append(ExceptionGroup(
            group_type="tds_cluster",
            title=f"{len(members)} amount mismatches — consistent with {rate:.0%} TDS (Sec {section})",
            record_ids=[m.record_id for m in members],
            total_itc_risk_paise=total_risk,
            recommended_action=f"Obtain Form 16A from vendor for all {len(members)} invoices.",
        ))
    return groups


def group_exceptions(entries: list) -> tuple[list[ExceptionGroup], list]:
    """
    entries: list of core.state.RecordEntry with exception_class set.
    Returns (groups, ungrouped_entries) — ungrouped_entries are records that
    didn't meet the minimum cluster size for any pattern and should be shown
    individually.
    """
    groups = _vendor_class_groups(entries) + _date_clusters(entries) + _tds_clusters(entries)

    grouped_ids = {rid for g in groups for rid in g.record_ids}
    ungrouped = [e for e in entries if e.record_id not in grouped_ids]

    return groups, ungrouped
