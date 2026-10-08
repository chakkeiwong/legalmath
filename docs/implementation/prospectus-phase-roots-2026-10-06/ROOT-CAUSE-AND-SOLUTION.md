# P0–P6: root causes and a repair that can be tested

6 October 2026. Baseline: commit `7fd9c4e864c22da1e8a5df8ed7bc5c59331eb25f`,
branch `feature/prospectus-evidence-master`. This commit preserves the previous
successor execution and corrected manuscript. This investigation changes no
production successor code.

## Finding

P0–P6 are partial implementations with broken connections between their results.
Their remaining work cannot be reduced to obtaining independent reviewers.
The code also contains reproducible correctness defects. Most produce excessive
abstention, but the legal evaluator can return **YES while a declared necessary
premise is false**. The BASF bank report inherits an AT1 classification from a
copied UBS request. Neither more PDFs nor another unchanged phase run repairs
these failures.

The [counterexamples](counterexamples.json) record 18 findings and one passing
control. Some findings are missing capabilities or conditional schema risks,
not demonstrated false legal answers. The [probe manifest](probe-manifest.json)
pins the tested code and environment; [code-trace.json](code-trace.json) records
the phase calls. The existing 50 passing tests remain valid observations about
those fixtures. They do not refute a counterexample outside their assertions.

The repaired design is a source-bound contract compiler followed by separate
contract, law, financial and bank evaluations. A reviewed representation must
connect every stage. Existing modules and exact arithmetic can be reused.
A stronger recognizer is a candidate component; it cannot repair an ignored
premise or a wrong instrument identity.

## Phase diagnosis

| Phase | What the current code actually does | Root cause and concrete repair | What establishes closure |
|---|---|---|---|
| P0: questions, baseline and review | Freezes files but writes empty reviewers/labels/cohort every time; reports unreconciled counts | Preparation has no input admission path. Read versioned question definitions, source-occurrence records, reviewer assignments and cohort exclusions; reconcile by stable keys | Every input has an owner/version; counts reconcile; changing an admitted input changes dependent results. Independent review remains a separate external requirement |
| P1: sources and geometry | Extracts printed lines; detects reference strings; source issues and all references block Q1/Q2 globally | A line inventory is being used as a reading and dependency graph. Preserve words/coordinates, group reviewed paragraphs and columns, namespace contexts, resolve references in the selected contract | Real German/multicolumn/scanned pages match checked reading order; changing visual wrapping preserves meaning; an irrelevant header does not block a question, but an indirect relevant reference does |
| P2: selected contract | Applies ten BASF edits, leaving 163 branches and an unmatched bracket | Regex deletion has no general representation of conditional choices, fields, marginal instructions or amendments. Construct a typed contract with reviewed selection/override rules and source maps | Every operative output span has a source and construction reason; no unresolved choice can affect an answered question; BASF and other retained agreement/amendment cases pass |
| P3: clause interpretation | Recognizes a few English sentences; ignores repeat occurrences in coverage; all conditions/exceptions cause abstention | Representation and evaluator do not express the required question, context and quantifiers. Use occurrence intervals, typed predicates and the existing partial-information solver | Positive, negative, mixed-asset, condition, exception, cross-reference and bilingual reviewed examples pass; automatic extraction is evaluated separately |
| P4: law and facts | Checks that `premises` is nonempty, then evaluates a fixed seven-name list; accepts arbitrary source strings; ignores fact `valid_from` | A checklist substitutes for the declared legal rule. Execute the supplied rule expression over anchored facts on validity and knowledge timelines | Additional false premises prevent YES; missing/contradictory inputs stay unknown/conflict; source/time/authority mutations are rejected; reviewed real legal cases validate translation |
| P5: finance | Runs one month-order test and lists kernels; no complete BASF scenario runs | Kernel availability substitutes for a contractual calculation. Define strict profile-specific schemas, legal aggregation identity, units, conventions and settlement events | Actual profile kernels and independently computed source examples pass; malformed inputs return structured errors; rounding/conservation and calendar boundaries hold |
| P6: integration | Installs the CLI, recomputes from P1, copies a UBS bank request and checks 14 obligations | Installation and inventory length substitute for semantic integration. Consume P3/P4/P5 products and bind instrument, dates, purpose, source versions, mappings and obligation identities | Installed CLI demonstrably consumes the exact preceding products; identity/premise/version changes cannot pass by retaining a count of 14; unknowns remain unknown |

