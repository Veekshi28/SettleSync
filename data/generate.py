"""
Synthetic data generator for SettleSync evaluation.
Commit this file AND the generated CSVs so judges can verify.
Run: python -m data.generate [--seed 42] [--records 80]
"""
import argparse
import random
import csv
from datetime import date, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# ── Vendor pool (messy on purpose) ──────────────────────────────────────────
VENDORS = [
    ("Tata Consultancy Services Ltd", "TATA CONSULTANCY SERVICES LIMITED",  "27AADCT2765Q1ZO"),
    ("Infosys BPO Pvt Ltd",          "INFOSYS BPO PRIVATE LIMITED",        "29AABCI1234P1Z5"),
    ("Wipro Technologies",            "WIPRO TECHNOLOGIES LTD",             "29AABCW1234M1ZP"),
    ("HCL Technologies Ltd",          "HCL TECHNOLOGIES LIMITED",           "06AABCH1234N1ZR"),
    ("Cognizant Technology Solutions","COGNIZANT TECHNOLOGY SOLS PVT LTD",  "33AABCC1234K1ZT"),
    # GSTIN-conflict trap: same name, different GSTIN
    ("Sharma Enterprises",            "Sharma Enterprises",                 "27AAJCS1111A1Z1"),
    ("Sharma Enterprises",            "Sharma Enterprises",                 "29AABCS2222B1Z2"),
]

MERCHANT_GSTIN = "27AADCM9876R1ZX"

def random_date(start: date, end: date, rng: random.Random) -> date:
    delta = (end - start).days
    return start + timedelta(days=rng.randint(0, delta))

def normalize_invoice_id(raw: str) -> str:
    """Mimic the normalization your engine will do."""
    return raw.upper().replace("/", "").replace("-", "").replace(" ", "")

@dataclass
class SyntheticRecord:
    record_id: str
    ground_truth: str              # what the evaluator checks against
    # settlements.csv
    settlement_txn_id: str
    settlement_invoice_ref: str    # messy format
    vendor_gstin_settlement: str
    settlement_date: date
    settlement_amount_paise: int
    utr: str
    # books.csv
    books_invoice_id: Optional[str]       # may be None for MISSING_ENTRY
    books_vendor_name: str
    books_vendor_gstin: Optional[str]
    books_invoice_date: Optional[date]
    books_taxable_paise: Optional[int]
    books_igst_paise: int = 0
    books_total_paise: Optional[int] = None
    books_recorded_date: Optional[date] = None
    # gstr2b.csv
    gstr_gstin_supplier: Optional[str] = None
    gstr_invoice_no: Optional[str] = None
    gstr_invoice_date: Optional[date] = None
    gstr_taxable_paise: Optional[int] = None
    gstr_total_paise: Optional[int] = None
    gstr_itc_available: bool = True
    gstr_supplier_filed: bool = True


