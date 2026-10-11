# Prospectus integration closure program

Status: executing after skeptical review; engineering and external acceptance remain separate.
Started 8 October 2026; plan reviewed and execution continued 9 October 2026
(Hong Kong). Mandatory capabilities remain partial; the program is not complete.
Source baseline:
`03883b5f7d914a2678ac4f472e688c9fc1c60006`, branch
`feature/prospectus-evidence-master`, worktree
`/home/chakwong/python/legalmath/.worktrees/bond-gap-closure`.

The [code audit](../implementation/prospectus-package-integration-audit/REPORT.md)
identifies twenty findings. We know concrete repairs for the reproduced defects
and the missing software connections. We have not established that automatic
interpretation will meet a broad accuracy target, that every source dispute can
be settled, or that the unexecuted ACTUS/CDM integrations will be suitable.
This program makes those distinctions testable while completing a bounded,
reviewed source-to-answer service.

## Delivery target and limits

The engineering deliverable is an installed service that accepts a declared
document bundle, optional OCR/layout output and reviewed interpretations, then
produces answers and supported financial calculations with recoverable source,
selection and reasoning evidence. Every dependency must reach an actual
consumer. A changed source, scope decision, annotation, term or runtime must
invalidate the results that depend on it when a current assessment is requested.
An explicitly labelled historical replay remains a separate supported operation.

There are three separately reported completion decisions:

1. **Engineering closure:** the reproduced defects are repaired, required
   consumers exist, and the declared installed workflow passes its positive,
   adversarial, recovery and restoration checks.
2. **Finite assisted validation:** genuine independent readings and adjudication
   support the declared questions on a frozen, unexposed cohort. Missing people
   or legal sources leave this pending even after software completion.
3. **Automatic capability:** each extraction/meaning family is evaluated
   separately. Reviewed inputs can establish an assisted path; they cannot be
   credited to automatic parsing. Unsupported families remain explicit.

The initial mandatory financial scope is a reviewed fixed-rate bond calculation
through schedule, accrual and rounded payable amount under declared entitlement
premises. Existing AT1 write-down/conversion subcalculations must keep their
regressions and conditional labels. Full tax, FX, floating-rate, callable and
transaction-settlement support is not silently added to that scope. Any retained
open scope requirement appears in the final support register; narrowing a
requirement cannot be recorded as fixing it.

The BASF source program remains necessary. Its fifteen bracket fields and 537
unresolved intervals are the audit baseline, not a target count to drive to zero.
Use the [source investigations](../implementation/prospectus-basf-reference-repair/NEXT-PROGRAM.md)
for references, margin scope, calculation-agent authority and incorporation.
If BASF remains incomplete, it stays partial. A separately frozen complete
fixed-rate development case may exercise the service, but cannot close the BASF
obligation. This program replaces the earlier source-only ordering, preserving
all its unresolved source questions and historical evidence.

## Intent and evidence contract

| Item | Predeclared contract |
|---|---|
| Main question | Can each required package output be validated and consumed without losing source identity, selected-contract applicability or the supplied meaning? |
| Mechanism under test | Shared occurrence/applicability validation, explicit adapters and actual service consumers, evaluated through the installed command. |
| Baselines | Audited source commit and retained probe results; existing finite evaluator on its supported domain; retained Poppler/OCR extraction; independent financial enumerations. The 153-test receipt is a historical regression comparator only. |
| Engineering pass criterion | Every mandatory gap has a repaired boundary, a positive control, an adversarial check and evidence of its downstream consumer. Exact expected answers are required on complete engineered fixtures; unsupported fixtures must give the specified unresolved reason. |
| Promotion veto | Any wrong supported answer, missing critical exception or source occurrence, admitted inapplicable premise, unresolved provenance, unexplained comparator discrepancy, or missing required independent review blocks the affected capability. |
| Continuation veto | Corrupt comparator/input, unexplained baseline drift, invalid environment, missing required diagnostics, unintended historical-output mutation, or exhausted recorded resources stops the affected run. |
| Repair trigger | A valid candidate fails its criterion: diagnose the first failing boundary, change code/configuration or acquire the missing record, and make a new bounded attempt. A failed candidate does not cancel a later phase intended to repair it. |
| Explanatory only | Test counts, HTTP success, text-map coverage, elapsed time, average edit distance, source-count reduction, solver speed and receipt currentness. |
| Not established by a pass | General legal correctness, package superiority, complete automatic interpretation, actual event occurrence, population accuracy, or permission to execute a transaction. |
| Result location | New immutable attempts under `docs/implementation/prospectus-integration-closure/`; per-phase results, manifests, residuals and refreshed next plan. |

