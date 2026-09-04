"""
"Ask the Controller" — natural-language Q&A over the current batch.

The correct division of labor: data retrieval and every number in the answer
come from the deterministic pipeline (core/, audit/). The LLM (Claude, via the
anthropic SDK) only translates an already-computed context dict into plain
English — it cannot see anything the deterministic layer didn't already
compute, and it has zero execution authority, same as agent/narrator.py. If
ANTHROPIC_API_KEY is unset or the call fails, a deterministic fallback
computes a real answer for the common questions so the panel never depends
on LLM availability.
"""
import json
import os

from fastapi import APIRouter
from pydantic import BaseModel

from core.close_gate import run_close_gates, compute_readiness_score, can_close
from api import state
from api.routers.vendors import list_vendors

router = APIRouter()

ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You are the SettleSync Finance Controller assistant.
Answer questions about the current batch state using only the
data provided — never invent numbers. Be direct and specific.
Lead with the answer, then one sentence of context if needed.
Use ₹ for amounts. 3 sentences maximum."""


class QueryBody(BaseModel):
    question: str


def _build_context() -> dict:
    batch = state.batch
    if batch is None:
        return {}

    gates = run_close_gates(
        batch=batch, ledger=state.ledger, thresholds=state.thresholds,
        sources_loaded={"settlements": True, "books": True, "gstr2b": True},
    )
    score = compute_readiness_score(gates)
    ready, blockers = can_close(gates)

    exception_entries = [e for e in batch.records.values() if e.exception_class is not None]
    top_exceptions = sorted(exception_entries, key=lambda e: e.itc_risk_paise, reverse=True)[:5]

    vendors = list_vendors()
    top_vendors = sorted(vendors, key=lambda v: v["itc_risk_paise"], reverse=True)[:5]

    total_itc_risk = sum(e.itc_risk_paise for e in batch.records.values())
    unresolved_variance = sum(
        e.raw.get("settlement_amount_paise", 0)
        for e in batch.records.values()
        if e.state.value in ("HUMAN_REQUIRED", "EXCEPTION", "AI_REVIEW")
    )

    return {
        "batch_summary": batch.summary(),
        "close_readiness_score": score,
        "can_close": ready,
        "blocking_gates": [b.name for b in blockers],
        "top_exceptions_by_risk": [
            {
                "record_id": e.record_id,
                "exception_class": e.exception_class,
                "itc_risk_paise": e.itc_risk_paise,
                "vendor_gstin": e.raw.get("vendor_gstin_settlement"),
                "settlement_amount": e.raw.get("settlement_amount_paise"),
                "human_action": e.human_action,
            }
            for e in top_exceptions
        ],
        "vendor_summary": [
            {
                "gstin": v["gstin"],
                "name": v["name"],
                "rule_37a_count": v["rule_37a"],
                "itc_risk_paise": v["itc_risk_paise"],
                "status": v["status"],
            }
            for v in top_vendors
        ],
        "total_itc_risk_paise": total_itc_risk,
        "unresolved_variance_paise": unresolved_variance,
        "thresholds": state.thresholds,
    }


def _deterministic_answer(question: str, context: dict) -> str:
    """Computes a real answer with no LLM — covers the common questions
    literally so the panel is fully usable without ANTHROPIC_API_KEY."""
    q = question.lower()

    if "block" in q:
        blockers = context["blocking_gates"]
        if not blockers:
            return "Nothing is blocking close — all gates pass."
        return f"{len(blockers)} gate(s) are blocking close: {', '.join(blockers)}."

    if "vendor" in q and ("most" in q or "risk" in q or "which" in q):
        vendors = context["vendor_summary"]
        if not vendors:
            return "No vendor data available."
        top = vendors[0]
        return (
            f"{top['name']} (GSTIN {top['gstin']}) has the most ITC at risk: "
            f"₹{top['itc_risk_paise']/100:,.2f}, status {top['status']}."
        )

    if "37a" in q.replace("_", "").replace("-", "").replace(" ", ""):
        total_37a = context["batch_summary"].get("exception_classes", {}).get("RULE_37A", 0)
        return f"{total_37a} RULE_37A exception(s) need review in this batch."

    if "total" in q and ("itc" in q or "risk" in q):
        return f"Total ITC at risk in this batch: ₹{context['total_itc_risk_paise']/100:,.2f}."

    if "summar" in q:
        s = context["batch_summary"]
        return (
            f"{s['total']} records processed: {s['resolved']} auto-resolved, "
            f"{s['human_required']} awaiting review. Close Readiness Score: "
            f"{context['close_readiness_score']}/100 "
            f"({'ready to close' if context['can_close'] else 'blocked'}). "
            f"Total ITC at risk: ₹{context['total_itc_risk_paise']/100:,.2f}."
        )

    s = context["batch_summary"]
    return (
        f"Close Readiness Score is {context['close_readiness_score']}/100 "
        f"({'ready to close' if context['can_close'] else 'blocked'}). "
        f"{s['human_required']} record(s) await review, "
        f"₹{context['total_itc_risk_paise']/100:,.2f} total ITC at risk."
    )


@router.post("/api/query")
def ask_controller(body: QueryBody):
    context = _build_context()

    if not context:
        return {
            "answer": "No batch has been run yet. Run reconciliation from the Control Tower first.",
            "used_llm": False,
            "context_keys_used": [],
        }

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "answer": _deterministic_answer(body.question, context),
            "used_llm": False,
            "context_keys_used": list(context.keys()),
        }

    try:
        from anthropic import Anthropic

        client = Anthropic()  # reads ANTHROPIC_API_KEY from environment
        prompt = f"Batch data:\n{json.dumps(context, indent=2)}\n\nQuestion: {body.question}"

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = response.content[0].text.strip()
        return {"answer": answer, "used_llm": True, "context_keys_used": list(context.keys())}
    except Exception:
        # Graceful degradation — same invariant as agent/narrator.py: LLM
        # failure never blocks the deterministic answer.
        return {
            "answer": _deterministic_answer(body.question, context),
            "used_llm": False,
            "context_keys_used": list(context.keys()),
        }
