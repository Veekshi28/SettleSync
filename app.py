"""
SettleSync — Streamlit UI
Run: streamlit run app.py
"""
import streamlit as st
import pandas as pd
import time
from pathlib import Path

st.set_page_config(
    page_title="SettleSync",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Session state init ────────────────────────────────────────────────────
if "batch" not in st.session_state:
    st.session_state.batch = None
if "ledger" not in st.session_state:
    from audit.ledger import AuditLedger
    st.session_state.ledger = AuditLedger("audit/ledger.jsonl")
if "records_df" not in st.session_state:
    st.session_state.records_df = None

ledger = st.session_state.ledger

# ── Navigation ────────────────────────────────────────────────────────────
tabs = st.tabs([
    "⬛ Control Tower",
    "📋 Reconciliation",
    "⚠️ Exceptions",
    "🔗 Audit & Evaluation",
    "📘 About",
])

# ═══════════════════════════════════════════════════════════════════════════
# TAB 1 — CONTROL TOWER
# ═══════════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.markdown("## SettleSync — Finance Control Tower")
    st.caption(
        "AI-assisted reconciliation for Razorpay merchants · "
        "Built for [Razorpay Agent Studio](https://razorpay.com/agent-studio/)"
    )
    st.divider()

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("**Batch data sources**")
        use_demo = st.checkbox("Use synthetic demo data (80 records)", value=True)
        if not use_demo:
            c1, c2, c3 = st.columns(3)
            s_file = c1.file_uploader("Razorpay settlements", type="csv")
            b_file = c2.file_uploader("Merchant books", type="csv")
            g_file = c3.file_uploader("GSTR-2B data", type="csv")

    with col_right:
        st.markdown("&nbsp;")
        run = st.button(
            "▶ Run reconciliation",
            type="primary",
            use_container_width=True,
            disabled=(st.session_state.batch is not None),
        )
        if st.session_state.batch:
            if st.button("🔄 Reset batch", use_container_width=True):
                st.session_state.batch = None
                st.session_state.records_df = None
                st.rerun()

    if run:
        from core.state import BatchState, RecordState
        from core.ingest import load_all
        from core.normalize import normalize_all
        from core.match import run_three_way_match
        from core.classify import classify
        from agent.narrator import explain_exception

        batch = BatchState()
        st.session_state.batch = batch

        ledger.append("BATCH_START")

        activity_box = st.empty()
        log_lines = []

        def activity(record_id: str, msg: str, icon: str = "🔄"):
            ts = time.strftime("%H:%M:%S")
            log_lines.append(f"`{ts}` {icon} **{record_id}** — {msg}")
            activity_box.markdown("\n\n".join(log_lines[-18:]))

        with st.spinner("Agent processing batch..."):
            records = load_all(
                "data/synthetic/settlements.csv",
                "data/synthetic/books.csv",
                "data/synthetic/gstr2b.csv",
            )
            normalized = normalize_all(records)
            ledger.append("INGESTED", detail={"count": len(normalized)})

            rows = []
            for r in normalized:
                rid = r["record_id"]
                entry = batch.add(rid, raw=r)

                entry.transition(RecordState.INGESTED)
                entry.transition(RecordState.NORMALIZED)
                entry.transition(RecordState.MATCHING)

                match = run_three_way_match(r)
                ledger.append("match_attempt", rid,
                               match_type=match.get("type"),
                               confidence=match.get("confidence", 0))

                if match["matched"]:
                    entry.match_type = match["type"]
                    entry.match_confidence = match["confidence"]
                    entry.transition(RecordState.RESOLVED)
                    ledger.append("resolved", rid, match_type=match["type"])
                    activity(rid, f"{match['type']} match @ {match['confidence']:.0%}", "✅")
                    row_status = "Resolved"
                    row_exc = ""
                else:
                    entry.transition(RecordState.EXCEPTION)
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
                    )
                    entry.exception_class = exc.exception_class
                    entry.exception_rule = exc.icai_citation
                    entry.exception_confidence = exc.confidence
                    ledger.append("classified", rid, exception_class=exc.exception_class)

                    narrative, used_llm = explain_exception(
                        r, exc.exception_class,
                        exc.explanation, exc.icai_citation, exc.resolution_hint,
                    )
                    entry.exception_narrative = narrative
                    entry.transition(RecordState.AI_REVIEW)
                    entry.transition(RecordState.HUMAN_REQUIRED)
                    ledger.append("human_required", rid,
                                  exception_class=exc.exception_class,
                                  llm_used=used_llm)
                    activity(rid, f"exception: {exc.exception_class} ({exc.confidence:.0%})", "⚠️")
                    row_status = "Needs review"
                    row_exc = exc.exception_class

                rows.append({
                    "Record ID": rid,
                    "Match type": entry.match_type or "—",
                    "Confidence": f"{entry.match_confidence:.0%}" if entry.match_type else "—",
                    "Exception": row_exc,
                    "Status": entry.status_label,
                    "_entry": entry,  # hidden
                })
                time.sleep(0.03)  # dramatic agent activity effect

        st.session_state.records_df = rows
        ledger.append("BATCH_COMPLETE", detail=batch.summary())
        st.rerun()

    # Metrics cards
    if st.session_state.batch:
        s = st.session_state.batch.summary()
        total = s["total"] or 1
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Records", s["total"])
        c2.metric("Auto-resolved", s["resolved"],
                  f"{s['resolved']/total*100:.1f}%")
        c3.metric("Awaiting review", s["human_required"])
        c4.metric("Escalated", s["escalated"])

        st.divider()
        st.markdown("**Agent activity — last 20 actions**")
        for ev in reversed(st.session_state.batch.activity[-20:]):
            st.markdown(
                f"`{ev['ts']}` **{ev['record_id']}** — "
                f"{ev['action']}: {ev['detail']}"
            )


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2 — RECONCILIATION TABLE
# ═══════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown("## Reconciliation")
    if not st.session_state.records_df:
        st.info("Run reconciliation from the Control Tower tab first.")
    else:
        rows = st.session_state.records_df
        display = [
            {k: v for k, v in r.items() if k != "_entry"}
            for r in rows
        ]
        df = pd.DataFrame(display)

        status_filter = st.selectbox(
            "Filter by status",
            ["All", "Resolved", "Needs review", "Approved", "Escalated"],
        )
        if status_filter != "All":
            df = df[df["Status"].str.contains(status_filter, case=False, na=False)]

        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(df)} of {len(rows)} records")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 3 — EXCEPTION CENTER (THE DEMO CLIMAX)
