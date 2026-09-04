"""
Ingestion — parse the 3 raw Razorpay/merchant CSVs into typed dicts.
No matching, no normalization, no business logic here.
"""
import csv
from datetime import date, datetime
from typing import Optional


def _parse_date(raw: str) -> Optional[date]:
    if not raw:
        return None
    return datetime.strptime(raw.strip(), "%Y-%m-%d").date()


def _parse_int(raw: str) -> Optional[int]:
    if raw is None or str(raw).strip() == "":
        return None
    return int(raw)


def _parse_bool(raw: str) -> bool:
    return str(raw).strip().lower() in ("true", "1", "yes")


def load_settlements(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        rows = []
        for row in csv.DictReader(f):
            rows.append({
                "txn_id":         row["txn_id"],
                "invoice_ref":    row["invoice_ref"],
                "vendor_gstin":   row["vendor_gstin"],
                "merchant_gstin": row["merchant_gstin"],
                "settlement_date": _parse_date(row["settlement_date"]),
                "amount_paise":   _parse_int(row["amount_paise"]),
                "utr":            row["utr"],
            })
        return rows


def load_books(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        rows = []
        for row in csv.DictReader(f):
            rows.append({
                "invoice_id":            row["invoice_id"],
                "vendor_name":           row["vendor_name"],
                "vendor_gstin":          row["vendor_gstin"] or None,
                "invoice_date":          _parse_date(row["invoice_date"]),
                "taxable_amount_paise":  _parse_int(row["taxable_amount_paise"]),
                "total_paise":           _parse_int(row["total_paise"]),
                "recorded_date":         _parse_date(row["recorded_date"]),
            })
        return rows


def load_gstr2b(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        rows = []
        for row in csv.DictReader(f):
            rows.append({
                "gstin_supplier":      row["gstin_supplier"],
                "invoice_no":          row["invoice_no"],
                "invoice_date":        _parse_date(row["invoice_date"]),
                "taxable_value_paise": _parse_int(row["taxable_value_paise"]),
                "total_paise":         _parse_int(row["total_paise"]),
                "itc_available":       _parse_bool(row["itc_available"]),
                "supplier_filed":      _parse_bool(row["supplier_filed"]),
            })
        return rows


def load_all(settlements_path: str, books_path: str, gstr_path: str) -> dict:
    """Returns {"settlements": [...], "books": [...], "gstr2b": [...]}."""
    return {
        "settlements": load_settlements(settlements_path),
        "books":       load_books(books_path),
        "gstr2b":      load_gstr2b(gstr_path),
    }
