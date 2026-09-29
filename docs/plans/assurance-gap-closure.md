# Closing assurance gaps 1–7 with a demonstrated circular-to-Java workflow

Date: 25 September 2026. Status: proposed implementation and evaluation plan.
This document answers the request to close gaps 1–7 while deferring gap 8,
integration with the bank's actual systems. It does not report a new execution.

## Target and current evidence

The next milestone is a reproducible investigation that takes retained official
sources, investigates their meaning, generates an actual Java package for its
supported rules, and explains both the decisions and remaining uncertainty.
It must demonstrate useful correct decisions as well as the ability to withhold
an answer. Installation, component agreement, and a workflow that abstains on
every case are insufficient acceptance criteria.

Closure is relative to a declared regulatory and language profile. General
interpretation of every circular, qualitative legal standard, or judicial
precedent is outside the first demonstration. Unsupported passages must remain
visible in the whole-document inventory; selecting a supported provision must
not imply implementation of its entire circular.

The inspected baseline is main `9160ce72` plus the uncommitted round-11 work.
The Catala worktree has a separate, newer implementation. Preserve these inputs
and the historical results when constructing the combined implementation.

| Gap | What exists and should be reused | What remains to demonstrate |
| --- | --- | --- |
| 1. Integrated investigation | `assurance/engine.py`, `search/engine.py`, `checkpoints.py`, `public_issue.py`, monitoring and repair modules | One durable workflow actually invokes the relevant source, abstraction, search, argument, solver and Java checks and reacts to their findings |
| 2. Source discrepancy resolution | Five extraction routes; twelve retained real-page discrepancies; bounded OCR actions | Evidence-backed region reconciliation, table/footnote relationships, materiality and adaptive resolution |
| 3. Competing factual abstractions | Rival readings, vocabulary objections, derived mappings and composition support | A vocabulary objection opens a separately versioned factual model and a consequential investigation |
| 4. Demonstrated diversity | Separate reader roles and model contexts, several parsers and formal engines | Measured common errors and complementary detection on representative challenges |
| 5. Implementation assurance | Python/Java conformance, bounded Z3/cvc5 checks, clingo checks and a PIT pilot | Broader independent encodings, actual generated-runtime mutation, and combined Catala validation |
| 6. Evidence for reduced review | Blind dispatch, reference cases, evaluation infrastructure and recorded abstentions | Independently supported reference outcomes, useful acceptance, unsafe-acceptance uncertainty and measured review burden |
| 7. Authority and legal semantics | Edition/provision catalog, bounded reference closure, arguments and example records | Integration of applicable definitions, amendments, priority evidence, language discrepancies and selected temporal duties |

Paths abbreviated as `assurance/` and `search/` are under
`src/legalmath/interpretation/`. The
[round-11 result](../implementation/interpretation-round11/execution-result.md)
records 628 passing tests, but its source disagreements remain unresolved and
its Inspect/PIT demonstrations are synthetic. The
[Catala remediation report](../../.worktrees/catala/docs/implementation/catala/gap-remediation-results.md)
records generated RuleIR lowering, complete result comparisons, and Java
transaction/release interfaces. Its 344 decision comparisons and 202 regression
tests were retained on that branch; this planning audit did not rerun them or
establish compatibility with all uncommitted round-11 changes.

## The demonstration we should require

For each declared case, retain the original source and editions, page and region
inventory, alternative factual models and readings, investigated disagreements,
decision tables, RuleIR, generated Java source and JAR, executable cases, and a
report connecting the observed answer to its evidence. The report must distinguish
source support, formal consistency, implementation conformance, and unresolved
judgment. A source quote proves where words occurred; it does not prove that a
proposed rule follows from them.

Use the five previously selected different circulars as development examples.
Select evaluation sources from additional families and freeze their reference
packets before exposing them to the implementation process. A previously read
circular is not a held-out example merely because its test directory is new.
Where genuinely unseen family data cannot be reserved, label the result a
development demonstration and leave generalisation unmeasured.

