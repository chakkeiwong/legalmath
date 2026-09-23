# Implementing the ensemble extension

The controlling explanation is chapters 6–8 of [the unified monograph](monograph.pdf).
Chapter 8 also maps the original product work packages to the executed MVP,
describes the complete source-to-Java workflow and lists its current API.
The extension task graph is [implementation-plan.json](implementation-plan.json).
These are proposed E01–E14 tasks, separate from the completed local T00–T22 MVP.
Do not replace the retained second-circular oracle with model-generated labels.

The [readiness assessment](../implementation/product-readiness.md) groups E01–E09
into three build milestones and records the checked prior results and remaining
evaluation decisions. It is an execution brief for this design, not a separate
task graph.

## Existing integration points

| Concern | Existing code to inspect before editing | Extension responsibility |
|---|---|---|
| Source intake | `src/legalmath/sources/intake.py`, `manifest.py`, `dependencies.py`, `extract.py` | Bind immutable source and derivative identities; add independent inventory/completeness checks. |
| Coverage/review | `src/legalmath/review/coverage.py`, `lifecycle.py` | Require interpretation report identity and disposition of all material issues. |
| Amendment impact | `src/legalmath/review/amendment.py` | Invalidate candidates through source, definition and inventory dependencies. |
| Formal comparison | `src/legalmath/analysis/compare.py` | Reuse the supported fragment and replay requirements; preserve UNKNOWN/unsupported/inconsistent-domain outcomes. |
| Java delivery | `src/legalmath/java/emit.py`, `manifest.py` | Bind accepted candidate to the existing bundle/build/report/release chain. |
| Release | `src/legalmath/review/releases.py` | Refuse unresolved or stale interpretation evidence; preserve existing approvals and applicability checks. |
| Jobs/API | `src/legalmath/api/jobs.py`, `worker.py`, `models.py`, `app.py`, `openapi.py` | Add bounded interpretation jobs and authenticated decisions; do not silently change old job semantics. |
| Interface | `src/legalmath/web` | Source/candidate comparison, dissent, issue histories and complete terminal reports. |

The generated class remains `hk.legalmath.Policy_<20 hash digits>` with the actual
String/Map overloads documented in chapter 7 and the current implementation closure.
Do not implement an older illustrative Java interface as though it were already
provided. The generic runner remains a conformance harness, not a release selector.

## Transaction contract

Add tables or equivalent records for interpretation runs, candidate revisions,
issues, actions, outbox entries, evidence, coverage, reports and decisions. Store
canonical immutable payloads with indexed identifiers; use foreign keys and unique
constraints. Store current projections separately from the immutable event history.

For one action reservation, in one serializable transaction:

1. Read and lock the run and the initial-phase or root budget account.
2. Check run state, expected revision, deadline, round, action type and every cap.
3. Verify that the referenced issue and input hashes still match the plan.
4. Insert a unique action ID and idempotency key with `issued_charge=1`.
5. Increment global and applicable root/initial counters.
6. Write the outbox event and audit event; commit together.

No worker dispatches without the committed reservation. A failed reservation changes
nothing. A crash after committed dispatch never refunds the issued-action count.
Outbox delivery and remote execution have separate identities. Provider idempotency
is used when available; absent it, lost responses can leave execution unknown.

For a resolution transaction, lock the expected issue revision; validate typed
resolution evidence and authenticated authority; link a new immutable candidate
revision if needed; invalidate dependent checks; update the projection and append
history atomically. The original issue, candidate and oracle remain available.

For a report, take a consistent run revision and reconcile complete collections,
not only the current UI page. Bind source, policy, candidates, issues, actions,
coverage, checks and resource outcomes. Store the report immutably. Late results
cannot rewrite it; they can justify an authorized successor run.

## Endpoint request behavior

All mutations require the existing authenticated caller and caller-scoped
`Idempotency-Key`. Request models reject unknown fields. Server-side identity,
roles, counts and approval state cannot be supplied as client authority.

