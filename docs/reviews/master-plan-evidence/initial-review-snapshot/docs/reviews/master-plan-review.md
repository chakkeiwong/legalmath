# Master plan 1.0: author audit and development-readiness assessment

Date: 22 September 2026. Review type: author engineering audit, not an independent
Claude review, compliance opinion or user-acceptance test. Scope: the v0.3
proposal, current contracts/schemas/SQL, original work packages, master task
graph and the executable SPI-Demo1 example. The user clarified that the requested
deliverable is a **master implementation plan**, not application implementation.

## Verdict

**Ready to start the staged public-source development program at T00–T03.** The
master plan now identifies a concrete product, Java delivery boundary, task
dependencies, executable acceptance criteria and the missing contracts that must
close before their implementation. It is not evidence that the engineering MVP
or bank deployment is ready. T00's contract closure is a real deliverable, not
permission to let each later coder choose a different meaning.

| Decision | Primary criterion status | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Start T00–T03 | Existing source/example evidence and explicit first-task outputs are sufficient for contract closure, isolated package, storage and source intake. | No missing bank interface blocks this public/synthetic work. | Independent review may expose additional contract defects. | Execute T00, preserving the adversarial expectations; then T01–T03. | Full specification completeness or user acceptance. |
| Enter full runtime/Java work | Conditional on T00 closure, stable source/evidence types and predecessor task checks. | The current helper is not the full validator; full event/release schemas and storage relations still need implementation preparation. | Cross-feature interactions and independent expected traces. | T05–T10, with exact response comparisons and new negative cases. | The 35 full-language cases have already run. |
| Complete engineering MVP | Not yet achieved. | UI, full runtimes, lifecycle, jobs, source discovery and transactional host do not exist. | Integration and human comprehensibility. | T11–T22 under the plan. | Production or live-model usefulness. |
| Make comparative business claims | Not yet supported. | No independent human/model pilot or statistical comparison. | Review cost and material errors in real task families. | Register T24 with reviewers and held-out sources. | Error reduction, savings or method superiority. |
| Deploy into a bank | Not ready. | No approved bank perimeter/data mapping, real host integration, deployment authority or bank controls. | Institution-specific operation and legal interpretation. | Separate authorized integration/release project after prototype evidence. | Compliance certification or bank authorization. |

## Method and baseline

The [audit plan](../plans/master-plan-audit-plan.md) was written before nontrivial
validation. It explicitly checked wrong baselines, proxy metrics, missing stop
conditions, hidden defaults, stale estimates, environment mismatch and artifacts
that would not answer readiness. It separates engineering, legal and empirical
evidence. This turn did not run a stochastic or human experiment.

The audit inspected the complete written execution/storage/Java contracts,
task descriptions, JSON schemas, SQL sketch, fixture generator/checker,
demonstration compiler/reference/build harness and Java consent implementation.
It used the previously reviewed manuscript and its source-specific case inventory;
it did not claim a new complete literature review or replay a published proof.
The original proposal PDF, demonstration sources, inputs and JAR remain unchanged.

The starting baseline has 31 recorded file hashes. One existing specification
check and an isolated Java rebuild were used to establish current evidence.
The isolated workspace copies the original demo, contract pack, checker and
retained SFC snapshots, so regeneration cannot overwrite the original run record.
The [evidence directory](master-plan-evidence/README.md) preserves commands,
results, targeted probes and version identity.

## Findings and disposition

“Resolved in plan” means that the engineering decision or dependency is written
and synchronized; it does not mean the application feature has been implemented.
An assigned implementation defect remains a condition on its owning task.