The locked demonstration must contain both cases that can be settled within the
supported profile and cases that require uncertainty. Every designated clear
acceptance case must produce the supported decision and a runnable Java package;
every designated material ambiguity must retain the affected alternatives or
missing evidence. Real-source findings can require correction of a reference
packet, but such a correction needs its own evidence and invalidates that packet
as an untouched holdout. A failing system cannot rewrite its expected answers
to obtain a pass.

## 1. One durable investigation

Create a common investigation record and dispatcher around the existing engines.
It should bind source editions, selected scope, abstraction versions, candidate
versions, argument premises, fact evidence, tool profiles and binaries. Reuse
the persistent search and task queues; do not replace them with an outer loop
that merely repeats the current narrow issue command.

Each tool result needs a target claim, input hashes, supported domain, actual
execution receipt, outcome, counterexample or other evidence, and explicit
limitations. Unsupported, unavailable, inconsistent and inconclusive checks
remain distinct. Tool agreement must not overwrite a source-coverage failure.
Scheduling scores express investigation priorities, not probabilities of legal
correctness.

Every discrepancy becomes a typed issue with affected dependencies and eligible
next actions. Examples include fetching a missing definition, inspecting a page
region, revising a factual abstraction, or running a separating Java scenario.
Choose an action for the unresolved question, record its result, and recheck the
dependent claims. A source or abstraction change invalidates downstream evidence.
Keep execution retries distinct from semantic reconsideration. Reserve each
action before dispatch, and enforce per-issue, total-call and wall-clock limits
across restarts. Exhaustion preserves alternatives and residual questions.

**Closure tests:** an actual tool discrepancy changes the next action; a changed
definition invalidates a previously completed decision; restart at every stage
preserves completed work and consumed allowance; missing outputs cannot pass;
an unresolved issue stops at the declared bound; at least one discrepancy is
resolved by new evidence and proceeds through generated Java. Serialising a
discrepancy without taking the relevant action does not close this gap.

## 2. Resolve source differences without erasing meaning

Extend `scripts/assurance_source_routes.py` and
`assurance/diversity.py` with page-region alignment. Preserve raw text, geometry,
rendered crops, extraction route and source edition. Align headings, table cells,
row/column headers, footnotes and their references before constructing clauses.
Use rendered-page evidence to challenge omissions shared by text parsers.

Start with the twelve retained disagreements. Separate mechanically verifiable
formatting differences from differences that might affect a condition, quantity,
exception, scope or date. Do not resolve negation, punctuation, inequalities,
currency, numbering or table relationships by destructive normalisation or a
majority vote. Materiality classifications remain challengeable evidence.

Select additional work from the actual failure: regional OCR, a different page
segmentation, table reconstruction, comparison with retained official HTML, or
retrieval of an annex. Record an explicit reason when an action adds no new
evidence. Do not treat repeated OCR with the same engine as independent votes.

**Closure tests:** each of the twelve discrepancies has an evidenced disposition
or a located residual question. Seeded loss of a negation, digit, unit, exception,
table header and footnote is detected; benign wrapping is resolved without
altering operative content. A missing image-only condition is found even when
text-based routes agree. Clear extraction cases proceed; unresolved material
regions block only the conclusions whose required evidence depends on them,
under an explicit dependency analysis.

## 3. Search over the facts as well as the formulas

The narrow issue workflow currently requires the supplied facts to remain
unchanged. Add a versioned abstraction proposal containing actors, objects,
components, relations, quantities, units, time, classifications, source anchors
and unresolved judgments. A vocabulary concern should create a child proposal;
it must not silently change the meaning of an existing fact name.

Run source-only abstraction proposals before showing proposers one another's
answers. Include a challenger tasked with identifying a legally relevant
distinction that none of the proposed schemas can express. Begin with breadth
across the relevant representational alternatives, then use the existing search
to investigate separating cases and counterarguments. A fixed number of readers
does not establish completeness, and artificial alternative readings are not a
success metric.

Map schemas only where their correspondence is supported. A partial or unsupported
mapping must return incomparability, with the missing information identified.
Generate cases that distinguish both classifications and interpretations, and
show a plain-language reconstruction of each executable rule beside its source.
Back-translation is a useful challenge, not independent proof of meaning.

