# Prospectus delivery program: source to qualified answer

6 October 2026. Proposed specification; implementation and legal promotion have
not run. Baseline: `da2c7a4336cbd1146a9d5b8896bc982d63668441` on
`feature/prospectus-evidence-master`.

[Machine specification](../implementation/prospectus-delivery-program-2026-10-06/program.json)
and [evidence summary](../implementation/prospectus-delivery-program-2026-10-06/PROGRAM-EVIDENCE.md).

This program addresses the repeated reopening of the prospectus work. The current
reader can preserve useful controls, but it does not construct the complete
operative contract, carry actors and exceptions across clauses and documents, or
separate source disclosure from applicable law and an actual event. A larger test
count or another OCR pass cannot close those boundaries by itself.

The program therefore delivers four linked results with separate statuses:

1. a hash-bound, time-aware source bundle and assembled contract;
2. a typed clause account that preserves actors, modality, elections,
   alternatives, conditions, exceptions and cross-references;
3. a separately dated assessment of external law and supplied facts; and
4. a report that exposes the evidence, unresolved dependencies and the existing
   bank obligations without silently turning a prospectus feature into a legal
   conclusion or trading permission.

The initial release is a qualified evidence service. It may state that a
mechanism is supported by the selected operative terms, unresolved or
contradicted, subject to the question contract below. It may not state that an
event occurred, that a law applies, that a customer is eligible, or that a bank
may execute a transaction unless the corresponding, separately evidenced result
is present. Existing `may_execute_transaction: false` behavior remains the safe
default.

## 1. Questions, outputs and intended use

Every request carries a versioned question. The broad phrase “loss absorption”
is not used as a universal label.

| ID | Question | Positive answer means | Required evidence | Explicit non-claim |
| --- | --- | --- | --- | --- |
| Q1 | `feature_presence.v3`: Does the selected debt instrument provide for principal reduction without full payment, unpaid cessation, or common-share conversion that can occur without holder election? | A supported contractual mechanism is present, with actor, trigger and effect. A separately named disclosure field records a stated statutory mechanism. | Assembled source bundle, clause witnesses and query-specific dependency disposition. | It does not establish that a disclosed statutory power applies, an event occurred, or an economic loss was realized. |
| Q2 | `feature_quantifier.v1`: Is the mechanism compulsory, issuer-held, holder-elected, or an alternative? | The requested quantifier is supported; a possible common-share alternative is not silently treated as common-share-only or compulsory. | Clause graph with alternatives, elections and inherited scope. | It does not choose among rival legal interpretations without a recorded disposition. |
| Q3 | `source_completeness.v2`: Are the material operative units and dependencies for this question completely resolved? | Every material unit and relevant dependency has a supported disposition; none is unevaluated or unresolved. | Source/dependency graph, page geometry, cross-reference inventory and review records. | It does not mean that every document in the issuer universe has been collected. |
| Q4 | `law_applicability.v1`: Does a specified dated rule or authority apply to this issuer, instrument, event and procedure? | The supplied authority is valid at the relevant time and all declared applicability premises are supported. | Authority source, jurisdiction, effective and known intervals, event facts and procedural facts. | It does not discover all law or infer applicability from country, issuer name or a prospectus sentence. |
| Q5 | `event_outcome.v1`: Given supplied contract and actual event facts, what contractual transition follows? | A guarded financial/legal profile executes with complete, typed inputs and reports a conditional result. | Contract profile, event facts, calendar, rounding, price and settlement inputs with provenance. | It does not establish that the event occurred or that a market value is realized. |
| Q6 | `bank_obligations.v1`: What obligations and missing evidence remain for the bank workflow? | The existing 14-obligation inventory is returned with source-linked statuses and no automatic clearance. | Product assertions, issuer basis, prospectus sources, client facts and law/fact receipts. | It does not authorize a trade, waive review or collapse unknown into permitted. |

Cancellation following full repayment, coupon cancellation, ordinary holder
conversion and creditor-approved restructuring have separate fields and do not
silently satisfy Q1. Q2 records both possible-common-share and common-share-only
questions, and distinguishes an issuer's power from a duty. A conditional feature
can be present without evidence that its trigger actually occurred. A positive
still needs its local dependencies and possible defeaters resolved; a known
amendment that could remove it prevents an unconditional positive.