def generate_dataset(seed: int = 42, n: int = 80) -> list[SyntheticRecord]:
    rng = random.Random(seed)
    records = []
    seq = 0

    def make_id():
        nonlocal seq
        seq += 1
        return f"RPZ-{seq:04d}"

    # Helper: base invoice ref with intentional messiness
    def messy_inv(n: int, style: int = 0) -> str:
        base = f"INV{n:04d}"
        styles = [base, f"INV-{n:04d}", f"INV/{n:04d}", f"inv{n:04d}",
                  f"  {base}  ", base.lower()]
        return styles[style % len(styles)]

    base_date = date(2025, 4, 1)  # FY2025-26 start
    late_date = date(2025, 12, 1)  # after 16(4) deadline for FY2024-25

    # ── 1. EXACT MATCHES (25) ─────────────────────────────────────────────
    for i in range(1, 26):
        vendor = VENDORS[rng.randint(0, 4)]  # avoid conflict-trap pair
        amount = rng.randint(50000, 500000) * 100  # ₹500–₹5000 in paise
        inv_date = random_date(base_date, date(2025, 9, 30), rng)
        settle_date = inv_date + timedelta(days=rng.randint(1, 15))

        # Intentionally messy invoice formats
        raw_inv = messy_inv(100 + i, style=rng.randint(0, 3))
        records.append(SyntheticRecord(
            record_id=make_id(),
            ground_truth="EXACT_MATCH",
            settlement_txn_id=f"pay_{rng.randbytes(6).hex()}",
            settlement_invoice_ref=raw_inv,
            vendor_gstin_settlement=vendor[2],
            settlement_date=settle_date,
            settlement_amount_paise=amount,
            utr=f"UTR{rng.randint(100000, 999999)}",
            books_invoice_id=messy_inv(100 + i, style=rng.randint(0, 2)),
            books_vendor_name=vendor[1],  # different capitalisation
            books_vendor_gstin=vendor[2],
            books_invoice_date=inv_date,
            books_taxable_paise=amount,
            books_total_paise=amount,
            books_recorded_date=inv_date + timedelta(days=rng.randint(0, 3)),
            gstr_gstin_supplier=vendor[2],
            gstr_invoice_no=messy_inv(100 + i, style=0),
            gstr_invoice_date=inv_date,
            gstr_taxable_paise=amount,
            gstr_total_paise=amount,
            gstr_supplier_filed=True,
        ))

    # ── 2. TIMING DIFFERENCES (15) ───────────────────────────────────────
    for i in range(1, 16):
        vendor = VENDORS[rng.randint(0, 4)]
        amount = rng.randint(50000, 300000) * 100
        # Invoice in March, settlement in April (cross-period). Uses FY2025-26
        # (not FY2024-25 like the ITC_TIME_BAR set below) so the Sec 16(4)
        # deadline check never collides with these purely-timing records.
        inv_date = date(2026, 3, rng.randint(28, 31))
        settle_date = date(2026, 4, rng.randint(1, 10))

        raw_inv = messy_inv(200 + i, style=rng.randint(0, 2))
        records.append(SyntheticRecord(
            record_id=make_id(),
            ground_truth="TIMING_DIFF",
            settlement_txn_id=f"pay_{rng.randbytes(6).hex()}",
            settlement_invoice_ref=raw_inv,
            vendor_gstin_settlement=vendor[2],
            settlement_date=settle_date,
            settlement_amount_paise=amount,
            utr=f"UTR{rng.randint(100000, 999999)}",
            books_invoice_id=messy_inv(200 + i, style=0),
            books_vendor_name=vendor[0],
            books_vendor_gstin=vendor[2],
            books_invoice_date=inv_date,
            books_taxable_paise=amount,
            books_total_paise=amount,
            books_recorded_date=inv_date,
            gstr_gstin_supplier=vendor[2],
            gstr_invoice_no=messy_inv(200 + i, style=0),
            gstr_invoice_date=inv_date,
            gstr_taxable_paise=amount,
            gstr_total_paise=amount,
            gstr_supplier_filed=True,
        ))

    # ── 3. AMOUNT MISMATCHES (12) — TDS deductions ───────────────────────
    TDS_RATES = [0.01, 0.01, 0.02, 0.10]  # 194C, 194C, 194C-transport, 194J
    for i in range(1, 13):
        vendor = VENDORS[rng.randint(0, 4)]
        books_amount = rng.randint(100000, 1000000) * 100
        tds_rate = TDS_RATES[i % len(TDS_RATES)]
        settlement_amount = int(books_amount * (1 - tds_rate))  # TDS deducted
        inv_date = random_date(base_date, date(2025, 9, 30), rng)
        settle_date = inv_date + timedelta(days=rng.randint(1, 10))
        raw_inv = messy_inv(300 + i, style=rng.randint(0, 2))

        records.append(SyntheticRecord(
            record_id=make_id(),
            ground_truth="AMOUNT_MISMATCH",
            settlement_txn_id=f"pay_{rng.randbytes(6).hex()}",
            settlement_invoice_ref=raw_inv,
            vendor_gstin_settlement=vendor[2],
            settlement_date=settle_date,
            settlement_amount_paise=settlement_amount,
            utr=f"UTR{rng.randint(100000, 999999)}",
            books_invoice_id=messy_inv(300 + i, style=0),
            books_vendor_name=vendor[1],
            books_vendor_gstin=vendor[2],
            books_invoice_date=inv_date,
            books_taxable_paise=books_amount,
            books_total_paise=books_amount,
            books_recorded_date=inv_date,
            gstr_gstin_supplier=vendor[2],
            gstr_invoice_no=messy_inv(300 + i, style=0),
            gstr_invoice_date=inv_date,
            gstr_taxable_paise=books_amount,
            gstr_total_paise=books_amount,
            gstr_supplier_filed=True,
        ))

    # ── 4. RULE_37A — supplier hasn't filed GSTR-3B (8) ─────────────────
    for i in range(1, 9):
        vendor = VENDORS[rng.randint(0, 4)]
        amount = rng.randint(50000, 400000) * 100
        inv_date = random_date(base_date, date(2025, 8, 31), rng)
        settle_date = inv_date + timedelta(days=rng.randint(1, 10))
        raw_inv = messy_inv(400 + i, style=rng.randint(0, 2))

        records.append(SyntheticRecord(
            record_id=make_id(),
            ground_truth="RULE_37A",
            settlement_txn_id=f"pay_{rng.randbytes(6).hex()}",
            settlement_invoice_ref=raw_inv,
            vendor_gstin_settlement=vendor[2],
            settlement_date=settle_date,
            settlement_amount_paise=amount,
            utr=f"UTR{rng.randint(100000, 999999)}",
            books_invoice_id=messy_inv(400 + i, style=0),
            books_vendor_name=vendor[0],
            books_vendor_gstin=vendor[2],
            books_invoice_date=inv_date,
            books_taxable_paise=amount,
            books_total_paise=amount,
            books_recorded_date=inv_date,
            gstr_gstin_supplier=vendor[2],
            gstr_invoice_no=messy_inv(400 + i, style=0),
            gstr_invoice_date=inv_date,
            gstr_taxable_paise=amount,
            gstr_total_paise=amount,
            gstr_itc_available=False,       # ITC not available
            gstr_supplier_filed=False,       # THE KEY FLAG
        ))

    # ── 5. ITC_TIME_BAR — FY2024-25 invoices past Nov 30 deadline (8) ───
    for i in range(1, 9):
        vendor = VENDORS[rng.randint(0, 4)]
        amount = rng.randint(50000, 300000) * 100
        # Invoice in FY2024-25 (before April 2025)
        inv_date = random_date(date(2024, 4, 1), date(2025, 3, 31), rng)
        settle_date = late_date + timedelta(days=rng.randint(0, 30))
        raw_inv = messy_inv(500 + i, style=rng.randint(0, 2))

        records.append(SyntheticRecord(
            record_id=make_id(),
            ground_truth="ITC_TIME_BAR",
            settlement_txn_id=f"pay_{rng.randbytes(6).hex()}",
            settlement_invoice_ref=raw_inv,
            vendor_gstin_settlement=vendor[2],
            settlement_date=settle_date,
            settlement_amount_paise=amount,
            utr=f"UTR{rng.randint(100000, 999999)}",
            books_invoice_id=messy_inv(500 + i, style=0),
            books_vendor_name=vendor[1],
            books_vendor_gstin=vendor[2],
            books_invoice_date=inv_date,
            books_taxable_paise=amount,
            books_total_paise=amount,
            books_recorded_date=inv_date,
            gstr_gstin_supplier=vendor[2],
            gstr_invoice_no=messy_inv(500 + i, style=0),
            gstr_invoice_date=inv_date,
            gstr_taxable_paise=amount,
            gstr_total_paise=amount,
            gstr_supplier_filed=True,
        ))

    # ── 6. MISSING_ENTRY — in settlement but not in books (7) ────────────
    for i in range(1, 8):
        vendor = VENDORS[rng.randint(0, 4)]
        amount = rng.randint(30000, 200000) * 100
        settle_date = random_date(base_date, date(2025, 9, 30), rng)

        records.append(SyntheticRecord(
            record_id=make_id(),
            ground_truth="MISSING_ENTRY",
            settlement_txn_id=f"pay_{rng.randbytes(6).hex()}",
            settlement_invoice_ref=messy_inv(600 + i, style=0),
            vendor_gstin_settlement=vendor[2],
            settlement_date=settle_date,
            settlement_amount_paise=amount,
            utr=f"UTR{rng.randint(100000, 999999)}",
            # Books data absent
            books_invoice_id=None,
            books_vendor_name="",
            books_vendor_gstin=None,
            books_invoice_date=None,
            books_taxable_paise=None,
            books_total_paise=None,
        ))

    # ── 7. GSTIN CONFLICT TRAP — same vendor name, different GSTIN (2) ──
    # These should NOT be auto-matched by fuzzy engine
    for i in range(1, 3):
        amount = rng.randint(80000, 300000) * 100
        inv_date = random_date(base_date, date(2025, 9, 30), rng)
        settle_date = inv_date + timedelta(days=rng.randint(1, 10))
        raw_inv = messy_inv(700 + i, style=0)

        # Settlement has Sharma Enterprises GSTIN A
        # Books has Sharma Enterprises GSTIN B → GSTIN mismatch should block auto-match
        records.append(SyntheticRecord(
            record_id=make_id(),
            ground_truth="GSTIN_CONFLICT_TRAP",  # evaluator expects MISSING_ENTRY classification
            settlement_txn_id=f"pay_{rng.randbytes(6).hex()}",
            settlement_invoice_ref=raw_inv,
            vendor_gstin_settlement=VENDORS[5][2],  # Sharma GSTIN A
            settlement_date=settle_date,
            settlement_amount_paise=amount,
            utr=f"UTR{rng.randint(100000, 999999)}",
            books_invoice_id=messy_inv(700 + i, style=1),
            books_vendor_name=VENDORS[6][1],        # Same name
            books_vendor_gstin=VENDORS[6][2],       # But GSTIN B!
            books_invoice_date=inv_date,
            books_taxable_paise=amount,
            books_total_paise=amount,
            books_recorded_date=inv_date,
        ))

    rng.shuffle(records)
    return records