The existing
[23EC46 example](../implementation/second-circular-verification.md)
provides a concrete development challenge: a fee waiver accompanied by a separate
voucher. An offer-level fact such as “contains a discount” can hide a component
distinction before any formula is compared. The experiment must discover or
retain the component-level alternative from the source and supplied offer
evidence. It cannot pass merely because the correct component schema was supplied
in advance. This tests the local example's stated interpretation; its old oracle
does not independently settle the legal classification.

**Closure tests:** discover a planted missing component, actor and time distinction;
retain an unencodable interpretation; preserve alternatives across vocabulary
changes; refuse unsupported fact mappings; demonstrate a concrete separating
case that fixed-vocabulary search misses. Hypotheses are eliminated by recorded
contradiction or justified equivalence within a declared domain, never merely
because fewer models proposed them.

## 4. Measure complementary failures

Track which routes share a source extraction, factual schema, model family,
prompt, formal encoding or host runtime. Separate source-only requirement
extraction, interpretation construction, formal counterexample search and
Java execution. Several tools downstream of one wrong RuleIR diversify execution
checks but do not diversify the English interpretation.

Extend provider routing so another model family can be used where authorised
and available. Fresh Codex contexts remain useful for anchoring control but
must retain their existing same-model correlation qualification. Cross-model
execution is a separate live-run prerequisite, not a reason to stop deterministic
integration or to describe prompt diversity as model independence.

Use blinded real-source cases and controlled defects. Record each route's
missed requirements, shared misses, unique detections and unresolved outputs.
Compare the existing workflow, a budget-matched repetition baseline, abstraction
search, and the full ensemble. Keep the complete system's safety evaluation
separate from the budget-matched method comparison; equal cost is not a reason
to remove a check required by the accuracy contract.

**Closure tests:** a predeclared fault matrix is checked against actual route
execution. The report identifies which common failures remain undetected and
which route combinations detect complementary faults. No claim of statistical
independence follows from different package names or a small sample. Superiority
or error-reduction claims require paired, source-family-aware uncertainty
analysis; descriptive differences alone nominate further investigation.

## 5. Check the generated implementation over its supported semantics

Integrate the completed Catala branch through a preserved combined baseline and
run both its retained conformance cases and the round-11 regressions. Do not
repeat the obsolete task of building a generic translator from two handwritten
Catala scopes: the current branch already lowers canonical RuleIR.

Extend cvc5 checks in declared stages: Boolean values and conflict/unknown
semantics; exact integer and monetary arithmetic; date and applicability
boundaries; and default/exception interactions. Use independently written
encodings against a documented reference semantics, explicitly recording shared
assumptions. Replay counterexamples in the actual Python and generated Java
implementations. A timeout or unsupported operation is not equivalence.

Move mutation testing from the authored pilot to generated rules and runtime
paths. Challenge polarity, comparison endpoints, lost exceptions, lazy
evaluation, error/conflict precedence, stale evidence, wrong versions, traces
and source binding. Use targeted source mutations where PIT cannot express the
fault. Kill each known material mutant or explain, with evidence, why it is
unreachable or equivalent in the supported profile; an unexplained surviving
material mutant triggers repair.

For a proof claim, specify a narrow theorem separately: the emitted Java for a
declared supported fragment preserves its formal reference semantics for all
valid inputs under explicit runtime assumptions. A bounded solver experiment
is not that theorem. A theorem about an abstract evaluator also does not verify
the emitted Java unless the refinement to the actual program is established.
Use proof tooling only after those obligations and the trusted components are
specified; installing KeY or another prover is not a substitute.

**Closure tests:** combined conformance passes; supported operators and meaningful
interactions have reference cases; injected faults alter actual binary behaviour
and are detected; complete results and traces are checked. Report the precise
domain of every proof and every finite test. Correlated Catala/Java host services
retain separate challenges. Whole-compiler proof remains open until discharged.

## 6. Establish a basis for selective automation

