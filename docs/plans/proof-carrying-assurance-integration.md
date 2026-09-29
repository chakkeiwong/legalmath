# Executed-evidence assurance integration: master program v3

Date: 2026-09-28. Scope: engineering integration and documented interpretation
uncertainty. The earlier plan and audit are preserved in
`docs/implementation/proof-carrying-assurance/plan-before-v2-consolidation.md`.
The user authorized documentation, thorough review and implementation. No new
provider allowance, bank deployment or legal approval is inferred.

## Problem and acceptance target

A circular's English meaning, its formal encoding and its Java behavior are
three different claims. Existing search, argumentation, source, RuleIR, SMT,
Java and Catala components produce useful evidence, but tests of these components
alone do not establish that they ran on the same question. The product needs a
single dossier whose proposed meanings, sources, actual checker results and
executables can be traced and rechecked together.

The first implementation failed this requirement. `build_fixture_dossier`
constructed `AGREES`, `PROVED` and `CHECKED` records by hashing descriptions,
without executing the named methods. Its tests checked the schema rather than
those assertions. The final audit rejected that implementation and interrupted
P5. Original attempts remain under `artifacts/proof-carrying-assurance/` and
are not accepted evidence. Three document failures and their repairs also remain
there. The repaired protocol first wrote to the explicit subdirectory
`verified-execution-v2`, with a new acceptance criterion and three attempts per
phase. That campaign has now closed without current acceptance; its history is
preserved. The explicitly reviewed v3 campaign validates the combined source
revision in an isolated copy and reexecutes every phase. It uses
`verified-execution-v3`, also with three attempts per phase and no automatic
campaign restart. It reuses no earlier phase pass.

## Research intent and evidence contract

| Item | Contract |
|---|---|
| Question | Can a generic dossier preserve all retained interpretations and attach real source, argument, formal and runtime evidence while rejecting stale, fabricated or mis-targeted success? |
| Baseline | Existing source extraction, typed criticism, search formalization, Java and pinned Catala implementations; the rejected descriptive fixture is an adversarial baseline, not a comparator for legal accuracy. |
| Mechanism | Strict records plus deterministic evidence verification, actual tool execution, explicit incomplete states, immutable attempt files and phase input/predecessor binding. |
| Primary engineering criterion | Every successful method result has retained input/output files; the verifier reconstructs targets and checks the relevant content; actual Java/Catala builds and replay occur; all tests and document checks pass. |
| Promotion veto | Forged success, missing/changed file, hidden candidate, wrong target, unknown proof promoted to proof, omitted shared dependency, unbound artifact, missing required check, failing/skipped regression or stale document. |
| Continuation veto | Corrupted source evidence, unsafe execution boundary, exhausted fixed retry budget, unavailable required execution environment, or irreconcilable concurrent input edits. |
| Repair trigger | A failing assertion, incomplete record, implementation defect or document defect with an identifiable repair. Preserve the failure, repair and rerun the affected checks. |
| Explanatory diagnostics | Candidate count, family labels, search scores, pair counts, finite replay size, elapsed time and PDF page count. These cannot establish legal accuracy, method independence or future coverage. |
| Prohibited conclusions | No probability of legal correctness, whole-compiler theorem, complete future-source interpretation, superior model accuracy, bank release or independent legal adjudication. |
| Result record | `artifacts/proof-carrying-assurance/verified-execution-v3/final-report.json`, all phase manifests, file-bound dossier and `docs/implementation/proof-carrying-assurance/post-execution-review.md`. |

The engineering, formal and interpretation ledgers remain separate. A successful
finite replay is `CHECKED`; a formal `PROVED` status requires a registered
certificate checker. This version registers none and rejects that status.
English uncertainty is represented by source-linked arguments and unanswered
questions; a timeout or exhausted search does not resolve it.

The final red-team pass found a second evidence-binding defect after a complete
1,015-test regression: deleting the original input-manifest reference still
allowed the verifier to accept its embedded configuration. Dossier schema v3
now requires that file, reparses its bounded `ReplayInput` schema and checks
equality with the embedded target. Three new regression cases cover deletion,
configuration substitution and an oversized probe budget. The previous full
report is retained as superseded evidence. The third permitted P1 attempt passed
30 contract tests but failed the input-stability check when four monograph files
changed concurrently. V2 therefore exhausted its fixed allowance without new
acceptance; no failure or attempt was erased or relabelled.
The P0 snapshot also archives actual input bytes and records installed package
versions: a base commit plus hashes cannot reconstruct overwritten dirty files.

### Reviewed isolation repair before v3 execution

