# Fact correspondence implementation and frozen-circular replay

P10–P12 passed on 23 September 2026. The current full suite has **310 passing
tests, including 78 search tests**. The implementation now distinguishes exact
fact renaming from a proposed change of meaning, replays differing witnesses in
the original Java classes, and records conditional mapping proposals and
separate reviewer decisions. The frozen replay preserves all 45 earlier
comparison outcomes and exports all 33 incomparable pairs for review. It used
no model calls; the shared ledger remains at 41 of 100.

The pre-execution contract is
[interpretation-fact-alignment.md](../../plans/interpretation-fact-alignment.md).
The acceptance manifest is
[P12 attempt 01](../../../artifacts/interpretation/round2/P12/attempt-01/run-manifest.json).
These are engineering and development-source results. No actual human mapping
review or independent evaluation of English interpretation was performed.

## The problem exposed by the saved readings

In the saved 24EC50 investigation, two readings encode the same visible rule
shape: if a covered submission occurs from 30 November 2024, test whether it
used e-IP. Their date declarations differ. One says when the submission is made
and marks it as requiring no judgment. The other explicitly leaves the
dispatch-versus-receipt convention unresolved and marks it as requiring
judgment. Renaming their route inputs cannot settle that timing question.
The comparator therefore keeps the pair incomparable until its correspondence
assumptions are made explicit. This describes the generated readings; it does
not decide the circular's proper legal construction.

The saved 23EC46 readings also differ in how they decompose inputs. One has a
single `gift_offered` fact and a separate fact concerning which product a fee
discount relates to. Another splits offer and gift classification into two
facts and separately declares the promoted product's subject matter. These
readings contain five and six facts. A one-to-one mapping cannot honestly
represent that difference. Projecting away a fact or guessing a conjunction
would conceal a new assumption about scope or an exception.

Those examples explain why more automatic matches were never the pass
criterion. The restricted matcher found **zero new exact-alias matches** in
the frozen population. That is consistent with the inspected definitions.
Their semantic discrepancies remain available for a substantive review.

## Implemented behavior

`alignment.py` compares all declaration metadata except names and declaration
order. Identical same-name facts are anchored first; remaining matches must be
unique and cover both declarations completely. The AST renamer substitutes fact
leaves simultaneously. It preserves operators and literal values. Its snapshot
adapter copies the entire tagged fact record to the partner name, including
missingness, conflict information and evidence. The plan gives the induction
argument for preserving the encoded calculation; tests exercise all 243
three-valued assignments of a five-fact swapped-name example.

For a detected difference, `formal.py` translates the witness into each
original vocabulary and runs both original generated Java classes. It checks
their results against the normalized comparison and retains original bundle
hashes and separately named snapshots. A normalized rule is not substituted
for the Java candidate delivered for review.

Changed meanings, units, source references or judgment flags require a
`Correspondence` proposal. The proposal binds exact source and reading hashes,
supplies a total bijection, and states each changed declaration's assumption.
It also states an output-meaning assumption: true might mean that a restriction
is triggered, or that a requirement is satisfied. This version supports no
implicit type/unit conversion, output negation or multi-fact decomposition.

Every such analysis is wrapped in `CONDITIONAL_ANALYSIS`, even if its inner
comparison proves equality in a supported declared domain. Conditional results
cannot enter unconditional behavioral groups or grant release authority.
`alignment_review.py` stores proposals, analyses and decisions separately from
the completed search. It checks owner/reviewer roles, source invalidation,
candidate and report hashes, and a rejection arriving during compilation.
Later rejection preserves earlier analysis but blocks new analysis. The
archive roundtrip preserves these records and the original report.

Five HTTP routes expose review packets, proposals, analysis, decisions and
history. The [operator guide](operator-guide.md) specifies the exact request
fields and roles. The regenerated
[OpenAPI description](../../specs/v0.1/openapi.json) includes the whole search
increment: 44 paths in total, with all preexisting route definitions retained.

## Comparator defect found and repaired before acceptance

The P12 audit found an inherited error when a solver returned UNKNOWN or
UNSUPPORTED for a caller-declared domain. The fallback ignored the bounds. For
example, `months >= 6` and `months > 6` agree for known months from 7 through 12,
but an unconstrained probe at 6 reports a difference. Reporting that witness
under the restricted domain is wrong relative to the stated target.

Three forced-unresolved regressions reproduced the defect: two numeric cases
and a Boolean pair restricted to false. The failing results are retained in
`artifacts/interpretation/round2/domain-fallback-before.xml`. The repaired path
preserves UNKNOWN or UNSUPPORTED with zero unconstrained probes for a declared
domain. All 15 comparator tests then passed in `domain-fallback-after.xml`.
Automatic complete Boolean domains keep their existing safe finite fallback;
an inconclusive solver plus finite agreement still establishes no equivalence.

This was an implementation failure with an executed repair. It does not reject
the multiple-interpretation approach. P12's full regression includes the repair.

## Frozen replay and concrete conditional result

Every recorded P8 comparison was replayed. Hashes of each original source
packet, investigation, report and archive were checked before and after the
run. No original history was rewritten. The stored allowance hash also stayed
unchanged.

