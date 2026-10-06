# Production repair program for P0–P6

Status: **reviewed proposal, with isolated reference checks executed**.
Production implementation is not claimed complete. This replaces repeated
unchanged phase execution as the proposed route to delivery. Baseline:
`7fd9c4e864c22da1e8a5df8ed7bc5c59331eb25f`.
Evidence: [diagnosis](../implementation/prospectus-phase-roots-2026-10-06/ROOT-CAUSE-AND-SOLUTION.md),
[probes](../implementation/prospectus-phase-roots-2026-10-06/counterexamples.json),
[literature](../implementation/prospectus-phase-roots-2026-10-06/LITERATURE-REVIEW.md)
and [proofs](../implementation/prospectus-phase-roots-2026-10-06/PROOFS.md).

## Question and evidence contract

Can the service answer a declared finite set of prospectus questions correctly,
from the selected source contract, applicable law and explicit scenario/context,
while preserving justified uncertainty and independently reviewable evidence?

The candidate is a source-mapped selected-contract representation with executable
predicates and real phase dataflow. The comparator is the pinned current successor
on identical questions, source editions and supplied facts. Do not compare a
reviewed repaired input with an unreviewed baseline input and attribute the
whole gain to automatic extraction.

Engineering pass criteria: the original demonstrated violations disappear under
the stated target; all supplied necessary premises participate; exact source
occurrences and context identities survive each transformation; installed CLI
consumes the accepted phase outputs. A change to a relevant upstream product
must either change/recompute the affected result or have a checked reason for
no effect.

Legal acceptance criterion: zero wrong supported answers on a predeclared finite
independently reviewed cohort, with useful positives and negatives for each
supported question. This is a finite release criterion, not proof of zero future
error. Record cohort size/exposure, coverage and all errors; wider deployment
needs a separately agreed risk criterion and uncertainty evidence. No numerical
coverage threshold may be invented after seeing the answers.

Promotion vetoes: wrong supported answer; unresolved source/rule/identity needed
for that answer; incomplete scoped evaluation; absent independent acceptance.
Continuation vetoes: wrong code import, corrupted source/output, invalid
comparison, hidden paid/model execution or an invalid mathematical target.
A missing reviewer blocks legal promotion, not engineering repairs. An expected
candidate failure triggers its next planned repair.

Explanatory only: test counts, text/reference counts, cache reuse, runtime,
file size and proportion UNKNOWN. They must not become substitutes for correct
useful answers. No stochastic models, model ranking or default parser change
is included in this first repair program.

## Skeptical review and revisions

The first tempting plan—assign reviewers, complete BASF and rerun all phases—is
rejected. It leaves ignored legal premises and wrong bank context in place,
and revised P2/P4/P5 outputs still do not flow to P6. Another controller wrapper
would likewise be insufficient unless it dispatches actual repair work.

The revised order below passes review for **bounded implementation**, not release.
It first makes dangerous answers/context mistakes impossible under tested
conditions, then connects the data, then improves meaning. The same real source
slice follows every stage. Legal evidence and automatic extraction are assessed
separately.

| Audit risk | Required revision or early diagnostic |
|---|---|
| Wrong/stale baseline | Pin checkpoint and code imports; preserve original receipts; new run directory and question version |
| Proxy promoted to criterion | Wrong-answer regressions and reviewed answers determine acceptance; counts and abstention are descriptive |
| Hidden facts/defaults | Strict request/profile schemas; execute actual legal AST; explicit dates, units, identities and conventions |
| Unfair comparison | Same question/source/time/scenario; compare reviewed and automatic inputs as separate arms |
| Environment mismatch | Pin worktree source for development and test a separate local installed package; bind parser/tool/rule versions |
| Commands answer the wrong question | Test phase-output mutations through installed CLI, not merely handler exit or receipt creation |
| Missing stop/repair conditions | Per-obligation repair record, diagnostic and bounded changed-input attempts; external evidence queue separated |
| Prototype mistaken for product | Reference proofs label assumptions; production regressions, real slice and independent cohort remain required |

## Default and assumption audit

| Choice / provenance | Reason | Failure mode | Earliest check | Status |
|---|---|---|---|---|
| BASF as first slice / existing retained 519-page bundle | Known difficult construction with concrete remaining branches | Overfit one German template | Parallel acceptance specifications for Deutsche/BES/G13–G17 and heldout families | Development baseline |
| Reviewed paragraph/choice structure / proposed AST | Isolates semantics from extraction | Manual interpretation quietly treated as automatic | Tag every supplied vs inferred relation; paired input arms | Explicit assumption |
| Partial Boolean completion / existing semantics.py | Missing facts need not become false | Missing variables, wrong formula or domain >12 | False-premise and complete truth-table regressions; symbolic extension separately reviewed | Reuse candidate |
| Question-specific reachability / formal dependency argument | Irrelevant documents should not block all questions | Missing edge hides a material exception | Inject direct/indirect references and review root exclusions | Hypothesis requiring real-source audit |
| Half-open time intervals / computational representation | Precise boundary semantics | Inclusive legal dates converted wrongly | Source-specific endpoint examples; explicit timezone/granularity | Representation choice |
| Exact rationals and per-holder floor / existing kernels and sourced profile | Avoid rounding ambiguity | Wrong legal grouping or cash convention | Two identities with same name; two accounts of one holder; boundary examples | Profile-specific, not universal |
| Docling or QuantLib / literature and official code | Candidate structure and comparator operations | Transferred model/library defaults | Same-page structure comparison; explicit schedule parameters | Optional candidates, not installed defaults |
| SHA-256 inputs / existing receipts | Bind immutable versions | Hidden reads, mutable snapshots, unbound code | Mutate each real input, tool/version and cached payload | Reviewed only under declared-dependency assumption |
| Independent reviewer identities / existing program | Separate implementation from legal evaluation | Fake independence or exposed cohort | Real assignment/exposure records and bound signoff | External evidence, cannot be fabricated |