# ═══════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown("## Exception Center")
    if not st.session_state.records_df or not st.session_state.batch:
        st.info("Run reconciliation from the Control Tower tab first.")
    else:
        exc_class_filter = st.selectbox(
            "Filter by exception class",
            ["All", "RULE_37A", "ITC_TIME_BAR", "AMOUNT_MISMATCH",
             "TIMING_DIFF", "MISSING_ENTRY"],
        )

        batch = st.session_state.batch
        exception_entries = [
            e for e in batch.records.values()
            if e.exception_class is not None
        ]
        if exc_class_filter != "All":
            exception_entries = [
                e for e in exception_entries
                if e.exception_class == exc_class_filter
            ]

        if not exception_entries:
            st.success("No exceptions in this filter.")
        else:
            for entry in exception_entries:
                with st.expander(
                    f"**{entry.record_id}** — {entry.exception_class} "
                    f"({entry.exception_confidence:.0%} confidence)",
                    expanded=False,
                ):
                    col_info, col_action = st.columns([2, 1])

                    with col_info:
                        r = entry.raw
                        st.markdown("**Amounts**")
                        amt_data = {
                            "Source": ["Settlement", "Books", "GSTR-2B"],
                            "Amount (₹)": [
                                f"₹{r.get('settlement_amount_paise', 0)/100:,.2f}",
                                f"₹{(r.get('books_total_paise') or 0)/100:,.2f}",
                                f"₹{(r.get('gstr_total_paise') or 0)/100:,.2f}",
                            ],
                        }
                        st.dataframe(pd.DataFrame(amt_data), hide_index=True)

                        st.markdown("**Agent explanation**")
                        st.info(entry.exception_narrative or "No narrative available.")

                        st.markdown("**ICAI rule reference**")
                        st.caption(entry.exception_rule or "—")

                    with col_action:
                        st.markdown("**Human review**")
                        if entry.human_action:
                            st.success(f"Action taken: {entry.human_action}")
                            if entry.human_note:
                                st.caption(f"Note: {entry.human_note}")
                        else:
                            note = st.text_input(
                                "Review note (optional)",
                                key=f"note_{entry.record_id}",
                            )
                            col_a, col_b = st.columns(2)
                            if col_a.button(
                                "✅ Approve",
                                key=f"approve_{entry.record_id}",
                                use_container_width=True,
                            ):
                                from core.state import RecordState
                                entry.human_action = "approved"
                                entry.human_note = note
                                entry.transition(RecordState.APPROVED, actor="human")
                                ledger.append(
                                    "human_approved", entry.record_id,
                                    actor="human", note=note,
                                )
                                st.rerun()

                            if col_b.button(
                                "🔺 Escalate",
                                key=f"escalate_{entry.record_id}",
                                use_container_width=True,
                            ):
                                from core.state import RecordState
                                entry.human_action = "escalated"
                                entry.human_note = note
                                entry.transition(RecordState.ESCALATED, actor="human")
                                ledger.append(
                                    "human_escalated", entry.record_id,
                                    actor="human", note=note,
                                )
                                st.rerun()

                            if st.button(
                                "❌ Reject",
                                key=f"reject_{entry.record_id}",
                                use_container_width=True,
                            ):
                                from core.state import RecordState
                                entry.human_action = "rejected"
                                entry.human_note = note
                                entry.transition(RecordState.REJECTED, actor="human")
                                ledger.append(
                                    "human_rejected", entry.record_id,
                                    actor="human", note=note,
                                )
                                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# TAB 4 — AUDIT & EVALUATION
