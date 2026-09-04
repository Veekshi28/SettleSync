# SettleSync — AI Finance Controller

> A controller that decides whether a merchant's books are safe to close —
> not a tool that reconciles records and stops there.

**Razorpay Buildathon 2026 · Track 04 · AI Finance Controller**

Built for [Razorpay Agent Studio](https://razorpay.com/agent-studio/),
which is explicitly positioned around agents that perform real business workflows —
not chatbots that explain financial data.

---

### Headline metrics (from `python -m evaluation.run`, committed at [evaluation/results/latest.json](evaluation/results/latest.json))

| Metric | Result |
|---|---|
| Records processed | **77** |
| Auto-resolved | **40** |
| Baseline match rate (naive exact string match) | 22.08% |
| SettleSync match rate | **51.95%** (+29.87 pp over baseline) |
| False auto-matches | **0** (0.0%) |
| Exception classification accuracy | **100%** (37/37) |
| Unsafe closure rate | **0%** (0/77) |
| Silent drops | **0** |
| Abstention quality | **100%** (37/37 ambiguous records correctly escalated) |
| Total ITC at risk (quantified, not just flagged) | **₹43,81,337.72** |
| Confidence calibration | **Well-calibrated** — 40/40 high-confidence (0.95–1.00) matches, 100% precision |

> **"Our most important AI capability is knowing when not to act."**

The 37 records SettleSync does *not* auto-resolve are exactly the 37 the synthetic
ground truth says should require human review: 12 TDS-driven amount mismatches,
8 unfiled-supplier (Rule 37A) records, 8 lapsed-ITC (Section 16(4)) records, and
9 missing/unverifiable entries (including the 2-record GSTIN-conflict trap). Zero
of them slip through as a false auto-match. Every one of those 37 records also
carries a deterministic ₹ risk figure by class:

| Exception class | Count | ITC at risk |
|---|---|---|
| RULE_37A | 8 | ₹17,41,943.00 |
| ITC_TIME_BAR | 8 | ₹12,64,969.00 |
| MISSING_ENTRY | 9 | ₹11,31,612.00 |
| AMOUNT_MISMATCH | 12 | ₹2,42,813.72 |

`evaluation/results/latest.json` also includes a **confidence calibration** table —
for each auto-resolved record, does the engine's reported match confidence actually
track real precision? On this dataset the exact-match pass is the only one
exercised (fuzzy/timing-adjusted matches don't occur in the synthetic data), so
all 40 auto-resolved records land in the 0.95–1.00 confidence bucket at 100%
precision — `"calibration_quality": "Well-calibrated"`.

---

### What it does

1. Ingests three financial sources: Razorpay settlement report, merchant books, GSTR-2B
2. Runs a deterministic three-way match engine (exact → fuzzy → timing-adjusted),
   gated on GSTR-2B compliance signals so a record can't auto-close just because
   its amounts happen to reconcile
3. Classifies unmatched records into a five-class Finance Exception Taxonomy — plus
   a sixth, non-risk **GSTR2B_PENDING** state for current-period invoices checked
   before GSTN's 14th-of-the-month generation date — and quantifies a deterministic
   ₹ ITC risk figure for every real exception
4. Groups related exceptions into review clusters (same vendor, same TDS rate,
   same cross-period settlement window) so a CA reviews clusters, not individual rows
5. Gives every exception a deterministic, ICAI/CGST-grounded resolution checklist
   (core/playbook.py) — checking a step is a human action recorded on the audit ledger
6. Shows a per-vendor compliance scorecard (Clean/Watch/Critical/Pending) computed
   purely from batch data
7. Enforces six Close Gates — deterministic rules that collectively answer "can we
   close?" — with thresholds the merchant can configure live from the sidebar
8. Computes a Close Readiness Score (0–100) visible at the top of the control tower
9. Runs a pre-flight scan of the settlement CSV alone — before books/GSTR-2B are
   even read — to predict exception risk ahead of a full reconciliation run
10. Routes exceptions to human review with AI-generated explanations (advisory only)
11. Lets you **ask the controller** natural-language questions about the current
    batch ("What's blocking close?", "Which vendor has the most ITC at risk?") —
    the answer is assembled from already-computed deterministic data; the LLM only
    puts it into plain English, with a fully deterministic fallback when unavailable
12. Requires human sign-off before authorizing close — and refuses override on the
    three gates POLICY.md marks as absolute constraints
13. Records every decision in a hash-chained, tamper-evident audit ledger, tracks
    run-over-run trends in SQLite, and exports a one-page Close Pack PDF on authorization

---

### Where AI is NOT used

Financial matching, amount comparisons, state transitions, close gate decisions,
and audit logging are fully deterministic. The LLM has no execution authority.

### Where AI is used

Claude generates plain-English explanations for exception records — helping the
finance controller understand why a mismatch occurred and what to do.
The explanation is advisory. The human decides. If the LLM is unavailable, the
batch continues with deterministic template explanations — zero financial
decisions are ever gated on LLM availability.

### Design principle

**"A controller decides whether the books are safe to close.  
A reconciliation tool just matches rows."**

See [POLICY.md](POLICY.md) for the complete operating rules and
[WHATBROKE.md](WHATBROKE.md) for the real bugs found and fixed during development.

---

### Quickstart

```bash
git clone https://github.com/YOU/settlesync
cd settlesync
pip install -r requirements.txt
python -m data.generate          # generates 77 synthetic records + ground truth
python -m pytest tests/ -v       # 19 tests covering the real failure cases + all 6 features
python -m evaluation.run         # prints all metrics including unsafe closure rate + ITC risk

cd frontend && npm install && npm run build && cd ..
uvicorn api.main:app --reload --port 8000     # backend + built React UI, at localhost:8000
```

For frontend development with hot reload, run `npm run dev` in `frontend/` instead
of `npm run build` — the Vite dev server proxies `/api` to the FastAPI backend on
:8000 (see `frontend/vite.config.js`).

Optional: set `ANTHROPIC_API_KEY` for live Claude narration and for "Ask the
Controller" to answer in natural language via Claude. Without it, both features
still fully work — the narrator falls back to deterministic templates, and the
query panel computes a real, data-backed answer deterministically for the common
questions (what's blocking close, which vendor is riskiest, RULE_37A counts,
batch summaries), labelling the response "deterministic" instead of "via Claude".
The key is never hardcoded in source — it's read from the environment only:
```bash
export ANTHROPIC_API_KEY=your_key_here
```

### Architecture

A FastAPI backend (`api/`) is a thin HTTP layer over the same deterministic Python
pipeline described above — it adds no business logic of its own. A React (Vite)
frontend (`frontend/`) is the only UI; the previous Streamlit app has been retired.
See [CLAUDE.md](CLAUDE.md) for the full endpoint list, page-by-page UI spec, and
design-token reference.
