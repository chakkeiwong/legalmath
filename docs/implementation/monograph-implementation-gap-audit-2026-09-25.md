# Monograph-to-product gap audit — 25 September 2026

## Finding and audit scope

LegalMath implements substantial parts of the monograph's interpretation method,
but it does not yet implement or validate the complete proposed bank product.
The central missing work is integration, source and factual-abstraction assurance,
representative evaluation, and operational acceptance. Installing every language
or reproducing every cited research system is a different objective and is not
the monograph's prescribed first implementation.

This audit inspected main at `9160ce72a17a255242299cc8ab33046f2501f42b`, the
separate Catala worktree, executable source, retained run records, and the
monograph's method and evaluation chapters. Main was clean before this report.
The Catala implementation is uncommitted work on `feature/catala-adapter`, based
on `66d15b2aee8f0c00076ab1dd24334b5f80dac058`. No files in that worktree were
changed. Visibility of its files and completed run records does not establish
whether its author is currently running another task.

The pre-audit check excluded three misleading baselines: the historical round-two
gap report, the book's round-four implementation status, and the Catala branch's
older main baseline. Each would incorrectly classify some later work as absent.
An implementation was counted only when executable code was located; execution
claims additionally required retained evidence. Passing tests was not treated as
legal correctness, and an implemented adaptation was not treated as reproduction
of a complete research system. No new model calls or legal conclusions were
needed for this audit. Test suites were not rerun.

The current PDFs contain **252 main-volume pages and 76 companion pages**, checked
with `pdfinfo`. [The monograph README](../monograph/README.md) explicitly says its
content integrates implementation through round four. Rounds five through ten
and Catala therefore need a new integration into the narrative and implementation
reference; existing historical observations must retain their dates.

## Catala work is visible and has real execution evidence

The other implementation is in
[`../../.worktrees/catala`](../../.worktrees/catala), with its own
[execution report](../../.worktrees/catala/docs/implementation/catala/execution-report.md),
[adapter](../../.worktrees/catala/src/legalmath/catala/adapter.py),
master program, authored Catala scopes, tests and Java package. Its final retained
run is `artifacts/catala/run-03` within that worktree.

The stored evidence records eight completed stages, 112 passing result-projection
comparisons and two detected mutations. **82 cases execute Catala calculations;
30 terminate in the shared input/scope/time boundary.** The latter are useful
boundary checks but are not independent compiler evidence. The report records
126 regression tests, including 19 Catala tests. Those tests were run on its own
baseline; they are not a combined regression of current main plus Catala.

For this audit, all 438 entries in the final run's SHA-256 manifest were checked
against retained files, with no mismatches. All 16 reviewed implementation inputs
still matched their recorded hashes. Reading `comparison.json` confirmed 112
passing rows and the 82/30 execution split. These are integrity and recorded-result
checks, not a fresh compiler/test execution.

The adapter is deliberately narrow: draft mode, four exact reviewed bundle
versions, a financial-condition scope and a synthetic exception scope. It is not
an arbitrary RuleIR-to-Catala translator. Full RuleIR trace correspondence,
transaction/release integration, broader operator support and reviewer benefit
remain unfinished. The recorded adoption decision is `NOT_PROMOTED`; no merge or
default replacement occurred. Integration must also reconcile its older baseline
with rounds eight through ten on current main.

One useful result is already concrete: the pinned Catala example coalesces two
applicable exceptions with the same consequence, while the selected RuleIR
fixture requires conflict. The authored Catala pilot adds explicit ambiguity
detection and tests a mutation that removes it. That evidence shows why adopting
a language does not automatically preserve the bank's chosen semantics.

## What is already implemented

These capabilities should be extended and integrated, not rebuilt on the mistaken
assumption that only generic prompts exist:

| Capability | Executable evidence | Important limit |
| --- | --- | --- |
| Competing readings, breadth-first and UCT investigation | `src/legalmath/interpretation/search/engine.py`, `models.py` | Finite search and heuristic rewards; no exhaustive set of English meanings |
| Source-only claim inventories, exact quotations and fidelity criticism | `assurance/semantics.py`, `sources.py`, `engine.py` | Source entailment labels remain model judgments; exact quotation is not entailment |
| Structured premises, strict/defeasible steps, undermining, rebuttal and undercutting | `assurance/arguments.py` | Bounded local profile; supplied premises/preferences are not automatically legally established |
| Grounded and stable argument extensions | `search/arguments.py` | Small bounded graphs; not full ASPIC+/Carneades semantics or every extension semantics discussed in the book |
| Official-example registry, analogy, distinction and countercase proposals | `assurance/examples.py`, `arguments.py` | Conditional case moves, not a general judicial reasoning system |
| Knownness-aware Z3 comparisons and Java witness execution | `src/legalmath/analysis/compare.py`, `search/formal.py` | Supported fragment and declared domain; solver proof certificates are not independently checked |
| Questions that distinguish candidate behavior | `assurance/questions.py`, `issue_search.py` | Counts separated candidate pairs; no calibrated legal information value |
| Explicit groups of duties and rival component combinations | `assurance/composition.py` | Grouping, exclusions and fact mappings must be supplied and checked; interactions can remain unmodeled |
| Source/context partitioning, cross-piece checks and durable bounded tasks | `assurance/decomposition.py`, `checkpoints.py`, `journal.py` | Declared limits and unresolved results remain material; partition success is not whole-law coverage |
| Retry accounting, semantic reconsideration and exact completed-run resume | `assurance/public_issue.py`, `declared_evaluation.py`, `recovery.py` | The latest public command has a narrow profile and one semantic cycle |
| Source/implementation monitoring, invalidation and a bounded scheduler | `assurance/monitor.py`, `operations.py` | Operator-supplied registry; no deployed institution-wide service or operating SLA |
| Java delivery, event replay, release records and synthetic host checks | `src/legalmath/java/`, `events/`, `review/` | Public/synthetic product boundary, not the bank's actual systems |

