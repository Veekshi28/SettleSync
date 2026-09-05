# SettleSync — AI Finance Controller

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

---

> **"A controller that decides whether a merchant's books are safe to close —
> not a tool that reconciles records and stops there."**

**Razorpay Buildathon 2026 · Track 04 · AI Finance Controller**

---

### Where AI is NOT used

Financial matching, amount comparisons, state transitions, close gate decisions,
and audit logging are fully deterministic. The LLM has no execution authority.

### Where AI is used

Claude generates plain-English explanations for exception records — helping the
finance controller understand why a mismatch occurred and what to do — and answers
natural-language questions in "Ask the Controller" by rephrasing an already-computed
context dict into plain English. Both are advisory only; the human decides, and both
fall back to deterministic output (templates / a computed answer) if the LLM is
unavailable. Zero financial decisions are ever gated on LLM availability.

---

### Quickstart

```bash
pip install -r requirements.txt && python -m data.generate
cd frontend && npm install && npm run build && cd ..
uvicorn api.main:app --port 8000
```

Open `http://localhost:8000` — all 6 pages (Control Tower, Reconciliation, Exception
Center, Vendor Intelligence, Close Review, Audit & Evaluation) are served from this
one process.

---

### Verify it

```bash
python -m pytest tests/ -v       # 26 tests covering the real failure cases + every feature
python -m evaluation.run         # regenerates evaluation/results/latest.json
```

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

For frontend development with hot reload, run `npm run dev` in `frontend/` instead
of `npm run build` — the Vite dev server proxies `/api` to the FastAPI backend on
:8000 (see `frontend/vite.config.js`).

---

### The 37 records that don't auto-resolve

Exactly the 37 the synthetic ground truth says should require human review:
12 TDS-driven amount mismatches, 8 unfiled-supplier (Rule 37A) records, 8 lapsed-ITC
(Section 16(4)) records, and 9 missing/unverifiable entries (including the 2-record
GSTIN-conflict trap). Zero of them slip through as a false auto-match. Every one
also carries a deterministic ₹ risk figure by class:

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
    batch ("What's blocking close?", "Which vendor has the most ITC at risk?")
12. Requires human sign-off before authorizing close — and refuses override on the
    three gates POLICY.md marks as absolute constraints
13. Records every decision in a hash-chained, tamper-evident audit ledger, tracks
    run-over-run trends in SQLite, and exports a one-page Close Pack PDF on authorization

### Architecture

A FastAPI backend (`api/`) is a thin HTTP layer over the same deterministic Python
pipeline described above — it adds no business logic of its own. A React (Vite)
frontend (`frontend/`) is the only UI; the previous Streamlit app has been retired.
See [POLICY.md](POLICY.md) for the complete operating rules, [WHATBROKE.md](WHATBROKE.md)
for the real bugs found and fixed during development, and [CLAUDE.md](CLAUDE.md) for
the full endpoint list, page-by-page UI spec, and design-token reference.