## Implementation contracts

Extend the existing modules and validators. New small modules are justified for
shared occurrence mapping, applicability, annotation admission and contract
terms; do not replace the whole service or import a general legal framework.

| Record | Required content and consumer |
|---|---|
| Source occurrence | Document/edition hash, extraction hash, unit, coordinate system, exact half-open interval and quotation. Page coverage and unit identity validated before any lookup. Consumed by all later admissions and evaluation labels. |
| Transformation map | Raw, corrected/display, CAS and assembled intervals with explicit copy/insert/delete/replace operations and parent identities. Multiple copies require distinct occurrence-use identities. Ambiguous and non-invertible regions remain explicit. |
| Applicability decision | Instrument, question, purpose, valid/knowledge times, source role, selected construction and authority/review evidence. Distinguish operative body, selection authority, governing law and observed fact; a caller-provided role name alone is insufficient. |
| Reviewed meaning | Bound occurrence uses, actors, modality, effect, condition, exception, reference/priority authority, language and question scope; reviewer/assignment and interpretation version. Consumed by P3 and, where appropriate, dated-law evaluation. |
| Solver result | Engine/version, admitted premises, query, status, unknown reason, named conflicts, witnesses and resource bounds. Preserved in products and reports. |
| Contract terms | Typed rate, principal, currency, dates, convention/calendar, entitlement and rounding, each linked to selected meanings and any permitted external facts. Consumed by finance. |
| Evaluation record | Source-bound independent readings, adjudication, case family, question, frozen method and actual prediction receipt. Consumed by scoring and acceptance. |

Construction has a bootstrap boundary: selecting a contract cannot require the
hash of the contract it has not yet built. Validate selection/override premises
against raw sources, declared purpose/times and the construction specification;
then bind the resulting decisions to P2 before admitting P3 premises. Do not let
P3 determine its own construction applicability circularly.

Version each changed request/product schema. Existing v2 products retain frozen
replay under their recorded assurance limits; a current assessment cannot silently
upgrade a legacy product missing new evidence. Reject it with a migration or
reassessment instruction. Update producers, consumers, installed package tests
and reader documentation together. A hash is an integrity check, not proof that
a reviewer or legal interpretation is correct.

## Ordered work packages

| Phase | Dependencies | Main deliverable | Audit findings |
|---|---|---|---|
| R0 Baseline and execution control | None | New namespace, failure fixtures, explicit outcomes and reviewed phase records | G20; supports all |
| R1 Source and evidence admission | R0 | Shared occurrence and applicability checks, AST mapping, label source binding | G01–G04 |
| R2 Solver contract | R1 | Consistent engine policy, preserved explanations, finite/Z3 parity | G06–G07 |
| R3 Extraction and layout consumers | R1 | New-scan intake, corrected maps, layout and governing-edge consumption | G08–G10, G16 |
| R4 Reviewed meaning and references | R2, R3 | Annotation-to-service translation, BASF meaning admission, bounded priorities | G05, G11–G13 |
| R5 Contract-to-finance connection | R4 | Selected terms consumed by local finance and compared with QuantLib | G14–G15 |
| R6 Restoration and complete workflow | Final gate after R5; environment work starts after R0 | Relocatable runtimes, installed execution, controller mutation/recovery | G16–G18, G20 |
| R7 Independent evaluation chain | R4 for workflow development; R6 for final candidate | Authenticated readings, adjudication, executed predictions, family separation | G04, G19 |
| R8 Attribution and final disposition | Results from R1–R7 | Per-package root-cause verdict, residual program and support register | All; ACTUS/CDM prerequisites |

Independent work packages may be interleaved; this plan does not require
delegating to agents. Source investigation and reader-workflow preparation can
proceed alongside engineering. Missing readers block acceptance, not local fixes.
Dependencies require valid interfaces and inputs, not success of every automatic
candidate. If Docling proposals fail but reviewed structure is valid, R4 proceeds
on that reviewed path while the automatic gap stays open. Restoration/controller
work can continue with fixtures when an actual-instrument premise is missing;
that fixture does not satisfy R5's real-instrument or R6's complete-delivery gate.

### R0 — Preserve the baseline and make completion meaningful

1. Verify the audit's source bindings before implementation. Preserve the audit
   probes and historical attempts. Port their fixtures into regression tests;
   record their observed pre-fix behavior without overwriting the audit outputs.
2. Add a new `closure` namespace to the existing controller/dispatcher rather
   than rerunning old repair/adoption programs. Register only implemented jobs.
   Start with R0 and focused checks; add later jobs as their code becomes ready.