## R0 — Contain false answers and wrong joins

Files: successor/law_facts.py, contracts.py, integration.py, financial_profiles.py,
evaluation.py, release.py, and corresponding focused tests.

1. Replace the unused premises list with a strict reviewed expression schema.
   Derive required fact names from the expression; reject ignored/unsupported
   fields. Evaluate through possible_decision. Handle alternative law bases
   according to an explicit relation, never by status consensus alone.
2. Require resolved source occurrences and subject/jurisdiction identifiers.
   Add explicit fact validity start/end and knowledge availability/history.
   Preserve actual exercise as a distinct unresolved question when absent.
3. Remove copied UBS context from the BASF scenario. Construct a sourced request
   for each question; reject incompatible instrument kind or missing mapping.
   Check obligation identity/version/premise sets.
4. Validate profile-specific input shapes before calculation. Unexpected internal
   failures remain errors; bad external shapes produce typed invalid input.
5. Bind reviewer roles and support scope to the evaluated cohort/report.
   The implementer cannot be the independent adjudicator.

Acceptance: P4-ignored-premise, P4-unresolved-source, P4-fact-valid-time,
P5-invalid-shape, P6-context-join and P0-P7-P8-independence-scope become production
regressions with the required outcomes. Do not relabel the old wrong output as a
new supported target. Removing a false YES is progress even if it exposes UNKNOWN.

## R1 — Make phase products the actual inputs

Files: successor/controller.py, jobs.py, service.py, contracts.py and
scripts/prospectus_delivery.py. Preserve the public phase entry point.

Refactor stage functions to consume versioned input bundles:
P1(source bundle), P2(P1 graph + selected terms/amendments),
P3(P2 selected contract + interpretation), P4(P1 authorities + P3 feature/subject
facts where relevant + actual observations), P5(P2 financial terms + applicable
P3 rules + scenario), P6(P3/P4/P5 + mapped bank context). Separate the all-in-one
convenience assessor from the phase consumer so it cannot silently rebuild and
discard supplied reviewed products.

Use immutable content-addressed products and complete input capabilities.
Record task/imported-rule/tool/config identities. Rehash output blobs; publish
completed receipts atomically, then update the state pointer. Read recovery
must tolerate an interrupted pointer update and reject incomplete attempts.
Treat model/parser proposals as recorded external inputs when determinism is
not established.

Add a repair record containing: obligation id, diagnostic, target phase,
input/code fingerprint, repair handler or required external record, acceptance
check, attempt number, and outcome. Refresh from actual failed obligations.
An implemented repair handler must execute a concrete change or ingest new
evidence; prose plus the same command is not a repair. Bound retries by unchanged
input identity; preserve changed-input repair opportunities. Do not invalidate
unrelated branches merely because a global source list changed.

Acceptance: replay identical run; change P2 selected text; change a P4 fact,
P5 scenario, bank request/store, imported rule and parser version; corrupt a
blob; interrupt publication. The installed P6 report must reflect/reject each
appropriate change. No phase may declare a consumed parent that it bypasses.

## R2 — Admit questions, review records and usable source structure

Files: jobs.py P0/P1, source_graph.py, new strict admission records and tests.

Version Q2 subquestions and declare the scope of every Q3 completeness result.
Reconcile 1,467 context records, 1,307 spans and 25 forms by source-edition,
occurrence, question and instrument; preserve many-to-many relationships rather
than adding unlike denominators. Read real assignments, labels, cohort membership
and exposure exclusions from files. Empty external inputs stay explicit; they
do not block offline implementation.

Preserve word boxes, paragraph/list/table membership, namespace and reading order.
Route scans through existing ResearchAssistant OCR with pinned settings and
geometry checks. Complete missing source dates and mark visibility consistently.
Represent reference occurrences and candidate targets by edition/clause scope.
Review body/margin instruction attachment on BASF, multicolumn/bilingual Deutsche
pages and scanned BES17. A Docling comparison is optional after the baseline
structure is checked; it must not replace those checks.

