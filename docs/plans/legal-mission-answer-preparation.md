# Bounded preparation of the complete legal answer

9 October 2026, after the user's instruction to continue. This is one engineering
attempt returning to the existing `product-contribution` task. The earlier
90-minute checkpoint is spent and its results remain sealed. This reviewed
revision adds at most 90 minutes of local preparation, counted from 08:03 UTC
(end 09:33 UTC), zero live calls and no installation or source acquisition over
the network. Cumulative local product allowance is 180 minutes; historical
provider deadlines and repair ledgers are unchanged. The one-detour limit is
unchanged and this attempt consumes it, even if the implementation succeeds.

## Question and reproduced obstacle

Can the actual investigation dossier feed a complete answer to the two original
P10/evidence questions, preserving sources, proposed readings, contrary evidence
and tool limits? The comparator is current code at `cde11a610`: the final
aggregation in `complete_investigation.py` retains findings but has no answer
consumer. `scripts/legal_tool_live.py` has a separate direct-source answer trial;
its `product_trial` only returns the dossier. Neither is evidence of a complete
dossier-based answer. The retained checkpoint used a local receipt sink and
cannot supply the missing evidence. This is an inspected missing acceptance
path, not a claim that all answer-related code is absent from the repository.

The substantive acceptance criteria remain those in
[the answer pilot plan](legal-mission-answer-pilot.md). A newly working consumer
is preparation, not a legal advance or an accepted answer.

## Implementation and evidence contract

1. Preserve a code trace and qualify source input through `acquire_context`,
   `packet_from_context` and `audit_packet`. Use the full retained 54-unit corpus
   and map text/qualifications explicitly; the previous 12-unit excerpt packet
   is not an equal-source baseline. Locally reconstructed text must be labelled
   as such and linked to the retained source, never represented as HTTP bytes.
2. Add an optional, bounded consumer of a verified CompleteInvestigation dossier.
   Bind its exact file, revision, packet, candidates, original questions and
   source qualifications. Retain every candidate, including unformalized ones,
   scoped uncertainty and source criticism. Require separate answer, inference,
   support, contrary, assumptions, unresolved issues and tool-use explanations.
   Reject changed questions, stale/missing references, fabricated quotations,
   lost candidates and claims of established legal correctness. Use existing
   provider/transport boundaries; do not alter historical runners or results.
3. Verify these boundaries with focused adversarial tests and a local receipt
   provider. Qualify actual payload sizes and source coverage before requesting
   live resources. No scripted answer is legal-quality evidence. If full source
   or dossier capacity fails, retain the exact failing payload and stop this
   attempt with a substantive return; do not silently truncate or enlarge caps.
4. If the complete two-arm invocation is demonstrably feasible, freeze it and
   its resource estimate for a grouped live approval. Otherwise state the precise
   outstanding capacity or implementation decision. No placeholder approval.

Primary preparation criterion: a bound dossier-derived request and structurally
validated complete-answer proposal, with negative controls rejecting stale or
missing evidence before it can be reported as valid. The primary future legal
criterion remains the complete answer review; it is not tested by this work.

Promotion vetoes: source/question drift, missing unformalized alternatives,
unsupported legal certification, feedback delivery described as consideration,
unqualified extraction metadata or a convenient small packet treated as full
source. Continuation vetoes: invalid source/evidence identity, required payload
exceeding declared capacity, expired local bound, unauthorized dispatch or an
additional repair attempt. A failed legal candidate is not a continuation veto.
Sizes, counts, timings and test totals are explanatory diagnostics only.

## Defaults, assumptions and skeptical audit

| Choice | Provenance and justification | Failure mode / early diagnostic |
|---|---|---|
| Two fixed original questions | Reviewed pilot, not a new surrogate task | Trigger-only answer; exact question and reading-accounting controls |
| Full retained corpus | Prior source analysis; applicability stays qualified | New source route loses qualifications; character/offset and provenance comparison |
| Existing dossier, optional consumer | Smallest missing product step | Large dossier or silently omitted criticism; inspect components and measure actual request |
| Single bounded answer proposal | Convenience baseline, no iterative answer tuning | Invalid response; preserve rejection rather than unlimited repairs |
| Existing byte/call limits | Inherited hypothesis, not presumed sufficient | Explicit capacity check before any provider dispatch; no automatic cap increase |
| One engineering attempt / 90 additional minutes | Reviewed local bound under continued-work instruction | More plumbing without answers; consume detour allowance and return with exact result |

Skeptical audit: **PASS for this bounded local preparation; live run not ready**.
The earlier receipt sink is an invalid baseline for answer benefit and is not
used as one. No ranking, legal accuracy or current-law completeness can follow
from passing these tests. Full-text/source and payload checks precede dispatch;
the consumer cannot replace source reasoning with tool votes. The main risk is
that a perfectly validated response remains legally wrong. Only later source
review of actual matched answers addresses that risk. A further risk is that
the full dossier exceeds transport capacity; that result would require a
separately reviewed method decision, not more retries.

Exact local command family, from the repository root:

```text
.venv/bin/python scripts/legal_mission_control.py check
.venv/bin/python scripts/legal_mission_control.py status
.venv/bin/python scripts/legal_mission_control.py admit
.venv/bin/python scripts/legal_mission_answer.py prepare
.venv/bin/python scripts/legal_mission_answer.py qualify
.venv/bin/python -m pytest -q tests/assurance/test_investigation_answer.py
.venv/bin/python scripts/legal_mission_control.py refresh
```

The preparation and qualification commands will have closed offline actions.
Results belong in `artifacts/legal-mission-control/2026-10-09/answer-preparation/`
and `docs/implementation/legal-mission-control/results/answer-preparation.md`.
The previous checkpoint is not repeated. No new master program, coverage matrix,
controller repair or tool installation is part of this attempt.
