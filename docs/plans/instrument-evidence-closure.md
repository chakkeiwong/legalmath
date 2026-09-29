# Closing instrument and evidence gaps

## Question, comparator and evidence contract

Can the completed UBS implementation handle additional contractual branches,
a materially different preferred share, and changing evidence without turning
missing facts or a source-dependent interpretation into legal clearance?
The comparator is the accepted I0–I4 increment in `instrument-gap-closure`.
Its frozen method remains available; `instrument-evidence-closure/baseline.zip`
protects the dirty working state before this increment. No human answer labels
or human judgments of legal quality are used.

The primary engineering criteria are exact source/issue binding; correct
conditional arithmetic; preservation of unknown, conflicting and superseded
evidence; rejection of unrelated entity/transaction evidence; and retention of
all fourteen bank obligations. Source-independent arithmetic theorems and
independent equations challenge the implementation. Actual Java/RuleIR and
Catala execution checks translation. Neither agreement nor quotation matching
proves that English has been completely or correctly formalized.

Missing agreements, actual notices, authentic market histories, amendments,
private bank/client data and unknown future law are expected evidence gaps.
The program must issue qualified results and explicit requests for the missing
evidence. Contractually required issuer, adviser or regulator determinations
are events to evidence, never interpretation-quality labels.

## Executable phases

| Phase | Work and acceptance | Next-phase refresh |
| --- | --- | --- |
| E0 | Acquire and preserve narrowly selected official public sources. Record retrieval failure and content changes. Implement source-watch and scoped evidence intake, including changed editions, calendar purpose, exact subject, time and completeness. | Identify acquired dependencies and those still unavailable; absence from search is not evidence of absence. |
| E1 | Extend UBS arithmetic with separate exchange calendars, explicit rounding alternatives and evidence-bound contractual determinations; implement delivery/tax/registration and alternative-notice checks as conditional branches. Preserve the printed formula anomaly. | Publish supported branches and qualifications; repair independent boundary counterexamples. |
| E2 | Bind the Bank of America Series SS supplement and its controlling-document dependencies. Execute non-cumulative dividends, depositary allocation, redemption timing and liquidation allocation. Join its source-dependent classification to the existing product/bank calculation. | Check cross-instrument substitution and conditional PI/non-PI scenarios without assuming bank clearance. |
| E3 | Prove rounding/floor and calendar-selection properties in Lean, run independent challenges and both native backends, and strengthen prospective source observations. Prepare a bounded real-model transport comparison; run it only under a fresh explicit allowance. | Record actual executions separately from pre-execution abstentions. Preserve all failures and missing observations. |
| E4 | Run affected regression; update monograph and process guide, compile and inspect changed pages; freeze the implemented method and record the final decision and remaining evidence needs. | Publish the next executable evidence-acquisition and reassessment actions. |

Entry point: `.venv/bin/python scripts/run_instrument_evidence_closure.py`.
Each phase reserves an immutable attempt, checks input and predecessor hashes,
records commands/environment/wall time and output hashes, and refreshes
`next-phase-plan.json` on success or failure. A failed attempt needs a causal
repair note before retry. Four attempts per phase is the continuation bound;
a substantive revision requires a new reviewed plan, not resetting history.
Document edits are inputs to E4 rather than invalidating unchanged arithmetic
phases. Relevant method/source changes do invalidate dependent phases.

## Research intent and diagnostic roles

The candidate is a more explicit evidence interface and two bounded instrument
profiles. Expected failures are incomplete history, incompatible calendars,
ambiguous prices, absent events and incorrect profile transfer. Source/hash,
identity, chronology, arithmetic and obligation-retention failures veto
promotion and trigger repair. Surviving deliberately wrong arithmetic or
scope variants also triggers repair. Unavailable required tools, corrupt
protected data, unauthorized live calls or exhausted attempts veto dependent
continuation; independent offline work continues. Runtime, counts and populated
premise totals are explanatory only. No stochastic ranking is planned.

A failed candidate does not reject the research direction. After each phase,
identify whether the harness, source, implementation or candidate failed and
whether the next phase repairs that cause. Do not stop at a failure which the
planned repair addresses. Result artifacts live under
`docs/implementation/instrument-evidence-closure/`.

## Defaults and assumptions audited before execution

Input-scope addendum after E2/attempt-003: the two unrelated executable-reference
v2 implementation/test files listed in `repair-007.md` were concurrently edited.
They are neither used by this program nor selected for its regression. Exclude
them explicitly while retaining all relevant method/source/tool bindings and
the failed attempt. The review distinguishes a harness-scope fault from a
financial or interpretation failure; no concurrent work is reverted.

| Choice and provenance | Justification, failure mode and earliest check | Status |
| --- | --- | --- |
| UBS June Annex A and BofA Series SS 2022 | Retained actual documents differ materially. A generic CoCo template would misclassify preferred equity. Check controlling-document clauses and issue identifiers first. | Bounded source baselines |
| Calendar purpose and covered intervals | SIC clearing, exchange trading and bank/FX opening are different propositions. A published holiday list cannot fill unspecified dates. Check purpose/year and missing-day rejection. | Reviewed evidence rule |
| Exact fractions and integer cents | Avoid binary rounding. UBS rounding and printed denominator remain ambiguous; enumerate declared alternatives and accept a unique result only when alternatives coincide or a scoped determination is supplied. | Conditional formalization |
| Contractual determinations | An actual determination can select a contractual result but does not prove legal interpretation or validity. Bind issue, clause, event, date, source bytes and exceptions. | Factual premise, never quality authority |
| BofA dividend periods | Twelve 30-day months and cent rounding are explicit. Month-end conventions and downstream depositary rounding are not interchangeable. Support unambiguous regular periods; qualify unspecified stubs/holder payment. | Source-dependent formalization |
| Freshness and force | A successful fetch establishes retrieved bytes, not current law or absence of amendments. Require separately dated coverage and applicability evidence. | Qualified source baseline |
| Later observations | A new content hash may be a new private fact rather than a new law. Bind document kind and dated publication/retrieval provenance and retain chronology as unverified where appropriate. | No future-accuracy promotion |
| Existing live budgets | Two 500-call grants and the 120-call market arm are exhausted. Prepare exact new study scope before requesting a bounded allowance; never reset a ledger. | Explicit resource limit |

## Skeptical review

The initial idea of completing every branch by supplying Boolean satisfaction
flags would merely move the missing evidence into unchecked inputs. This plan
instead requires typed, scoped, content-addressed records and keeps their truth
qualified. Separate calendars must select their own preceding five dealing
days; shared dates are not assumed. An issuer determination cannot silently
rewrite a source anomaly. BofA's supplement explicitly gives its Certificate of
Designations precedence, so acquiring that document is an early task, and
missing it limits the profile. Synthetic examples are tests of declared
relations, never approvals or prospective observations.

The baseline is the retained accepted increment, not a hand-picked weak model.
Native comparisons share frontend inputs and use independent mathematical
checks. A whole-program theorem, complete applicable-law discovery, universal
English equivalence, actual private-bank clearance and unknown future accuracy
are outside the supported conclusion. These limits remain explicit even if
every command passes. The revised plan passes the bounded audit: artifacts can
answer the engineering question and cannot be mistaken for legal validation.
