# LegalMath master implementation plan

Version 1.0 — 22 September 2026 — prepared for independent review.

**Readiness decision:** development can begin on the public-source prototype.
Start with T00, contract closure, then the isolated foundation and source import.
The existing Java demonstration proves a bounded route from reviewed rules to
executable Java. It does not constitute the workbench. Completing each milestone
requires the evidence below; production bank deployment is a separate project.

The user requested a master implementation plan. This document is the controlling
execution plan derived from proposal v0.3. The [review](../reviews/master-plan-review.md)
records the audit and repairs; the [Claude handoff](../reviews/claude-review-handoff.md)
requests an independent challenge. No Claude verdict is assumed. The
[task graph](master-plan.tasks.json) makes dependencies and status explicit.

## 1. Product, users and completion target

LegalMath is a local regulatory specification workbench for a Hong Kong private
bank. A compliance analyst opens a preserved SFC circular beside a proposed
interpretation, its required evidence and distinguishing client examples. An
engineer evaluates the same typed rules, sees exact reasons and source passages,
and generates a Java library. Designated reviewers approve a precise version.
An amendment produces a new version and an impact view while old decisions
remain reproducible.

The required bank-side output is a **Java 17 JAR**, generated deterministically
from reviewed RuleIR. Python supports authoring, storage, reference evaluation
and development checks. A Java decision must run without Python, a model,
MCP, a solver or a network service. The Java version is an explicit prototype
choice; a different bank version requires a separately tested target.

The first business profile is **23EC35, individual client, solicited transaction,
Annex 1 paragraph 8.3(a) execution monitoring**. The synthetic Ms Lee case is
the running acceptance story. Her HK$40m portfolio meets the inclusive financial
route while her HK$75m net assets excluding the home do not. Five appropriate
category transactions support one qualification route; the bank's reasonable
satisfaction, non-conservative objectives, category choice, documentation and
consent remain independent inputs. HK$8m plus the HK$2m proposed exposure reaches
the agreed HK$10m threshold. Withdrawal changes the subsequent consent result.

The prototype must preserve the whole circular inventory and visibly exclude
unimplemented profiles. Corporate ownership, unsolicited transactions and
designated-account monitoring are not silently approximated by this route.
Imported PI definitions, legal scope, source effectiveness, ownership/FX mapping
and assessments remain named interpretation/data tasks. Annual-review suspension
is a proposed bank restriction, not an invented automatic consequence of the
circular. A successful streamlining subcondition is never a trade authorization.

**Engineering MVP completion** means T00–T22 have their acceptance evidence,
including source/review UI, deterministic rules, Java export, consent/duties,
amendment replay, bounded comparison, corpus discovery, a drafting interface and
a synthetic host integration. Stub-based drafting proves the integration only;
usefulness of a live model is evaluated separately. T23 research adapters and
T24 the human/model comparative pilot are separate deliverables. Neither a
pending human study nor a failed optional adapter stops independent core work.

Excluded from this implementation scope: bank production connections, private
client data, enterprise IAM, automatic publication/deployment, business-day
calendars, unrestricted legal logic, general Stipula compilation, universal
compiler proofs and autonomous legal approval.

## 2. What exists and what must be built

| Component | Current state | Required change |
| --- | --- | --- |
| Proposal and literature | 66-page v0.3 PDF; 62 references; 38 retained PDF editions | Use as design/evidence background, not as proof that code exists. |
| Source snapshots | Actual 23EC35 main text and both annexes; other pilot circular snapshots | Build immutable import, source/dependency register, span verification and discovery. |
| RuleIR contracts | Three schemas, written semantics, 35 decision cases, six negative variants | Implement full validation, normalization, evaluator, traces and result identity. |
| Fixture checker | Checks supplied structure, selected references/types, source and SQL | It is not the production validator; three invalid-ID/source probes currently pass it. |
| Java example | SPI-Demo1, ten Boolean rules, 32 decisions, eleven consent histories, three compiled mutations | Preserve as regression evidence; implement all RuleIR operators, full responses and event projection. |
| Storage/review/API | Proposed SQL and written contracts | Implement missing lookup relations, migrations, transactional lifecycle, local identities and endpoints. |
| UI, solver, drafting, adapters | Design and fixtures | Implement in dependency order; keep optional research outside transaction execution. |
| Bank host | A separate synthetic JAR caller | Add a synthetic transactional adapter proving reservation, stale-consent and idempotency behavior. |

The existing 35 decision cases and eight event histories have **not** run against
the full planned runtime. The four release examples check only named premises
and lack binary-identity/concurrency cases. Do not count them as a completed
release engine. Existing schema-generated expected projections are starting
examples, not the only oracle for source fidelity or trace correctness.

The original proposal PDF and original Java evidence remain unchanged by this
planning task. [Audit evidence](../reviews/master-plan-evidence/README.md) records
an isolated rerun and the inspected baseline. The proposal is background when a
later, explicitly dated implementation clarification differs from its wording.
User requirements and regulatory sources retain their own authority; a software
plan cannot settle a disputed legal interpretation.