The reader-facing report shows Q1–Q6 as separate rows. A missing document blocks
only the questions that depend on it. A missing document cannot turn an
unrecognized clause into Q1=No.

## 2. Evidence contract and research ledger

The implementation must record this contract before each decision-making run.

**Question.** Does a source-to-answer path preserve the meaning of a selected,
possibly amended and bilingual prospectus while distinguishing disclosure,
external law and actual facts?

**Comparators.** The evaluation ladder is: (A) the ordinary production reader,
(B) the frozen 4 October candidate, (C) the successor using independently
reviewed source and clause inputs, and (D) the successor using automatic
extraction against the same frozen source cohort. An optional model-assisted arm
is a separately registered experiment and cannot be promoted by this program.
Arm C is an oracle-input diagnostic of downstream computation, not an accuracy
competitor with A/B/D. Freeze arm D before the independent evaluator supplies
arm C's reviewed clause structures. Neither final labels nor oracle structures
may enter D's extraction, prompts, selection or repair during the frozen run.

**Primary pass criterion for the first release.** Deliver a reviewed, assisted
service for an explicit finite scope. Every independently labeled, decidable
release question must be answered correctly with all material qualifiers and
source dependencies; every labeled unresolved question must preserve its reason.
Both supported positives and supported negatives must be exercised. This is a
zero-error acceptance screen over that finite set, not a population error bound.
No unresolved release-critical unit may be silently dropped from the denominator.

General automatic promotion is a separate gate. Before an unexposed cohort is
opened, the product/risk owner and evaluation lead must specify the tolerable
error and abstention rates, sampling unit, sample-size justification and
uncertainty method in `thresholds.json`. They are currently unassigned; no
unsupported numeric tolerance is substituted here. That missing decision blocks
general promotion, not P1–P6 engineering or delivery of a clearly scoped
assisted service. A threshold chosen after seeing results requires a fresh cohort.

**Promotion vetoes and repair triggers.** A candidate fails if it crashes,
produces a negative without a completeness certificate, changes a qualifier or
actor, treats an explicitly non-operative example as operative, treats a holder
option as compulsory, uses a source outside its validity/knowledge interval,
executes an incomplete financial profile, or marks an unimplemented handler or
unassigned review as complete. Preserve the failed outputs and continue the
planned repair. The existing four semantic/dependency counterexamples reject the
current readers for general promotion; they do not reject further investigation.

**Continuation vetoes.** Wrong imported baseline, corrupted source or output,
evaluation-label leakage, invalid comparator/question mapping, or a missing
required diagnostic invalidates the affected experiment. Quarantine its result,
repair the harness or data, and restart that experiment before interpreting it.
Unavailable primary sources and independent reviewers block only their dependent
evidence/release tasks. A budget cap stops the affected automated job and writes
a resumable work order; it is not evidence against the design.

**Explanatory diagnostics.** Counts of tests, extracted words, OCR corrections,
runtime, parser confidence, candidate scores, and the 20–30 corner fixtures are
useful for repair. They are not legal accuracy, convergence or production
readiness evidence by themselves.

**Non-conclusions.** Passing the controls does not establish general legal
accuracy, completeness of an issuer dossier, correctness of an external-law
interpretation, event occurrence, market value, or permission to transact.

**Preserved artifact.** Each run writes a manifest containing the Git commit,
exact command, environment, input and method hashes, source/time selections,
randomness (or `N/A deterministic`), wall time, phase receipt, output report,
decision table, inference-status table and next action. The controller never
rewrites historical receipts.

## 3. Design derived from the code and literature

The current call chain is `master_phases.run_corpus` →
`run_bond_loss_absorption_classification.py` →
`loss_absorption_reader.py` → four Boolean premises in
`loss_absorption.py`. `feature_investigation.py` then replays the feature,
joins the 14 bank obligations and deliberately records
`NO_AUTOMATIC_IMPLICATION`. The frozen candidate is used by
`prospectus_corner_repair_worker.py` and optional admission loaders; it is not
the ordinary reader. The BASF
consumer returns choices and locators, with `full_german_contract_constructed:
false` and `legal_answer: null`.

The design uses the following bounded lessons from the retained literature:

* ContractNLI supports discontinuous, self-contained evidence and distant
  exceptions, but its embedded-text NDA corpus does not justify a prospectus
  accuracy claim for scanned or multicolumn PDFs.
