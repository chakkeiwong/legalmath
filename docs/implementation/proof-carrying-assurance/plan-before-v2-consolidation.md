# Proof-carrying assurance integration: reviewed execution plan

**Date:** 2026-09-28  
**Status:** v1 acceptance rejected at final audit; v2 repair reviewed for execution  
**Owner:** LegalMath implementation  
**Target readers:** the implementation agent, a compliance technology reviewer, a
qualified legal reviewer, and the engineer responsible for the Java host.

## Purpose and decision boundary

### Binding repair discovered during execution

The first implementation did not meet this plan. Its fixture constructor created
`AGREES`, `PROVED` and `CHECKED` records from descriptive dictionaries without
executing the named methods on the recorded target. Hashing a description is
not checking its truth. The generic regression suite could not repair this
defect. The P5 suite was interrupted after discovery; no partial suite is a pass.
All original attempts remain under `artifacts/proof-carrying-assurance/` as
rejected engineering evidence. They must not be cited as validated dossiers.

The repaired execution uses the fixed subdirectory `verified-execution-v2`.
This is a materially stronger acceptance protocol, not an attempt-budget reset
for the rejected protocol. Each phase has three attempts; exhaustion stops it.
There is no supervisor-file exception to invalidation. Changes to the controller,
allowlist or plan invalidate current acceptance, as do changed evidence files.

The repair replaces the fixture assertions with adapters that actually:

* extract and audit retained source bytes against the archived packet;
* validate all retained candidate quotations and formalizations;
* reevaluate the typed criticism proposal through the existing argument engine;
* visit every retained candidate before comparing any pair, then compare pairs
  only under an explicit common fact vocabulary and output meaning;
* typecheck, compile and replay Python/Java, and the installed pinned Catala
  backend, preserving executable files, commands, input cases and result files;
* report missing live generation, proof-assistant and new-authority work as
  incomplete, without substituting archived proposals for fresh generation.

The selected replay input is the complete five-candidate 23EC46 investigation
from round 3, A7 attempt 08, including its source packet and criticism proposal.
This is a regression of previously proposed readings, not a future-circular
accuracy evaluation. A generic input manifest names and hashes these files so
the adapter does not contain circular-specific legal rules. The audit also
requires synthetic unknown-operator, evidence-tampering, missing-proof,
mis-targeting and source-change tests. Imported proposal origin remains visible.

The verifier now requires file-backed evidence, reconstructs the target from
its inputs, checks all record references, blocks every incomplete required
obligation, and recomputes shared-dependency groups. Finite differential replay
is `CHECKED`, never a proof certificate. Formal `PROVED` is unavailable without
a registered certificate checker. This version registers no such checker.

The controller's acceptance requires artifact hashes, predecessor-manifest
hashes, exact input hashes and completed JUnit reports with zero failures,
errors and skips. It records interruption before any retry and executes a
focused repair command. Refreshing the next plan is a deterministic operation
over these verified records; it cannot convert an open interpretation into an
accepted legal answer. Failed commands preserve their argv, exit status and log.

**Skeptical repair audit:** the earlier baseline was wrong because it measured
schema acceptance rather than executed evidence. V2 makes actual file-backed
executions the engineering criterion. Runtime agreement is still conditional
on shared RuleIR and fact meanings. Missing fresh generation is a promotion
veto, not a veto on the useful offline integration repair. No legal or general
future-source accuracy claim is permitted. The current pinned JDK and Catala
are inspected rather than assumed unavailable. The smallest discriminating
check is a dossier with a fabricated evidence digest: it must fail before any
expensive backend execution.

The current repository contains useful but separately recorded capabilities:
source retention and extraction, competing interpretation search, structured
arguments, RuleIR validation, bounded solver checks, Python/Java execution,
Catala pilot support, and extensive round-16 evidence. The monograph explains
each of them, but a new implementer still has to infer how one circular moves
through all of them and what a passing result means. This plan closes that
integration gap.

The deliverable is a proof-carrying assurance package. “Proof-carrying” has a
narrow engineering meaning here: every formal or execution claim is accompanied
by its exact target, assumptions, checker, input hashes, result status and
limitations. It does not mean that a checker proves that an English reading is
the regulator's intended meaning. English interpretation remains a source-bound
argument with explicit alternatives, missing authority and an abstention path.

The plan therefore has three separate ledgers:

1. **Engineering ledger:** the controller, schemas, hashes, commands, replay and
   generated artifacts are internally consistent.
2. **Formal ledger:** each theorem, solver query, type check and backend
   comparison states the formal object and domain it covers.
3. **Interpretation ledger:** source passages, candidate readings, arguments,
   counterarguments, unanswered questions and legal-owner decisions remain
   visible. No engineering pass promotes this ledger to legal approval.

The execution uses public or synthetic fixtures already retained in the
repository. The shared live-model allowance is already exhausted, so this run
must not make a provider call. A provider-unavailable result is a required
tested state, not a reason to fabricate a candidate or a success.

## Baseline inventory

The baseline is the existing worktree at the time this plan is created. It
includes the round-16 result, its protected historical artifacts, the current
monograph source, the process map, the four integrated-assurance source
fixtures, the existing assurance/search/argumentation modules, the Java host
demonstration, and the optional Catala adapter. Existing dirty files are
preserved. The execution controller records exact SHA-256 bindings for every
material input and writes a new result directory; it does not rewrite earlier
rounds.

The main source is `docs/monograph/monograph.tex`. It includes
`chapters/06-ensemble.tex`, which in turn includes the round-15 and round-16
source units `06a` through `06f`. The process guide is
`docs/monograph/frontmatter/process-map.tex`. The reader-facing build is
`scripts/build_reader_facing_monograph.py`; its output is checked by
`scripts/check_reader_facing_monograph.py` and the process guide is exported by
`scripts/export_monograph_process_guide.py`.

The current baseline does not contain the following single, reviewable
interface:

* a versioned record that binds a source packet, interpretation hypotheses,
  argument graph, proof obligations, tool results, Java/Catala artifacts and
  release gates;
* a validator that rejects stale, mis-targeted, unsupported or incomplete
  evidence rather than treating it as agreement;
* a controller that runs the existing checks in fixed phases, executes a
  repair exercise, refreshes the successor plan from actual hashes, and
  refuses to claim release readiness; or
* a monograph/process-map account of those exact artifacts and stop conditions.

## Skeptical plan audit (required before execution)

The plan was audited against the following failure modes.

| Audit question | Finding and mitigation |
|---|---|
| Wrong baseline | Round-16 outputs and the current source tree are already dirty and contain historical evidence. The controller freezes only hashes and writes new outputs; it never assumes a clean checkout. |
| Proxy promoted as correctness | Method agreement, Java/Python agreement, solver `UNSAT`, proof-assistant success and search score are each typed to a target. None can set `legal_correctness_established` or `release_eligible` to true. |
| Missing stop condition | Missing source material, provider unavailability, unsupported RuleIR, solver `UNKNOWN`, stale inputs, conflicting facts, incomplete candidate families, and failed repair all stop the affected gate. |
| Correlated methods | Every method records family and shared dependencies. The validator reports correlation and never treats a method count as a probability. Catala and Java are explicitly marked as sharing RuleIR/input preparation. |
| Future circular overfit | The fixture includes a deliberately novel clause dimension. A candidate grammar that has no supported family must return `UNRESOLVED`/`EXTENSION_REQUIRED`; it may not reuse the nearest old rule. |
| Hidden environment drift | Commands are fixed, run offline, CPU-only, and record Python/JDK/tool identities. Optional tools have explicit `UNAVAILABLE` results. |
| Unbounded retries | The controller fixes phase and repair limits, persists attempts, and consumes a repair record. A retry cannot erase a failed attempt or reset a budget. |
| Artifact mismatch | Each result stores input hashes, implementation hashes, target IDs and result hashes. A changed input invalidates that phase and its successors before execution. |
| Unfair comparison | The run compares methods only on a declared shared target and fixture. Different vocabularies, scopes or output meanings become `NOT_COMPARABLE`, not a disagreement score. |
| Non-answering artifacts | A green test run is not the final artifact. The controller must produce the dossier, phase manifests, uncertainty report, next-phase plan, document build and rendered-page review record. |
| Environment mismatch | The execution uses the repository Python environment where available, explicitly hides accelerators, and reports missing JDK/optional tools. No GPU or network result is inferred from a sandbox failure. |
| Command authorization | The master program has a literal allowlist of commands and arguments. It rejects interpolated shell text and arbitrary paths. |

The audit passes for an engineering integration run because the primary
acceptance artifacts are typed and deterministic. It does **not** pass a legal
accuracy or production-release audit; those remain explicit vetoes.