## 3. Architecture and ownership boundaries

```text
Preserved circulars/annexes -> clauses + dependency register
                                       |
                         proposed interpretations + issues
                                       |
                         typed RuleIR + dated evidence
                          /                        \
               Python reference             generated Java + runtime
                          \                        /
                           cases + traces + comparison
                                       |
                       exact-version review and release
                                       |
               Java host adapter + other bank controls

Immutable event log -> Python/Java replay -> consent and duty assessments
Drafting and bounded search propose work; they cannot approve a release.
```

Create the module tree in [work-packages.md](work-packages.md). Keep expression
evaluation pure. Put I/O, identity selection, normalization, approval, scheduling,
model calls and solver jobs at explicit boundaries. The same immutable facts and
rule version must reach the reference and Java implementations.

| Boundary | Interface and owner | Required failure behavior |
| --- | --- | --- |
| Source import | `import_source(SourceImport) -> SourceRevision`; source module | Changed bytes create a new revision; missing annex/dependency remains an issue. |
| Interpretation | `RuleBundle`, `Interpretation`, `Issue`; meaning reviewer | Unresolved material interpretation blocks its release, not unrelated source intake. |
| Fact normalization | `normalize(records, declarations, subject, valid_at, known_at)`; data adapter | Missing, stale and conflicting evidence stay distinct; no guessed FX/ownership. |
| Reference decision | `evaluate(bundle, snapshot, rule_id, valid_at, known_at, mode)` | Exact tagged result, deterministic trace and diagnostics; no model/network calls. |
| Java generation | `compile_java(bundle, target_release) -> JavaSourceTree` | Unsupported constructs fail before build; no model-written Java fragments. |
| Java execution | `CompiledRuleSet.evaluate(FactSnapshot, RuleId, AssessmentContext)` | Same semantics as reference; explicit technical failure at the host boundary. |
| Event replay | `replay(stream, valid_at, known_at, profile_version)` | Unknown completeness/order cannot become consent or a proven breach. |
| Review/release | `transition(...)`, `release(...)`; local review service | Exact hashes, independent identities, optimistic revisions and atomic audit. |
| Host transaction | `evaluate_and_reserve(order, idempotency_key)`; synthetic adapter | Recheck consent/exposure/release versions atomically; bounded retry then review. |

The implementation engineer owns code and conformance; a technical reviewer
owns semantic/compiler review; a compliance owner owns source interpretation
and scope; operations/data owners own evidence mappings; an independent reviewer
owns the pilot oracle. One person may develop the local demonstration, but its
synthetic reviewer identities do not establish real independent approval.

## 4. Engineering decisions that must not be invented during coding

### 4.1 Expressions, evidence and errors

RuleIR 0.1 is a finite acyclic language with Boolean, arbitrary integer, HK-cent
money and Gregorian-date types. Operators are literal, fact, unconditional rule
reference, all/any/not, same-type comparisons, add/sub, exact rational scale,
conditional and nested defaults. Unknown is not false or zero. All/any evaluate
every child in order: an error or conflict cannot disappear behind a sufficient
Boolean branch. `if` evaluates only its chosen value; an unknown guard returns
unknown even if its branches agree. Multiple true sibling exception guards
conflict even when their values match; an unresolved competing guard can block
the otherwise applicable value.

Validate all declarations and the static transitive dependency closure, including
scope and skipped branches. An input conflict in that closure takes precedence
over Boolean evaluation. Unrelated conflicts do not block a rule. Every fact
has explicit evidence, validity and recording time; both assessment times are
inputs, not clock reads. `[from, until)` excludes the endpoint. The authoritative
details are in [semantics.md](../specs/v0.1/semantics.md), with the full
[service contract](../specs/v0.1/contracts.md).

T00 freezes deterministic error-stage order and message templates. T05 validates
duplicate **source-span and interpretation IDs** as well as fact/rule/node IDs;
it checks source links inside every interpretation and exception. The current
fixture helper misses those three negative examples. Do not import that helper
as the finished product validator.

Malformed JSON/transport is rejected with structured diagnostics before any
decision is trusted. No invented all-zero digest stands in for unhashable input.
T00 specifies an SDK input exception for a request that cannot produce the
declared request identity; schema-valid executions still return the full tagged
EvaluationResult. Maintain the existing invalid-fixture distinction between
input validation and rule execution.

### 4.2 Deterministic identity and comparison across Python and Java

Canonical JSON uses ASCII object keys sorted by code point, original array order,
UTF-8, no implicit Unicode normalization, exact decimal-string domain amounts,
and no floats, duplicate keys or unpaired surrogates. Store canonical-byte test
vectors, including control characters and supplementary Unicode. Python's JSON
output is a useful reference, not a reason to accept a different Java escaping
or duplicate-key policy.