Paths beginning with `assurance/` and `search/` in this table are relative to
`src/legalmath/interpretation/`. The detailed distinctions in
[round three's method profile](interpretation-round3/method-profile.md) and
[round four's method boundaries](interpretation-round4/method-boundaries.md)
remain useful, but their dated remaining-work statements must be read alongside
the later code.

## Remaining product gaps, with implementation targets

### 1. One persistent investigation spanning all assurance stages

**Partial integration, highest engineering priority.** The broader
`interpretation-assurance` engine performs source acquisition, inventories,
tree search, source fidelity checks, structured criticism and bounded repair.
The newer `assurance-interpret-issue` command calls `MethodRun.execute`: initial
readers, a missing-reading challenger, finite behavioral comparison, source
criticism and at most one reconsideration followed by another audit.

The newer command does not invoke the broader engine's full authority-closure,
atomic-inventory, structured-argument and BFS/UCT sequence. Its `search` arm names
a bounded challenger workflow; that label is not evidence that it calls the UCT
tree engine. The older HTTP/search interface also does not expose the complete
new resumable issue workflow. Multiple useful entry points now exist without one
demonstrated, persistent product investigation joining all of them.

Build a common investigation record and dispatcher that reuses these modules,
links every concern to its source and affected candidates, checkpoints each
stage, and exposes configurable semantic-cycle and per-issue limits. Keep
transport retry distinct from substantive reconsideration. Invalidate downstream
results after upstream changes and surface the resulting questions in the API
and workbench.

Acceptance should include interrupted recovery at each stage, an omitted
definition requiring actual retrieval, an inventory disagreement, incompatible
supported formulas, a rejected response containing a lost alternative, a new
argument changing the next action, and a persistent disagreement reaching its
declared limit. Each case must demonstrate the actual next action and preserved
uncertainty, not merely a successful status field.

### 2. Search over factual abstractions, not only formulas

**Partial implementation, central interpretation risk.** `IssueSpec` accepts one
to four declared Boolean facts. It correctly retains unencodable readings and
vocabulary objections. However, the newest workflow requires those fact
definitions to remain unchanged and does not automatically open a separately
versioned investigation with new actors, relations or classifications.

For example, formulas over “income above reimbursement” and “profit objective”
cannot settle whether those are the legally decisive distinctions in the first
place. Every candidate can agree because the missing distinction is absent from
all inputs. The general reading format supports more scalar types, and derived
fact correspondences exist, but neither establishes the correctness of a supplied
classification.

Build explicit competing factual schemas, each with source passages, actor/object
bindings, time, units, judgment requirements and mappings to the other schemas.
Distinguishing examples must identify whether a difference comes from the reading,
the factual classification or the mapping. An unsupported mapping must remain
incomparable rather than becoming agreement. Acceptance needs a planted missing
actor or component distinction that formula-only search cannot discover but
abstraction revision can preserve and investigate.

### 3. Rendered-source coverage and richer authority acquisition

**Text and version controls implemented; important source coverage unfinished.**
There are two text extraction paths, visual-resource warnings, retained source
bytes, edition/provision catalogs and bounded reference retrieval. The PDF
inventory explicitly reports `ocr_performed: false`. There is no implemented OCR
and layout-to-text reconciliation proving that a table, scanned annex or image
footnote entered the interpretation packet. Two agreeing text extractors can miss
the same visual content.

Authority resolution checks exact catalog identities, retained bytes and declared
temporal/context information. It does not automatically establish every
incorporated definition or the legal priority of apparently conflicting sources.
The bilingual round-eight critic is retained evidence for one issue, not a general
cross-language alignment and discrepancy-resolution service.

Build page-linked visual and textual inventories, OCR where required, table and
footnote reconstruction, and source-region reconciliation. Add bounded discovery
of missing prose references and edition relationships, preserving uncertain
dates and precedence. Acceptance needs scanned and mixed-layout fixtures, changed
annexes, stale editions and distant definitions whose omission blocks completion.

### 4. Judicial precedent and deeper legal argumentation

**Selected methods implemented; the full literature systems are not.** Existing
case records and constructors support sourced factors, analogies, distinctions
and countercases. They are a real advance beyond a prompt asking for an analogy.
They do not implement a judicial corpus with reliable holding-versus-submission
classification, ratio extraction, subsequent treatment, binding/persuasive status
or automatic precedence resolution.

There is no complete HYPO claims lattice, CATO factor hierarchy, AGATHA theory
game, full ASPIC+ closure/rationality implementation or Carneades dialogue/proof-
standard engine. The local argument solver computes grounded and stable results;
it does not implement every extension semantics illustrated in the monograph.

The next useful increment is a small source-bound authority/case corpus with
reviewable factors, treatment relationships and competing authority arguments.
Test authentic-but-inapplicable citations, changed authority, a material
distinction and an unresolved priority cycle. Reproducing every historical system
is optional; implementing the specific missing legal distinctions is the product
requirement. Model-generated priorities must not silently acquire authority.

### 5. Diversity that is measured beyond fresh contexts

**Procedural separation implemented; common-error protection unvalidated.** The
live provider inspected is `CodexProvider`; its provenance explicitly says
`CONTEXT_ONLY_SAME_MODEL_CORRELATION_UNMEASURED`. Fresh source-only readers and
delayed exposure to peers reduce one form of anchoring, but no executed
cross-provider comparison establishes complementary error behavior.

Add role-specific provider routing and retain model/version, prompt, source and
dependency identities. Compare prompt-only diversity with genuinely different
available model/representation routes at declared budgets. Measure jointly missed
material conditions, not just agreement. Catala adds an executable comparison
route; it does not by itself diversify the interpretation of English. Access to
an additional provider may require separate user authorization before live use.

### 6. A basis for safely reducing review

**Evaluation infrastructure implemented; decision evidence absent.** Blind input
dispatch, annotation/freeze APIs, source-family accounting and four-arm studies
exist. Round nine completed 16 live method/case jobs across two source families
and their clean/altered versions. All retained a candidate matching an authored
reference on hidden finite scenarios; **all 16 abstained**. The 7,168 final
Java/Python evaluations matched. Those observations establish useful mechanics,
but there are zero accepted decisions from which to estimate unsafe acceptance.
The references were not independently legally verified and the families were
development-exposed.

Target-specific probability calibration, semantic-entropy risk calibration and
conformal interpretation sets are not implemented as a validated product policy.
The public report correctly leaves `legal_correctness_probability` null. There
is no demonstrated rule saying which case can omit individual legal review while
meeting a predeclared error criterion. This is the most important evidence gap
for the user's economic objective.

Construct a frozen, source-diverse reference corpus, using explicit official
answers where available and narrow internal adjudication for residual disputes.
References must preserve acceptable alternatives and uncertainty rather than
force a single answer. Separate development, calibration and held-out source
families; measure material omissions, unsafe acceptance, accepted coverage,
residual-question quality and actual reviewer time. Include unanimous-error and
future-source-change challenges. A calibration method needs its own justified
target population and assumptions before supplying a release threshold.

This does not require commissioning an external opinion for every circular.
Reusable internal reference decisions, automatic change-impact checks and narrow
residual questions can concentrate expensive review. Whether that actually saves
time safely remains an outcome to measure. Repeating the existing cases with the
remaining call allowance cannot substitute for a valid reference and study design.

### 7. Broader temporal and normative semantics

**Consent and achievement profiles implemented; general contract semantics
absent.** The runtime preserves explicit event ordering, valid/known times,
withdrawal, deadlines, incomplete observation windows and late performance.
The documented profile defers maintenance duties, pre-emptive satisfaction,
waivers, legal compensation and business-day calendars. A general model of
permissions, powers, prohibitions and interacting continuing duties is not
provided by the current scalar expression language.

Add only profiles required by selected circulars, with explicit actors,
activation/discharge/breach rules and deadline conventions. Their acceptance
cases should distinguish permission from occurrence, absence from incomplete
observation, and late performance from removal of an earlier breach. Stipula,
eFLINT or Symboleo may inform or implement a selected profile after its semantics
are aligned; none is integrated into the runtime now.

### 8. Proof coverage beyond finite executions

**Useful formal checking exists; a full implementation-preservation proof does
not.** Z3 compares the supported Boolean/integer/money fragment with knownness.
The inspected encoder excludes defaults, scaling and dates; conflict cases have
other finite execution checks rather than this SMT encoding. Its reported target
is status/type/value and `proof_certificate_checked` is false. The Lean file in
the monograph review proves selected mathematical properties, not the complete
Python/Java evaluator, compiler, trace or bank host.

There is no integrated Stipula-to-Java/JML/KeY verification route, general compiler
correctness proof, CUTECat concolic adapter or independently checked solver-proof
pipeline. Python/Java agreement is valuable but can share a wrong specification.

Prioritize proof obligations for concrete failure-prone operations and extend
symbolic comparison only with explicit semantics. A broader checker should
reject unsupported inputs, generate replayable counterexamples, and keep proof
scope attached to the result. A formal theorem about a language does not transfer
automatically to this adapter or settle its English source.

### 9. Institution integration and supervised operation

**Synthetic host and controls implemented; bank deployment absent.** The code
has release-role checks, historical replay, content identities, source-change
invalidation, a local scheduler and synthetic transaction tests. The application
documentation explicitly treats direct SQLite administration as trusted and
records unsigned local review evidence.

The bank's Java interface/version, real fact/evidence mappings, service identities,
data retention, transaction integration and staging environment are not supplied.
Enterprise identity, signing/tamper resistance, secret management and operational
acceptance therefore remain separate work. Existing deterministic host tests
cannot answer whether the bank supplies the right actor, amount, category or
knowledge cutoff.

The institution-specific acceptance test is a shadow replay through the actual
adapter, including forced withdrawal/amendment races, stale/conflicting evidence,
rollback and reconstruction of a past decision. External inputs are required for
that phase; they do not prevent the repository work in gaps 1–8.

### 10. A current, explicit implementation map in the monograph

**Documentation is behind the code.** The main and companion books integrate
round four, while `START-HERE.md` still leads with round one and contains older
statements about live studies. Those records should not guide current task
selection without the later reports. Neither book currently incorporates the
round-nine all-abstention finding, the round-ten repair/command limits or the
Catala pilot's actual result.

Create a versioned method-to-code/test/evidence matrix distinguishing required
product behavior, optional research routes and background literature. Update the
narrative and implementation entry points against that matrix, preserving the
existing content and dated evidence. Build and inspect the revised PDFs; page
counts and successful compilation alone do not establish coherence or completeness.

## Literature routes that have not become runtime integrations

These are not all mandatory work items. The monograph's synthesis explicitly
chooses a small executable core and specialized adapters for declared fragments.

| Literature/software family | Current disposition |
| --- | --- |
| Catala | Real bounded pilot in the separate worktree; not merged or generally adopted |
| Stipula, Java/JML/KeY, reachability/liquidity and amendment analyses | Surveyed and illustrated; no product backend or executed KeY proof route |
| s(LAW)/s(CASP), ASP/Clingo, eFLINT, Symboleo | Concepts inform design; no adapters providing independent runtime conclusions |
| LegalRuleML and other interchange/language routes such as L4, DMN/KIE, OpenFisca | No implemented production interchange/backend adapters; local JSON carries selected metadata concepts |
| HYPO/CATO/AGATHA | Selected case/argument/search mechanisms adapted; complete systems not reproduced |
| ASPIC+/Carneades | Selected attack and premise mechanisms implemented; broader semantics and legal proof standards not fully implemented |
| ContractNLI, ARc, Logic-LM, LINC and tax-reasoning work | Selected evidence, symbolic checking, repeated interpretation and repair ideas adapted; no claim of deploying or reproducing those original systems or their reported accuracy |
| CUTECat | No concolic adapter; current project has boundary, mutation and finite comparison checks |
| Semantic entropy and conformal prediction | Discussed; no target-validated risk score or calibrated set/acceptance implementation |
| MathDevMCP | Invoked by document mathematics checks; not a runtime proof adapter for every generated control |
| ResearchAssistant | Used in citation/PDF archive tooling; not a complete runtime source-assurance integration |
| DynareMCP | Search/investigation patterns borrowed; no runtime MCP integration located in `src/legalmath` |

These dispositions are about local implementation. This audit did not reassess
the latest external releases, re-read all papers or assign the literature's
empirical results to LegalMath.

## Recommended next sequence

1. Reconcile the current capability map and define one persistent full-assurance
   workflow. Implement the missing orchestration/API links using existing modules.
   Keep the Catala branch under its current owner's control.
2. Add competing factual schemas and source-region/authority completeness checks.
   Use planted shared omissions and unencodable readings as acceptance cases.
3. Expand the source-bound case/authority model and provider routing. Compare the
   additional redundancy on distinct failure mechanisms; do not count more model
   agreement as proof.
4. Construct the held-out reference and reviewer study alongside development.
   Introduce a selective-review policy only after its own acceptance criteria are
   met. Reserve external specialist review for the unresolved material questions.
5. Integrate the reviewed Catala result into current main, expand only needed
   temporal/proof profiles, and perform the actual institution adapter/shadow
   checks once its technical contract is available.

Each implementation phase should retain the existing pattern: skeptical review,
explicit comparator and pass/fail conditions, execution, observed-failure repair,
fresh evidence and a refreshed next-phase plan. A failed candidate blocks its
adoption; it need not block a planned repair that addresses the observed failure.

## Decision record

| Decision | Primary evidence | Veto/uncertainty | Next action | What is not concluded |
| --- | --- | --- | --- | --- |
| Count the interpretation/search/repair core as implemented | Located executable modules and retained rounds 3–10 evidence | Fragmented entry points and bounded profiles | Integrate and exercise the complete workflow | Exhaustive or correct English interpretation |
| Count Catala as an unmerged bounded pilot | 438 retained hashes and 16 current reviewed inputs matched; 112 passing recorded cases, 82 actual Catala calculations | Narrow projection, older baseline, no complete host/trace integration | Continue its own integration plan and later run combined regression | RuleIR replacement or production readiness |
| Do not claim reduced legal review yet | Round nine reports 16 abstentions and zero accepted outcomes | No independently validated legal reference or measured reviewer savings | Build the reference/study and selective-review policy | A safe automatic-clearance rate |
| Continue product work without a blanket consultancy prerequisite | Several concrete engineering gaps do not require a new legal opinion | Residual authority/classification questions and bank inputs remain | Build reusable controls and focused review packets | That all material legal judgment can be eliminated |

The strongest alternative explanation for the audit's positive implementation
findings is that isolated modules and development fixtures may overstate their
behavior in combination. The weakest evidence is still safe acceptance on unseen
source families and reviewer benefit. A new end-to-end adversarial case exposing
lost source material, a silently discarded reading or unsupported clearance would
require revising the corresponding implementation status even if older tests pass.