3. Record execution outcome, artifact validity/currentness, primary criterion,
   consumer verification, and external acceptance separately. Missing fields
   mean unverified, not success. Dependencies state whether they require a valid
   diagnostic artifact or a passed capability. A failed trial can feed a repair.
4. Replace keyword-based classification of new obligations with explicit gap
   IDs, code/source owner, dependency, closing test, next action and external
   requirement. `status` must be read-only; `refresh` writes only the new program.

Pass: a deliberately failed but valid trial remains reusable as evidence, is
never called integrated, and produces a concrete repair action. An interrupted
attempt and a corrupted receipt are never reused as complete. R0 records the
remaining jobs as unimplemented; the runner cannot generate missing code itself.

### R1 — Repair shared source, applicability and evaluation boundaries

Work in `source_graph.py`, `anchors.py`, `construction_ast.py`, `service.py`,
`predicates.py`, `evaluation.py` and small shared validators as needed.

* Require exact ordered OCR page coverage `1..N` for the full-document profile,
  unique units and valid source ranges. A future subset profile must declare its
  page set explicitly; do not infer it from list length. Reject non-integer page
  identities, missing/duplicate pages and inconsistent coverage.
* Admit each semantic solver premise for a declared purpose and selected
  occurrence. Reject excluded, superseded and unrelated body premises. Permit
  legitimate external selection authorities/law/facts through their typed path,
  with source and applicability evidence. Keep legal review explicit.
* Resolve references using interval/use mappings between raw and assembled
  occurrences. Test one-to-many copies, split targets, replacements, deleted
  references and duplicate text. Never silently choose the first matching copy
  or assume that sharing a raw unit makes all its intervals operative.
* Validate label evidence against loaded source graphs using the shared binder;
  reject bad offsets, invented quotations and foreign editions. Add prediction
  receipts binding outputs to inputs, method and actual execution. Historical
  free-form scores stay legacy evidence rather than becoming accepted records.

Pass: all G01–G04 counterexamples are rejected or remain explicitly unresolved;
valid controls work. In particular the excluded-alternative constraint cannot
produce a supported YES, while a correctly admitted external authority can
still be used. An AST-selected definition resolves through the installed service.
Fabricated label evidence never contributes to an accepted score.

### R2 — Route reasoning consistently and retain its evidence

Introduce a common bounded engine interface for clause activation, construction
constraints, law premises and multiple-law aggregation. Preserve finite as the
legacy default; explicitly requested Z3 reaches each supported Boolean phase.
Do not increase capability by silently dropping constraints or coercing unknowns.
Out-of-domain, unavailable solver and timeout are typed unresolved outcomes.

Compare finite and Z3 on the same admitted observations and expressions within
the finite domain. For constraints, use an independent test-only enumerator over
admissible worlds; the existing unconstrained `decide` is not that oracle. Include
explicit conflicts, inconsistent constraints, tautologies, both witnesses,
empty admissible worlds, thirteen-fact inputs and forced resource exhaustion.
Enumeration over at most twelve facts is exhaustive for each selected formula,
not a proof over every possible formula.

Preserve named premise IDs, expression, engine/version, unsat core, witnesses,
unknown reason and limits from the solver through P3/P4 to CLI JSON. Construction
must reject inconsistent selections and retain unresolved selections. Unsat cores
are explanations of encoded premises, not guaranteed minimal legal explanations.

Pass: exact decision parity on the declared small-domain corpus, successful
thirteen-fact cases in all advertised phases, no vacuous YES from inconsistency,
and diagnostic preservation through installed `assess` and `consume`.

### R3 — Make OCR and layout feed the service

Add optional versioned extraction/layout admissions to request validation and P1.
Retain raw source quotation authority. Build configurable CPU OCR profiles around
the existing PyMuPDF/Tesseract environment before evaluating additional OCR
packages. Use explicit languages, DPI, page limits and model identities. An empty
Poppler result is a scan candidate, not proof that a page contains readable text;
support blank/unsupported dispositions and preserve the page image evidence.

Implement corrected-text mapping with insertions, deletions and uncertain regions.
OCR geometry belongs to the original words; changed text receives a reviewed
transformation map and image/source references, not borrowed word boxes.

Admit Docling's mapped layout as a separate structure layer. Start with explicit
reviewed governing edges and a P2/P3 consumer that uses them. A raw model region
does not itself establish legal scope. Demonstrate the BASF shared definition
survives all options it governs, and the supplement's competing incorporation
readings remain unresolved until adjudicated.