| ID / severity | Finding, evidence and concrete consequence | Disposition and acceptance |
| --- | --- | --- |
| R01 / P1 | The older backlog could be read as treating the narrow demo and 35 structural fixture checks as the product baseline. Full decision/event/release engines are absent. | Master sections 1–2 and each task distinguish existing versus planned behavior. T07 runs the 35 actual decisions; T13/T14 run full events; T11/T12 implement lifecycle. No completion inferred from schema success. |
| R02 / P1 | Full responses include engine identity in the result hash, while cross-backend wording suggested equal complete hashes. Identical semantics with real Python/Java identities necessarily hash different request bytes. The saved two-engine probe demonstrates this. | Contracts and Java plan now compare every field except engine/version hash, then independently reconstruct both native execution hashes. T08/T09 implement A08; a common forged engine name is forbidden. |
| R03 / P1 | `build_java -> JavaReleaseManifest` included a test-report hash although the build is the object that must first be tested; the release prose also bound reports to manifests. This invited a circular digest dependency or premature approval. | BuildManifest -> VerificationReport -> JavaReleaseManifest -> ReleaseRecord, with explicit directed hash references. Manifest is external to the JAR it names. T10/T12 prove changed/wrong binaries cannot reuse approval. |
| R04 / P1 | A single export command left candidate compilation and approved release export ambiguous. Requiring approval to obtain the JAR whose tests support approval would deadlock development. | Separate `build-java --bundle-hash` candidate operation from `export-java --release-hash`. Candidate has no release authority. W03J and master commands synchronized. |
| R05 / P1 | Current `semantic_structure` accepts duplicate source-span IDs, duplicate interpretation IDs and an interpretation citing a missing span. Three targeted probes observed acceptance. | Explicitly recorded as an existing checker limitation; T00/T05 negative cases reject all three. Current checker/demo code is unchanged, so this is not falsely reported as repaired software. |
| R06 / P1 | Full result fixtures are expected projections. Schema validation and matching two runtimes do not independently verify postorder traces, source inheritance, skipped roots or result hashes. | T08 adds independent trace/result invariants and hash reconstruction; T09 compares full semantics. A08 plus source/evidence mutations expose false agreement. Finite cases remain finite evidence. |
| R07 / P1 | W03J initially expected full consent histories before W05 created the event contract implementation. The demo replay assumes caller attribution and cannot replace full actor/stream/sequence handling. | Separate decision backend T09/T10 from full event Java projection T14, after Python replay T13. Preserve all eleven narrow consent regressions; add full event attribution tests. |
| R08 / P1 | No-future completeness was explicit in the Java addendum/demo but not in the general event semantics. A connector could otherwise certify withdrawal absence through a future instant. | Synchronized written event rule: `complete_through <= assertion.recorded_at`, for consent and duty evidence. T13/T14 require future-seal, late-evidence and incomplete-window cases. |
| R09 / P1 | Supersession visibility was specified by knowledge time but interval-local behavior was not explicit. A correction known today but valid tomorrow could prematurely erase today's fact. | Interval-local suppression is now specified in contracts/master. Unknown target, cross-subject/fact/type and cycles fail or quarantine. T06 implements both future-valid and late historical correction tests. |
| R10 / P1 | Supplied SQL lacks explicit lookup/persistence for several described entities: release records/validity, authors, applicability, source dependencies, fact corrections and stream headers. JSON payloads do not automatically give correct unique selection. | Mark SQL as a starting sketch. T00 freezes data relations; T02 implements forward migrations, constraints/indexed queries and crash/reload checks. T12/T13 cannot claim completion while state exists only in memory. |
| R11 / P1 | API described event append and jobs without complete stream creation, draft submission or job retrieval/cancellation. A body-provided reviewer role could also be mistaken for caller authority. | Added operation names, lifecycle behavior and local registry boundary to master/contracts. T00 supplies complete schemas; T16 implements restart/idempotency/cancellation and role-spoofing tests. No enterprise IAM claim. |
| R12 / P1 | Host concurrency was discussed but lacked its own scheduled acceptance task. Two orders can each pass the right formula while jointly exceeding the threshold; a withdrawal can invalidate the consent read. | T15 owns a synthetic transactional host with deterministic barriers, consent/release/exposure version checks and idempotent reservation. A13/A14 are engineering-MVP requirements, not deferred paper prose. |
| R13 / P2 | The backlog still said W00–W04 takes three weeks despite mandatory W03J; listed estimates sum to 17–25 engineer-days before new closure/host work. | Replaced by a provisional four-to-five-week block and re-estimation after M2. Twelve weeks is an allowance subject to scope/review capacity, not a promise. Pilot claims remain a separate stage. |
| R14 / P1 | Malformed/unhashable requests could be confused with schema-valid ERROR results that require request/bundle hashes. Dummy hashes would falsify identity. | T00 must freeze the separate boundary-error envelope; no zero/hash placeholder is allowed. Complete runtime responses retain exact request/result identities. T05/T08/T16 test both boundary and semantic failures. |
| R15 / P2 | Only the normative prose may change while `build_spec_examples.py` later regenerates obsolete schemas/fixtures. | T00 explicitly owns generator and generated-schema changes together; deterministic regeneration is a completion condition. No schema/code is silently upgraded by this planning task. |
| R16 / P1 | On a second task-graph read, T21 required scoped semantic comparison but initially lacked T18 as a dependency. | Added T18 to T21 in prose, diagram and JSON graph. Core closure includes all T00–T22 and excludes optional T23/pilot T24. |
| R17 / P2 | The demo check uses Python `assert`, an existing subset validator and build-directory assumptions. Its passing run under normal flags is not a hardened production acceptance runner. | Preserve the demonstration and classify evidence precisely. T08/T10 require explicit failing exits, complete validation, clean staging, malformed-response/hash rejection and stale-class tests. Claude is asked to inspect these limitations. |

