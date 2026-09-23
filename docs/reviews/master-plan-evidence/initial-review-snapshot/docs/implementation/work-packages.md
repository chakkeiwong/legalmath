# Implementing the LegalMath public-source prototype

This backlog implements the versioned specification in `docs/specs/v0.1/`.
Commands below W00 are **future acceptance commands** for the complete product.
The separate [SPI-Demo1 Java demonstration](../../examples/java-dry-run/README.md)
is executable now, but does not implement every RuleIR operator or product module. Today `python3 scripts/check_spec_pack.py` checks
the specification pack. Do not report that as runtime implementation completion.
Each work package ends with a runnable slice, a result note and preserved inputs.
Java delivery is mandatory: W03J follows W03 and is a dependency of W04.

The [master plan](master-plan.md) now controls task order and readiness. Its
T00–T24 tasks refine these W packages, close identity/release ambiguities and add
the synthetic transactional Java host. Use the machine task graph for dependencies.

## Environment and layout

W00 creates a new project-local Python 3.11 virtual environment. Do not install
dependencies into MathDevMCP, DynareMCP, ResearchAssistant or the existing `tfgpu`
environment. Pure CPU document/logic work requires no GPU libraries.

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest tests/unit -q
```

Create `pyproject.toml` with Python `>=3.11,<3.12`, `jsonschema`, `pydantic`,
`fastapi`, `uvicorn`, `httpx` and `pypdf`; development dependencies `pytest`,
`hypothesis`, and optional `z3-solver`. Resolve compatible exact versions in W00,
write a lock/constraints file, record Python/SQLite/Poppler versions and license
identifiers, then use that lock for every run. These names are stack choices, not
a claim that their newest versions have been tested here. Use standard-library
`decimal`, `datetime`, `zoneinfo`, `hashlib` and `sqlite3`. PDF text extraction uses
pinned Poppler or the isolated ResearchAssistant adapter; record which path ran.
Initial UI: server-rendered Jinja2 HTML with static JavaScript for rule trees.
Add Jinja2 in W00. No graph database, message broker, vector database or frontend
framework is needed for this corpus. Persist bounded jobs in SQLite.

```text
src/legalmath/
  canonical.py, domain.py, errors.py
  sources/{fetch,extract,anchors,dependencies}.py
  ir/{load,typecheck,graph,normalize,evaluate,trace}.py
  events/{records,consent,obligations,replay,calendar}.py
  review/{lifecycle,coverage,amendment}.py
  storage/{database,blobs,migrations/001.sql}.py
  analysis/{domain,z3_encode,compare,mutations}.py
  drafting/{provider,prompts,validate,repair}.py
  adapters/{research_assistant,mathdev,dynare,export}.py
  java/{emit,manifest,conformance}.py
  api/{app,models,routes}.py
  web/{templates,static}/
  cli.py, conformance.py
