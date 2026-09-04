"""
Normalization — invoice ID cleanup, paise amounts (already int from ingest),
and joining settlements to books/GSTR-2B by normalized invoice ID.

Settlements.csv is the pipeline's spine: every record originates from a
Razorpay settlement, so record_id = settlement txn_id. Books/GSTR-2B rows
that don't join to any settlement are not part of the reconciliation scope
(the merchant's books may contain purchases with no Razorpay settlement at
all — out of scope for this batch).
"""
from typing import Optional

from core.ingest import load_all


def normalize_invoice_id(raw: Optional[str]) -> str:
    """Uppercase, strip -, ., /, and whitespace."""
    if not raw:
        return ""
    cleaned = raw.strip().upper()
    for ch in ("-", ".", "/", " "):
        cleaned = cleaned.replace(ch, "")
    return cleaned


def _index_by_invoice_id(rows: list[dict], key: str) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for row in rows:
        norm = normalize_invoice_id(row.get(key))
        if norm and norm not in index:
            index[norm] = row
    return index


def normalize_all(raw: dict) -> list[dict]:
    """
    raw: output of core.ingest.load_all() — {"settlements", "books", "gstr2b"}.
    Returns one normalized record per settlement row, left-joined to the
    matching books/GSTR-2B rows by normalized invoice ID.
    """
    books_index = _index_by_invoice_id(raw["books"], "invoice_id")
    gstr_index = _index_by_invoice_id(raw["gstr2b"], "invoice_no")

    normalized = []
    for s in raw["settlements"]:
        norm_id = normalize_invoice_id(s["invoice_ref"])
        books = books_index.get(norm_id)
        gstr = gstr_index.get(norm_id)

        normalized.append({
            "record_id":                  s["txn_id"],
            "norm_invoice_id":            norm_id,
            "merchant_gstin":             s["merchant_gstin"],
            "vendor_gstin_settlement":    s["vendor_gstin"],
            "vendor_gstin_books":         books["vendor_gstin"] if books else None,
            "settlement_date":            s["settlement_date"],
            "books_invoice_date":         books["invoice_date"] if books else None,
            "settlement_amount_paise":    s["amount_paise"],
            "books_total_paise":          books["total_paise"] if books else None,
            "gstr_total_paise":           gstr["total_paise"] if gstr else None,
            # Razorpay settlement data does not carry the vendor's legal name —
            # only GSTIN and invoice ref. Fuzzy vendor-name matching can only
            # use the books side; the settlement side is intentionally blank.
            "vendor_name_settlement":     "",
            "vendor_name_books":          books["vendor_name"] if books else "",
            "supplier_filed":             gstr["supplier_filed"] if gstr else True,
            "gstr_supplier_filed":        gstr["supplier_filed"] if gstr else True,
            "gstr_itc_available":         gstr["itc_available"] if gstr else True,
            "settlement_invoice_ref":     s["invoice_ref"],
            "books_invoice_id":           books["invoice_id"] if books else None,
        })

    return normalized


def normalize_records(settlements_path: str, books_path: str, gstr_path: str) -> list[dict]:
    """Convenience wrapper: ingest 3 CSVs then normalize in one call."""
    raw = load_all(settlements_path, books_path, gstr_path)
    return normalize_all(raw)
