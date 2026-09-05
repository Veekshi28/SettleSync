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

---

## Incident 006 — Threshold slider changes were silently reverted by the status poll

**What happened:**  
`ControlTower.jsx` polls `GET /api/batch/status` every 2 seconds while a batch is
loaded, and that poll's callback (`refreshStatus`) also re-fetches the close gates
using the current threshold values. `refreshStatus` was memoized with `useCallback`
whose dependency array only listed `refreshGates` — not `thresholds` — so it closed
over whatever `thresholds` value existed at the moment it was first created. Every
2-second poll tick then called `refreshGates` with that stale snapshot, silently
overwriting the Close Readiness Score and gate statuses back to the *old* thresholds
within seconds of a user dragging a slider. The UI would flash the correct, updated
score for a moment and then revert it, with no error and no indication anything
had gone wrong.

**How we found it:**  
Caught in code review before any browser testing: tracing `refreshStatus`'s
dependency array against where `thresholds` was read showed a classic React stale-
closure shape — a `useCallback`/interval combination that captures state at creation
time instead of at call time.

**Fix:**  
Added a `thresholdsRef` that is reassigned to the latest `thresholds` value on every
render (`thresholdsRef.current = thresholds`), and changed `refreshStatus` to read
`thresholdsRef.current` instead of the closed-over `thresholds` variable. The ref is
always current regardless of when the enclosing callback was created, so the poll
and the user's slider changes stay consistent.

**Result:** Verified via Playwright — lowering `min_match_rate` from 0.85 to 0.50
now keeps the RECONCILIATION gate passed across multiple 2-second poll cycles,
instead of reverting to BLOCKED within one cycle.

---

## Incident 007 — Pre-flight TDS heuristic flagged 100% of settlements

**What happened:**  
The pre-flight scan's `looks_like_tds` check flagged a settlement amount as a likely
TDS adjustment using `abs(gross - round(gross, -2)) < 50`, where `gross` is the
reconstructed pre-TDS amount. `round(x, -2)` rounds to the nearest hundred, which by
definition is never more than 50 away from `x` — the comparison was true for almost
every amount regardless of whether it had anything to do with TDS. The endpoint
reported 77 of 77 settlements (100%) as "Likely TDS adjustments," a number with no
discriminating signal at all.

**How we found it:**  
A live browser check of the pre-flight card showed every single risk-indicator row
at the same implausible count — no real settlement batch has 100% TDS incidence.
Cross-checking against the synthetic dataset's actual ground truth showed only 12
of 77 records are true `AMOUNT_MISMATCH` (TDS) cases.

**Fix:**  
Replaced the tautological rounding check with a distance-to-whole-rupee test:
reconstruct `gross = net / (1 - rate)` for each of the 1%/2%/10% TDS rates and flag
the amount only when `gross` lands within 5 paise of an exact rupee value
(`min(gross % 100, 100 - gross % 100) < 5`) — a test that is only true for amounts
that actually reconstruct to a round gross figure, not for arbitrary numbers.

**Result:** Flagged count dropped from 77/77 (100%, meaningless) to 33/77 (43%), a
plausible heuristic result given the true count of 12 TDS-driven records plus
coincidental matches inherent to any settlement-only (no-books) heuristic.