* SARA-style extraction makes arguments and spans explicit; a missing argument
  must remain visible instead of being filled by a nearest-date or first/last
  day default.
* LegalRuleML and structured argumentation supply a vocabulary for source,
  interpretation, authority, alternatives and defeat. They do not decide which
  prospectus reading is correct.
* Catala's formal semantics can execute reviewed premises and expose conflicts;
  its translation proof does not prove that prose was interpreted correctly.
* Date arithmetic must distinguish calendar days, business-day movement,
  accrual periods and rounding. Contractual convention is an input, not a
  library default.
* The autoformalization study supports separating translation from solver
  execution and recording unsupported assumptions; its inconsistent dataset
  accounting and different logical target exclude its reported rankings from
  our thresholds.

These are design constraints, not transferred benchmark results. The detailed
review is [LITERATURE-REVIEW.md](../implementation/prospectus-root-cause-2026-10-06/LITERATURE-REVIEW.md).

## 4. Interfaces to implement

The successor is deliberately typed and source-linked. JSON schemas and Python
dataclasses are to be added only when their phase begins; this document defines
their required fields so that a passing phase cannot quietly omit a dependency.

### Source bundle and time graph

`SourceBundle` contains `instrument_id`, `issue_date`, `query_as_of`, a document
set, selection purpose (`issue_formation`, `amendment`, `event` or `review`),
and a dependency graph. Each `DocumentVersion` records its byte hash, source
authority, document date, valid interval, known interval, language, page count,
supersedes/amends relation, acquisition receipt and page-level geometry status.
Issue-formation documents and later amendments are different supported time
paths. A post-issue document cannot be admitted to an issue-time question merely
by removing the existing guard.

### Geometry-preserving text units

`TextUnit` retains source page, bounding box, reading order, paragraph/list
parent, language, raw text, normalized text, extraction method and review status.
Columns, German margins, footers, continuations and blank operative pages remain
separate units until a reviewed ordering rule joins them. A text hash alone is
not a layout or completeness certificate.

### Contract and clause graph

`ClauseNode` has typed fields for actor, affected holder/issuer, modality,
principal or coupon, trigger, mechanism, payment/loss effect, condition,
exception, election/option, alternative group, temporal scope, antecedent,
cross-reference and provenance. Edges include `governs`, `qualifies`,
`exception_to`, `references`, `alternative_to`, `supersedes` and `inherits_scope`.
Every operative unit starts `UNEVALUATED`; it can become `SUPPORTED`,
`CONTRADICTED`, `UNKNOWN` or `CONFLICT` only with an evidence disposition.
Matcher silence never creates `CONTRADICTED` or a negative answer.

### Law, facts and calculations

`LawBasis` stores authority, jurisdiction, edition, effective interval, known
interval, source, interpretation alternatives and applicability premises.
`FactRecord` stores the actual issuer, client, bank, event, date, procedure,
calendar, rounding, price and settlement fact with observation and knowledge
times. A prospectus statement, a supplied legal rule and an observed event are
different record kinds. `FinancialProfile` reuses guarded
`closure_mechanisms.py` kernels only after all advertised inputs, units,
rounding and calendars are complete; unsupported profiles remain unsupported.

### Query result and report

`QueryResult` contains question/version, a typed value and status, quantifier,
source witnesses, completeness certificate, dependencies, unresolved items,
law/fact statuses and non-claims. Propositions use `YES`, `NO`, `UNKNOWN` or
`CONFLICT`; quantities and obligation lists retain their own types. The report
renders the same result objects and cannot manufacture a conclusion from a
display-only field. Bank integration consumes the report through an explicit
adapter and retains every existing obligation.

## 5. Phased execution program

The machine specification is the authoritative dependency graph. All handlers
below are currently `NOT_IMPLEMENTED` and `NOT_EXECUTED`; the readiness checker
must fail if a future phase is described as accepted without a handler and its
receipt. Phase acceptance is split into engineering, evidence and release
statuses.

### P0 — Freeze the contract, evidence and independent cohort

Create the schemas above, version Q1–Q6, freeze the current production and
candidate import hashes, snapshot the 1,467 issue records/1,307 spans and the 25
unassigned review forms, and write the reviewer protocol. Curate a family,
issuer, template and document-version split before any successor is trained or
tuned. Assign independent reviewers; the coding agent may prepare packets but
cannot fill an independent legal label.

