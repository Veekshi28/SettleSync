# What broke, and how we got out

## Incident 001 — Fuzzy matching over-merged vendors with same name, different GSTIN

**What happened:**  
During early testing, `Sharma Enterprises (GSTIN A)` was being fuzzy-matched against
`Sharma Enterprises (GSTIN B)` — a 100% name similarity score caused an automatic
match with 95%+ confidence. Two records were being incorrectly resolved as EXACT_MATCH
when they were actually MISSING_ENTRY (different legal entities).

**How we found it:**  
A GSTIN-conflict trap was deliberately built into the synthetic data generator.
The ground truth evaluator flagged 2 false matches when we first ran `evaluation/run.py`.

**Fix:**  
Every matching pass now requires GSTIN agreement as a blocking condition — checked
before any invoice-ID or vendor-name comparison runs. If GSTINs differ, the record is
refused outright and falls through to classification as MISSING_ENTRY, regardless of
how similar the vendor names look. Added `test_gstin_conflict_blocks_match` to the
test suite.

**Result:** False match rate dropped from 2.5% → 0%.

---

## Incident 002 — ITC time-bar classifier fired on current-year invoices

**What happened:**  
The ITC_TIME_BAR classifier was incorrectly flagging invoices from FY2025-26 as
time-barred. Root cause: the financial year detection function returned the wrong
year for invoices dated between January and March (Q4 of the fiscal year).

**How we found it:**  
`test_itc_NOT_time_barred_current_fy` failed. The bug was a one-liner:
`return d.year - 1 if d.month <= 3 else d.year` was incorrectly written as
`d.month < 3` (using `<` instead of `<=`), missing March invoices.

**Fix:**  
Corrected the boundary condition. All months ≤ 3 (Jan, Feb, Mar) belong to the
previous financial year's Q4. Added targeted test cases for Jan, Feb, and March dates.

---

## Incident 003 — LLM narration blocked batch processing when API was rate-limited

**What happened:**  
During a full batch test run, the Claude API returned a 429 rate-limit error
mid-batch. Because the narration call was not wrapped in try/except, the
entire batch loop crashed and no ledger events were written for the remaining records.

**How we found it:**  
Deliberately ran the batch with a saturated API key during testing.

**Fix:**  
`agent/narrator.py` wraps every API call in try/except. On any exception,
`explain_exception()` returns the deterministic template string and `used_llm=False`.
The batch continues regardless. Zero financial decisions are ever gated on LLM
availability.

---

## Incident 004 — Evaluation had no valid join key back to ground truth

**What happened:**  
`ground_truth.csv` was keyed by an internal synthetic-data id (`RPZ-0001`, ...) that
never appears in `settlements.csv`, `books.csv`, or `gstr2b.csv` — the three CSVs a
real pipeline actually ingests. `evaluation/run.py` looked up every result by that id
and silently found nothing, so `silent_drops` read 77/77 and classification accuracy
read 0% even though the underlying matching and classification were correct.

**How we found it:**  
The headline evaluation numbers didn't move no matter what we fixed in `classify.py`
or `match.py` — a sign the join itself, not the logic, was broken.

**Fix:**  
`record_id` is now the Razorpay settlement `txn_id` end-to-end — the one identifier
every source in the pipeline (including MISSING_ENTRY and GSTIN_CONFLICT_TRAP records,
which have no books entry) actually carries. `ground_truth.csv` is generated keyed by
the same `txn_id`.

---

## Incident 005 — Synthetic TIMING_DIFF and ITC_TIME_BAR records shared a fiscal year

**What happened:**  
`TIMING_DIFF` invoices (dated March 31) and `ITC_TIME_BAR` invoices both fell inside
FY2024-25, so once evaluation ran with a `run_date` past the Nov 30, 2025 Section
16(4) deadline, all 15 `TIMING_DIFF` records also tripped the ITC time-bar check and
were reclassified as `ITC_TIME_BAR` — a 15-record swing in the exception breakdown
with zero code changes.

**How we found it:**  
`evaluation/run.py` reported 23 `ITC_TIME_BAR` records against a ground truth of 8,
and the match rate was 20 points below what the dataset's category counts implied.

**Fix:**  
Moved the `TIMING_DIFF` synthetic invoices to FY2025-26 so their Section 16(4)
deadline (Nov 30, 2026) can't collide with FY2024-25's. The two exception classes are
now generated from genuinely disjoint fiscal years, independent of which date the
evaluation happens to run on.
