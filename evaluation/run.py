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
    itc_at_risk_by_class: dict[str, int] = {}
    total_itc_risk_paise = 0

    for r in normalized:
        rid = r["record_id"]
        match = run_three_way_match(r, run_date=run_date)

        if match["matched"]:
            ss_results[rid] = ("matched", match["type"], match["confidence"])
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
                vendor_gstin_books=r.get("vendor_gstin_books"),
                supplier_filed=r.get("gstr_supplier_filed", True),
                run_date=run_date,
            )
            ss_results[rid] = ("exception", exc.exception_class, exc)
            exception_classes[exc.exception_class] = (
                exception_classes.get(exc.exception_class, 0) + 1
            )
            itc_at_risk_by_class[exc.exception_class] = (
                itc_at_risk_by_class.get(exc.exception_class, 0) + exc.itc_risk_paise
            )
            total_itc_risk_paise += exc.itc_risk_paise

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

    # ── Governance metrics ───────────────────────────────────────────────
    # Unsafe Closure Rate: records auto-resolved that ground truth says
    # should have been exceptions.
    auto_resolved_should_be_exc = 0
    for rid, truth in gt.items():
        if truth in ("RULE_37A", "ITC_TIME_BAR", "AMOUNT_MISMATCH",
                      "MISSING_ENTRY", "GSTIN_CONFLICT_TRAP"):
            result = ss_results.get(rid)
            if result and result[0] == "matched":  # auto-resolved when it shouldn't be
                auto_resolved_should_be_exc += 1

    # Silent drops: records in ground truth not present in results at all
    silent_drops = sum(1 for rid in gt if rid not in ss_results)

    # Abstention quality: of records that should be exceptions,
    # what % were correctly NOT auto-resolved (i.e., correctly escalated)?
    should_be_exceptions = sum(
        1 for truth in gt.values()
        if truth in ("RULE_37A", "ITC_TIME_BAR", "AMOUNT_MISMATCH",
                      "MISSING_ENTRY", "GSTIN_CONFLICT_TRAP")
    )
    correctly_not_auto_resolved = should_be_exceptions - auto_resolved_should_be_exc
    abstention_quality = (
        correctly_not_auto_resolved / should_be_exceptions
        if should_be_exceptions else 1.0
    )

    # ── Confidence calibration ──────────────────────────────────────────────
    # When the engine reports high confidence, does it actually get it right?
    # Only auto-resolved ("matched") records carry a confidence score — a
    # match is "correct" here if ground truth says it was actually safe to
    # auto-resolve (EXACT_MATCH or TIMING_DIFF); any other ground truth on a
    # matched record would be a false match (see unsafe_closure_count above).
    BUCKETS = [(0.50, 0.70), (0.70, 0.85), (0.85, 0.95), (0.95, 1.01)]
    BUCKET_LABELS = ["0.50–0.70", "0.70–0.85", "0.85–0.95", "0.95–1.00"]
    SAFE_TO_MATCH = {"EXACT_MATCH", "TIMING_DIFF"}

    calibration = []
    for (lo, hi), label in zip(BUCKETS, BUCKET_LABELS):
        bucket_records = [
            (rid, result) for rid, result in ss_results.items()
            if result[0] == "matched" and lo <= result[2] <= hi
        ]

        if not bucket_records:
            calibration.append({"bucket": label, "count": 0, "correct": 0, "precision": None})
            continue

        correct = sum(1 for rid, _ in bucket_records if gt.get(rid, "") in SAFE_TO_MATCH)
        precision = round(correct / len(bucket_records) * 100, 1)
        calibration.append({
            "bucket": label,
            "count": len(bucket_records),
            "correct": correct,
            "precision": precision,
        })

    high_conf_bucket = calibration[-1]
    calibration_quality = (
        "Well-calibrated" if high_conf_bucket.get("precision") == 100
        else "Review confidence thresholds"
    )

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
        "total_itc_risk_paise":   total_itc_risk_paise,
        "itc_at_risk_by_class":   itc_at_risk_by_class,
        "exc_classification_accuracy": (
            round(exc_correct / exc_total * 100, 2) if exc_total else 0
        ),
        "exc_classified_correctly":  exc_correct,
        "exc_total":                 exc_total,
        "unsafe_closure_count":    auto_resolved_should_be_exc,
        "unsafe_closure_rate":     round(auto_resolved_should_be_exc / total * 100, 2),
        "silent_drops":            silent_drops,
        "abstention_quality":      round(abstention_quality * 100, 2),
        "should_be_exceptions":    should_be_exceptions,
        "correctly_escalated":     correctly_not_auto_resolved,
        "confidence_calibration":  calibration,
        "calibration_quality":     calibration_quality,
    }

    # Save results (commit this file)
    out_path = Path("evaluation/results/latest.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    r = evaluate()
    print("\n-- SETTLESYNC EVALUATION --------------------------------")
    print(f"Total records:              {r['total_records']}")
    print(f"SettleSync match rate:      {r['settlesync_match_rate']:.1f}%")
    print(f"Baseline match rate:        {r['baseline_match_rate']:.1f}%")
    print(f"Improvement over baseline:  +{r['improvement_pp']:.1f} pp")
    print(f"False matches:              {r['false_matches']}  ({r['false_match_rate']:.1f}%)")
    print(f"Exception classification:   {r['exc_classification_accuracy']:.1f}% accurate")
    print()
    print("Exception breakdown:")
    print(f"Unsafe closure rate:        {r['unsafe_closure_rate']:.1f}% (target: 0%)")
    print(f"Silent drops:               {r['silent_drops']}  (target: 0)")
    print(f"Abstention quality:         {r['abstention_quality']:.1f}% (correctly escalated)")
    print(f"")
    print(f"The headline: {r['unsafe_closure_count']} unsafe auto-closures out of {r['total_records']} records.")
    for cls, count in sorted(r["exception_classes"].items()):
        print(f"  {cls:20s}: {count}")
    print()
    print(f"Total ITC at risk:           Rs {r['total_itc_risk_paise']/100:,.2f}")
    for cls, paise in sorted(r["itc_at_risk_by_class"].items()):
        print(f"  {cls:20s}: Rs {paise/100:,.2f}")
    print()
    print(f"Confidence calibration ({r['calibration_quality']}):")
    for b in r["confidence_calibration"]:
        precision = f"{b['precision']:.1f}%" if b["precision"] is not None else "—"
        print(f"  {b['bucket']:12s}: {b['count']:3d} matched, {precision} precision")
    print("-----------------------------------------------------------")