## Why repeated execution does not close the gaps

The declared DAG in
[controller.py](../../../src/legalmath/prospectus/successor/controller.py:12)
says P3 follows P2 and P6 joins P3/P4/P5. The jobs do something different:
[P3](../../../src/legalmath/prospectus/successor/jobs.py:130) reads P1's request;
[P4](../../../src/legalmath/prospectus/successor/jobs.py:140) produces a retained-law
verification; P5 produces an inventory; and
[P6](../../../src/legalmath/prospectus/successor/jobs.py:157) reads P1 again.
[service.assess](../../../src/legalmath/prospectus/successor/service.py:8)
reconstructs source, assembly and clauses from the request. A reviewed correction
saved only in P2/P3/P4/P5 cannot reach the installed report through these jobs.

A DAG must describe actual consumed data, not merely execution order. The repair
is to make each stage a function of explicit immutable inputs. A receipt should
bind the exact parent products, task code, imported rules, parser/tool versions,
configuration and newly admitted review records. Store large source/assembly
products once and refer to them by content hash; embed concise evidence excerpts
in the report. The prior 1.6 GB run tree arose partly from repeated full reports.
Its new lossless checkpoint archive addresses storage, not semantic integration.

The current controller correctly distinguishes PARTIAL from release acceptance,
but `execute` reuses any current artifact, including PARTIAL. Its refreshed
plan contains prose obligations and the same phase command; it contains no
executable semantic repair. Its global code/source hash also misses the old
bank request/store that P6 reads and some deeper imported rule/tool inputs.
Conversely, one bound change invalidates every phase.

Use a dependency-aware cache plus a separate repair queue. Each failed obligation
needs a diagnostic, an implemented repair handler or named external input,
the required input change, its acceptance check and a bounded attempt record.
An unchanged deterministic failure should wait for a meaningful change.
A candidate failure triggers its planned repair; it does not invalidate the
research direction. Snapshot inputs before execution, publish a receipt only
after all outputs are complete, and recover interrupted attempts without
promoting orphaned products.

## Where the contract is lost

[P1 extraction](../../../src/legalmath/prospectus/successor/source_graph.py:10)
creates one text unit per printed line. Recognition expects full sentences.
The repayment control returns NO, but the same sentence split across two lines
returns UNKNOWN. Context identifiers based on page/block alone also need the
document edition namespace. Word geometry, explicit reading order, paragraph
membership, lists, footnotes, tables and German marginal instructions must
remain available for inspection. Existing ResearchAssistant OCR can supply
characters; it cannot by itself establish paragraph order or contractual meaning.

[Reference handling](../../../src/legalmath/prospectus/successor/service.py:25)
currently treats a detected header reference as an unresolved obligation of
both Q1 and Q2, even when that header is excluded from semantics. A literal
`RESOLVED` string can suppress the obligation without a target or source-bound
resolution. Resolve an occurrence to a versioned clause/definition/document
target, retaining ambiguous targets. Traverse the dependencies of each question.
An exclusion is valid only with a reviewed scope reason; relevance must never
be inferred from whether removing a reference produces a desired answer.

The [BASF constructor](../../../src/legalmath/prospectus/successor/basf.py:9)
pins one source edition and uses page/geometry cutoffs, six deletion patterns
and four scalar substitutions. It removes margin text from the body without
generally attaching its instructions to the corresponding alternatives. A
whole-document bracket stack cannot recover omitted delimiters reliably.
The unmatched opening at raw offset 14862 requires inspection of the rendered
source and its governing instruction, not automatic balancing. Other offerings
need their own executed agreements and precedence evidence.