After that connection passes, expand the old two-page worker to the frozen page
inventory: tables, columns, multilingual terms, margin/footnote scope and scans.
Preserve per-page completion and continuation/error records. Compare identical
pages and admitted scope with baseline structure, Docling-proposed structure,
and independently reviewed structure. If a legal relation is not represented
by Docling, implement/review it in our adapter; do not treat that as a parser bug.

Pass: a new scan and genuinely blank page reach the installed service with correct
dispositions; a reviewed non-English profile is exercised; all designated critical
occurrences survive; a governing edge changes the intended selected meaning or
answer. Missing OCR resources/Poppler produce a typed preflight/error result.
Aggregate text coverage cannot compensate for a lost governing relation.

### R4 — Connect reviewed annotations, construction and meaning

Support standalone XMI with an explicit type-system argument and ZIP exports
containing their type system; keep legacy valid command forms. Validate missing
or mismatched types before decoding. Update the actual reader command and tests.

Map authored CAS spans through the exact extracted text into raw and assembled
occurrence uses. Exercise Unicode/UTF-16 boundaries, combining characters, line
endings, hyphenation, discontinuous spans, repeated clauses and cross-document
links. A packet label alone does not become a legal predicate: separately admit
typed actors, effects, conditions, exceptions and scope with review evidence.

Add a reviewed BASF disposition/meaning input. Promote only the reviewed source
uses and question scope; leave unrelated unresolved material visible. Determine
question completeness from its dependencies, never from an operator's blanket
`complete` flag. Preserve the profile's full-contract partial status until all
required source obligations actually pass.

Extend reference admission to named, relative, external and amendment references
using edition, occurrence, language and authority. Discovery may propose targets;
admission checks them. Implement an explicit bounded acyclic priority/exception
semantics with independently hand-enumerated examples. Contradictory authorities,
unsupported cycles or ambiguous targets remain UNKNOWN/CONFLICT. Test distant
exceptions and amendments, including the known BASF reference examples in the
retained source plan. Governing-law admission must not be confused with body-text
selection; changing jurisdiction or valid/knowledge dates must affect only the
relevant legal result under the declared premises.

Pass: an actual authored exception reaches installed P3 and changes its expected
answer; redirecting its target or changing its source invalidates it. A reviewed
German clause can be evaluated without claiming automatic German interpretation.
Removing required evidence prevents a supported answer. Both reviewed and
automatic-input arms use the same interpreter and declared facts.

### R5 — Derive financial premises from selected meanings

Add a reviewed typed contract-terms admission bound to P2/P3 and question scope.
Separate contractual terms from market observations, holder/event facts and
hypothetical scenarios. Deterministic parsing of an explicit amount/rate is
different from reviewing which clause controls it; record both steps. Finance
must consume those admitted terms rather than merely checking P2/P3 parent hashes.

First deliver the fixed-rate scope: schedule dates, reference periods/stubs,
day count, payment calendar/adjustment, entitlement, holder aggregation and
rounding. Keep exact decimal/rational monetary calculations locally. Compare
dates, fractions and payments with QuantLib supplied the same admitted terms,
using independently derived schedules/fractions as a third comparator. Require
exact dates/rational identities where applicable and exact final minor-unit
payments; set floating comparison tolerances per operation before inspecting
results, based on numerical error analysis rather than desired agreement.

Exercise leap years, short/long stubs, month-end, holidays, transfer/record dates,
per-holder versus per-account aggregation, and event ordering. Preserve the
existing AT1 checks. Any term change in the operative contract must invalidate
the old admitted terms and calculation. A wrong but numerically plausible rate
must fail its term binding even if both calculators agree on that rate.

Pass: at least one complete real-instrument development calculation traverses
selected meanings to terms to the actual service output, with all mandatory
conventions reviewed and the independent comparator checks passing. Synthetic
cases can close arithmetic tests, but cannot replace this real-instrument check.
Missing actual entitlement/event evidence keeps the result conditional.

### R6 — Restore runtimes and test the complete installed workflow

Begin capability preflight and configurable paths after R0 so R3/R4 are not
dependent on temporary resources. Finish this phase only after the consumers
exist. Work in setup scripts, `read_context.py`, controller bindings, CLI error
handling and installed-workflow tests.

Provide separate application, OCR, layout/finance and authoring profiles. Record
Python/Java/system-library versions, transitive Python locks with hashes, model
revisions, language files and browser identities. Reuse the known package
versions as baselines; do not combine incompatible environments or modify the
shared ResearchAssistant/training environment. Default durable resource paths
to configurable project-local directories. An existing download receipt with
missing runtime files must produce a restore action; restoration creates a new
receipt and verifies bytes instead of overwriting old evidence.