Acceptance: duplicate occurrences, line wrapping, cross-document context collision,
multi-span quotes, hidden sources, excluded headers, indirect references, ambiguous
renumbering and missing source metadata. Keep source page images with annotations
and exact identities so a reviewer can reconstruct each case.

## R3 — Construct one real contract completely, then extend the representation

Files: basf.py, contract_assembly.py, source/reference types, admitted construction
records. Implement Text/Sequence/Choice/Field/Reference/Override with correlated
constraints, source maps and precedence reasons.

For BASF, review the unmatched bracket at raw offset 14862 against the page image;
attach marginal instructions; resolve each of the 163 current alternatives or
show why it cannot affect a declared question. Resolve the incorporated-report
195–209 versus 209–290 range discrepancy using primary evidence. Complete fields
and bilingual precedence. Record source-backed selections rather than blanket
deletion. Then construct Deutsche/BES and G13–G17 agreement/amendment sets with
the same representation or document a necessary extension.

Acceptance: every included/excluded occurrence has a justified role; output
characters/fields/amendments have provenance; no unresolved dependency can change
a supported answer. The checked AST and its rendered contract are both reviewed.
The claim is question-specific completeness unless the whole contract has been
independently checked.

## R4 — Execute the intended question over typed clauses

Files: clause_graph.py, semantics.py only where an explicitly reviewed extension
is required, typed interpretation schema and real-clause tests.

Replace first-match quote coverage with occurrence intervals. Represent actor,
election, affected interest, effect, polarity, executable triggers/exceptions,
definitions and precedence. Do not fill actor/modality from convenience defaults
when evidence is absent. Define contractual feature existence separately from
current event truth; distinguish compulsory/possible-common/common-only conversion.
Execute negatives and resolved conditions. Missing scope and interpretations
remain unknown; inconsistent premises remain conflict.

Acceptance: original occurrence/multispan/negative/condition/Q2/Q3 findings plus
negation scope, distant exceptions, holder-only elections, contingent issuer
choices, disjunction/conjunction and conflicting authority. Compare three
explicit arms: reviewed construction + reviewed interpretation; reviewed
construction + automatic interpretation; automatic construction + interpretation.
This isolates the first faulty transition.

## R5 — Complete sourced law and financial cases

P4 must produce case-specific executable law/fact bundles consumed by P6.
For retained Annex2B/HETA/Dana/Lloyds/Ukraine/Popular/Snoras/Italian65/67 cases,
record primary authority versions, applicable forum/entity/instrument, actual
event/procedure/suspension evidence and effective/knowledge dates. Do not infer
facts from statutory power alone. Missing authoritative sources yield a concrete
external-input obligation.

P5 must run each claimed financial profile, including completed Deutsche/BBVA/SEB
paths and explicitly admitted UBS/BASF scenarios where supported. Specify legal
aggregation identity, dimensions/currency, threshold comparisons, price windows,
FX, rounding, dates/calendars, accrual, anti-dilution, fractions and settlement
events as required by each contract. Independently work calculations from the
source. Use QuantLib only for reviewed explicit operations, with its version and
parameters recorded.

Acceptance: exact boundary/property tests plus independent numerical examples
and dated legal counterfactuals. Distinguish a supported subcalculation, complete
conditional settlement and a proven actual event. A missing real event need
not block a clearly labelled hypothetical calculation.

## R6 — Installed end-to-end acceptance and independent evidence

Run the installed CLI over accepted phase products. Verify content/context
bindings, question-specific unknowns, original bank obligation identities,
source/rule traces and no unsupported clearance. Pair the repaired and pinned
baseline engines on the same finite source/question set. Development cases are
not an unexposed cohort.

Then independent readers/adjudicator assess predeclared reserved issuer/template/
language/version groups. Signoffs bind cohort, report, method and supported
scope. Reconcile findings into repair obligations, refresh descendants and
rerun only what changed. A new supported error vetoes promotion and triggers
repair; it does not erase successful unrelated engineering evidence.

## Commands and preserved results

Available now, CPU-only with worktree interpreter/source enforced by the scripts:

```text
python3 -m scripts.audit_prospectus_phase_roots
python3 -m scripts.check_prospectus_phase_reference
```

The first reproduces the pinned **current defects** and is expected to need a
separate forward regression mode after production repair; do not overwrite its
historical observations with changed expected behavior. The second checks
isolated specifications and is not a delivery command.

After implementing and testing each handler above, use the existing exact
command form, for example:

```text
python3 -m scripts.prospectus_delivery phase --phase P4
python3 -m scripts.prospectus_delivery phase --phase P6
```

Do not run those now and call reuse a repair. The production repair interface,
forward regressions and new run directory must be implemented before accepting
new receipts. Local source/docs/test edits and offline checks are already within
the authorized scope. Group any genuine new network/model/resource permissions
only after the concrete command and evidence need are known.

Every meaningful run records commit, code/data hashes, actual command, interpreter,
tool versions, CPU/GPU setting, elapsed time, output paths, plan and result.
Refresh the reset memo with what changed, the first remaining failed interface
and the next executable repair. External reviews remain named pending inputs,
never fabricated completed phases.