Use `Text / Sequence / Choice / Field / Reference / Override` nodes. Retain
correlated choices and language/edition precedence explicitly. An unresolved
choice yields alternative constructions or a symbolic condition. It must not
silently select the first branch. Every copied character keeps its original
occurrence; substitutions keep both the replaced interval and the final-terms
authority; inserted formatting is labelled. The BASF adapter must honor source
visibility, as the generic assembler already does. The isolated prototype
implements only Text/Sequence/Choice, deliberately leaving full amendment and
field construction for the production repair.

## Meaning is more than recognizing a phrase

[Clause coverage](../../../src/legalmath/prospectus/successor/clause_graph.py:61)
validates a quotation as a substring, then uses its first `find` occurrence.
Repeated identical clauses therefore leave later occurrences uncovered.
A joined multi-unit quotation is accepted, but coverage processes only
single-unit nodes. Replace quotation identity with
`(document hash, document id, unit id, start, end)` intervals and preserve
all intervals in an evidence group.

The recognizer's defaults include issuer/holder roles, positive polarity and
empty conditions/exceptions. Its captured trigger string is not an executable
condition. The evaluator subsequently treats any nonempty condition/exception
list as unresolved, including a resolved target. Negative nodes do not by
themselves produce NO. These are implementation limits, not an inherent inability
to reason safely with missing facts.

Reuse [possible_decision](../../../src/legalmath/prospectus/semantics.py:73)
over reviewed Boolean expressions. It enumerates missing facts, preserves
conflict and forbids treating absence as false. For a larger or constrained
domain, extend its semantics explicitly before introducing a solver; its current
limit is twelve independent Boolean facts. Actor, election, affected interest,
effect, trigger, exception, temporal scope and source priority must be represented
before evaluation. Reviewed rules may later be lowered to the existing
RuleIR/Catala/Lean paths; proving an unfaithful translation would prove the wrong
claim.

For Q1, distinguish a *contractual loss feature* from *a loss event today*.
For a fixed admissible contract reading, a feature may exist if a legally
admissible contingency can trigger it. Across unresolved readings, a definite
answer requires agreement. Q2 also needs versioned subquestions: conversion
without holder election, possible receipt of common shares, and receipt of
common shares only. A common/preferred mix makes the second true and the third
false; a single NO cannot communicate both. Q3 should cover every declared
question and subquestion, including law and finance dependencies. It currently
reports only Q1/Q2.

## The most urgent defects: legal premises and instrument context

In [law_facts.assess](../../../src/legalmath/prospectus/successor/law_facts.py:6),
`basis.premises` is required but unused after validation. The probe supplies
all seven fixed facts as true and a declared necessary court-order premise
as false. The result is YES. That result is **wrong relative to the supplied
conjunctive rule**; it is not a disputed interpretation of a real court case.

The remedy is to evaluate the actual expression supplied by the reviewed legal
basis. Every fact needs subject, predicate, value, source occurrence, validity
interval and knowledge interval. Observation/publication/retrieval dates must
remain distinct. A true observation cannot be applied before its stated
`valid_from`. An unresolved source identifier is invalid evidence. An open-ended
record does not establish that no later amendment or decision exists.

Alternative legal bases need a declared relationship: alternative sufficient
powers, jointly necessary conditions, or conflicting interpretations. The current
“all statuses equal, otherwise UNKNOWN” rule supplies none of those meanings.
Likewise, applicability of a power is distinct from an authority actually
exercising it, a court suspending it, or a contractual event occurring. Preserve
these as separate answers with dated primary evidence.

The [P6 copy](../../../src/legalmath/prospectus/successor/jobs.py:191) changes
only the instrument id. The actual integrated request uses
`basf-senior-2032` with `instrument_kind=at1_bond`. Its bank effective/knowledge
dates are 4 October 2026, while the source bundle asks about 8 March 2023 with
knowledge through 6 October 2026. Different dates can be appropriate for
different questions, but require an explicit mapping. No such mapping is
present. Copying the UBS context is not an admissible mapping.