Construct source-bound reference packets before running the candidate system.
Prefer explicit official examples and directly supported conditions; separately
label constructed examples and judgment-dependent interpretations. Allow a set
of defensible readings and an unresolved disposition. A single author or model
writing both candidate and expected answer does not supply independent meaning
evidence.

Reuse internal compliance knowledge for targeted reference assessment, and reserve
external counsel for material residual questions whose answer is needed. Neither
an expensive blanket consultancy nor a legal review of every future output is
a prerequisite to the engineering demonstration. However, if the available
references lack independent support, label interpretation accuracy unvalidated;
model agreement cannot repair that evidence gap.

Freeze development, any calibration, and final evaluation sources by family and
edition relationships. Include omissions, ambiguity, amendments, bilingual
differences and out-of-profile cases. Keep reference answers inaccessible to
generation and repair. Any tuning after viewing final results requires new final
evaluation data. Synthetic mutations test known failure mechanisms; they do not
estimate the natural prevalence of legal errors.

Before live execution, declare a useful-acceptance requirement and the treatment
of severe errors. Report accepted wrong decisions among accepted decisions,
accepted correct decisions among all eligible cases, omitted material
requirements, avoidable abstentions, and unresolved cases. Count related scenarios
within a circular as related observations, rather than thousands of independent
legal judgments. Use source-family-aware uncertainty; if the corpus is too small,
report the observed demonstration without a low-error-rate claim.

For review burden, compare the same cases and available evidence with a manual
baseline, recording correction work and elapsed review time. Control order and
learning effects. A measured reduction in calls to a model is not a measured
reduction in compliance review work.

**Closure tests:** the frozen clear cases produce the supported outcomes; frozen
material uncertainties are preserved; no known severe error is accepted in the
demonstration; the predeclared useful-acceptance requirement is met. All-abstain
fails usefulness even when it avoids unsafe decisions. Quantified assurance and
review-saving claims remain open until the corresponding independent reference
and uncertainty evidence is adequate.

## 7. Resolve the authorities needed by each decision

Extend and integrate the existing authority catalog. Record edition identity,
publication, effective intervals, the decision's relevant date, referenced
definitions and provisions, amendments and supersession evidence. Keep actual
effective time separate from when information became available. Track every
decision's dependency on those records so that an amendment invalidates the
right interpretation and executable evidence.

For bilingual material, align provisions and preserve differences as questions;
one translation must not silently resolve a substantive conflict. For priority,
exceptions, official examples and case-based arguments, record the source of
the claimed relationship and its applicable scope. An authentic citation can
still be inapplicable. Clingo verifies consequences of the supplied argument
graph; it does not establish the authority of its premises or preferences.

Implement temporal duties only within explicit profiles: one-time conditions,
deadlines, recurring obligations, ongoing requirements and withdrawals have
different state transitions. Qualitative standards remain judgment-dependent
unless the sources justify a concrete operational definition. Broader judicial
holding extraction, subsequent treatment and general precedent reasoning require
a separate evaluated scope; their absence cannot be concealed by an argument
solver.

**Closure tests:** retrieve a required distant definition; distinguish historical
and amended editions; reject an authentic but inapplicable authority; preserve
a priority cycle and a material bilingual discrepancy; invalidate dependent
results on amendment; replay a supported continuing-duty scenario. Close this
gap for the demonstrated circular profiles while listing unsupported legal
reasoning explicitly.

## Execution order and repair between phases

The current round-11 successor file lists tasks. It is not an executable
implementation of this larger closure plan. Extend the existing master program
only after defining the following phase commands, artifacts and acceptance tests.
The phase labels below are proposed, not existing CLI subcommands.