The concurrent edits document the other agent's Catala implementation and must
be preserved. They invalidate document/input acceptance, not the 30 observed
test outcomes. The separate package-fingerprint diagnostic found repeated
enumeration of the same name/version through duplicate import paths. V3 records
unique name/version pairs while retaining distinct conflicting versions; a
regression checks both properties. This does not claim that package version
strings authenticate every installed dependency byte.

The new execution is justified by a repaired harness and a frozen combined
revision, not by a weaker pass criterion. Copy the full repository into
`/tmp/legalmath-assurance-v3-20260928`, preserve the Catala toolchain's logical
repository path with an internal symlink, and point the copied editable Python
installation at the copied `src`. Compare all material input hashes before and
after copying. Run all six phases there; concurrent changes to the original
checkout cannot enter the run. Before delivering results, compare the original
checkout's material inputs with the accepted snapshot. Only identical inputs
permit copying the new output directory and built PDFs back and reverifying
every accepted manifest and dossier in the original repository. Otherwise keep
the frozen result scoped to that revision and report the difference.

This is one explicitly reviewed successor campaign under the user's existing
authorization to complete necessary implementation repairs. It uses no model
allowance, installs no packages and expands no legal acceptance criterion. A
further exhausted ceiling or irreconcilable drift stops execution for a new
decision; the program has no reset or automatic campaign-creation command.
The v2 closure, old controller and old plan are retained under
`docs/implementation/proof-carrying-assurance/`.

## Skeptical review and assumptions

The revised plan was checked before execution for wrong baselines, proxy
promotion, missing stops, unfair comparison, hidden defaults, stale context,
environment mismatch and commands that do not answer the question.

| Risk | Finding and correction |
|---|---|
| Wrong baseline | A typed description was mistaken for executed evidence in v1. V2 requires actual stored responses, RuleIR, cases, compiler manifests, JARs and runtime results. |
| Proxy promotion | Solver results and finite replay remain conditional; a hash alone never proves a proposition. Release/legal fields are fixed false. |
| Correlation | Java and Catala share the proposed RuleIR and facts. Required shared dependencies are checked, and the report lists dependency groups without claiming independence. |
| Future overfit | The real run replays five archived 23EC46 readings. It measures integration, not recall on an unseen circular. Unknown operators are separately tested to retain `EXTENSION_REQUIRED`. |
| Unfair comparisons | Only exactly matching fact definitions and explicitly common result meanings are compared. Other pairs remain `NOT_COMPARABLE`; no guessed mapping. |
| Stale context | Catala integration was merged into the shared repository during work. V2 includes current translation modules and their tests and records the current commit and file hashes. |
| Environment mismatch | JDK and Catala paths/bytes are inspected. Document checks use the existing PyMuPDF environment. API tests require trusted host thread facilities; sandbox stalls are not interpreted as product failures. |
| Non-answering commands | Generic tests are additional evidence. P2 must execute the actual dossier, and P4 must build/export and retain PDFs. |
| Hidden mutation | Every accepted phase binds exact input, predecessor and output hashes. No controller/plan/allowlist exception to staleness is permitted. |
| Missing stop | Three attempts per phase; failures and interruptions require executed repair. Provider/network work is disabled. |
| Allowlist escape | Only exact fixed test/document argv are allowed, including the JUnit path within the attempt directory. User/model text is never shell code. |

Audit verdict: sufficient for the engineering question after the evidence-binding
repair; insufficient for legal accuracy or release. Missing fresh generation is
a promotion veto, not a reason to abandon offline engineering work. The shared
allowance was checked at 500 recorded calls against a maximum of 500.

| Choice | Provenance/justification | Failure mode and early check | Status |
|---|---|---|---|
| All five round-3 A7/08 readings | Existing retained model proposals, not newly authored expected answers | Shared omissions; preserve proposal origin and do not report future-source coverage | Replay baseline |
| 24 probes per reading | Existing `Comparisons.verify` bound | Finite domain can miss cases; persist every case and label finite conformance | Convenience bound |
| Ten pairs | Five readings yield ten unordered pairs | A lower budget could hide pairs; store total and unvisited counts and test coverage | Complete pair coverage of this retained set only |
| Exact fact definitions | Existing type/meaning boundary | Overly strict comparison reduces coverage; retain a mapping question rather than guess | Conservative implementation default |
| Typed argument profile | Existing sourced criticism evaluator | Premises/priorities can be wrong; recompute semantics and preserve all critical questions | Conditional method |
| SHA-256 evidence binding | Existing canonical and raw hashing | Hashes do not authenticate source acquisition or prove a historical invocation; rerun deterministic checks and state the trust base | Integrity mechanism |
| Pinned Java/Catala | Existing merged toolchains | Toolchain or lowering bug; actual builds and independent execution paths, plus full backend/translation tests | Engineering comparator |
| No provider calls | Existing 500/500 ledger | No fresh reader/critic result; record `UNAVAILABLE` and `NOT_RUN` | Resource constraint |
| Three retries | Bounded repair policy | A persistent failure could consume all retries; stop with preserved evidence | Governance limit |

