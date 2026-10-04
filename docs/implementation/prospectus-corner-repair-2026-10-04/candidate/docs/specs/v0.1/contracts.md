# RuleIR 0.1: storage and service contracts

Read alongside `semantics.md`. These are proposed implementation requirements,
not a description of a deployed service. The mandatory Java output is specified
in `java-backend.md`; the narrower SPI-Demo1 demonstration is executable. `rule-bundle.schema.json`,
`fact-snapshot.schema.json` and `evaluation.schema.json` are normative structural
contracts. The checked JSON examples in `fixtures/` instantiate them.

The 22 September implementation clarifications below support the
[master plan](../../implementation/master-plan.md): interval-local corrections,
exact result hashing, backend comparison and an acyclic build/release sequence.
These are proposed contracts, not claims that the full runtime already exists.

## 1. Canonical bytes and identity

`canonical_v1(value)` accepts only JSON objects with ASCII keys, arrays, strings,
booleans, null and integers. Reject duplicate keys, floats, NaN, infinity and
unpaired Unicode surrogates at decoding. Preserve string code points (no implicit
Unicode normalization) and array order. Sort object keys by ASCII code point;
emit compact JSON without whitespace, UTF-8, `ensure_ascii=False`, `allow_nan=False`.
JSON integers are limited to [-9007199254740991,9007199254740991]; RuleIR numeric
values use decimal strings instead. This explicitly specified local format is
not a claim of implementing RFC 8785. Hash the resulting bytes with SHA-256;
digests are lowercase 64-character hex strings without a prefix.

Source blobs have `raw_sha256 = sha256(original_bytes)`. A text derivative records
its raw source hash, extractor name/version/configuration, exact UTF-8 text hash,
and page boundaries. Normalize line endings to LF and remove a leading UTF-8 BOM;
do not merge words, remove headers or silently repair OCR in this derivative.
Repairs produce a new derivative with an explicit transformation record.
Spans use zero-based Unicode code-point offsets `[start,end)` in that derivative,
page index starting at one, and `quote_sha256 = sha256(span_text.encode('utf-8'))`.
The UI also shows the original page. A text hash mismatch invalidates its spans.

Bundle hashes cover the entire immutable bundle JSON, including interpretations
and source identifiers. Review decisions live outside the bundle and bind its
hash. Editing a source link, explanation, fact type or rule creates a new hash
and invalidates prior approval for release. No hash includes its own hash field.

## 2. Source register, applicability and interpretation

`SourceRevision` fields: `source_id`, `revision_id`, `raw_sha256`, `media_type`,
`official_url`, `retrieved_at`, `published_date` (nullable), `effective_from`
(nullable), `effective_until` (nullable), `language`, `authority`,
`source_kind`, `supersedes_revision_ids`, `derivative_ids`.
Publication is not automatically effectiveness. Source kinds include circular,
annex, FAQ, code, bank policy and reviewer interpretation; a bank policy never
receives the authority label of the circular it implements.

`SourceDependency` fields: `from_revision_id`, `locator`, `target_revision_id`
(nullable), `relation`, `resolution_status`, `resolution_note`. Relations include
incorporates, defines, amends, replaces, interprets and references. Unknown targets
remain unresolved rows. Crawling the product-authorization category alone cannot
establish the bank's regulatory perimeter. W01 imports 23EC35 and its SPI annexes;
W08 expands to the five fixed circulars and implements general discovery/pagination.

`ApplicabilityAssessment` fields: `assessment_id`, `bundle_hash`, `legal_entity`,
`regulated_role`, `activity`, `product_class`, `client_class`, `jurisdiction`,
`valid_interval`, `conclusion` (`in_scope`, `out_of_scope`, `unresolved`),
`reason`, `source_span_ids`, `reviewer_id`. All dimensions require a value or an
explicit unresolved marker. This human assessment supplies the bundle's scope
facts; an LLM cannot approve it. The public prototype uses synthetic entity IDs.