java-runtime/src/main/java/hk/legalmath/{api,values,trace,events}/
java-runtime/src/test/java/hk/legalmath/
tests/{unit,conformance,integration,security}/
corpus/{sources,interpretations,reviewed_cases}/
artifacts/{runs,releases,comparisons}/
```

## W00 — Reproducible shell and immutable bytes (one to two engineer-days)

Dependencies: none. Implement package, CLI entry point, canonical JSON and blob
storage. Copy `storage.sql` into migration 001 with an explicit migration version.
Functions: `canonical_v1(value)->bytes`, `digest(value)->str`,
`put_blob(data:bytes, media_type:str)->BlobRef`, `get_blob(hash)->bytes`.
Reject duplicate JSON keys, floats and surrogate characters before hashing.
Test reordered keys, changed array order, exact preservation of non-ASCII strings,
partial write recovery, wrong digests, SQLite foreign keys and migration idempotence.
Use a temporary directory/database, never the paper library as a storage test.

Completion: `pytest tests/unit/test_canonical.py tests/integration/test_storage.py`;
an environment manifest plus hashes round-trip deterministically across two fresh
processes. Stop for identity collisions, partial references or nondeterministic
bytes; repair before W01. Hash agreement is a storage property, not legal evidence.

## W01 — Import one circular and its annexes (two to three days)

Dependencies: W00. Start offline with preserved 23EC35 JSON/PDFs. Implement
`import_source(spec:SourceImport)->SourceRevision`,
`extract(revision, extractor_config)->TextDerivative`,
`anchor(derivative,start,end,page)->SourceSpan`, `verify_span(span)->None`.
Persist exact official URLs, retrieval instant and source/extractor hashes.
Reference parsing proposes dependencies; a reviewer resolves their identities.
Fetch only configured official hosts, validate redirects/MIME/PDF magic and impose
20 MB/document and 30-second request limits as configurable engineering budgets.
These are resource controls, not accuracy criteria. Oversize files become explicit
manual-import work, not silently incomplete sources.

Completion: `legalmath sources import --manifest corpus/sources/pilot.json`;
`pytest tests/integration/test_spi_import.py tests/security/test_fetch.py`.
Reproduce the checked Annex 1 paragraph 3.1 anchor. Test changed PDF bytes,
re-extraction, rotated/scanned pages, broken references, HTML at a PDF URL and
private-network redirects. OCR text can be drafted against but blocks release
until its supporting spans have been visually verified. Missing annexes block
affected rules, not unrelated imports. Output source register and dependency report.

## W02 — Typed RuleIR and normalized evidence (three to four days)

Dependencies: W01. Implement schema loading without remote schema retrieval,
domain dataclasses, cross-reference checks, unique nodes, acyclic dependency graph,
unconditional rule-reference constraint and literal/date checking. Public API:
`load_bundle(bytes)->RuleBundle`, `validate_bundle(bundle)->list[Diagnostic]`,
`dependency_closure(bundle,rule_id)->DependencySet`,
`normalize(records,declarations,subject_id,valid_at,known_at)->FactSnapshot`.
Errors include JSON Pointer locations and source IDs. Unknown and conflict are
tagged domain values; Python `None`, falsy strings and NaN are never substitutes.

Completion: `pytest tests/unit/test_types.py tests/unit/test_graph.py
tests/unit/test_normalize.py`; replay all six invalid contract cases, add direct
and indirect cycles, self references, invalid leap dates, invalid numeric strings
(including `-0`), two equivalent records,
conflicting records, late correction, expiry at exact interval endpoint and a
correction known only after the assessed decision. Expected results come from
the written contracts. Stop if normalization cannot explain a selected value.

## W03 — Financial condition and deterministic trace (three to four days)

Dependencies: W02. Implement all expression operators exactly as `semantics.md`.
Pure API: `evaluate(bundle,snapshot,rule_id,valid_at,known_at,mode="draft")->EvaluationResult`.
Implement `legalmath.conformance:evaluate_case(case)` as the fixture adapter.
No HTTP, LLM, solver or adjacent MCP call inside the evaluator. Implement a
trace renderer that uses only evaluated nodes and exact source spans.

```sh
.venv/bin/python scripts/check_spec_pack.py --runtime legalmath.conformance:evaluate_case
.venv/bin/python -m pytest tests/conformance/test_decisions.py -q
legalmath evaluate --case docs/specs/v0.1/fixtures/decision-cases.json --id f01
```

Completion requires all 35 decision cases, including negative amount, unknown
alternative, conflict precheck, competing equal-valued exceptions, unknown scope,
exact/inexact scaling and equal unknown branches. Add property tests for known
financial-condition monotonicity over a stated integer domain, trace determinism,
irrelevant-fact invariance, and known Boolean results' empty blocking set. Kill
the listed threshold/OR/unknown/conflict mutations. Tests generated solely from
the evaluator cannot replace the fixed source-derived boundary cases.

The first demonstrable slice is now complete: original paragraph, typed rule,
synthetic evidence, result and explanation. It is a subcondition, not SPI
qualification or trade permission. Stop for a mismatch between displayed and
computed units, source bytes or traces; repair before adding automation.

## W03J — Required generated Java library (five to eight engineer-days, provisional)

Dependencies: W03. Start by rebuilding `examples/java-dry-run/`; preserve its
independent source-derived expectations. Implement the complete contract in
`docs/specs/v0.1/java-backend.md`. Python emits Java; the deployed JAR has no Python,
LLM, network, HTTP-server or MCP dependency. Keep authoring and deployment separate.

Files: `src/legalmath/java/{emit,manifest,conformance}.py`;
`java-runtime/src/main/java/hk/legalmath/{api,values,trace,events}/`;
`tests/conformance/test_java.py`, `tests/integration/test_java_host.py`.
Interfaces: `compile_java(bundle, target_release=17)->JavaSourceTree`;
`build_java(source_tree, toolchain)->JavaBuildManifest`;
`compare_backends(case)->ComparisonRecord`; Java
`EvaluationResult evaluate(FactSnapshot, RuleId, AssessmentContext)`.
Types, logical/error behavior, source/node traces and hashes must match the full
reference contract; the demonstration's smaller response must be upgraded.

Completion commands (future full-product commands):

```sh
.venv/bin/python -m pytest tests/conformance/test_java.py tests/integration/test_java_host.py -q
legalmath build-java --bundle-hash HASH --target-release 17 --out artifacts/candidates/HASH
```

Execute all 35 full-language decision fixtures in both backends, plus the 32 SPI
scenarios and independently specified source cases. Preserve the eleven demo
consent histories; full Java event conformance follows W05/master-plan T14. Verify exact
arithmetic, unknowns, conflicting sibling exceptions, skipped-root trace markers,
canonical result hashes, inexact scale, dates and interval boundaries. Every
accepted operator needs a code-generation implementation and conformance cases;
unimplemented operators must fail compilation. Compile a separate caller against
the actual JAR; test wrong types, missing declarations, stale evidence,
unsupported release, dependency-free invocation, idempotent replay and deterministic
rebuilds. Runtime tests must detect the strict threshold, OR-to-AND and
consent-bypass mutations by outcome, not merely by changed hashes. Extend to event
properties in W05. No universal compiler-correctness or legal-fidelity claim follows
from these tests.

The build manifest contains bundle/source hashes, generated-source hashes,
compiler/runtime versions, Java target, dependency/license list and JAR hash.
The verification report references that build; the final release manifest
references both, avoiding a hash cycle. Compare complete semantic response fields
and independently verify each backend's execution hash under its real engine
identity. Stop and repair for divergent statuses, source traces, money/time meaning,
unchecked operators, or tests run against a different JAR. A partial emitter can
remain a demonstration; it cannot silently become the production backend.

## W04 — Review, amendments and release (three to four days)

Dependencies: W03 and W03J. Implement the lifecycle and exact-hash approvals in
`contracts.md`. `transition(bundle_hash,event,expected_revision,caller)->ReviewState`
and `release(bundle_hash,evidence_hash,expected_revision)->ReleaseRecord` run
inside transactions. Implement clause coverage rows: clause ID, executable rule
IDs or reason for non-execution, dependencies, open issues, reviewer decision.
Every in-scope normative clause receives a disposition; recall is not calculated
against an LLM's own extracted clause list.

`compare_structure(old,new)->ChangeReport` includes added/removed/changed source
links, definitions, constants, scopes, operators, deadlines and dependency closure.
Use 23EC53/26EC22 to demonstrate explicit supersession and unaffected historic
replay. A paragraph renumbering alone is not a semantic change verdict; it changes
anchors and requires confirmation. An amendment to a definition affects all
dependent rules even when their own expression bytes did not change.

Completion: `pytest tests/integration/test_review.py tests/integration/test_amendment.py`.
Execute four release fixtures plus concurrent review, author self-approval,
different-hash evidence, unresolved dependency, failed tests, stale source span,
effective-date gap and overlapping releases. Production version selection must
be unique for an assessed time or return a conflict. Export contains all inputs,
interpretations, hashes, traces and evidence; import into a fresh database replays
the result. A draft cannot enter a production export. The evidence and release record bind
both the bundle hash and the Java release-manifest/JAR hash. A correct report for
a different binary cannot release this binary. The preexisting release fixtures
cover only their named review guards; add wrong-JAR and unsupported-Java-target cases.

## W05 — Consent and one obligation profile (four to five days)

Dependencies: W03–W04. Implement immutable event ingestion, replay at explicit
valid/known times, consent generation, non-preemptive achievement obligations,
watermarks, late performance and leap-policy scheduling. API:
`append_event(stream,event,expected_revision)->EventRef`,
`replay(stream,valid_at,known_at,profile_version)->ReplayResult`,
`anniversary(date,years,leap_policy)->date`.
An opening can be received after a related performance: retain unmatched records,
then assess by occurrence time on replay; before-activation performance still
does not satisfy this profile. Effective rule version for an existing obligation
is the version captured at its opening unless an explicit reviewed migration says
otherwise. Regulation-specific migration cannot be inferred from publication.

Completion: `pytest tests/conformance/test_events.py tests/unit/test_calendar.py`.
Execute eight event fixtures and add duplicate IDs, content collision, absent
ordering authority, simultaneous grant/withdraw, unknown deadline, missing
watermark, late-arriving timely evidence, Feb 29 policies, known-at exclusion,
and performance with wrong actor/action/subject. Do not drop an observed event
because the advice view would have prohibited it. Reject maintenance/compensation
templates in v0.1. These are explicit later work, not silently modeled as one-off
tasks. Retain every superseded assessment.

## W06 — Review interface and API (four to five days)

Dependencies: W04–W05. Implement the documented endpoints, schema-generated API
documentation and four pages: source/paragraph, rule/evidence, case/trace and
amendment/release. The first screen shows source, normalized interpretation,
required evidence, unresolved issues and a distinguishing case together. Clicking
a result opens its historic source revision. Generated diagrams are views of the
AST, never another hand-maintained specification. Review changes create drafts.

Completion: API request/response snapshots, role/transition integration tests,
keyboard navigation, visible cents-to-HKD formatting, empty/error/conflict cases,
and a recorded walkthrough of the five SFC cases. Test idempotent requests and
stale revisions. Exit requires a compliance reviewer to identify what the
financial test does and does not decide using the screen alone. Until that human
review occurs, report usability as pending, not passed by screenshot inspection.

## W07 — Bounded counterexample search (three to four days)

Dependencies: W03–W04. Implement only the solver fragment in `semantics.md`.
`encode(bundle,rule_id,domain)->EncodedProblem | Unsupported`,
`compare(left,right,domain,timeout_ms)->ComparisonResult`.
Default budget 10 seconds, maximum 10,000 expression nodes per job; configurable
convenience choices reported with the result. Validate a nonempty input domain
before any equivalence query. Unknown/conflict are not modeled as unconstrained
classical Booleans. Input conflicts are outside the solver fragment and are
explicitly excluded in the declared domain.

Completion: `pytest tests/conformance/test_solver.py`. Deliberately change `ge`
to `gt` at HK$40m; get and replay the exact-boundary counterexample. Compare
`A or not A` with true under unknown A; obtain the difference. Test empty domain,
timeout, unsupported default/date/event constructs and inconsistent domain.
For the supported small Boolean fragment exhaustively enumerate all T/F/U inputs
and compare solver encoding with interpreter outputs. Unsat answers remain
solver evidence, not independently checked Lean/F* certificates.

## W08 — Corpus coverage and candidate drafting (five to seven days)

Dependencies: W04, W06; W07 useful but not required. Implement pagination with
saved cursor/total counts, attachment deduplication and changed-content detection
for official circular listings. Build source dependency closure, not merely a
keyword index. Fixed pilot includes 23EC35, 23EC46, 23EC53, 26EC22 and 25EC48,
annexes and the imported definitions selected by compliance.

Drafting interface:
`propose(source_packet,allowed_schema,model_config)->CandidateSet`.
Candidate records include model/version, prompts, source hashes, token/cost usage,
schema diagnostics and unresolved alternatives. Retrieval only returns preserved
source spans. Prompt asks for clause inventory, actors, scope, definitions,
modality, conditions, exceptions and missing information before expressions.
Schema repair can correct syntax/types; it cannot assert that meaning is settled.
Maximum two automated repair attempts per candidate, then retain an issue.
Cap 3 alternative drafts/clause and 10 candidate analyses/clause initially;
these are budget hypotheses, not convergence conditions.

Completion: `pytest tests/integration/test_drafting.py tests/security/test_source_instructions.py`.
Use a stub provider for deterministic tests. A model-provider plug-in cannot write
review/release tables. Adversarial source text asking the model to approve a rule
must remain inert text. Measure omitted clauses and wrong operators against the
independent clause inventory; report abstention as well as accepted results.
Models may propose a missing definition, but may not fabricate its source.

## W09 — Narrow reuse adapters (two to four days, optional for MVP)

Dependencies: W01/W07/W08 as applicable. Implement subprocess/protocol adapters
with 60-second parse and 30-second analysis smoke-test budgets; explicit timeout
responses and isolated output directories. Pin adjacent repository commits and
record command, environment and output hashes. Do not import their dependency
trees into the evaluator. See `decisions.md` for inspected boundaries.

ResearchAssistant supplies discovery/PDF parsing; fallback is the preserved
source plus local Poppler. MathDevMCP receives a named mathematical proposition,
assumptions and supported expression encoding; reject structural-only certificates
as proof results. DynareMCP supplies investigative scheduling patterns, not an
economic-model parser or a legal theorem prover. UCB/MCTS-like ranking is an
optional candidate-exploration experiment after a deterministic baseline works.

Completion: adapter contract tests against captured fixtures, then one bounded
real call per enabled adapter. Store exact output and classify `checked_proof`,
`solver_result`, `structural_check`, `test_result` or `unverified_proposal`.
If no supported proposition or runtime is available, record NOT_RUN and keep the
core usable. Neither optional adapter failure nor a low search score is a reason
to replace the semantic target.

## W10 — Evaluation and pilot decision (two weeks including reviewers)

Dependencies: W06–W08. Register the experiment in `docs/plans` before live model
or human comparisons. Question: does the workbench reduce material interpretation
or implementation errors at acceptable review cost on selected changes?
Baseline ladder: current manual workflow; source-grounded LLM summary/checklist;
human-authored RuleIR with interpreter; LLM-assisted RuleIR with the same reviews;
then optional search/proof enhancements. All arms receive identical source
versions, required definitions and case information. Report human-authored rule
construction time; never give only the proposed arm gold formal rules for free.

Construct at least 30 independently adjudicated clause-level change tasks from
the selected families, with 10 development and 20 held-out tasks. This is a
feasibility budget hypothesis, not a powered accuracy claim. Split by circular
family/amendment chain, not neighboring paragraphs; if five source families
cannot support the split, collect more documents before claiming generalization.
Two compliance readers adjudicate expected scope, rule meaning and scenarios;
disagreements remain a separate stratum and cannot be silently discarded.
Use synthetic clients. Keep development cases out of held-out drafting prompts.

Primary engineering release screen: zero unresolved critical false approvals or
missed critical duties in the adjudicated pilot cases, all source/lifecycle
checks passing. This is a veto screen, not evidence of zero population error.
Primary comparative outcomes: paired task-level material-error difference and
reviewer minutes including rework. Report confidence intervals clustered by
change task/family; for too few families, report descriptive differences and the
sampling limit rather than a ranking. Secondary diagnostics: clause omission,
wrong scope/modality/operator, abstention, accepted-answer precision, source-link
coverage, mutation detection, latency and cost. No aggregate score may hide a
critical false approval. Define “critical” with the bank before unblinding.

Stop and repair the harness for leaked answers, unsupported gold interpretations,
unequal source access or corrupted histories. A poor drafting arm triggers its
predeclared repair; it does not invalidate the human-authored-rule product.
Completion report contains commands/environments/model versions, corpus hashes,
all cases including failures, adjudication agreement, uncertainty and a decision
table: continue narrowed scope, repair candidate, or stop the proposed pilot.
Bank system integration and production release require a separate approved change.

## Sequence, staffing and deliverables

W00–W04 including W03J have a provisional four-to-five-week allocation; their
existing estimates alone total roughly 17–25 engineer-days. W05–W08 add roughly
four-to-five weeks, followed by integration/review and any separately staffed
pilot. Twelve weeks is a planning allowance that must be re-estimated after the
Java milestone, especially with the new contract and host tasks. Estimates are
work hypotheses, not vendor commitments. A technical
lead/formal-methods reviewer contributes part-time at W02/W03/W07; a compliance
sponsor owns scope and gold cases; operations owns data meanings. Independent
review cannot be replaced by the implementer's own tests.

Weekly deliverables: preserved sources; first financial-condition replay; reviewed
release/export; consent/duty history; counterexample demonstration; assisted
drafting comparison. Each produces a reset memo stating passed checks, failed
checks, remaining interpretation issues and the next package. No week is complete
merely because its UI exists or its paper list grew.