| Source | Recorded pairs replayed | Different | Equivalent in declared domain | No difference in finite probes | Incomparable |
|---|---:|---:|---:|---:|---:|
| 24EC50 | 21 | 1 | 0 | 2 | 18 |
| 23EC46 | 24 | 6 | 3 | 0 | 15 |

The new packets contain both complete readings, declared facts, formal scope
and result, assumptions, questions, retained source and dependencies. Start at
the [24EC50 index](../../../artifacts/interpretation/round2/P12/attempt-01/replay/24EC50/review-packets/index.md)
or the [23EC46 index](../../../artifacts/interpretation/round2/P12/attempt-01/replay/23EC46/review-packets/index.md).
They are candidate-exposed review material, not independent reference labels.

For the preselected 24EC50 pair, the stored
[hypothetical proposal](../../../artifacts/interpretation/round2/P12/attempt-01/replay/24EC50/hypothetical-correspondence.json)
assumes the same covered submission, the same timing convention and the same
observed route. Its [analysis](../../../artifacts/interpretation/round2/P12/attempt-01/replay/24EC50/conditional-analysis.json)
found no encoded difference in **36 Python boundary probes**. No difference
witness arose for additional Java replay. The result is
`CONDITIONAL_ANALYSIS / NO_DIFFERENCE_IN_FINITE_PROBES`, with
`equivalence_established=false` and `release_eligible=false`. The two original
candidates' P8 Java checks remain historical evidence; the current workflow's
Java verification and original-witness adapter are exercised in regression.
The 36 probes neither resolve the date convention nor prove global equivalence.

## Execution record

| Phase | Actual command scope | Result | Supervisor wall time |
|---|---|---|---:|
| P10 attempt 01 | Alignment and distinguishing-question tests | 21 passed | 10.607 s |
| P11 attempt 01 | Alignment review, API and search integration tests | 10 passed | 39.472 s |
| P12 attempt 01 | Full test suite, then frozen P8 replay | 310 passed; 45 pairs and 33 packets | 275.128 s |

The full pytest process reported 258.39 seconds, with two existing dependency
deprecation warnings. These phase counts overlap and must not be added as
independent tests. P12 is the current acceptance set. Runtime is descriptive;
no speed comparison was designed. Its manifest records all 191 current input
hashes, exact commands, artifact hashes, Python 3.11.15, JDK-backed execution,
CPU-only context, and base commit
`bb0e8b3b4b9431df22dd5517a124d2952896c6bf`. The implementation was tested as a
dirty worktree. No new stochastic generation or random seed was involved.

The original fixed supervisor was used in the trusted execution context; the
earlier sandbox-specific stalls remain documented. Execution was preceded by
the P10, P11 and P12 author reviews. This is not an independent code-review
verdict. The final verification record is
`artifacts/interpretation/round2/fact-alignment-evidence-check.json`.

## Decision, uncertainty and next action

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | What is not concluded |
|---|---|---|---|---|---|
| Accept correspondence engineering for development | Original-Java witnesses, strict mapping and authority tests; full suite and frozen replay pass | No observed current regression or altered history; domain fallback defect repaired | Unexercised inputs and correctness of declared definitions | Use the explicit review workflow; preserve conditional status | Correct legal interpretation or absolute software robustness |
| Retain all 33 incomparable pairs | No silent change of meaning or dropped facts | Semantic definitions differ; some decompositions cannot be mapped | Whether any correspondence is legally and operationally justified | Obtain substantive decisions on the supplied packets | Failure of the search direction or permission to loosen equality |
| Retain the 24EC50 hypothetical analysis | Explicit assumptions and actual comparison method recorded | Missing timing/meaning review; finite date probes only | Input convention and completeness of source authorities | Resolve those questions or preserve them as unresolved | Global equivalence or an approved route control |
| Withhold legal-accuracy and release claims | Independent reference and exact-candidate approvals required | Those prerequisites remain absent | Shared model omissions and bank data bindings | Source-first human annotations and a reviewed held-out study | Bank deployment readiness |

| Inference status | Finding |
|---|---|
| Hard veto screen | Invalid mappings, stale sources, forged roles, concurrent rejection and out-of-domain fallback regressions behave as required |
| Statistically supported ranking | None; no stochastic method comparison was run |
| Descriptive-only differences | 45 replay outcomes, 33 review packets and one conditional 36-probe example |
| Default readiness | Exact aliases are permitted by the restricted contract; semantic correspondences remain hypotheses; no legal release default changed |
| Next evidence needed | Qualified mapping review, operational fact definitions, independent source-first adjudication and held-out evaluation |

The strongest alternative explanation for apparent agreement remains a shared
omission or an assumption that erases a real distinction. A reviewer finding
different submission events, a missing exception or opposite output meanings
would overturn the corresponding mapping hypothesis. The weakest evidence is
still the fidelity of the generated readings and supplied facts to the English
and bank operations. The [next-phase plan](next-phase-plan.md) now separates
that missing evidence from the remaining representation work.