For a complete result, build the request object with exactly `bundle_hash`,
`snapshot_hash`, `rule_id`, `mode`, `valid_at`, `known_at`, `engine_version`.
Build the semantic result object with exactly `status`, `type`, `mode`,
`diagnostics`, optional `value`, `reason_codes`, `missing_inputs`,
`blocking_inputs`, `trace`. The result hash is
`sha256(canonical_v1({"request": request, "result": semantic_result}))`.
Record real, different engine identities, including their code/version digest.

Two backends may therefore produce **different execution hashes for the same
answer**. Compare every complete response field except `engine_version` and
`result_hash`; independently reconstruct each of those hashes using its real
engine identity. Reject any difference in status, diagnostics, value, source/node
trace, evidence, missing/blocking inputs, times, mode or common input identities.
Do not make Java impersonate the Python engine to obtain equal hashes. Within
one backend/version, replay of the same request must reproduce its hash.

The SPI-Demo1 demonstration has its own smaller result/hash protocol. Preserve
that regression suite; migrate scenarios into full RuleIR responses without
pretending their old response bytes already implement this contract.

### 4.3 An acyclic build, evidence and release sequence

Use four immutable records in this order:

1. **JavaBuildManifest:** bundle/source/generated-code/runtime digests, compiler
   identity, Java target, dependencies/licenses, build command and JAR digest.
   It contains no test-report, release-manifest or approval hash.
2. **VerificationReport:** exact build-manifest and JAR digests, reference identity,
   test corpus, actual commands, checks/results and failure details. It does not
   name a future release manifest or approval.
3. **JavaReleaseManifest:** build-manifest hash, verification-report hash, supported
   profile, reviewed applicability and effective interval. Its digest can now
   be computed without a cycle.
4. **ReleaseRecord:** immutable Java-release-manifest and bundle hashes, two
   reviewer decisions, authority profile, activation/retirement history and
   audit/revision references. Approval is outside the bytes being approved.

Build candidate source/JAR before approving release. Use a separate
`build-java` operation for a draft candidate; `export-java` exports a reviewed
release. Draft evaluation and candidate compilation must not require a release
that depends on tests that have not yet run. The result record and UI distinguish
`LOCAL_SYNTHETIC` authority from bank deployment authorization. Passing
`mode=production` tests the lifecycle path in the prototype; it does not create
bank authority.

### 4.4 Fact normalization, events and persistence closure

An accepted correction names an existing record for the same subject, fact and
type. T00 settles supersession as interval-local: a correcting record suppresses
its predecessor only where the correction is known and its validity covers the
assessed instant. Outside that intersection the predecessor remains available.
Cycles, cross-subject targets and unresolved correction targets are errors or
quarantined issues, not silently applied replacements. Identical admissible
values combine evidence; different values conflict. Test a correction that is
known now but becomes valid tomorrow, and a late correction to yesterday.

For consent, completeness must cover inception or a reviewed initial snapshot
through the assessed time, and be recorded by the knowledge cutoff. An assertion
cannot cover a time later than its own recording time. The same no-future rule
applies to obligation watermarks. Full replay must validate stream identity,
actor/subject/category, positive unique sequence numbers and declared ordering
authority. The small demo assumes its caller has supplied one correctly attributed
stream; that assumption is not a full event-ingestion implementation.

The supplied SQL is a starting layout, not all required persistence. T00/T02 add
versioned definitions for source dependencies/derivatives, fact records and
supersession, applicability, authorship/reviewer identity, release records,
build/evidence associations, stream headers and source-backed obligation
templates. Immutable payloads may remain JSON blobs; all fields needed for unique
release selection, referential integrity and concurrency need indexed relations
or validated transactional queries. Forward migrations and fresh-database replay
are required. Do not hide missing state in process memory.

### 4.5 Services and jobs

Implement the existing source, bundle, review, release, evaluation, event and
comparison endpoints. Add explicit entry points for creating streams, submitting
normalized snapshots or fact records, proposing drafts and retrieving/cancelling
jobs. T00 freezes their request/result schemas, size limits and fixed diagnostics;
T16 publishes the resulting OpenAPI contract. A stored job without a way to
retrieve its result is incomplete.

Use `POST /v1/event-streams`, `POST /v1/fact-records`,
`POST /v1/snapshots`, `POST /v1/drafts`, `GET /v1/jobs/{id}` and
`POST /v1/jobs/{id}/cancel` for those additions. A draft request returns 202 and a
job ID. GET returns state plus a result hash or diagnostics. Cancellation is
idempotent, stops bounded work and never partially updates a bundle. Job failure,
timeout or cancellation confers no verification or review authority.

Bind localhost, use public/synthetic data and a local configured identity registry.
The service resolves the caller's permitted roles; a request body cannot appoint
itself a compliance approver. Escape source/model text in HTML; reject path
traversal, private-network redirects, oversized inputs and attempts to invoke
tools from document contents. Budget violations are explicit unsupported/manual
tasks; no truncation may masquerade as a complete circular or proof.

