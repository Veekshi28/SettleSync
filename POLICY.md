# SettleSync Finance Controller — Operating Policy

> These rules govern every decision the controller makes.
> They are not suggestions. Violations halt the operation.

---

## The Ten Rules

**Rule 1 — Never fabricate financial evidence.**
The controller will not infer, estimate, or generate amounts, dates, or identifiers
it cannot verify against an ingested source document.

**Rule 2 — Never auto-close an ambiguous record.**
When matching confidence falls below policy threshold, the record is escalated.
The controller does not guess. Abstention is the correct decision for uncertain cases.

**Rule 3 — The language model has no authority over financial state.**
The LLM may explain. It may summarize. It may suggest. It may not resolve, approve,
reject, or close any record. State transitions belong to the deterministic engine
and to human reviewers.

**Rule 4 — Every automatic decision must be reproducible.**
Given the same input data and the same seed, the controller must produce identical
output. Non-deterministic auto-resolution is a policy violation.

**Rule 5 — Every closed record must have traceable evidence.**
An auto-resolved record without a verifiable matching chain is not closed — it is lost.
The "Why was this auto-closed?" query must return a complete answer for every record.

**Rule 6 — Material variances block close.**
Any unresolved financial variance exceeding the configured threshold prevents
close authorization. The threshold is configurable by the merchant; the enforcement is not.

**Rule 7 — Conflicting identifiers block auto-resolution.**
Records where vendor name similarity is high but GSTINs differ are not fuzzy-matched.
They are classified as MISSING_ENTRY and escalated. Identity conflicts are not
resolved probabilistically.

**Rule 8 — AI-generated explanations are advisory, not authoritative.**
The LLM explanation on an exception record is a hypothesis, not a finding.
The human reviewer is responsible for the decision. The explanation assists; it does not decide.

**Rule 9 — AI service failure must not block deterministic reconciliation.**
When the LLM API is unavailable, the reconciliation engine continues using
deterministic template explanations. Zero financial decisions are gated on LLM availability.

**Rule 10 — Every state transition produces an audit event.**
The ledger is append-only. Events are hash-chained. No state changes without a record.
The audit trail is not a feature — it is a constitutional requirement.

---

## Close Gate Policy

The controller will not authorize close unless all six gates pass:

| Gate | Threshold (default) | Override allowed? |
|---|---|---|
| Data integrity | All 3 sources loaded | No |
| Reconciliation rate | ≥ 85% resolved | Yes, with justification |
| Material variance | ≤ ₹10,000 unresolved | Yes, with justification |
| Compliance exceptions | 0 open RULE_37A / ITC_TIME_BAR | Yes, with justification |
| Rule 37A review | All Rule 37A records human-reviewed | No |
| Audit chain | Ledger intact | No |

Gate overrides are logged as immutable ledger events with the reviewer's justification.
Some gates cannot be overridden — they represent absolute constraints.

---

## Trust Boundary