`Interpretation` fields in the bundle: `id`, `statement`, `basis`
(`source_explicit`, `reviewer_interpretation`, `bank_policy`, `synthetic_test`),
`source_span_ids`, `issue_ids`. Each rule and default exception references one.
`Issue` fields: `id`, `bundle_hash`, `kind`, `question`, `affected_rule_ids`,
`alternatives`, `resolution` (nullable), `resolved_by` (nullable), `resolved_at`
(nullable). An unresolved issue in a requested release's dependency closure
blocks release, including definitions supplied by another circular.

## 3. Fact normalization and evaluation

An immutable `FactRecord` has `record_id`, `subject_id`, `fact_name`, `type`,
`value`, `evidence_ids`, `valid_from`, `valid_until`, `recorded_at`,
`supersedes_record_ids`. Corrected records must preserve history and use the same
subject/fact. Unknown is not a persisted value record; a normalized snapshot
explains absence, expiry or unresolved assessment. Supersession is acyclic and
only visible once the correcting record is known at the requested time.
Supersession is interval-local: an eligible correcting record suppresses its
predecessor only where its validity covers `valid_at`. A correction known today
but effective tomorrow does not remove today's predecessor. Reject cross-subject,
cross-fact/type and cyclic correction targets; an unresolved target is quarantined
pending resolution. Preserve those rules in normalization fixtures before coding.

`normalize(records, declarations, subject_id, valid_at, known_at) -> FactSnapshot`
selects exactly the declared facts. It rejects undeclared input names and type
mismatches; it marks absent/expired entries unknown and different admissible
values conflict. Identical admissible values combine sorted evidence IDs. A known
normalized interval is the intersection of the selected records' intervals;
`recorded_at` is their maximum. An empty intersection indicates a normalization
bug because all selected intervals must contain `valid_at`.

`evaluate(bundle, snapshot, rule_id, valid_at, known_at, mode="draft") -> EvaluationResult`
validates hashes, time eligibility, schema, semantic typing and static closure
before executing. A production request names an exact released bundle hash.
A sandbox request can evaluate a draft but carries `mode: "draft"` throughout
and is never accepted by a production adapter. The response includes `status`,
`type`, `mode`, `diagnostics`, optional known `value`, `reason_codes`, `missing_inputs`,
`blocking_inputs`, `trace`, `bundle_hash`, `snapshot_hash`, `engine_version`,
`valid_at`, `known_at`, and `result_hash`. For errors/conflicts the `type` may be
null when typing did not succeed. The schema permits no additional properties.
Each diagnostic contains a fixed `code`, a JSON Pointer `pointer` into the
request/bundle (empty for the root), and a deterministic `message` from the
engine's versioned templates. A successful evaluation normally has an empty
diagnostics array. Transport validation errors use the same diagnostic shape.
The pure evaluator records the explicit mode; the service/export layer checks
release authority before invoking it in production mode. Passing a mode string
to the pure function does not grant deployment authority.

Trace entries are identified by the expression's `node_id`. Bundle-wide unique
node identifiers make this stable. Evaluate a referenced rule once and refer to
its existing nodes thereafter; the `rule` expression itself gets its own entry.
For a skipped branch, emit one entry for its root with `status: "SKIPPED"` and
`children: []`; do not emit skipped descendants. For a parent, `children` lists
the root IDs actually evaluated or marked skipped in source order. The list is
postorder, with a shared child permitted to occur earlier than an intervening
unrelated node. No node appears twice. Validation/conflict prechecks may return
an empty trace with affected fact IDs in `blocking_inputs` and `reason_codes`.

The semantic result hashed with the canonical request contains status, type,
mode, diagnostics, value (if present), reasons, missing/blocking inputs and the trace. The request
contains bundle/snapshot hashes, rule ID, mode, both times and engine version.
Request IDs, durations and the `result_hash` itself are excluded. Error precedence
is structural validation, reference/duplicate errors, typing, cycles, temporal
eligibility, input conflict, then scope/body execution. Within a stage sort errors
by JSON Pointer and return all of them; runtime traversal uses expression order
and returns the first error, otherwise conflict, otherwise a computed value.