Build and install a non-editable wheel in a fresh interpreter without system
site packages or checkout imports. Run from a separate working directory with
only copied source/admission fixtures and installed resources. Build P1 through
P5 there and execute `assess`, not merely `consume` on checkout-built products.
Run the same workflow after relocation. Check missing Poppler, model, language
file, Java/browser and annotation sidecar separately; optional unavailable
capabilities must be distinguished from an unusable core install.

Make `consume` distinguish frozen replay from current assessment. Frozen replay
must state the historical method and validation limits. Current assessment
revalidates sources, derivatives, admissions and runtime identities, rebuilding
or refusing stale products. Missing external resources can leave historical
replay possible without making a current assessment possible.

For subprocesses, enumerate source/model/configuration inputs and bind the
runtime distribution, environment choices and supported system dependencies.
Use a dedicated working directory and an explicit child environment. These
steps improve reproducibility but do not establish confinement. For a worker
whose full read set is unverified, prohibit reuse under a claim of complete
currentness and rerun it; mark its dependency assurance partial. To close G18's
stronger reuse requirement, either observe and bind all relevant reads for the
supported invocation, or run with tested filesystem/network restrictions.
Exercise the audit's undeclared-read counterexample through the real worker:
the read must be rejected, tracked so its change invalidates reuse, or prevent
currentness certification. No empty cache or directory convention counts as an
OS restriction. Missing tracing/confinement support remains an explicit gap.

Extend Hypothesis sequences through the real controller using isolated roots:
change source, extraction, annotation, meaning, calendar, model and missing-file
state; interrupt before/after receipt publication; recover; retry; corrupt an
output; and contend for the execution lock. Compare incremental results with a
clean recomputation of the same supported inputs. Start with conservative
invalidation; narrow it only when the dependency evidence justifies doing so.

Pass: the required profiles restore and relocate; installed service outputs
match the reviewed development expectations; missing resources fail clearly;
stale inputs cannot masquerade as current results; crash recovery preserves
sealed attempts; and no unexplained incremental/recomputed difference remains.
A fresh virtual environment on this host proves interpreter isolation and
relocation, not a new operating-system installation. An OS-image test is needed
before claiming system portability beyond the recorded host profile.

### R7 — Complete the review-to-score chain

Develop the workflow against synthetic assignments first. Genuine evaluation
requires assigned qualified people: two independent first readers and a distinct
adjudicator, with implementers excluded. The authenticated server/project export
must bind account, assignment, source edition, submission and edit history;
operator-provided identity strings and hashes alone do not establish who read.
Persist first readings before adjudication and retain the disagreements.
Disable predictions/recommendations and cross-reader access until first readings
are sealed. Test this with access-denial and premature-exposure controls.

Freeze the candidate method, question scope and cohort before scoring. Enforce
issuer/template/amendment-family grouping through a reviewed registry; related
documents and duplicate editions cannot cross into heldout evaluation merely
by changing IDs. An unresolved family assignment blocks heldout admission.
All documents and labels already used in this repair are development evidence.
Contacting or inviting readers is a separate external action and is not done by
the local engineering runner.

Connect preserved authored exports to the R1 source binder and R4 meanings, then
to adjudicated labels. Predictions must come from the installed service on the
frozen inputs, with its execution receipt. Test stale methods, wrong subjects,
foreign editions, altered exports, forged/unassigned labels, duplicate family
IDs and predictions that were typed by a caller instead of executed.

Use the evaluator appropriate to the declared question: Boolean/adjudicated
outcomes for Q1/Q2 and applicable Q4 cases; completeness/disposition checks for
Q3; exact numerical and prerequisite checks for Q5; existing bank obligations
for Q6. Do not force CONDITIONAL numerical answers into a Boolean scoring schema.
Keep the bank adapter's transaction restriction and existing regressions.

For finite assisted acceptance, retain the existing no-wrong-supported-answer
rule and require useful correct positive and negative decisions wherever the
declared Boolean scope promises both. Add explicit UNKNOWN/CONFLICT and absent-
premise controls. Complete engineered fixtures require their exact expected
answer; abstaining on every case cannot pass. Report coverage and exclusions with
fixed denominators. Human signoffs must bind the exact scope, method, cohort and
result. Missing readers or source decisions give an honest pending result while
the engineering workflow can be complete.

This finite validation is not a population-accuracy study. Any claim about
generalization or a ranking requires a separately frozen sampling unit (normally
independent document family), risk threshold, sample-size rationale and paired
uncertainty analysis before results are exposed. Small or correlated samples
remain descriptive; no zero-error percentage is presented as proof of zero risk.