No confirmed source-faithfulness defect was resolved by inventing a bank rule.
The proposed annual-review suspension remains explicitly bank policy; real PI
definitions, ownership/FX, calendars, freshness and review authority remain
owner decisions. Their absence blocks a bank release, not public-source T01.

## Concrete adversarial review

The plan was checked against inclusive threshold/OR mistakes, unknown alternatives,
static conflicts in skipped branches, multiple/default guard interactions,
exact/inexact money, future and late corrections, real engine hash differences,
late withdrawal and false completeness, overlapping releases, wrong binaries,
concurrent exposure reservations, idempotent retries, cancelled jobs, malicious
source/model text and amended definitions. These are A01–A16 in the plan.

The distinction between describing and implementing each case remains explicit.
The three invalid-reference probes are observed limitations of the current
checker. The cross-engine hash probe is a deterministic demonstration of the
identity consequence, not a run of a full product interpreter. Host races,
full language defaults, scheduler duties and real review transactions were
reviewed against their contracts; they were not executed because that application
does not exist.

## Actual validation

The existing spec checker passed: three valid schemas, 35 fixture contracts,
six negative examples, eight event structures, verified source anchors and SQL
creation. It correctly reports zero runtime decisions and no event/release
outcomes. This is engineering evidence about the supplied examples only.

The isolated Java run passed 32 decisions and eleven consent histories, detected
all three deliberately modified classes by outcome, rejected the unsupported
operator, invoked the separate host and reproduced fresh binary bytes. Fifteen
input/source/generated/binary hashes match the original verification record.
The run used local JDK 17.0.20.1 and CPU subprocesses; no model, network, GPU,
bank data or adjacent environment was used. The exact record is preserved rather
than reporting timing as performance superiority.

The plan checker validates the dependency graph, task headings, required-core
closure, acceptance mappings, local links, current review inputs and protected
original example/PDF identities. It is a document consistency check, not a
runtime or legal correctness test. Review status is explicitly Claude NOT_RUN.

The first plan check also caught a planning-tool defect: a multiline regular
expression captured section bodies as task titles, leaving machine-readable
acceptance text empty. The metadata extraction and checker were repaired to
bound titles to one line; every task was regenerated and checked against the
prose. The failed check is retained as `plan-check-initial-parser-failure.json`.
This was a task-metadata/checking failure, not evidence against the product design.

## Remaining work and strongest objections

The strongest remaining objection is that T00 could grow into unbounded design
work. Its output is therefore a fixed contract inventory: full request/result
identity, SDK errors, release/data/event schemas, missing API request/results,
fixed diagnostic templates and a conformance matrix. It may add a necessary
counterexample; it may not add arbitrary language features or reopen every
framework choice. If a bank decision is necessary, retain an owned issue and
continue independent contracts.

The main technical uncertainty is feature interaction across the full language,
event profile and host lifecycle. Independent source cases and carefully chosen
negative scenarios matter more than a growing fixture count. The greatest
epistemic weakness is a shared source interpretation behind both evaluators;
neither their agreement nor an eventual proof can replace compliance adjudication.

The plan remains feasible as staged engineering with scope control. It is not
an evidenced twelve-week commitment. Source discovery/attachments, temporal
normalization, cross-language trace identity and release transactions warrant
early review. The Claude memo explicitly asks for counterexamples to this
verdict and recommendations about which task may start if a later stage fails.

Human understanding, legal approval and business effectiveness are pending.
Their pending status must neither be hidden nor be turned into a blanket ban
on developing the public-source prototype.