The exact hash payload is `{"request": request, "result": semantic_result}`.
Use exactly the request and semantic-result fields listed above, preserving
omission of optional `value`; hash its `canonical_v1` bytes. An input that cannot
be decoded or assigned those identities is a boundary validation failure, not
an EvaluationResult containing fabricated zero hashes. Freeze that SDK/transport
error envelope in master-plan T00. A schema-valid runtime request returns the
declared tagged EvaluationResult.

Python and Java report their actual, different `engine_version` identities.
Cross-backend comparison requires equality of every response field except
`engine_version` and `result_hash`, then independently recomputes both execution
hashes with their respective engine identities. Never forge identical engine
names to force matching hashes. Replays within one unchanged engine/version must
reproduce the original execution hash. SPI-Demo1 has its own smaller response and
hash protocol; it is not a full-contract implementation.

## 4. Review and release

Lifecycle: `DRAFT -> IN_REVIEW -> APPROVED -> RELEASED -> RETIRED`.
`IN_REVIEW -> DRAFT` is a rejection. Approval does not modify bundle bytes.
Any edit creates a new DRAFT revision linked to its parent. A release requires
an approved exact hash, two distinct reviewer identities (compliance meaning and
engineering implementation), no unresolved blocking issues/dependencies,
explicit effective interval, applicable scope assessment, and a passing evidence
report bound to that hash and to the exact Java release-manifest/JAR hash. The author cannot fill either approval role for that
revision. These are prototype governance choices to be adapted to bank policy.

Transitions accept `expected_revision` for optimistic concurrency; a stale value
returns HTTP 409 without mutation. Each accepted transition appends an audit
record atomically with the new state. `RETIRED` blocks new production decisions
but historic evaluation remains possible under `mode: "replay"` against the
original valid/known times. Supersession schedules a new release; it does not
erase the previous interpretation or silently migrate existing obligations.

Build/evidence/release records are acyclic. A `JavaBuildManifest` identifies the
candidate bundle, toolchain, source and JAR; it contains no verification or release
hash. A `VerificationReport` references that build and its actual JAR. A
`JavaReleaseManifest` references both build and report plus applicability/effective
scope. A later `ReleaseRecord` binds that manifest and reviewer decisions. None
contains its own hash or a future record's hash. The manifest containing the JAR
digest is external to the JAR. Candidate compilation is allowed before approval;
export for use requires the release checks. Local synthetic review authority is
explicit and cannot stand in for a bank's deployment authority.

## 5. Persistent model and transactions

Use Python 3.11, SQLite with foreign keys enabled and WAL mode, and content-addressed
files for the public prototype. Single service writer; no distributed-lock claim.
`storage.sql` defines the minimum tables and immutable payload storage. JSON
payloads retain the full contracts; columns support lookup and referential checks.
The supplied DDL is a starting sketch: master-plan T00/T02 must add versioned
source-dependency/derivative, fact/supersession, applicability, author/reviewer,
build/evidence/release and stream-header relations or indexed immutable-payload
references. Release selection and concurrency state cannot exist only in memory.
Write a blob to a temporary file, fsync, rename to its content hash, then insert
the database reference inside a transaction. Orphan blobs may be garbage-collected
only if no record references them; a referenced missing blob is a hard integrity
failure. Never overwrite a blob. SQLite migration files are forward versioned.

All state-changing requests require a caller-scoped `Idempotency-Key`. Store
request hash and response in the same transaction. Reuse with identical bytes
returns the previous response; reuse with a different request returns 409.
Release validates evidence and writes state/audit rows in one transaction.
Events are append-only with unique event ID and unique authoritative stream
sequence; replay results are separate immutable records. A hash chain on audit
rows detects accidental changes but provides no protection against an administrator
who can rewrite the database and all hashes. External signed retention is later
bank integration work.

## 6. Local HTTP API

Bind the prototype to `127.0.0.1`. Use FastAPI/Pydantic only as transport; semantic
code takes plain domain values and does not depend on HTTP. Public/synthetic data
only. A local reviewer registry provides named role identities for demonstrations;
it is not an enterprise authentication implementation.