### R8 — Attribute failures and close only demonstrated capabilities

Use the same sources, question, admitted facts and evaluator for the following
diagnostic comparisons. Label assisted steps explicitly.

| Comparison | What it can locate |
|---|---|
| Independently specified typed meanings versus the expected answer | Local interpretation/lowering/reasoning error, or an inconsistent expected answer needing review |
| Reviewed evidence groups through our translator versus those typed meanings | Annotation-to-meaning or occurrence-mapping error |
| Automatic extraction/group proposals versus reviewed groups | Extraction, layout, retrieval or reference-discovery failure |
| Direct pinned package invocation versus our wrapper on the same input | Configuration, adapter or package behavior |
| Local exact finance, independent enumeration and QuantLib with identical terms | Numeric/convention implementation differences; none proves the chosen contract terms |

The first failing comparison nominates a cause; inspect the relevant source and
counterexample before making the verdict. A reviewed comparator can itself be
wrong. Preserve a minimal input, exact environment and expected/actual output.

Each package receives one or more supported dispositions: integrated for the
named role; local defect remaining; usage/configuration repaired; unsupported
capability in the pinned release; missing source/reviewer/runtime prerequisite;
or untested. A fundamental limitation requires a supported direct configuration,
inspected official behavior and evidence that the required capability cannot be
provided by an acceptable configuration or faithful adapter. A failed local
wrapper, a missing model, a 404 or one unsuccessful trial cannot establish it.

ACTUS and CDM are conditional side studies, not dependencies of R1–R7. Follow the
[retained prerequisites and smallest trials](../implementation/prospectus-integration-repair/feasibility-006/deferred-tool-decisions.json).
For ACTUS obtain the usable pinned core and version-specific terms, inspect PAM
schedule/payoff/state code and run the independently enumerated plain PAM case.
For CDM first name the receiving version/profile and required functions, then
test the official bond fixture through reference resolution, condition validation
and semantic round trip. Required Python native stubs need implementations or
a supported Java route. If the prerequisites remain missing, record untested and
the specific next action; do not manufacture rejection or installation success.

Alternatives such as MinerU, olmOCR or another annotation platform are nominated
only by a remaining measured capability failure. Replacing packages is not a
substitute for R1–R5. ResearchAssistant remains a research/OCR resource;
RuleIR/Catala/Lean and standard exchange formats retain their separately declared
roles and do not supply proof of dynamic prospectus translation.

The final report contains the support register, every G01–G20 disposition,
per-package attribution, source/reviewer prerequisites, engineering/numerical/
interpretation decisions and strongest alternative explanations. Update the
reset memo, next plan and the existing prospectus LaTeX discussion to match the
actual result; build and inspect changed document pages. Report partial closure
when any mandatory check is missing. Historical trial completion stays dated.

## Required development cases and discriminating checks

R0 freezes exact source IDs, hashes, page ranges, questions and expected results
in `corpus.json` before package comparisons. Start from retained sources and the
audit fixtures; select a genuinely new scan for the intake check. Do not silently
exchange a difficult case for one that passes. The rows below specify mandatory
families, not an invented statistically sufficient sample size.

| Family / starting evidence | Required positive control and adverse check |
|---|---|
| Audit source/constraint/AST/evaluation probes | Valid occurrence, applicable constraint, resolvable target and real label; reject each recorded mutation and ambiguous partial-unit alternatives |
| BASF p112 shared reference-period definition | Reviewed governing edge keeps every intended use; omitted/overextended edge and source change fail |
| BASF supplement p12 incorporation and unresolved agency designation | Preserve both documented readings; missing authoritative resolution cannot be replaced by a guessed range/address |
| BASF selected reference cases and repeated labels | Correct target occurrence resolves; same label in another use/edition, removed target or unsupported cycle does not |
| Deutsche bilingual terms and retained BES OCR | Correct reviewed language/source binding; wrong governing language/model, changed extraction and missing page fail |
| New scan, blank page and table/column case | Actual installed intake preserves complete page inventory and designated critical text; truncation, hallucinated blank text and lost margin fail |
| INCEpTION edited/discontinuous/cross-document group | Persisted authored exception affects the actual service answer; stale offsets/types, moved endpoints and unauthorized reading fail |
| Boolean engine and dated-law cases | Finite/Z3 agreement, larger Z3 case and dated jurisdiction control; contradiction, missing fact, expired authority and timeout remain typed |
| Fixed-rate coupon and retained BBVA/SEB/Deutsche controls | Independent dates/fractions and exact rounded amount; wrong operative term, omitted calendar, entitlement or event order cannot pass |
| Controller/restoration/installed workflow | Clean versus incremental equality and relocation; corrupt receipt, resource disappearance, undeclared read and interrupted publication are detected |

