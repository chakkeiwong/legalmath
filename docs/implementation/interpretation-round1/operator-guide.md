# Running the bounded interpretation workbench

This increment implements the investigation and review workflow described in the
unified monograph. It runs deterministic, supplied member proposals and supplied
repair proposals. It does not call a language model, discover legal meanings by
itself, or establish that the supplied inventory covers all applicable law.

The implementation uses the existing Python service and emits the existing Java 17
library. Open `/interpretations` for the new review page and `/docs` for the API
console. These pages use the same local identity registry as the original workbench.
Tokens are held in the browser input only; decisions derive authority from the
server's registry. The records label that authority `LOCAL_SYNTHETIC`.

## Start with fresh working data

Use a fresh directory for ordinary work. The old acceptance databases are retained
historical evidence and should not be used as mutable working databases. Supply a
project-local identity JSON file with separate author, meaning and engineering
principals, using the shape in the whole-round demonstration's `local-identities.json`.
Those demonstration tokens are public synthetic credentials.

```sh
.venv/bin/legalmath serve \
  --data-dir artifacts/interpretation/workbench \
  --identities artifacts/interpretation/round1/P4/attempt-03/demonstration/local-identities.json \
  --jdk .localresources/java-toolchain/jdk-17.0.20.1+1
```

The successful attempt path is recorded in [execution-report.md](execution-report.md).
If a later attempt supersedes the example above, use its identity file instead.
The server binds to localhost, normally port 8765. Import retained sources through
the existing source API before creating a packet that references source spans.

## One investigation, from source to report

Every mutation uses `Authorization: Bearer <token>` and a unique `Idempotency-Key`.
Reusing the same key with a different request fails. The generated
[OpenAPI](../../specs/v0.1/openapi.json) is the exact transport contract.

1. Create any RuleIR candidate bundles through `POST /v1/bundles`. This validates
   the existing language and assigns immutable bundle hashes. Build and verify
   candidate Java using the existing engineering endpoint when applicable.
2. Send `POST /v1/interpretations` with a `packet`, optional fixture `policy` and
   optional terminal `predecessor` run ID. A packet declares `source_key`,
   `authority`, `selected_slice`, `units`, `dependencies` and `family_ids`.
   Each unit has a unique ID, locator, exact text, normative flag and source span.
   A synthetic unit uses `span: null`; a retained-source unit must resolve against
   imported source bytes and the retained text derivative. A dependency supplies
   a retained `source_hash`, or null when missing. The response supplies the
   exact `source_packet_hash` used in every proposal.
3. A different meaning reviewer inspects a retained inventory before execution
   and calls `POST /v1/interpretations/{run_id}/inventory-review` with the exact
   packet hash, complete ordered unit IDs and rationale. A synthetic fixture
   inventory is visibly marked as such. Neither mark proves exhaustive legal scope.
4. Configure `POST /v1/interpretations/{run_id}/configuration` with the four
   required roles: `inventory`, `normative`, `controlled-language`, `alternatives`.
   Each role has `{"adapter":"scripted","proposals":[...]}`. Inventory proposals
   must be empty because this member reads the separately supplied inventory.
   A proposal supplies source hash, source-unit IDs, family IDs, subject,
   controlled-language statement, nullable bundle hash, assumptions, arguments,
   nullable parent ID and revision reason. Optional `repairs` are up to three
   separately recorded scripted specifications. Optional `verification_hashes`
   identify actual successful engineering verification records, never booleans
   asserting success. Configuration becomes immutable before dispatch.
5. Send `POST /v1/interpretations/{run_id}/execute`. It returns 202. Poll the GET
   operation or reload the review page. The supervisor persists the start request,
   freezes initial outputs, reconciles disagreements, performs permitted repairs
   and stops under the policy. An independent inventory omission, missing source,
   new ambiguity, invalid response or unexplored proposal remains visible.
6. Inspect the terminal report, all candidates, original assumptions, all issues,
   action counts, retained responses and available checks. A terminal processing
   state can coexist with an unresolved legal question. `release_eligible` is
   always false in an investigation report.

The fixture policy allows four initial actions, at most three resolution rounds,
three actions per issue root and twelve actions overall; it stops after two rounds
without a newly resolved discrepancy. Each action has a 30-second bound, and the
run has a 600-second deadline. These are test settings. Paid profiles are rejected.
There is no automatic retry of a dispatched action whose result was lost. A stale
completion is retained as an observation and cannot rewrite a closed report.

The candidate cap reserves remaining slots for unseen declared reading families.
Deferred proposals and their linked bundles are retained and create an explicit
search-incomplete question. Families are currently declared in the packet; open
ended family discovery by live models is subsequent work. Priority scores are
scheduling fields and carry no legal correctness probability.

## Meaning decisions and successors

Before a run closes, `POST /v1/interpretations/{run_id}/issues/{issue_id}/decision`
requires the current issue revision, candidate ID, decision, rationale, response to
the strongest objection and retained evidence references. Resolving a definition
creates an authenticated decision plus validated adjudication evidence. Missing
sources, unsupported search, integrity defects and failed Java/formal checks cannot
be voted away through this endpoint.

After a ready report closes, `POST /v1/interpretations/{run_id}/review` requires the
candidate ID and exact candidate/report/source hashes, the decision, rationale,
objection response and all inventoried source-unit IDs. The request's `revision`
field is retained for the transport shape; immutable hashes are the controlling
staleness check. `ACCEPT_MEANING` is refused while structural or material questions
remain. A later rejection revokes that candidate's meaning acceptance.

A blocked report remains immutable. Create a successor with its `predecessor` field
to continue investigation. Unresolved issues and their ancestor roots are copied
into the new run, with explicit predecessor hashes and fresh unresolved state.
Previous counters and reports remain unchanged. Issue decisions can be entered
before starting the successor controller. After the successor is itself reviewed,
`POST /v1/interpretations/{run_id}/supersede` requires the exact predecessor report
hash and a rationale. Every inherited unresolved question must have a resolution.
A new run alone cannot hide the earlier investigation.

For source changes, a meaning reviewer calls
`POST /v1/interpretation-sources/{source_key}/invalidate` with the replacement
packet and reason. All affected old investigations become invalid for current
release use. An unchanged Boolean formula does not preserve the approval. The old
source and report remain available for historical inspection.

## Java delivery and operational boundaries

The existing build, applicability assessment, two-role review and release process
still applies. Any bundle associated with an interpretation investigation must
also satisfy the new exact-evidence guard. The guard runs in the old review and
release APIs, current release selection and Java export. All bound investigations
are checked, including deferred candidates. Legacy manually reviewed bundles
retain their original route; this extension does not assert that every old bundle
has ensemble evidence.

An accepted export contains `policy.jar`, build/verification/release records and
an interpretation-review sidecar. The generated class exposes static String and
Map overloads of `evaluate(snapshot, ruleId, validAt, knownAt, mode)`. Supported
modes are `draft`, `production` and `replay`. The separate host in the acceptance
run compiles against the exported JAR and calls the generated class directly.
A copied JAR cannot consult this service after export: a bank host must enforce
current release/source status when admitting transactions. That host integration
is E14 work; the local service's guard is not remote binary revocation.

History archives include interpretation projections, action/outbox state and
immutable record history. Imported login credentials remain disabled. Single-host
recovery identifies dead workers by PID and process start identity; distributed
leases, provider billing and enterprise identity are outside this implementation.
