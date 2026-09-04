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
| Auto-resolved | **40** (51.9%) |
| Baseline match rate (naive exact string match) | 22.1% |
| SettleSync match rate | **51.9%** (+29.9 pp over baseline) |
| False auto-matches | **0** |
| Exception classification accuracy | **100%** (37/37) |
| Unsafe closure rate | **0%** |
| Silent drops | **0** |
| Abstention quality | **100%** (37/37 ambiguous records correctly escalated) |

> **"Our most important AI capability is knowing when not to act."**

The 37 records SettleSync does *not* auto-resolve are exactly the 37 the synthetic
ground truth says should require human review: 12 TDS-driven amount mismatches,
8 unfiled-supplier (Rule 37A) records, 8 lapsed-ITC (Section 16(4)) records, and
9 missing/unverifiable entries (including the 2-record GSTIN-conflict trap). Zero
of them slip through as a false auto-match.

---

### What it does

1. Ingests three financial sources: Razorpay settlement report, merchant books, GSTR-2B
2. Runs a deterministic three-way match engine (exact → fuzzy → timing-adjusted),
   gated on GSTR-2B compliance signals so a record can't auto-close just because
   its amounts happen to reconcile
3. Classifies unmatched records into a five-class Finance Exception Taxonomy
4. Enforces six Close Gates — deterministic rules that collectively answer "can we close?"
5. Computes a Close Readiness Score (0–100) visible at the top of the control tower
6. Routes exceptions to human review with AI-generated explanations (advisory only)
7. Requires human sign-off before authorizing close — and refuses override on the
   three gates POLICY.md marks as absolute constraints
8. Records every decision in a hash-chained, tamper-evident audit ledger

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
python -m pytest tests/ -v       # 10 tests covering the real failure cases
python -m evaluation.run         # prints all metrics including unsafe closure rate
streamlit run app.py             # launches the 6-tab UI
```

Optional: set `ANTHROPIC_API_KEY` for live Claude narration. Without it, the
narrator falls back to deterministic templates and the batch still runs fully.