Exit requires a valid machine DAG, question schemas, denominator definitions,
reviewer protocol and role requirements, a frozen source manifest, and explicit
pending resource/threshold fields. A blank reviewer identity is never treated as
assigned. P1–P6 depend on this engineering receipt; the evidence gate separately
requires named reviewers and frozen independent labels before evaluation. Review
assignments and cohort reservation start here, not in P7. No messages are sent to
potential reviewers without the user's authorization.

### P1 — Build the source and geometry graph

Implement a successor intake that binds acquisition receipts, preserves page
geometry and languages, inventories cross-references and represents issue,
amendment, event and review time separately. Start with the seven existing
offerings, the 17 BES scan pages, Deutsche bilingual pages 36–38 and the BASF
base/supplement/annual-report set. Use the existing OCR runtime where its
receipts pass; installing another OCR engine is not a prerequisite.

Create `src/legalmath/prospectus/successor/service.py` and the supported
`legalmath prospectus assess` command in this phase. Initially it consumes
reviewed typed inputs and returns explicit `UNKNOWN` for unavailable stages.
P2 and P3 must extend that same path with real assembled contracts and clause
meanings. A schema-only stub does not pass a source-to-answer slice; P6 hardens
the integrated path rather than introducing it for the first time.

Acceptance is lossless reviewed reconstruction on a small source slice,
including an intentionally blank operative page and a multicolumn/margin page,
with page order and hashes preserved. Stop if a source cannot be authenticated
or its reading order cannot be reviewed; issue a bounded acquisition work order
instead of guessing.

### P2 — Assemble selected contracts and dependencies

Implement `contract_assembly` over the source graph. It must construct
continuous controlling text with every deletion, substitution, filled field,
condition and cross-reference traceable to a source. The first real slices are:

* BASF German Option I: nested alternatives/placeholders, successor guarantee
  §10(d), change-of-control right, holder put exclusion, clean-up call, and the
  195–209 versus 209–290 incorporation discrepancy;
* Deutsche pages 36–38 and the remaining bilingual operative pages, preserving
  language authority, holder elections and conversion alternatives; and
* one BES dossier with all 29 declared dependencies and the duplicate risk
  factor 1.17 precedence decision.

Then execute the retained G13–G17 work orders for Enel, Unilever, Lloyds, SEB,
LVMH and BBVA as source availability permits. The assembler reports
`COMPLETE`, `PARTIAL` or `UNRESOLVED` per question. It may not declare a full
contract from checkbox completion or locators alone.

### P3 — Interpret typed clauses with safe unknowns

Implement clause graph construction and a deterministic, source-derived
semantic interpreter. Preserve scope across sentences, actors, modality,
antecedents, negation, examples, exceptions, elections and alternative groups.
Add at least 30 corner fixtures: the seven retained probes plus reviewed
examples for distant exceptions, issuer/holder swaps, creditor-approved versus
statutory mechanisms, unpaid cessation, amendment precedence, bilingual
authority, option inheritance, non-operative schedules and duplicate clauses.

Acceptance has zero hard-screen failures on controls and independently reviewed
real slices. In particular, the unprovided Condition 14 and unfamiliar unpaid
cessation cases cannot receive a negative through matcher silence; the example
and holder-option cases cannot receive a compulsory positive. A negative requires
affirmative repayment/absence evidence and a completeness certificate.

### P4 — Apply law and actual facts on separate timelines

Implement the `LawBasis` and `FactRecord` paths using the existing
`LegalVersion` validity/knowledge distinction. Record forum, authority,
effective date, known date, event date, procedure and applicability premises.
Keep the issue-formation validator for its declared pre-issue purpose and add a
separate amendment/event path. Admit exact primary sources for Portuguese
Annex 2B, HETA, Dana, Lloyds, Ukraine, Popular/Snoras and historical Italian
Articles 65/67 under bounded work orders; the remaining 24 retrieval requests
are a resource limit, not evidence of applicability.

Acceptance uses dated counterfactual pairs that change one premise at a time:
issue date, amendment date, effective law, forum, event, suspension and
procedure. The report must show when a result is `UNRESOLVED` because a rule or
fact is missing. It must not infer law from an issuer country or a prospectus
label.