| Method/path | Request | Response and failure |
| --- | --- | --- |
| `POST /v1/sources/import` | official URL or local blob, reference ID, media type | 201 revision and derivative hashes; 422 invalid content; 502 fetch failure |
| `POST /v1/bundles` | RuleBundle | 201 hash, DRAFT, revision=1; 422 schema/type issues |
| `GET /v1/bundles/{hash}` | none | exact bundle, review state, issues; 404 unknown hash |
| `POST /v1/bundles/{hash}/review` | decision, reviewer ID/role, comment, expected_revision | new state and revision; 409 stale/conflicting decision; 422 invalid transition |
| `POST /v1/bundles/{hash}/release` | evidence_report_hash, java_release_manifest_hash, expected_revision | release record; 409 stale; 422 unmet release guards |
| `POST /v1/evaluations` | bundle_hash, snapshot, rule_id, mode, valid_at, known_at | EvaluationResult; 422 malformed request; 409 nonreleased production bundle |
| `GET /v1/evaluations/{result_hash}` | none | original request, result and source links; 404 unknown |
| `POST /v1/event-streams/{id}/events` | event, expected_revision, ordering_authority | stored event and revision; 409 duplicate mismatch/sequence collision |
| `POST /v1/event-streams/{id}/replay` | valid_at, known_at, profile_version | immutable consent/obligation result with evidence |
| `POST /v1/comparisons` | old_hash, new_hash, rule_id, declared domain | job ID; result UNSUPPORTED, UNKNOWN, INCONSISTENT_DOMAIN, COUNTEREXAMPLE or NO_COUNTEREXAMPLE_IN_DECLARED_DOMAIN |
| `GET /v1/changes/{old_hash}/{new_hash}` | none | structural changes, affected dependency closure, evidence requiring rerun |

Asynchronous solver/drafting jobs use a persisted job row and bounded worker
subprocess. Status is QUEUED/RUNNING/SUCCEEDED/FAILED/CANCELLED. A worker timeout
is UNKNOWN for proof analysis, never a successful check. An interpreter result
with `status: "ERROR"` is HTTP 200 when the request is structurally valid: it is
the result of assessing a well-formed request, not a transport failure.

The master plan adds `POST /v1/event-streams`, `POST /v1/fact-records`,
`POST /v1/snapshots`, `POST /v1/drafts`, `GET /v1/jobs/{id}` and
`POST /v1/jobs/{id}/cancel`. T00 freezes their complete schemas and T16 implements
them. Draft submission returns 202/job ID; retrieval returns state and result
hash or diagnostics. Cancellation is idempotent and cannot partially approve or
publish a bundle. Caller roles come from the configured local registry, not from
untrusted role names supplied in request bodies.

## 7. Error and explanation boundaries

Use fixed machine codes plus source-linked human explanations. Minimum codes:
E_SCHEMA, E_DUPLICATE_ID, E_REFERENCE, E_TYPE, E_CYCLE, E_VERSION_TIME,
E_HASH_MISMATCH, E_INEXACT_SCALE, E_ORDER_UNRESOLVED, E_EVENT_ID_COLLISION,
E_UNSUPPORTED_PROFILE, E_STALE_REVIEW, E_RELEASE_BLOCKED.
Evidence conflicts use CONFLICT/INPUT_CONFLICT; competing exceptions use
CONFLICT/MULTIPLE_EXCEPTIONS; missing evidence uses UNKNOWN/MISSING (or its
specific normalization reason). No exception handler returns FALSE as a fallback.

Official-source pages, PDFs and LLM output are untrusted input. They cannot invoke
tools or change release status. Source fetching accepts configured SFC/HKMA
hosts, checks redirects and MIME/magic, rejects private-network targets, and
enforces size/time limits. Keep downloaded documents inert. Drafting tools receive
only approved public source text and return schema-constrained proposals.
Draft reference evaluation walks the AST and never executes model-written code.
The Java deployment runs only deterministically emitted, compiled and tested code
from the approved rule bundle, with the exact JAR bound into its release record.