## 5. Milestones and dependency graph

| Milestone | Tasks | Demonstrable exit |
| --- | --- | --- |
| M0 — frozen starting contract | T00 | Closed engineering choices, adversarial cases and versioned contract inventory. |
| M1 — preserved source and typed evidence | T01–T06 | One actual circular and both annexes, verified passages, typed rules and dated evidence. |
| M2 — deterministic reference and Java decisions | T07–T10 | Full decision conformance, separate Java caller, reproducible candidate JAR and build/evidence identities. |
| M3 — review, history and host behavior | T11–T15 | Exact-version lifecycle, consent/duties in both runtimes and synthetic transactional host. |
| M4 — reviewable workbench | T16–T17 | Source-to-decision screens, APIs, jobs and inspectable historical results. |
| M5 — bounded assistance and change handling | T18–T21 | Counterexamples, complete pilot discovery, safe candidate drafting and amendment replay. |
| M6 — engineering MVP acceptance | T22 | Fresh installation, full dry run, export/replay and every core acceptance condition evidenced. |
| M7 — optional research and business evaluation | T23–T24 | Scoped adapter evidence and a separately registered comparative pilot. |

Core order:

```text
T00 -> T01 -> T02 -> T03 -> T04 -> T05 -> T06 -> T07 -> T08
                                                          |
                                                        T09 -> T10 -> T11 -> T12
                                                                                 |
                                                                               T13 -> T14 -> T15
                                                                                       |
                                                                                     T16 -> T17
T08 + T12 -> T18              T04 + T16 -> T19
T17 + T19 -> T20              T12 + T14 + T18 + T19 -> T21
T15 + T17 + T18 + T20 + T21 -> T22 -> T24
T18 + T20 -> T23 (optional)
```

The machine task graph is authoritative for individual edges. Branches describe
independent work, not an instruction to spawn agents. A single implementing
agent follows topological order. The first release is decision-only; event-aware
release tests are added after T14. This removes the prior ambiguity in expecting
full event conformance from the decision backend before W05 exists.

## 6. Task specifications

Existing W00–W10 work packages remain detailed module references. T00–T24 below
give the master sequencing, add missing integration tasks and define evidence.
Each task records its actual commands and output paths under
`artifacts/runs/<task-id>/<run-id>/`; task completion updates the task graph only
when the named criteria pass. All task output paths below are **planned** unless
explicitly identified as existing in section 2.

### T00 — Close contracts before runtime work

No dependencies; maps to preparation for W00–W05. Freeze the section 4 resolutions
in normative contracts and schemas, including full result hashing, malformed
input handling, release record DAG, interval-local corrections, event/replay
schemas, storage additions and missing API operations. Update
`scripts/build_spec_examples.py` together with its generated schemas/fixtures;
regenerating old templates must not erase corrections. Create an operator/type/
error conformance matrix and individually named adversarial cases A01–A16 below.
Exit: no conflicting definition remains across master plan, contracts, generator
and task graph; fresh schema regeneration is stable. Open bank/legal questions
have owners and block only dependent legal release. Evidence: contract inventory,
change rationale, schema/fixture checks and reviewer disposition.

### T01 — Isolated application package and toolchain

Depends T00; W00. Create `pyproject.toml`, `src/legalmath`, a `.venv` using Python
3.11 and a pinned dependency/constraints file. Record exact versions and licenses
for JSON Schema, FastAPI/Pydantic, HTTP/PDF/UI packages and test dependencies.
Use the verified local JDK 17 or record/verify another explicit JDK. Add a CLI
entry point, offline smoke test and continuous-test command. No installs into
adjacent repositories or `tfgpu`. Exit: a clean environment installs the locked
application and runs import/CLI checks; a dependency manifest is preserved.

### T02 — Canonical JSON, blobs and database

Depends T01; W00. Implement `canonical.py`, `storage/blobs.py`, migration 001 and
transaction helpers. Reject duplicate JSON keys, floats, bad Unicode and out-of-
range transport integers. Write/fsync/rename immutable blobs before committing
references; never overwrite content. Add the T00 storage relations. Exit: golden
bytes agree across fresh Python processes, corrupt/missing blobs fail, migrations
are repeatable, foreign keys work, and interrupted writes leave no committed
missing references. Orphan cleanup is a separate explicit maintenance operation.

### T03 — Offline circular intake and exact anchors

Depends T02; W01. Import preserved 23EC35 main text and both annexes; retain URLs,
bytes, extraction configuration, page boundaries and code-point offsets. Reproduce
the supplied paragraph 3.1 anchor and all used SPI source spans. Extraction repair
creates a new derivative. Exit: changed source bytes, wrong page/offset, missing
annex and HTML-instead-of-PDF are detected; source register and original-page
display input are reproducible. Scanned/OCR passages need a recorded visual check
before release. Network pagination belongs to T19, not this first import.