| Phase | Work | Required exit evidence |
| --- | --- | --- |
| P0 | Freeze supported profiles, current baselines, known-failure matrix, development sources and blinded evaluation protocol; update the monograph's current implementation map without deleting historical results | Reviewed contracts, source/label provenance, locked evaluation criteria, explicit proof boundaries and resource budgets |
| P1 | Implement common investigation records and region-level source reconciliation | Real discrepancy changes the workflow; source faults and benign differences handled correctly; restart and invalidation tests |
| P2 | Integrate alternative abstractions, authority dependencies and evidence-driven search | Missing-schema challenge investigated; missing definition retrieved; incompatible models and authority ambiguity preserved |
| P3 | Integrate Catala, broaden formal profiles and challenge the actual generated runtime | Combined binary conformance, counterexample replay and material mutation evidence |
| P4 | Connect live routes, run development cases and freeze the complete candidate | End-to-end Java packages, resolved and unresolved investigations, complete call accounting and dependency records |
| P5 | Run untouched evaluation, common-error study and the scoped review-burden comparison | Useful acceptance and unsafe-acceptance results, uncertainty and residuals; no post-hoc relabelling or hidden tuning |

P0 must declare exact call, retry and wall-time allowances before live work.
Older allowance numbers are historical authorisations whose remaining ledger
balance must be verified, not assumed available. Use already installed toolchains
and narrow fixed-vector commands. A changed master must not inherit authority to
make new network/model calls merely because its old command prefix was approved.

After each phase: verify input and artifact hashes, review acceptance and veto
evidence, execute focused repairs when indicated, rerun affected checks, and
refresh the next phase's concrete plan. Keep failed attempts and consumed budgets.
A failed interpretation blocks that interpretation and triggers the planned
repair; it does not automatically stop work on the investigation machinery.
A broken evaluator, corrupted evidence or exhausted authorised budget does stop
dependent execution until repaired or supplied with the missing prerequisite.
An updated file hash is not a substitute for a substantive review after a design
change.

## Evidence contract and skeptical review

The engineering question is whether the integrated workflow can discover,
investigate and expose consequential omissions and disagreements while producing
useful Java decisions on its supported scope. The interpretation question is
whether its accepted readings agree with independently supported reference
outcomes and retain uncertainty where those outcomes are unsettled. The review
question is whether it reduces actual correction effort without increasing
unsafe acceptance. These questions require separate evidence.

The baselines are the current source/interpretation workflow and its fixed-fact
issue path, frozen by source hash; for method comparisons, add equal-budget
repetition and abstraction-only ablations. For review burden, the comparator is
the documented manual procedure on the same cases. Never promote mutation counts,
solver agreement or the number of proposals to interpretation-accuracy criteria.

Promotion vetoes include a material missed source region, unsupported factual
mapping treated as equivalence, missing authority dependency, lost alternative,
wrong actual Java output, unexplained material surviving mutant, stale evidence,
or an accepted severe error. Runtime, ranking scores, raw parser agreement and
mutation percentages are explanatory diagnostics. A useful-acceptance shortfall
rejects product usefulness under the protocol but can motivate targeted repair.
Harness invalidity, corrupted inputs and missing authorised resources are
continuation vetoes for dependent work.

The skeptical audit identifies five ways a superficially successful plan could
mislead: all routes share the same omission; every question is sent to a human;
an authored oracle repeats the model's misreading; a tool proves a different
formal object from the emitted Java; or selected easy paragraphs are presented
as whole-circular coverage. The corresponding controls are common-error
challenges, mandatory clear-case acceptance, independently supported and blinded
reference packets, target-bound proof/conformance evidence, and visible
whole-document dispositions. These controls make the plan suitable for detailed
implementation, conditional on P0 freezing actual cases, budgets and pass criteria.

Material defaults remain hypotheses: required extraction routes depend on source
layout; breadth and action budgets trade investigation against resource limits;
support profiles constrain what a successful result means; and independent
reference availability constrains accuracy claims. P0 must record the provenance,
failure mode and earliest check for each selected value. No convenient inherited
limit or calibration setting becomes a validated policy by repetition.

Preserve phase manifests, exact source and code versions, commands, tool/model
identities, CPU status, seeds where applicable, wall time, attempts and output
hashes. Final results need separate decisions on engineering correctness,
interpretation evidence and review benefit, plus the strongest remaining common
failure explanation. A demonstrated working version can close its declared
engineering scope before a general low-error-rate claim becomes supportable.
Actual bank integration remains deferred throughout this plan.