# ═══════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown("## Audit & Evaluation")

    col_audit, col_eval = st.columns(2)

    with col_audit:
        st.markdown("**Audit ledger — last 25 events**")
        events = ledger.recent(25)
        for e in reversed(events):
            st.markdown(
                f"`#{e.seq:04d}` `{e.timestamp}` **{e.action}** "
                + (f"· {e.record_id}" if e.record_id else "")
                + f"  \n`{e.current_hash[:16]}…`"
            )

        if st.button("🔒 Verify chain integrity"):
            intact, broken_at = ledger.verify()
            if intact:
                st.success(f"✅ {len(ledger)} events verified — chain intact.")
            else:
                st.error(f"❌ Tamper detected at sequence #{broken_at}.")

    with col_eval:
        st.markdown("**Evaluation metrics**")
        try:
            import json
            with open("evaluation/results/latest.json") as f:
                results = json.load(f)

            st.metric("SettleSync match rate",
                      f"{results['settlesync_match_rate']:.1f}%")
            st.metric("Baseline match rate",
                      f"{results['baseline_match_rate']:.1f}%",
                      delta=f"+{results['improvement_pp']:.1f} pp vs baseline")
            st.metric("False matches", results["false_matches"],
                      delta="target: 0", delta_color="inverse")
            st.metric("Exception classification accuracy",
                      f"{results['exc_classification_accuracy']:.1f}%")

            st.markdown("**Exception breakdown**")
            exc_df = pd.DataFrame([
                {"Class": k, "Count": v}
                for k, v in results.get("exception_classes", {}).items()
            ])
            if not exc_df.empty:
                st.dataframe(exc_df, hide_index=True, use_container_width=True)
        except FileNotFoundError:
            if st.button("▶ Run evaluation"):
                from evaluation.run import evaluate
                with st.spinner("Running evaluation..."):
                    r = evaluate()
                st.success("Evaluation complete.")
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# TAB 5 — ABOUT
# ═══════════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.markdown("## About SettleSync")
    st.markdown("""
**SettleSync** is an AI Finance Controller built for the Razorpay Buildathon (Track 04).

### Where AI is NOT used
Financial matching, amount comparisons, state transitions, and compliance checks are
**fully deterministic**. These operations touch real money and must be reproducible and
auditable. An LLM cannot modify batch state.

### Where AI is used
The agent uses Claude to generate plain-English explanations of unresolved exceptions —
helping a finance controller understand *why* a mismatch happened and what to do.
The AI explanation is advisory only; the human approves or rejects.

### Why that distinction matters
> **"We use AI for ambiguity, not arithmetic."**

This is Razorpay's [Agent Studio](https://razorpay.com/agent-studio/) philosophy:
agents that understand intent, access systems, and perform real business workflows —
not chatbots that talk about finance.

### Architecture
- **Deterministic match engine**: exact → fuzzy (rapidfuzz ≥ 85%) → timing-adjusted
- **ICAI-cited exception taxonomy**: 5 classes grounded in Indian GST law
- **Finite state machine**: 11 states, strict transition rules, no LLM authority
- **Hash-chained audit ledger**: tamper-evident, verifiable, append-only
- **Human-in-the-loop**: Approve / Reject / Escalate on all exception records
""")