### T04 — Definitions, scope and provision coverage

Depends T03; W01/W04. Turn the existing circular disposition inventory into
persisted clause rows, dependency edges and interpretation issues. Every provision
has implemented rules, reviewed input mapping, human task, outside-profile reason
or unresolved status. Retain imported PI/source dependencies. Exit: removed annex
paragraphs and unresolved definitions block affected releases; a product-provider
rule is not automatically assigned to a distributor; source and bank-policy
authority remain distinct. Output a reviewer-readable inventory, not an LLM-only
coverage denominator.

### T05 — Full AST loading and semantic validation

Depends T04; W02. Implement typed immutable domain values, strict JSON decoding,
schema loading without remote resolution, name/source checks and acyclic graphs.
Validate all identifiers, actual calendar dates, scalar values, source references
and unconditional referenced scopes. Avoid repeated exponential graph traversal;
memoize completed nodes and enforce declared resource limits. Exit: existing six
negative cases plus duplicate source/interpretation IDs, unresolved interpretation
spans, direct/indirect cycles and malformed Unicode/date/numeric values are
rejected with stable codes/pointers. Accepted nodes have declared types.

### T06 — Dated evidence normalization

Depends T05; W02. Implement immutable FactRecord storage, interval/knowledge
selection, interval-local supersession, explicit unknown reasons and conflicts.
Never collapse missing evidence into false or choose the latest contradictory
record by arrival order. Exit: exact expiry, late corrections, future-valid
corrections, identical-value evidence merging, correction cycles/unknown targets
and cross-subject corrections behave as specified. A known selected value can
be explained from preserved evidence and its contributing records.

### T07 — Full reference evaluator

Depends T06; W03. Implement every accepted RuleIR operator and static conflict
closure, scope, eager all/any, conditional skipping and default selection. Money
and integers are exact; scale rejects nonzero remainders. Exit: all 35 full-language
cases execute through `legalmath.conformance:evaluate_case`, including unknowns,
equal-valued exception conflicts and inexact arithmetic. Add interactions such
as an eager sibling error, a skipped but conflicting input, empty exception list
and negative exact scaling input. No external tool is called during evaluation.

### T08 — Trace, identity and independent decision oracle

Depends T07; W03. Implement complete postorder node traces, one skipped-root
marker per skipped branch, shared-reference memoization, deterministic errors,
source inheritance and result hashing. Independently reconstruct hashes from
stored requests and results. Extend the projection-only fixture harness with
full trace and result-invariant checks; do not merely have two evaluators copy
the same bad trace. Exit: altered evidence/source links, child ordering, skipped
roots, duplicate nodes, blocking sets and forged hashes fail. Preserve manually
derived boundary outcomes as a separate oracle from generated tests.

### T09 — Full deterministic Java backend

Depends T08; W03J. Implement emitter and immutable Java API/runtime for the full
operator/type/error contract. Use BigInteger and validated LocalDate; match exact
scale and timestamp rules. Explicitly reject unsupported versions, operators or
limits. Exit: all 35 cases and migrated 32 SPI scenarios agree by section 4.2,
with real backend identities and independently checked execution hashes. Compile
the three outcome-changing mutants and demonstrate detection. Test type/malformed
inputs and invoked non-Boolean rule results. Keep narrow-demo regressions separate.

### T10 — Candidate build and portable Java evidence

Depends T09; W03J/W04. Build from an empty staging directory, compile with declared
`--release`, package deterministic JAR entries, and compile a separate caller
against the exact resulting JAR. Implement build manifest then verification report;
publish neither as a legally approved release. Exit: fresh rebuild hashes match,
injected stale class files cannot leak into the JAR, wrong toolchain/target is
visible, and Java executes without Python or model services. Evidence names the
actual JAR tested. Normalize build paths/timestamps only under documented rules.

### T11 — Review lifecycle and local role enforcement

Depends T10 and T04; W04. Implement immutable draft lineage, review/rejection,
exact-hash approvals, author separation, issue/dependency checks and optimistic
revision transactions. Synthetic roles come from the configured local registry.
Exit: self-approval, forged body roles, edited-after-approval bytes, unresolved
dependency, concurrent stale review and incorrect evidence hashes fail. Every
accepted change has an atomic audit record. Explicitly mark synthetic review
authority; do not present it as compliance adjudication.

### T12 — Release selection, export and historical import

Depends T11; W04. Implement the four-record release sequence, effective/applicability
selection and export/import into a fresh database. Legal validity and operational
deployment history are separate: preserve both which rule applied and which
binary actually ran. Exit: absent/overlapping applicable release, wrong JAR/report,
retired new-use request, stale activation revision and tampered package are
rejected. Historical replay uses its recorded version and evidence. Rollback
repairs implementation; it cannot revive a superseded legal rule automatically.