| Operation | Request fields | Response and failure contract |
|---|---|---|
| Create run | `source_packet_hash`, `profile_id`, `policy_id` | 202 with `run_id`, `job_id`; 422 invalid shape; 409 incompatible versions/limits; no partial run. |
| Read run | Path `run_id` | 200 with run projection and resource links; 404 absent; authorization checked. |
| Cancel | `expected_revision`, `reason` | 202/200 idempotent cancellation; 409 stale revision; preserve outstanding charges and terminal report. |
| Read report | Path `run_id`, optional explicit report version | 200 immutable report or explicit pending response; blocked/failed reports remain accessible. |
| Read issue | Path `issue_id` | Include original discrepancy, all attempts, evidence need, resolution and processing states. |
| Adjudicate issue | `expected_revision`, `candidate_hash`, `report_hash` if already issued, `decision`, `proposition`, `rationale`, `evidence_refs`, `conditions` | Require legal reviewer authority for meaning; derive principal from authentication; 409 stale identity; never auto-release. |
| Create successor | `expected_revision`, `reason`, `policy_id`, `source_packet_hash` | 202 new linked run with separate explicit authority; old counters/history unchanged. |

The schemas describe persisted decision records; request DTOs omit fields derived
from authentication or computed hashes. A decision on an open issue can precede a
terminal report: store its exact issue/candidate/source revision, then include it
in the eventual report. A final meaning approval additionally binds the immutable
report. The implementation must distinguish those two records rather than invent
a circular report-to-decision hash dependency. The `issue-decision` schema records pre-report adjudication; `review-decision`
records **post-report review**. Implement their separate authorization and
transaction checks in E01/E09 before wiring the endpoint.

## Deterministic scheduler

Implement chapter 6's lexicographic issue order and source-aware action selection
first. Initial proposals remain blind and frozen. Candidate retention reserves one
slot per supported family before refinements; excluded families remain reported.
Question selection begins with equal-weight pair disagreement and stable tie breaks.
All these choices are explicit baselines, not empirically selected defaults.

Every discrepancy is reconciled. A verified cosmetic difference may close with its
reason immediately; unknown materiality blocks. Integrity/cancellation/deadline
checks run both inside the loop and before readiness. Readiness also independently
checks mandatory roles, source coverage, dependencies and verification, even when
no issue was generated. Reports never grant release authority themselves.

## Task completion and acceptance commands

Each task adds focused tests under `tests/interpretation` (or repository conventions
established at E01). Keep fixtures deterministic and use a controlled clock and
scripted provider for lifecycle tests. Suggested files:

- E01–E04: `test_contracts.py`, `test_inventory.py`, `test_candidates.py`, `test_issues.py`.
- E05–E06: `test_budget_transactions.py`, `test_outbox_recovery.py`, `test_controller.py`.
- E07–E09: `test_comparisons.py`, `test_reports.py`, `test_release_integration.py`.
- E10: `test_provider_boundaries.py`; include transport retries and source injection.
- E11–E12: frozen reference manifests and a separate preregistered evaluation plan.
- E13: `test_argumentation.py`, `test_search_frontier.py`; small graphs with known outcomes.
- E14: deployment-specific identity, transaction and amendment rehearsals.

Run each focused file with `.venv/bin/python -m pytest <file> -q` after it exists.
Run the existing contract and affected integration suites when their behavior is
changed. Do not report these future commands as already executed. Preserve command,
environment, input identities and results in each task's declared evidence directory.

The document package's already available checks are:

```bash
.venv/bin/python scripts/check_interpretation_contracts.py
python3 scripts/check_monograph.py
```

They verify the design examples and manuscript. They do not replace the future
service tests, concurrency tests, independent legal reference or bank acceptance.

The first vertical slice completes E01–E09 with scripted members. Its end-to-end
acceptance requires an explicit-omission repair, a persistent ambiguous definition,
a unanimous source omission, a budget boundary/crash case, source-change
invalidation and a recovered failure report. The original 23EC46 packet remains
blocked until actual reviewed evidence settles its dependencies.