### P5 — Complete guarded financial profiles

Inventory each advertised Deutsche, BBVA, SEB and UBS profile. For every
profile, bind derivation/source anchors, principal and coupon units, trigger,
conversion price, rounding, calendar, accrued amount, corporate action and
settlement inputs. Test non-associative month arithmetic and business-day
movement as distinct operations. Keep the existing exact arithmetic where its
premises hold; mark a profile `UNSUPPORTED` if an input or convention is absent.

Acceptance is an invariant suite over complete typed scenarios plus source-bound
hand calculations reviewed independently. A numerical result is conditional on
the supplied premises and never becomes an actual event or market-value claim.

### P6 — Harden the supported vertical slice

Harden the successor service/CLI introduced in P1 so a complete source slice
traverses intake → assembly → clause graph → Q1–Q6 → report → bank obligations.
The fixed future command, with slice/output choices bound in its run manifest, is:

```text
python3 -m scripts.prospectus_delivery phase --phase P6
```

That handler does not exist yet and must not be substituted with a shell stub.
The vertical slice must run through the installed package/import path, not by
inserting the frozen candidate directory. It must emit a receipt, source map,
question results, unresolved dependencies, decision table and the unchanged 14
bank obligations. A clean end-to-end run with reviewed inputs is required before
automatic extraction is evaluated.

### P7 — Independent paired evaluation

Run arms A–D on the frozen, unexposed cohort. Evaluate each question separately:
true/false positives and negatives where a binary label is appropriate,
qualifier/actor/exception preservation, evidence completeness, abstention
reasons, dependency recall, and report integrity. Publish denominators by
instrument, issuer family, document layout, language, template and time path.
Identical text spans with different selections or amendment histories remain
distinct cases.

The evaluator is independent of the semantic interpreter. The current
`validate_semantic_witness` replay remains an integrity check only; it is not a
semantic oracle. Results include hard-veto, descriptive and statistical
evidence classes, paired uncertainty intervals where applicable, and the
strongest alternative explanation. Do not add the 186 and 885 suite counts or
call a 20–30-case fixture screen an accuracy estimate.

### P8 — Scoped release and maintenance

Release only the questions, source families, languages, law editions and
financial profiles that pass their gates. The release manifest states what is
supported, what remains conditional or unresolved, the reviewer sign-offs, and
the exact non-claims. Every source or method change invalidates dependent
receipts and refreshes a next-phase plan before rerun.

The maintenance controller is finite and resumable: at most three bounded
attempts and two semantic repair cycles per phase, deterministic attempt
directories, durable pre-dispatch accounting, and downstream invalidation when
an input hash changes. After the cap, status is `BLOCKED_EXTERNAL` or
`REPAIR_REQUIRED` with a concrete work order; it is never silently closed.

## 6. Evaluation and promotion rules

The program maintains three ledgers:

* engineering correctness (imports, schemas, hashes, deterministic execution);
* evidence and numerical validity (source completeness, law/fact intervals,
  arithmetic invariants and reviewer agreement); and
* interpretation and intended use (question-specific independent labels and
  human acceptance).

Evidence cannot move from one ledger to another without its gate. For stochastic
or model-assisted arms, one seed, a short run or a descriptive tail cannot rank
methods. A candidate that passes a hard screen is viable under that screen; it
is not thereby superior. An optional model must follow a separate reviewed
training/evaluation protocol and may propose constrained clause data only.

The release gate is conjunctive:

1. all applicable hard screens pass with zero failures;
2. the source bundle and clause graph have no unaccounted material units for the
   released question;
3. the declared finite assisted-service acceptance screen passes; any general
   automatic claim additionally passes its pre-registered sampling/risk rule
   with uncertainty reported;
4. law, facts and financial inputs are complete for any corresponding
   non-conditional applicability or event claim;
5. intended-use reviewers sign the exact scope and non-claims; and
6. every handler and artifact is present, hash-bound and reproducible from the
   supported entrypoint.

An all-`UNKNOWN` system does not pass: it fails usefulness for the question.
Conversely, a high answer rate with unresolved dependencies fails safety. The
program seeks supported answers and honest, local abstention.

## 7. External dependencies and stop conditions

The following are explicit dependencies, not hidden promises:

* qualified independent legal reviewers for the 25 existing forms and the
  unexposed cohort;
* authenticated executed agreements, amendments and filings in the G13–G17
  work orders;
* exact dated primary law and event/client/bank facts;
* German and bilingual source review for BASF and Deutsche;
* a documented intended-use decision for any bank-facing output.

If any source, reviewer or fact is unavailable, the affected question remains
`UNRESOLVED` and the controller writes a work order. It may continue unrelated
engineering phases. A missing dependency is not a reason to rewrite old receipts
or to report a global failure.

## 8. Current implementation status

The investigation, seven constructed probes and the seven-paper literature
review are complete and retained. The delivery program, machine specification,
evidence manifest and skeptical review are the artifacts of this turn. The
successor source graph, clause graph, legal/fact service, vertical CLI, evaluator
and maintenance controller are **not implemented and not executed**. The
readiness checker validates this statement; it is not a substitute for those
handlers.

The root-cause report is [ROOT-CAUSE-REPORT.md](../implementation/prospectus-root-cause-2026-10-06/ROOT-CAUSE-REPORT.md), and the review record is
[SKEPTICAL-REVIEW.md](../implementation/prospectus-delivery-program-2026-10-06/SKEPTICAL-REVIEW.md).

## 9. Concrete execution and acceptance details

### Dependency order and implementation units

The DAG is `P0 → P1 → P2 → P3`, with `P1 → P4` for law/facts and
`P2 → P5` for financial profiles. P6 joins P3/P4/P5, P7 compares the arms,
and P8 delivers the scoped result. Dependencies are engineering prerequisites.
Source, legal and intended-use acceptance are separate gates and can remain
pending while an unrelated module is implemented. The module names, owners
and exact future argument vectors are in `program.json`; they are planned,
currently unavailable commands. The common future phase form is:

```text
python3 -m scripts.prospectus_delivery phase --phase P0
```

P0 implements the small dispatcher and fixed phase registry, reusing existing
lock, attempt-receipt and durable-budget code. It reads the pinned program
path, selects an implemented function from that registry, and never executes
shell text supplied by a plan or document. It must reject an absent handler
before opening an attempt. P1 adds the application CLI; P2/P3 extend its real
source-to-answer behavior. P6 installs a package in an isolated environment,
runs it outside the checkout with no candidate path injection, and compares
the emitted questions and report with the source-run results.

### Meaning, coverage and baseline compatibility

The initial source inventory must account for every admitted page unit before
deciding whether it is operative. Headers, examples, selected clauses, excluded
alternatives and repeated text each need a role and rationale. A detector that
only inventories the phrases it recognizes has not solved R06. Dependency
discovery uses all explicit incorporation and clause references plus a
reviewer-authored document-role inventory; a manual-only list and an automatic
reference pass are compared for omissions. A dependency can be excluded from a
question only with a recorded relevance argument, not because retrieval failed.

The clause interpreter emits supported candidate readings and their unresolved
choices. Consistent rival readings that change an answer produce UNKNOWN;
contradictory applicable assertions without a resolved priority produce
CONFLICT. A negative requires a complete, accepted question scope and no
qualifying mechanism in any retained reading. A positive requires a supported
mechanism and disposition of known exceptions/amendments that could defeat it.
A missing unrelated annual-report metric must not obscure a supported textual
feature. Such local relevance claims are independently reviewed.

Create a reviewed adapter for the existing `prospectus-loss-absorption.v2`
question, which includes disclosed statutory principal loss. Compare arms A–D
only on that common projection, preserving its scope and exclusions. Report
the richer native contractual/disclosure/quantifier Q1–Q6 results separately.
If a question cannot be mapped, report NOT_COMPARABLE and its denominator;
do not count the old reader as wrong on an output it never claimed to provide.

Boolean YES/NO/UNKNOWN/CONFLICT applies to propositional queries. Q5 additionally
returns a typed quantity, unit and conditional-input record; Q6 returns the
obligation list with individual statuses. Neither is forced into one Boolean.
The ordinary feature interface remains a versioned compatibility adapter;
switching defaults requires scoped acceptance and a rollback path.

### Independent labeling and useful coverage