### T13 — Full event ingestion and Python replay

Depends T12; W05. Implement stream headers, attributed immutable events,
completeness assertions, ordering authority, consent generations, achievement
duties and explicit anniversary policies. Retain observations that a control
would have disallowed. Exit: eight existing event scenarios execute, plus late
timely evidence, duplicate/colliding IDs, sequence conflicts, unknown deadlines,
future seals, wrong subject/actor/category and February 29 policies. Without a
complete observation window, absence does not establish breach. Opening source
version remains attached to an obligation unless a reviewed migration exists.

### T14 — Java event projection and decision composition

Depends T13 and T09; W05/W03J. Implement the same replay in Java and version the
event runtime separately in build/release records. Feed projected consent and
duty assessments into the typed decision snapshot with evidence references.
Exit: complete replay results agree across languages, the eleven narrow consent
regressions remain visible, and withdrawal/regrant/late-evidence end-to-end cases
reach the correct generated decision. Passing a consent Boolean alone does not
complete the full attributed event contract. Release tests now cover both components.

### T15 — Synthetic host transaction protocol

Depends T12 and T14; Java integration acceptance. Build a test host with versioned
release, consent, holdings and outstanding reservations. Evaluate outside or
inside its transaction as designed, then atomically validate versions, reserve
exposure and append the decision. Use an explicit barrier to force simultaneous
orders in tests, not probabilistic sleeps. With HK$8m exposure and two HK$1.5m
orders under HK$10m, at most one may reserve that route. Exit: concurrent withdrawal,
release change, changed retry payload, duplicate retry and exhausted retries
produce specified outcomes. This tests a synthetic adapter, not the bank's systems.

### T16 — Service API, jobs and integration boundaries

Depends T12 and T14; W06. Implement all section 4.5 endpoints and existing
contracts, persisted job transitions, cancellation and restart recovery. Keep
pure evaluation outside transport types. Exit: malformed requests have documented
HTTP errors, semantic ERROR is distinct, idempotency/revisions survive restart,
job results can be retrieved, timeouts confer no proof, and local role checks are
enforced. Store OpenAPI/request/response snapshots and path/resource-limit tests.

### T17 — Source/rule/case/amendment reviewer screens

Depends T16; W06. Present original passage, interpreted condition, required
evidence, unresolved questions and a distinguishing example together. Derive
diagrams from the adopted AST/trace; show unknown/conflict/error without success
styling. Exit: browser/keyboard checks, escaped hostile text, exact cents-to-HKD
formatting, source revision links and historic decision views work. Record an
engineering walkthrough. Human understanding/usability remains pending until
a compliance reader completes a separate walkthrough; it does not block later
offline engineering tasks.

### T18 — Bounded solver comparison

Depends T08 and T12; W07. Encode only the declared Boolean/integer/money fragment,
including knownness. Check nonempty domains before difference queries; replay
counterexamples in both implementations. Exit: strict-boundary and OR-to-AND
differences are found, `A or not A` differs from true for unknown A, and timeout,
empty domain, unsupported date/default/event/scale constructs remain explicit.
Use exhaustive tiny T/F/U domains as an independent encoding check. An unsat
answer is solver evidence, not a replayed proof certificate.

### T19 — Pilot corpus discovery and changes

Depends T04 and T16; W08. Add bounded official-host fetch, pagination/cursor state,
deduplication, attachment/dependency changes and the five pilot circulars.
Use captured responses for deterministic tests; separately record one permitted
live refresh when needed. Exit: repeated pages, deleted attachments, changed
bytes, no-result/fetch-error distinction and private-network redirects are
handled. 25EC48 remains a review announcement, not an invented numeric rule;
23EC53/26EC22 retain their replacement relationship. Discovery coverage is not
the bank's complete regulatory perimeter.

### T20 — Candidate drafting with a deterministic stub first

Depends T17 and T19; W08. Implement provider-neutral structured candidate input/
output, source inventory, alternatives, missing definitions, schema validation
and bounded repair. Drafts cannot write review/release records. Exit: a stub
provider exercises success, malformed output, missing citation, repeated repair,
timeout and prompt injection. Preserve model configuration/prompts/costs when a
real provider is later enabled. Three repeated model suggestions are not three
independent legal opinions. Live model quality belongs to T24.

### T21 — Amendment impact and historical replay

Depends T12, T14, T18 and T19; W04/W08. Combine source/definition dependencies, typed
structural differences and scoped semantic comparisons. Renumbering changes an
anchor; it does not alone prove unchanged meaning. Exit: changed definition
invalidates dependent evidence, new approvals bind the new bundle/JAR, original
decisions reproduce, ongoing obligations retain their opening version, and
unsupported migration stays an issue. Exercise actual tokenisation replacement
metadata and a clearly synthetic SPI threshold/consent amendment separately.

### T22 — Engineering MVP acceptance