Preserve all fourteen applicable bank obligations by **identity, rule version,
premises and disposition**, not just count. Bind a bank question to the accepted
instrument taxonomy and its own transaction/client facts. Unknown product
features cannot become negative answers merely to unlock regulatory relief.
The current report still denies transaction permission; this audit does not
claim an actual transaction or release occurred.

## Finance and evaluation require their own evidence

[financial_profiles.assess](../../../src/legalmath/prospectus/successor/financial_profiles.py:29)
provides three bounded source-bound kernels, not complete settlement.
A malformed price-list shape raises uncaught TypeError. Strict per-profile
validation should reject wrong shapes, floats where exact values are required,
unit/currency mismatches, absent conventions and unsupported fields before
arithmetic. Preserve known defects as regressions. Avoid a broad catch-all
that turns internal programming errors into apparently valid financial results.

The existing share-allocation kernel groups by registration-name string.
Two distinct registered holders with the same display name, each converting
6 at price 10, must receive zero whole shares each under a per-holder floor
rule. Combining them gives one. This is a **conditional schema defect**:
the actual contract may legitimately require aggregation of accounts belonging
to the same registered holder. Supply and review that legal aggregation identity.
Do not simply switch to account id and assume that is always correct.

Date addition, holiday adjustment, accrual, money rounding, anti-dilution,
fraction treatment, conversion and delivery must be separate operations with
source-backed parameters. An exact remainder identity proves arithmetic; it
does not create a contractual entitlement to cash. Run each supported kernel
on real sourced scenarios and independently checked examples. UBS successor
mapping, BASF scenarios and complete settlement remain unfinished.

P0's external review problem also has a software side. A probe through the
adjacent P7/P8 code permits the implementer to act as adjudicator and allows
Q5 support based on Q1-only scores. It returns a finite assisted candidate
while still refusing automatic transaction clearance. Enforce disjoint
identities, cohort exposure records, scored-question coverage and signoffs
bound to the exact report/cohort/scope. These checks cannot manufacture genuine
independence or good legal labels.

## What has been established, and what remains

The [literature review](LITERATURE-REVIEW.md) identifies usable ideas and their
limits. The [proofs](PROOFS.md) establish conditional engineering properties;
the [reference results](reference-results.json) exercise eight groups:
64 paragraph partitions, 7,068 Boolean truth-table comparisons, 6,052 consistent
completions of decisive answers, 675 validity/knowledge combinations and 1,690
exact allocation cases, plus dependency, context, source and reviewer mutations.
These counts describe finite exhaustive checks; they are not estimates of
real-prospectus accuracy.

| Decision | Primary criterion | Veto evidence | Main uncertainty | Next justified action | What does not follow |
|---|---|---|---|---|---|
| Reject current P0–P6 as delivered | Useful, source-correct joined result not met | Ignored false premise, context mismatch and disconnected products | Full real-contract interpretation remains unreviewed | Implement the ordered [repair program](../../plans/prospectus-phase-repair-2026-10-06.md) | The whole research direction has failed |
| Retain the proposed algorithms for implementation | Reference oracle/property checks pass | No failing check in the declared finite domains | Production wiring, legal translation and larger domains | Port invariants with failing production regressions, then a real reviewed slice | Prototype proves production correctness |
| Keep release blocked | Independent scoped accuracy not evaluated | No accepted independent cohort and signoffs | Human/legal evidence | Complete P0 admission and independent evaluation after repair | Missing review prevents engineering progress |

The strongest alternative explanation for low coverage is that incomplete legal
sources alone force abstention. It explains some BASF unknowns, but cannot explain
the duplicate-clause, false-premise or copied-context counterexamples. Those
isolate software defects with explicit inputs. Conversely, the weakest evidence
for future useful coverage is the synthetic reference model: its success says
nothing about how often a parser will recover the correct German contract.
A real independently checked source-to-answer slice can overturn the proposed
representation or reveal a missing legal distinction. The repair program requires
that test before broad claims.