def write_csvs(records: list[SyntheticRecord], out_dir: str = "data/synthetic"):
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    with open(f"{out_dir}/settlements.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "txn_id", "invoice_ref", "vendor_gstin", "merchant_gstin",
            "settlement_date", "amount_paise", "utr",
        ])
        w.writeheader()
        for r in records:
            w.writerow({
                "txn_id": r.settlement_txn_id,
                "invoice_ref": r.settlement_invoice_ref,
                "vendor_gstin": r.vendor_gstin_settlement,
                "merchant_gstin": MERCHANT_GSTIN,
                "settlement_date": r.settlement_date.isoformat(),
                "amount_paise": r.settlement_amount_paise,
                "utr": r.utr,
            })

    with open(f"{out_dir}/books.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "invoice_id", "vendor_name", "vendor_gstin",
            "invoice_date", "taxable_amount_paise", "total_paise", "recorded_date",
        ])
        w.writeheader()
        for r in records:
            if r.books_invoice_id is None:
                continue
            w.writerow({
                "invoice_id": r.books_invoice_id,
                "vendor_name": r.books_vendor_name,
                "vendor_gstin": r.books_vendor_gstin or "",
                "invoice_date": r.books_invoice_date.isoformat() if r.books_invoice_date else "",
                "taxable_amount_paise": r.books_taxable_paise or "",
                "total_paise": r.books_total_paise or "",
                "recorded_date": r.books_recorded_date.isoformat() if r.books_recorded_date else "",
            })

    with open(f"{out_dir}/gstr2b.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "gstin_supplier", "invoice_no", "invoice_date",
            "taxable_value_paise", "total_paise",
            "itc_available", "supplier_filed",
        ])
        w.writeheader()
        for r in records:
            if r.gstr_gstin_supplier is None:
                continue
            w.writerow({
                "gstin_supplier": r.gstr_gstin_supplier,
                "invoice_no": r.gstr_invoice_no,
                "invoice_date": r.gstr_invoice_date.isoformat() if r.gstr_invoice_date else "",
                "taxable_value_paise": r.gstr_taxable_paise or "",
                "total_paise": r.gstr_total_paise or "",
                "itc_available": r.gstr_itc_available,
                "supplier_filed": r.gstr_supplier_filed,
            })

    # Ground truth is keyed by settlement_txn_id, NOT the internal RPZ record_id —
    # settlements.csv (the pipeline's spine) never carries the RPZ id, so that id
    # is not a valid join key back to the operational data. txn_id is present on
    # every record (including MISSING_ENTRY / GSTIN_CONFLICT_TRAP) and is what
    # normalize.py uses as record_id downstream.
    with open(f"{out_dir}/ground_truth.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["record_id", "ground_truth"])
        w.writeheader()
        for r in records:
            w.writerow({"record_id": r.settlement_txn_id, "ground_truth": r.ground_truth})

    print(f"Generated {len(records)} records -> {out_dir}/")
    counts = {}
    for r in records:
        counts[r.ground_truth] = counts.get(r.ground_truth, 0) + 1
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--records", type=int, default=80)
    args = parser.parse_args()
    records = generate_dataset(seed=args.seed)
    write_csvs(records)