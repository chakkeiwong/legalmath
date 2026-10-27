# Final deployment audit

Review found a material admission mismatch before any deployment: the new v7
service policy inherits progressive timing from v6, but phase admission names
only v5/v6. It would pessimistically reserve all contingent two-hour server delays
for a single recovery and refuse the authorized continuation. Repair admission to
use the existing delayed-policy predicate. The global deadline, actual wait
checks, request limits and call ceiling do not change. Test a one-call phase with
one hour remaining: v6 and v7 must both admit, while a phase whose logical-call
time exceeds the window must still fail. This is the earliest discriminating
check and requires no provider call. Archive the additional predecessor file
additively. Audit PASS for this named correction before deployment.

The offline preflight initially refused reuse after its checkpoint changed.
That is the intended product-identity integrity check. Give each offline fixture
its checkpoint-derived directory; retain the previous fixture. Live continuation
still uses one registered successor runtime and never overwrites historical work.

The ended failure at charged slot 4027 already has an old admitted service-stage
record, but no scheduled replacement and no started dispatch. Reusing that stage
under the successor binding would correctly fail the binding check. The new
deployment therefore stores service admission and resumption under its own work
directory, preserving the old stage and all shared recovery charges. This changes
where the successor's records are written; it grants no replacement or retry and
does not alter the exact failed request. Audit PASS subject to actual local
successor admission before live execution.

Final bounded sequence (repository root; no shell wrappers or substitutions):

1. `.venv-context/bin/python artifacts/legal-mission-control/2026-10-23/p14-deployment/deploy_local.py`
2. `.venv-context/bin/python scripts/legal_review_deployment.py register`
3. `.venv/bin/python scripts/legal_mission_control.py refresh`
4. `.venv-context/bin/python scripts/legal_integration_master.py status`
5. `.venv-context/bin/python scripts/legal_review_deployment.py arm`

The first command checks both local-test receipts and both offline production
checks, detects conflicting edits, and installs only the 33 reviewed files.
Registration checks the frozen predecessor and staged mission before committing
the successor transaction. Local registration does not dispatch. The fixed arm
action needs trusted network execution and uses the existing authorized Sol
route; any tool permission is restricted to that script/action. It checks the
registered provider binding and refuses duplicate active or ended workers.

Final measured context maximum: 94,256 input bytes and 22,635 local tokens across
672 requests, below the existing 250,000-byte / 70,000-token envelope. The measured
provider form peaks at 93,149 bytes / 22,441 local tokens; CLI-internal framing
remains unmeasured. These figures do not predict legal sufficiency or latency.
The focused suite passed 229 tests; the final admission/service suite passed 20
(including overlaps). The actual import check separately verifies 1,699 retained
reviews and 52 failed continuations. Its provider dispatch is disabled to stop at the
service prerequisite boundary because the pre-deployment binding still protects
the archived plan; successor authority is checked by registration and provider
check after deployment, never inferred from this fixture. The diagnostic retains
the provider's live identity for authenticating predecessor dispatch hashes and
substitutes only its authority-check method; complete() is forbidden and the
service prerequisite raises before a new reservation. Setting live=False was
rejected because live identity is part of those historical request hashes. That
diagnostic failure is retained and no predecessor was changed to make it pass.

Offline fixture follow-up: provider mode also participates in saved phase
contracts. Reusing a fixture created with live=False correctly failed that
contract. Offline directories now include the diagnostic's own hash as well as
candidate code and checkpoint hashes. This fixes diagnostic isolation; it does
not alter product identity checks or authorize a new live attempt.