P0 prepares the 25 existing review packets and reserves an unexposed cohort.
The 25-form queue and 1,467-record queue are different evidence units; identify
their overlap explicitly and do not add their counts.
Each real release question needs two independent first-pass readings, made
without viewing engine predictions, followed by a third adjudicator or recorded
reasoned agreement for disagreements. If staffing is unavailable, report that
constraint and continue engineering; do not replace the second reading with
the implementing agent or the same recognizer. A reviewer may conclude that
the sources genuinely leave an issue unresolved. Preserve alternatives and
the missing evidence; majority vote does not create legal authority.

Process the 1,467 original records in batches of at most 50 unique spans,
chosen to cover question families rather than only easy records. This batch
size is a workload cap, not a statistical design. Deduplicate source text for
display, then restore all 1,467 instrument-context instances before assigning
answers. Retire a record only with an exclusion reason. Labels include source
scope, operative role, actor, effect, election, condition, exception, governing
language, time, references and acceptable uncertainty. Measure reviewer time
and unresolved disagreement; an assisted answer is not automatic extraction.

For each question and stratum publish total assigned N, independently decidable
D, correct supported answers C, wrong answers W, abstentions A, conflicts and
invalid inputs. Show useful coverage C/D, wrong-supported fraction W/(C+W),
and all-case accounting; display N/A for a zero denominator. These are
descriptive on the development and finite acceptance sets. Safety is not shown
by excluding hard questions, and useful coverage is not shown by counting
manually supplied clauses as automatically recovered.

Freeze issuer, template and source-version groups before evaluation. Reserve
at least one unexposed group for each advertised language/layout/mechanism;
if that cannot be done, narrow the support register. A statistical generalization
study requires independent sampling units and enough groups for the agreed error
bound; 30 correlated clauses from one template do not supply 30 independent
observations. Holdout failure can direct repair, but after its labels guide
changes it becomes development data and a fresh cohort is needed for promotion.

### The 30-case development screen

The seven existing probes remain unchanged and exposed. Add the following
23 fixtures in P3, with source-inspired language and expected behavior reviewed
before evaluation. Counterfactual partners can be added, but do not inflate
the independent case count. These are fixture specifications, not downloaded
new prospectuses or an executed benchmark.

| Fixture | Construction and discriminating behavior |
| --- | --- |
| F08 | Governing paragraph on the previous page: inherit the issuer and trigger. |
| F09 | Exception several clauses away: block an otherwise positive reading. |
| F10 | Issuer/holder actor swap: preserve the changed election owner. |
| F11 | Coupon-only cancellation: do not infer principal loss. |
| F12 | Note cancellation after full redemption: do not infer unpaid loss. |
| F13 | Principal obligation discharged without payment: retain the loss effect. |
| F14 | Holder vote amends principal: record creditor restructuring separately. |
| F15 | Authority imposes loss without holder consent: separate disclosure and actual applicability. |
| F16 | Common or preferred share alternatives: possible common is not common-only. |
| F17 | Cash or shares at issuer election: distinguish choice from compulsory shares. |
| F18 | Conversion at holder election subject to an issuer veto: preserve both actors. |
| F19 | Denial of issuer power followed by an exception: scope the negation correctly. |
| F20 | Cross-reference cycle with a missing target: stop traversal and name the dependency. |
| F21 | Supplement overrides base wording: preserve source and temporal priority. |
| F22 | Later amendment after issue: issue-time answer unchanged, event-time answer reassessed. |
| F23 | German governing text conflicts with English translation: retain governing-language evidence. |
| F24 | Margin instruction says delete for selected issuer: remove only its governed branch. |
| F25 | Unselected schedule contains write-down text: do not promote it to operative meaning. |
| F26 | Duplicate clause number with different text: require precedence disposition. |
| F27 | One issuer has no initial guarantee but conditional successor guarantee: retain the condition. |
| F28 | Clean-up call threshold reached without note reduction: preserve the missing conjunct. |
| F29 | Bail-in acknowledgment but no established authority/event: no law or event conclusion. |
| F30 | Month-end, holiday and ambiguous rounding: no invented date or settlement quantity. |

### Default and assumption audit