For complete cases, write exact expected answers before examining candidate
output. For unsupported cases, write the required reason and affected question.
Do not use broad sets such as `{YES, UNKNOWN}` as the closing criterion where a
specific expected decision is known. Old permissive safety screens may remain
as regressions alongside these stronger checks.

## Defaults, assumptions and uncertainty

| Choice / provenance | Status and justification | Failure mode | Earliest discriminating check |
|---|---|---|---|
| Audited HEAD and 76-file evidence index | Verified baseline; binds the diagnosed implementation | New work or stale receipts mistaken for comparator | Recheck identities before R0 and record deliberate changes thereafter |
| Existing source units plus PDF images | Comparator, not infallible truth | Extraction error becomes a false gold label | Inspect disputed page/interval before fixing expected meaning |
| Docling 2.60.1, retained model, existing OCR profile | Controlled baselines; isolate adapter repairs first | Inappropriate language/model or two-page limit hides capability | Profile preflight and one named failure page before expansion |
| Shared validators with explicit reviewed meanings | Design hypothesis; repairs repeated boundary inconsistencies | New layer merely trusts a role/meaning field or creates circular authority | Excluded-premise, source-mutation and construction-bootstrap controls |
| Finite legacy default, explicit Z3 | Compatibility choice; no untested global default switch | Constraints ignored or only one phase routed | Same-input decision parity and thirteen-fact phase checks |
| Acyclic explicit priorities | Initial supported subset | Cycles or disputed precedence silently flattened | Cycle/conflicting-authority controls; record broader semantics as unsupported |
| Fixed-rate first, current AT1 slices preserved | Staged delivery hypothesis, not full-instrument closure | Easy example conceals remaining finance requirements | Terms-to-service test and final support register listing every excluded feature |
| Separate CPU environments and durable caches | Engineering choice; preserve current working installations | Old files/checkout imports conceal missing dependencies | Empty-profile restoration, relocation and installed import-path capture |
| Two readers and distinct adjudicator | Inherited finite-review protocol, not proof of reliability | Shared answers, account spoofing or template leakage | Assignment/access/first-reading records and reviewed family registry |
| Zero wrong supported answers on fixed finite cases | Engineering/finite acceptance screen | All-UNKNOWN candidate or tiny sample presented as accuracy proof | Required positive/negative utility and fixed denominators; population claims deferred |
| Bounded attempts and CPU runs | Resource controls, not scientific rejection thresholds | Timeout mistaken for package incapability | Capture progress/resource cause and revise the affected micro-plan |

No package/default ranking follows from a small set of descriptive measurements.
If a later comparison is stochastic, its result note must separately record hard
vetoes, viable candidates, descriptive differences, statistically supported
ranking (usually none at the first stage), default readiness and next evidence.
Record seeds and paired uncertainty only under a predeclared design; no extra
seeds or thresholds are selected after seeing favorable outcomes.

## Execution, refresh and resource discipline

R0 implements the following command forms in the existing dispatcher. R0–R8
now have focused phase handlers. Their checks and partial results are recorded
separately from completion of every capability listed in this plan:

```text
python3 -m scripts.prospectus_delivery --program closure preflight
python3 -m scripts.prospectus_delivery --program closure status
python3 -m scripts.prospectus_delivery --program closure phase --phase R0
python3 -m scripts.prospectus_delivery --program closure refresh
```

Subsequent phases use the same literal `phase --phase R1` through `R8` form.
The runner selects the application interpreter and sets `CUDA_VISIBLE_DEVICES=-1`
before scientific-package imports. Fixed phase handlers choose their tests,
input manifest and fresh output directory; they accept no arbitrary shell code,
URLs or commands. Status/preflight must not rewrite old program state.

After each coherent phase: verify its input/method identities, seal the attempt,
classify validity and the primary result separately, identify the earliest
failed boundary, update the gap ledger and write a refreshed next plan. That
plan names the exact implementation/source change, closing test and runnable
command, with a skeptical review. Repair code or obtain the missing input before
retrying; rerunning unchanged failed input is not a repair. Reuse a passing
current result without rerunning it unless a relevant change justifies doing so.

Use `docs/implementation/prospectus-integration-closure/phases/Rn/attempt-NNN/`
for new manifests and outputs; `RESULT.md`, `RESET.md`, `gap-status.json` and
`next-phase.json` describe the current program. Preserve source commit, diff hash
when applicable, command argv, interpreter/distribution/model identities, CPU
mode, data/version, seeds or deterministic designation, wall time, plan, result
paths and hashes. Serious numerical/comparative results include the decision
table: primary criterion, veto status, main uncertainty, next action and limits.
All phase manifests must be internally consistent after a crash/recovery.

