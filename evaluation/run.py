"""
Batch evaluation with baseline comparison.
Run before filming the video — these are your headline numbers.
Usage: python -m evaluation.run
"""
import csv
import json
from datetime import date
from pathlib import Path
from core.normalize import normalize_records
from core.match import run_three_way_match
from core.classify import classify


def load_ground_truth(path: str) -> dict[str, str]:
    gt = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            gt[row["record_id"]] = row["ground_truth"]
    return gt


def baseline_match(normalized: list[dict]) -> dict[str, str]:
    """
    Naive baseline: exact string match on raw invoice_id + exact amount.
    No normalization, no fuzzy, no timing adjustment.
    This is what merchants do in Excel today.
    """
    results = {}
    # index books by raw invoice_id
    books_index = {}
    for r in normalized:
        if r.get("books_invoice_id"):
            books_index[r["books_invoice_id"].strip().upper()] = r

    for r in normalized:
        raw_key = r["settlement_invoice_ref"].strip().upper()
        if (raw_key in books_index and
                r["settlement_amount_paise"] == books_index[raw_key].get("books_total_paise")):
            results[r["record_id"]] = "matched"
        else:
            results[r["record_id"]] = "unmatched"
    return results


def evaluate(
    settlements_path: str = "data/synthetic/settlements.csv",
    books_path: str = "data/synthetic/books.csv",
    gstr_path: str = "data/synthetic/gstr2b.csv",
    ground_truth_path: str = "data/synthetic/ground_truth.csv",
    run_date: date = None,
) -> dict:
    run_date = run_date or date.today()
    gt = load_ground_truth(ground_truth_path)

    normalized = normalize_records(settlements_path, books_path, gstr_path)
    total = len(normalized)

    # ── SettleSync evaluation ──────────────────────────────────────────────
    ss_results = {}
    exception_classes = {}
    false_matches = 0

    for r in normalized:
        rid = r["record_id"]
        match = run_three_way_match(r)

        if match["matched"]:
            ss_results[rid] = ("matched", match["type"], None)
            # Check against ground truth for false match detection
            truth = gt.get(rid, "")
            if truth in ("RULE_37A", "ITC_TIME_BAR", "AMOUNT_MISMATCH",
                         "MISSING_ENTRY", "GSTIN_CONFLICT_TRAP"):
                false_matches += 1
        else:
            exc = classify(
                record_id=rid,
                settlement_amount_paise=r.get("settlement_amount_paise"),
                books_amount_paise=r.get("books_total_paise"),
                gstr_amount_paise=r.get("gstr_total_paise"),
                invoice_date=r.get("books_invoice_date"),
                settlement_date=r.get("settlement_date"),
                vendor_gstin_settlement=r.get("vendor_gstin_settlement"),
                vendor_gstin_books=r.get("books_vendor_gstin"),
                supplier_filed=r.get("gstr_supplier_filed", True),
                run_date=run_date,
            )
            ss_results[rid] = ("exception", exc.exception_class, exc)
            exception_classes[exc.exception_class] = (
                exception_classes.get(exc.exception_class, 0) + 1
            )

    ss_matched = sum(1 for v in ss_results.values() if v[0] == "matched")
    ss_rate = ss_matched / total

    # ── Baseline evaluation ────────────────────────────────────────────────
    bl_results = baseline_match(normalized)
    bl_matched = sum(1 for v in bl_results.values() if v == "matched")
    bl_rate = bl_matched / total

    # ── Exception classification accuracy ──────────────────────────────────
    # For records that should be exceptions, did we classify them correctly?
    exc_correct = 0
    exc_total = 0
    for rid, truth in gt.items():
        if truth in ("EXACT_MATCH", "TIMING_DIFF"):
            continue  # these are "matched" class
        if truth == "GSTIN_CONFLICT_TRAP":
            truth = "MISSING_ENTRY"  # expected classification
        exc_total += 1
        result = ss_results.get(rid)
        if result and result[0] == "exception" and result[1] == truth:
            exc_correct += 1

    report = {
        "total_records":          total,
        "settlesync_matched":     ss_matched,
        "settlesync_match_rate":  round(ss_rate * 100, 2),
        "baseline_matched":       bl_matched,
        "baseline_match_rate":    round(bl_rate * 100, 2),
        "improvement_pp":         round((ss_rate - bl_rate) * 100, 2),
        "false_matches":          false_matches,
        "false_match_rate":       round(false_matches / total * 100, 2),
        "exception_classes":      exception_classes,
        "exc_classification_accuracy": (
            round(exc_correct / exc_total * 100, 2) if exc_total else 0
        ),
        "exc_classified_correctly":  exc_correct,
        "exc_total":                 exc_total,
    }

    # Save results (commit this file)
    out_path = Path("evaluation/results/latest.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    r = evaluate()
    print("\n── SETTLESYNC EVALUATION ──────────────────────────────────")
    print(f"Total records:              {r['total_records']}")
    print(f"SettleSync match rate:      {r['settlesync_match_rate']:.1f}%")
    print(f"Baseline match rate:        {r['baseline_match_rate']:.1f}%")
    print(f"Improvement over baseline:  +{r['improvement_pp']:.1f} pp")
    print(f"False matches:              {r['false_matches']}  ({r['false_match_rate']:.1f}%)")
    print(f"Exception classification:   {r['exc_classification_accuracy']:.1f}% accurate")
    print()
    print("Exception breakdown:")
    for cls, count in sorted(r["exception_classes"].items()):
        print(f"  {cls:20s}: {count}")
    print("───────────────────────────────────────────────────────────")