### Repair-budget revision after the first document attempts

The original controller allowed two attempts per phase. P4 then exposed three
different defects: the first attempt compiled the documents but used a Python
without PyMuPDF; the second compiled with the correct interpreter but stopped
because six new citation contexts lacked author-review records; and the third
passed citation checking but invoked the process-guide exporter through the
wrong interpreter. These are separate failures with separate repairs, so
silently discarding any attempt would corrupt the execution history. The
allowlist now permits four attempts per phase, only P4 uses the fourth attempt,
and all failed manifests plus their executed repairs remain in the output. The
increased budget changes supervisor governance; it does not change the
acceptance criterion or release vetoes.

## Research intent and evidence contract

**Question.** Does a single controller preserve multiple interpretations and
their source/argument/proof/execution evidence while detecting stale or
unsupported claims across the existing assurance methods?

**Candidate mechanism.** A versioned `AssuranceDossier` with a family-aware
method registry, proof-obligation statuses, deterministic validators, a bounded
repair phase, and successor-plan refresh.

**Expected failure mode.** A method reports success for a different target, a
shared dependency is counted as independent, a future clause is silently
classified using an old family, a stale result survives a source edit, or a
repair/retry hides the original failure.

**Primary engineering pass criterion.** The local fixture produces a dossier
whose required fields and hashes validate; the deliberately stale, unsupported,
correlated and novel-clause mutations are rejected or retained as uncertainty;
the Java and optional Catala results are bound to the same RuleIR package; the
master completes every phase and writes a successor plan derived from actual
results.

**Hard vetoes.** Any validator accepts stale or mis-targeted evidence; any
unknown/unavailable/unsupported result is converted to agreement; an old failed
attempt disappears; an allowlisted command is not the exact command executed;
the document build fails; or the full targeted regression has a failure, error
or unexpected skip.

**Explanatory diagnostics.** Method-family counts, search scores, elapsed time,
number of hypotheses, Java/Python agreement counts, and document page counts
describe the run. They do not promote it.

**What the run cannot conclude.** It cannot prove that an English interpretation
is legally correct, estimate a probability of correctness, establish statistical
independence, establish complete coverage of future circulars, or authorize
production bank use.

**Preserved artifact.** `artifacts/proof-carrying-assurance/` contains the phase
manifests, dossier, mutation/repair results, document checks, rendered-page
inspection record, next-phase plan and a final engineering report. The result
directory is append-only after a phase is accepted.

## Default and assumption audit

| Choice | Provenance and justification | Failure mode | Early diagnostic | Status |
|---|---|---|---|---|
| JSON canonical hashing | Existing `legalmath.canonical` and assurance journals already bind evidence this way. | A non-canonical serializer could make equivalent records look different. | Hash the same object twice and reorder keys in a test. | Reviewed implementation default |
| Required method families | Existing diversity module requires unique method IDs and at least two families. | A large number of correlated wrappers could create false confidence. | Shared-dependency report and family-count veto. | Reviewed safety rule |
| No live model calls | Shared 500-call allowance is exhausted and the run must be reproducible. | The fixture may not measure future provider quality. | Provider-unavailable test and explicit non-claim. | Deliberate engineering constraint |
| CPU-only execution | The requested integration is not a numerical GPU experiment; reproducible local checks are sufficient. | A tool may behave differently on an accelerator. | Environment manifest records hidden devices; tool-specific GPU work remains a separate plan. | Convenience constraint, not production default |
| Required Catala result | Catala is an optional, shared-input backend; including it tests the boundary. | Missing compiler could block a useful Java-only engineering check. | `UNAVAILABLE` is a valid result but blocks release and is reported. | Boundary hypothesis |
| Finite fixture scenarios | Existing 23EC46/24EC50/25EC71/26EC2 manifests provide retained public/synthetic scope. | Finite scenarios can miss an unseen case. | Novel-clause mutation and explicit finite-domain wording. | Regression baseline |
| Release gate always false | No independent legal owner approval or bank production controls are present. | A downstream consumer might mistake a green artifact for approval. | Schema requires `release_eligible=false`; tests attempt a false promotion. | Safety invariant |

## Implementation phases

### P0 — Freeze inputs and document the target

Create the phase plan, protected baseline, command allowlist and input manifest.
Record the document source files, existing round-16 report, optional-tool
profiles and the implementation modules that the dossier will bind. Amend the
monograph and flow map in later phases, but record their pre-change hashes here.