Start with focused checks bounded to 600 seconds, three attempts per unchanged
method/input and 200 MB of new non-runtime evidence per phase, inherited from
the source continuation as convenience limits. Deterministic failures get a code
or input change before another attempt; three is a cap, not a retry target.
Existing live-authoring bounds (300-second startup, 900-second workflow and 2 GB
Java heap) remain starting limits. Before a resource restoration/download or a
larger run, record actual expected disk/network/time requirements in its phase
plan; do not pretend those fit the evidence cap. Resource exhaustion stops that
run and triggers a budget review, not a package-rejection verdict.

Local authorized edits need no extra permission. Reuse existing command rules
and literal argv forms. Where downloads, protected-path writes or trusted
loopback execution require platform escalation, prepare the bounded commands
and group related requests where possible. Any persistent approval should cover
only the relevant fixed action, not unrestricted Python/shell execution or every
closure action. Do not alter protected approval configuration as part of ordinary
file edits. The runner cannot eliminate sandbox requirements or authorize
external messages. No new approval is needed to write/review this plan.

Never run `scripts.verify_prospectus_repairs`, overwrite sealed historical
attempts or use historical masters to manufacture current receipts. Preserve
main's unrelated work and existing stashes.

## Skeptical review and pre-mortem — 9 October 2026

Self-review verdict: the proposed sequence passes planning review after the
corrections below. This is not independent legal review, an execution result or
a proof that all future package trials will succeed. Each phase must still bind
its exact fixtures, commands and environment before execution.

| Risk examined | Correction incorporated / evidence required |
|---|---|
| Wrong baseline or stale context | Keep audited HEAD/probes and recheck all source bindings; date historical receipts rather than counting them as current integration. |
| Success proxies | Require actual installed consumers and exact answer changes; separate mapping count, artifact validity, criterion pass and acceptance. |
| Circular applicability | Raw source/selection authority bootstraps construction; P3 binds to the completed P2. An external authority is not rejected merely because it is outside body text. |
| False reference closure | Resolve occurrence intervals and repeated uses, not raw-unit IDs; deletion, partial copying and one-to-many maps get adverse controls. |
| Weak or unfair solver baseline | Compare admitted inputs equally; add an independent constrained enumerator because current `decide` has no named-constraint semantics. |
| Package blamed for legal interpretation | Separate layout regions from reviewed governing edges, raw authored spans from admitted meanings, and model proposals from human review. |
| A consumer passes by abstaining | Complete fixtures require exact useful answers and polarity coverage; unsupported cases have explicit expected reasons. |
| Clean install is actually the old environment | Install a wheel into a fresh interpreter, hide checkout imports, construct products there, relocate and disclose OS-profile limits. |
| False native-read assurance | Dedicated directories alone do not confine; undeclared reads must be tracked/denied or prevent reuse certification. |
| Numerically correct wrong contract | Require selected-term binding and a term-change mutation; independent arithmetic and QuantLib share identical reviewed premises. |
| Family leakage or fake independence | Freeze reviewed family membership and actual assignments; preserve first readings and actual method predictions. |
| Missing external inputs stop all work | Block only dependent acceptance/capability; continue source repairs, software integration and synthetic workflow validation. |
| Scope narrowed to claim completion | BASF and excluded financial/semantic capabilities remain individually open in the support register. A substitute development instrument cannot close BASF. |
| Unbounded retries or future command fiction | Fixed phase budgets, implementation-aware handler registration and clearly marked planned interfaces; refresh after changed evidence. |

Pre-mortem: the program could appear successful because all adapters emit valid
JSON while the service ignores it, because hand-reviewed meanings are credited
to automation, because a copied comparator shares the same wrong premise, or
because the service abstains on every difficult case. Consumer interventions,
reviewed-versus-automatic arms, independent small oracles and exact-answer
controls address those risks. They still cannot prove general legal accuracy.

After each phase ask whether a failure invalidated inputs/harness/implementation
or merely rejected the candidate. Continue a planned repair unless a stated
continuation veto fired. Final red-team analysis must state the strongest
alternative explanation, the weakest evidence and what result would overturn
each claimed closure.

The first executable increment is R0 plus R1: preserve the counterexamples,
create honest controller outcomes and repair occurrence/applicability/reference/
evaluation admission. Do that before broader parser trials or new package
installation. R6 runtime preflight can start alongside this increment.