Depends T15, T17, T18, T20 and T21; W10 engineering portion. Run the fresh-install,
offline complete Ms Lee dry run: intake, rule review, synthetic approval,
evidence, Java candidate tests, release export, separate host, withdrawal,
amendment and original-result replay. Record all failures and pending human
questions. Exit: all core acceptance rows pass; no unresolved critical source,
identity, numeric, event, review or release defect is hidden by averages. Export
and restore into a new working directory. Report `ENGINEERING_MVP_COMPLETE` with
synthetic authority, remaining legal scope and human usability explicitly pending.

### T23 — Optional research adapters

Depends T18 and T20; W09; optional. Implement isolated ResearchAssistant parsing,
exact-target MathDevMCP evidence and only justified Dynare-style investigation
scheduling. Pin interfaces/versions and distinguish structural checks, tests,
solver answers and checked proofs. Exit per enabled adapter: captured-contract
tests plus one bounded real invocation, or explicit NOT_RUN with cause. MCTS/UCB
needs its own question and baseline; search score never grants interpretation
authority. Optional failures leave the core workbench usable.

### T24 — Human/model pilot and investment decision

Depends T22; W10 research portion. Before comparing methods, register source
access, human roles, task families, independence, budgets and uncertainty analysis.
Compare current manual work, a grounded summary, human-authored RuleIR and assisted
RuleIR under equal information. Count rule preparation and review time. Keep
held-out circular families out of development prompts. Exit: independent
adjudication, complete outcomes/abstentions, paired uncertainty or an explicit
descriptive-only conclusion, costs and a scoped investment decision. Insufficient
reviewers/families blocks claims about effectiveness, not engineering completion.

## 7. Acceptance matrix and adversarial cases

These conditions are a specification to implement. Existing results in section 2
do not discharge future tests automatically. T00 assigns stable test filenames
and preserves each independent expected outcome before writing its implementation.

| ID | Required distinguishing case | Owner task / failure meaning |
| --- | --- | --- |
| A01 | Source bytes or extracted paragraph change while an old anchor is reused | T03/T04: reject identity mismatch and affected release. |
| A02 | Duplicate span/interpretation IDs or an interpretation cites a missing span | T05: reject; the current fixture helper accepts these probes. |
| A03 | HK$40m inclusive boundary; HK$35m/90m alternative; one-cent changes | T07/T09: exact outcomes; strict-comparison and OR-to-AND mutants fail. |
| A04 | Missing portfolio with sufficient versus insufficient net assets | T07/T08: known success versus unknown; distinct missing/blocking sets. |
| A05 | Conflict in a skipped static dependency; unrelated conflicting fact | T07: first conflicts; second leaves the requested rule unchanged. |
| A06 | Two equal-valued active exceptions; unknown competitor; empty defaults | T07/T09: conflict, unknown and base value respectively. |
| A07 | Inexact scale and an eager sibling error; unknown conditional with equal branches | T07/T09: exact error/unknown semantics, no optimizer simplification. |
| A08 | Same semantic response under different engine identities; forged execution hash | T08/T09: compare semantic fields, verify native hashes, reject forgery. |
| A09 | Expiry endpoint; future-valid correction; late correction; wrong-subject supersession | T06: correct temporal selection and explicit validation failure. |
| A10 | Withdrawal arrives late; incomplete stream; future completeness claim; sequence collision | T13/T14: knowledge-aware replay, unknown or explicit error, never inferred active consent. |
| A11 | Timely performance, exact-deadline performance and missing observation watermark | T13/T14: on-time, late-with-supported-breach, and open/unproven breach as specified. |
| A12 | Correct bundle approved but wrong JAR, stale evidence, self-approval or overlap | T11/T12: reject release; no circular manifest/report dependency. |
| A13 | Two simultaneous HK$1.5m orders from HK$8m under HK$10m; simultaneous withdrawal | T15: atomically reserve at most one; stale consent cannot be consumed. |
| A14 | Same idempotency key/payload versus same key/changed payload; restart mid-job | T15/T16: repeat result, conflict, recover/cancel without partial authority. |
| A15 | Superseded source, changed definition and existing obligation | T21: dependent change review; original result and opening-version duty retained. |
| A16 | Malicious source/model text, SSRF redirect, empty solver domain and timeout | T16/T18/T19/T20: inert text, bounded failure, no fabricated approval/equivalence. |

For a task to pass, compare expected outcomes and required trace/evidence
properties. Case count, code coverage, mutation percentage, schema acceptance
and successful compilation are supporting diagnostics, not substitutes for those
criteria. A failure blocks promotion of the affected component and triggers
repair/retest. Preserve a minimal reproducer and do not remove a hard case to
make the stage pass.

## 8. Commands, artifacts and running discipline

Commands that exist **now**, from the repository root:

```sh
python3 scripts/check_spec_pack.py
python3 examples/java-dry-run/build_and_verify.py \
  --jdk .localresources/java-toolchain/jdk-17.0.20.1+1
```