Pre-mortem: the run can pass while all archived readings miss the same qualifier.
The answer is to retain that limitation and obtain fresh/independent evidence,
not to inflate method counts. It can fail because of a timestamp format,
missing binary or sandbox thread behavior rather than a legal-method failure.
Input validation, pinned-tool inspection and a small real replay distinguish
those explanations before the complete regression.

## Implementation contract

`integration_contract.py` defines strict hypotheses, methods, obligations,
artifacts, questions and discrepancies. `integration_execution.py` implements
`run_replay` over a hash-bound `ReplayInput`. `integration_verifier.py` registers
source, proposal, argument, type, runtime, search and unavailable-tool profiles.
It reconstructs the target, validates exact quotations and candidate-to-bundle
links, reextracts source text, reevaluates arguments and Python answers, checks
stored Java traces and build/JAR identities, and preserves incomplete required
obligations. Hashes alone are insufficient. The verifier's trust base includes
its implementation, the pinned executors and retained source/proposal inputs;
it is not a signed attestation from an independent party.

The command-line application exposes `assurance-dossier` and
`assurance-dossier-verify`. The manifest can name another retained investigation;
the adapter contains no 23EC46 legal predicate. Model proposals remain data
processed by the restricted parser. Existing live source/search/investigation
commands remain the generation layer. This offline integration consumes their
retained results; it does not silently invoke them or fabricate a fresh result.

## Reviewed phases and exact acceptance

| Phase | Executed work | Acceptance |
|---|---|---|
| P0 | Record current source/implementation/document inputs and rejection of v1 | Exact baseline exists; original attempts unchanged |
| P1 | Adversarial contract and execution tests | Forged evidence, wrong targets, stale source, erased questions, hidden shared inputs, missing proofs and future operators cannot obtain a clean verified dossier |
| P2 | Execute all five archived readings through extraction, criticism, RuleIR, pairs, Java and Catala | File verification succeeds; all readings survive; runtime evidence is real; unresolved interpretation remains blocked |
| P3 | Supervisor tests | Exact allowlist, zero-skip JUnit, retained failures/interruptions, stale-output and controller-change invalidation, and retry ceiling work |
| P4 | Build monograph/companion, check citations and export process guide | Build and checks pass; PDFs are copied into the attempt and publication hashes retained; rendered additions inspected before delivery |
| P5 | Execute wrong-target mutation/rejection/restoration; run four disjoint full-regression partitions | Every collected test directory covered exactly; all completed JUnit reports pass without skips; accepted input/output/predecessor hashes and dossier are reverified |

All phases refresh the next-phase plan. Failure writes an immutable attempt and
requires `repair --phase Pn --note ...` before retry. A repair note states the
failure, changes and regression. The controller actually executes the focused
contract suite (controller suite for P3, document build for P4). The retry then
executes the failed phase again. No phase is accepted solely because the repair
note says it is fixed. Input change invalidates the phase and successors; output
change does the same. Interrupted state cannot be silently resumed as passed.

Fixed controller commands from the repository root:

```sh
.venv/bin/python scripts/run_proof_carrying_master.py audit
.venv/bin/python scripts/run_proof_carrying_master.py execute --through P4
.venv/bin/python scripts/run_proof_carrying_master.py execute --from P5 --through P5
.venv/bin/python scripts/run_proof_carrying_master.py status
.venv/bin/python scripts/run_proof_carrying_master.py refresh
```

The P5 command runs in the trusted host context because the repository already
records a sandbox thread-wakeup limitation for HTTP TestClient tests. This is
an execution-environment requirement, not permission to contact a provider.
The project allowlist is `docs/implementation/proof-carrying-assurance/allowlist.json`;
host command approval remains a separate sandbox control.

Full regression partitions are assurance; Catala/conformance/translation;
search/interpretation; and integration/unit/security. The controller checks that
their file inventory covers every `test_*.py` under `tests` before running. A new
test directory therefore cannot be silently omitted.

## Review and successor

Inspect every changed rendered page, the diagram branches and captions, citation
scope, record links and named proof limits. Preserve previous monograph content.
Compilation and source-unit retention are engineering checks, not a human
readability verdict. The result note must include a decision table, inference
status, strongest alternative explanation, what would overturn acceptance and
what failed assumptions remain.

The next justified work is source-driven generation and criticism on prospective
held-out circulars under a renewed bounded allowance, acquisition/adjudication of
specific missing authorities, a real registered translation-proof checker, and
bank fact/identity/operational controls. Those are distinct from completing the
current engineering integration. No amount of replay replaces the missing
interpretive evidence, and no consultancy engagement is triggered automatically.