| Choice | Provenance/status | Why use it | Failure mode | Early diagnostic |
| --- | --- | --- | --- | --- |
| Scoped assisted first release | Proposed product boundary | Delivers useful checked work while automation remains unproved | Manual labor hidden as accuracy | Separate C/D and record review minutes |
| Typed deterministic baseline | Hypothesis from R02–R07 and literature | Exposes transformations for inspection | Graph simply renames regex output | Seven probes plus source-unit accounting |
| 30 development fixtures | Convenience coverage screen, not sample-size claim | Exercise identified failure classes | Overfit exposed phrasing | Unexposed template/family groups |
| Three attempts/two semantic repairs | Inherited bounded-controller pattern, convenience cap | Prevent repeated empty phases | Stops a viable repair too soon | Work order preserves remaining repair and evidence |
| 30 minutes per automated phase attempt | Proposed resource ceiling | Makes long jobs reviewable and resumable | Large dossier exceeds cap | Start one slice; split jobs without dropping units |
| 50 unique spans per review batch | Workload hypothesis | Establish real review throughput before scaling | Grouping erases instrument differences | Re-expand all context instances |
| All complete finite-scope answers correct | First-release acceptance policy | A known wrong accepted answer has a concrete repair | Blanket abstention or scope gaming | Freeze scope; require decidable positives/negatives |
| Automatic error/coverage thresholds | Human risk choice, unassigned | Must match intended use and independent sampling | Arbitrary post-hoc threshold | Lock thresholds and sample justification before exposure |
| Existing OCR and exact kernels | Reviewed reuse baseline | Preserve working tools and source-bound code | Layout/edition/convention mismatch | P1 layout checks; P5 source and unit checks |

### Repair, refresh, budgets and command discipline

After each phase, write `next-phase.json` with the first failed interface,
counterexample, invalidation set, remaining budgets, handler existence, exact
argument vector, source/reviewer dependencies and next acceptance test.
Supported mechanical repairs can execute automatically under the registered
handler. New semantic repairs require a code change and skeptical review by
the supervising coding agent; the controller does not invent or run source
code contained in data. Up to two semantic repair cycles and three execution
attempts are allowed per phase. The controller then returns REPAIR_REQUIRED
or BLOCKED_EXTERNAL with the specific unfinished task; it never marks it done.

Any input/method/question change invalidates descendants by dependency hash.
Resumption must be idempotent, concurrent writers must be rejected by the
existing lock scheme, and an interrupted retrieval must consume its recorded
budget before dispatch so a retry cannot create invisible requests.
Missing source and reviewer evidence prevents promotion, but unrelated DAG
branches remain available. A changing source does not authorize rewriting
an earlier result; the report identifies the new version and its affected answers.

Keep the existing 188/212 retrieval ledger. Use retained sources before new
requests; queue the next discriminating executed agreement or dated authority,
rather than a broad search. At the 24-request remainder, stop retrieval and
record unresolved work. New spending, model calls, installs or GPU use need
their own justified task and evidence contract; none is needed for P0/P1.
Future phase runs use an existing Python 3.11 CPU environment and record its
actual interpreter and package versions. Optional learned components need a
separate target-specific training, budget, seed and downstream evaluation plan.

Use the fixed `python3 -m scripts.prospectus_delivery` command form once the
wrapper exists. Local file edits already have standing permission. Do not
modify protected allow-list files to claim that OS restrictions disappeared;
request only any actually missing narrow execution permission, grouped before
the corresponding batch. No broad Python/shell permission is required by this
design. Historical authorization for a task does not install a sandbox rule.

P8 completes the prospectus LaTeX narrative with the revised question meanings,
source construction, measured results and supported-use register, builds its
PDF and inspects rendered pages. It publishes an installation/runbook and
receipt replay procedure for another checkout. This plan does not certify
independent human acceptance of that future document or the legal service.

## 10. Reviewed starting point

The first implementation milestone is deliberately small: P0 plus the P1
source/service path, then one continuous BASF Option I assembly and its typed
Q1–Q3 report. It must retain the scheduled-put exclusion, change-of-control
right, successor guarantee and both clean-up-call conditions. Known missing
agreements remain question-local dependencies. Passing this slice justifies
expansion to Deutsche/BES and the remaining source work orders; it does not
silently approve general automation.

The [skeptical review](../implementation/prospectus-delivery-program-2026-10-06/SKEPTICAL-REVIEW.md)
records repaired design flaws and remaining resource decisions. Its verdict
is specification readiness for incremental implementation, not completed
product execution. Validate the specification with:

```text
python3 -m scripts.validate_prospectus_delivery_program
```