The second regenerates demo outputs. For review without changing the historical
verification record, copy its directory, `docs/specs/v0.1`, the fixture checker
and retained SFC sources to a temporary workspace first, as in the audit evidence.
The first command validates fixtures; it currently executes zero full-runtime
decisions.

Planned application commands after the corresponding tasks (these do not exist
yet and are not recorded as run):

```sh
# T01: after pyproject.toml and locked requirements exist
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-deps -e .

# T03 / T07 / T08
.venv/bin/legalmath sources import --manifest corpus/sources/pilot.json
.venv/bin/python scripts/check_spec_pack.py --runtime legalmath.conformance:evaluate_case
.venv/bin/python -m pytest tests/unit tests/conformance -q

# T10: build a candidate before approval; HASH names actual immutable bytes
.venv/bin/legalmath build-java --bundle-hash HASH --target-release 17 --out artifacts/candidates/HASH

# T12: export an already reviewed release
.venv/bin/legalmath export-java --release-hash RELEASE_HASH --out artifacts/releases/RELEASE_HASH

# T22: fresh-install/host/workbench acceptance
.venv/bin/python -m pytest tests/integration tests/security -q
.venv/bin/legalmath acceptance --scenario spi-23ec35 --offline --out artifacts/acceptance/spi-23ec35
```

Every task result records source/contract versions, exact command/environment,
inputs, outputs, checks, failures, interpretation and next justified action. Use
the [result template](../plans/templates/experiment-result-template.md) and
[reset memo template](../plans/templates/reset-memo-template.md). For a genuine
model/human comparison, first fill the
[experiment plan](../plans/templates/experiment-plan-template.md), including
baseline, primary criterion, vetoes, repair triggers and what cannot be concluded.
Ordinary compile/unit checks do not require an invented research experiment.

Fresh contexts read START-HERE, this plan, task status and the latest result memo.
Recheck saved hashes before relying on old evidence. Resume the first unfinished
task whose dependencies passed; do not repeat completed tests without a change,
failure or unresolved concern. No commit, remote publication or external review
submission is implied merely by completing a local task.

## 9. Budget, defaults and human decisions

The proposal's twelve weeks is a planning allowance, not a forecast established
by measured development. The older three-week W00–W04 paragraph is obsolete:
including W03J, the existing estimates total roughly 17–25 engineer-days before
new contract/host work. Use a provisional **four-to-five-week** foundation/Java/
release block, four-to-five weeks for event/UI/assistance and two weeks for
integration/review, subject to scope and reviewer availability. The pilot may
extend beyond that envelope. Re-estimate after M2 using actual completed tasks;
do not weaken semantics or independent review to preserve a calendar promise.

| Choice | Provenance / status | Failure mode and first diagnostic |
| --- | --- | --- |
| Python 3.11, Java 17, SQLite/local service | Proposal and demonstrated JAR; engineering baseline | Environment mismatch; T01 clean install and T10 separate caller. |
| Exact cents, conservative static conflict and finite AST | Explicit semantics, not a financial model claim | Wrong data mapping or incompleteness; A03–A09 and independent source cases. |
| 20 MB document / 30-second fetch | Existing engineering budgets, configurable | Valid source excluded; show manual-import work and coverage gap in T19. |
| 10-second / 10,000-node solver budget | Convenience default, not evidence of equivalence | Timeout/large graph; explicit UNKNOWN/UNSUPPORTED and small exhaustive checks. |
| Two repair attempts, three drafts/clause, ten analyses | Budget hypotheses | Useful candidate missed; preserve failure/alternatives and evaluate in T24. |
| Two reviewer roles and synthetic local identity | Prototype governance choice | Mistaken enterprise-authority claim; A12 and visible authority profile. |
| 30 pilot tasks, 10 development / 20 held out | Feasibility hypothesis, not power calculation | Too few independent families; expand corpus or report descriptive-only evidence. |

Pending bank choices do not block public-source development: actual Java/framework
version, bank legal perimeter, PI/ownership/FX/freshness mappings, calendar
interpretations, review owners, release authority, retention and production data
interfaces. They **do** block a corresponding bank release or empirical claim.
Record them as issues with scope and owners; never fabricate approvals to complete
a milestone.

## 10. Readiness and next action

Begin T00, then T01–T03. The first reviewable increment is immutable 23EC35 and
its annexes with verified anchors and typed, dated evidence. The second is a
full-language reference/Java decision with independently checked results. This
sequence gives the implementing agent concrete work while preserving the user's
requirement that the final transaction component is Java.

The plan has had the author audit described in the review record. Independent
Claude review, human comprehension and legal adjudication remain distinct
pending evaluations. A reviewer should identify specific blocking tasks and
counterexamples; a global claim that “formal methods prove compliance” is not
an acceptance criterion anywhere in this plan.