**Acceptance:** all required paths exist; all hashes are recorded; the plan's
skeptical audit is present; no historical round artifact changes.

### P1 — Add the assurance contract

Implement `src/legalmath/interpretation/assurance/integration_contract.py`.
It defines strict records for interpretation hypotheses, method evidence, proof
obligations, generated artifacts, discrepancies, unresolved questions and the
top-level dossier. The validator checks identity, target, shared dependencies,
status-specific required fields, hash links and the release vetoes.

**Acceptance:** unit tests cover valid records plus stale hashes, wrong targets,
duplicate methods, one-family evidence, solver unknown, unsupported future
clause, shared Java/Catala inputs and attempted release promotion.

### P2 — Connect the existing methods without conflating them

Implement the local fixture adapter and method registry. It records source
inventory/ResearchAssistant-style extraction, independent candidate families,
ASPIC+/Carneades-style arguments, bounded breadth-first/UCT scheduling,
RuleIR/type checking, solver/Lean-style formal obligations, Python/Java
execution, and the optional Catala boundary. The adapters return typed evidence
and capability limits; they do not rewrite candidate meanings.

**Acceptance:** at least two interpretive families survive the initial breadth
pass; a counterexample separates the fee-rebate readings; a formal obligation
has a checked target; Java replay is bound to the exact bundle; Catala either
passes its reviewed profile or returns `UNAVAILABLE` with a blocking reason; a
future clause is retained as an extension obligation.

### P3 — Implement the master controller

Add `scripts/run_proof_carrying_master.py` with fixed commands:
`audit`, `execute`, `repair`, `status` and `refresh`. Each phase writes a
run manifest, exact argv, environment, hashes, result status and next-phase
plan. A source or implementation change invalidates the affected phase and all
successors. The controller executes only allowlisted commands and uses an
append-only attempt history.

**Acceptance:** an interrupted/failed attempt cannot be overwritten; a repair
record is required before retry; the executed repair reruns focused tests and
retains the original failure; successor plans change when a material input
changes; no model call or network access occurs.

### P4 — Amend the monograph and process map

Add a self-contained source unit to Chapter 6 after `06f` explaining the
proof-carrying dossier, the method families, the 23EC46 dry run, the precise
meaning of formal proof, future-clause extension, Codex/ResearchAssistant/
MathDevMCP/DynareMCP boundaries, and the master program's commands and
artifacts. Add a process-guide chart for the typed evidence path, discrepancy
gate, repair/refresh loop and final abstention route. Link the chart to the
source unit and keep the existing limits visible.

**Acceptance:** canonical TeX compiles; citation and mathematical checks pass;
the process guide exports; the new chart has a question before it and an
interpretation after it; the rendered pages are inspected and the document
checker records any pending human readability review.

### P5 — Execute, red-team and refresh

Run the master on the retained local fixture. Run focused integration tests,
the existing assurance/search/Catala/Java suites affected by the change, and
the reader-facing document build. Red-team the result against the audit table:
identify the strongest shared-error explanation, the observation that would
overturn the engineering conclusion, and the evidence still needed for English
correctness. Write the final report and the next-phase plan from actual hashes.

**Acceptance:** all hard vetoes are clear; the dossier validates; the repair
exercise is executed; the document build and tests pass; `legal_accuracy_-
established=false` and `release_eligible=false` remain explicit; the next plan
contains the unresolved source/legal/operational work rather than declaring
completion.

## Exact command policy

The master may execute only these command shapes from the repository root:

* the repository Python interpreter running the fixed master and fixed test
  targets;
* `python3 -m pytest` with the literal test paths listed in the allowlist;
* `latexmk -xelatex -interaction=nonstopmode -halt-on-error -cd` on the two
  canonical document sources;
* the existing fixed document-check and process-guide export scripts.

No shell fragments, package names, URLs, arbitrary output paths, model prompts,
or user-provided executable arguments are accepted by the master. Optional
installation remains a separately reviewed action; this execution is offline
and reuses the existing installed environments.

## Completion interpretation

Completion means the integration controller and its documentation are
implemented and the local engineering evidence is reproducible. It does not
mean that the bank can use the generated Java. The next plan must still cover
independent legal adjudication of representative circulars, held-out future
editions, source-scan/OCR review, fact/identity controls, security, change
management, calibrated evaluation, and a supervised shadow period.
