# Bounded failure diagnosis and recovery in the integration master

This is an amendment of the existing integration master, not a replacement
program. The user requested diagnosis, repair and repeat after the settled P10
failure. The latest run finished: 85 original accounts, 78 validated and seven
failed. Four responses violated the typed reference representation; three
requests returned generic invalid_request without output. The latter cause is
unknown. The old hook stopped because it can drain ready work but cannot create
a reviewed recovery transition.

## Evidence contract and skeptical review

The engineering question is whether a bounded recovery can preserve every
successful source-grounded account, repair only failed requests, refresh its
diagnosis after settlement, and continue independent work. The comparator is
P10 attempt 9 and its authenticated 512-row dispatch journal (505 validated,
seven failed), plus its complete 85-account census. The journal limit is 8,100,
not 512. All original four questions, 46 obligations and 35 readings remain.

Passing requires production checkpoint reconstruction and immutable success
reuse, exact preservation of document-qualified source gaps, ordinary output
validation, and a persisted completion-only diagnosis after every pass. Actual
P10 preparation additionally requires all 85 accounts and the existing source
and synthesis checks. Local tests are engineering evidence, not legal acceptance
or complete evaluation of the six tools.

Veto execution for corrupted evidence, an unknown in-flight dispatch, changed
source or provider identity, expired authority, or exhausted global calls. A
failed response rejects that response and its consumers; it does not veto
independent accounts or other question branches. A repeated unchanged failure
exhausts that request's recovery; it must not be endlessly retried. Refusals,
authentication errors and unknown failures are retained for separate review.

Assumptions: existing typed-reference validation is the reviewed baseline; the
generic invalid_request is not assumed transient or caused by capacity. One
unchanged replay is a diagnostic hypothesis expressly authorized by this user
instruction. Existing per-request admission, provider model, global 8,100-call
ceiling, cumulative charges, service retry ledger and UTC deadline remain. The
local date is 19 October in Hong Kong; authority is checked against exact UTC
timestamps, not the local calendar date.

The bounded choice is two recovery passes within one additional P10 owner
attempt, with at most one representation correction or unchanged no-output
invalid-request replay for any request. The second pass is for newly exposed
failures, not repetitions of the same failure. Known unrecoverable responses
are reused as failures so they do not block repairs of independent requests.
No new global call allowance or deadline is implied.

Skeptical audit: PASS for this bounded engineering repair. A full rerun would
waste validated work; accepting 78/85 would weaken the target; relabelling
invalid_request as a transient outage would invent a cause. Those alternatives
are excluded. A successful correction can still omit law, so normal complete
source review remains mandatory. No automatic code rewriting is authorized.

## Dependencies and execution

| Item | Requires success | Requires completion | Independent work | Result |
|---|---|---|---|---|
| Freeze and diagnose | Verified final receipts | P10 attempt 9 | Provider parameter inspection | Exact failure census |
| Implement bounded recovery | Reviewed diagnosis | Existing hook settlement | Offline tests and request inspection | Restartable policy and regression evidence |
| Register amendment | Local tests and production replay | Mission refusal recorded | Other reviewed local tasks | One reopened P10 attempt, unchanged grant |
| Repair P10 | Valid binding and own source prerequisites | Previous P10 pass | Other questions remain independent | Corrections, retained successes, failed requests |
| Diagnose next pass | Evidence integrity | Every repair pass, including failure | All original eligible nodes | Refreshed finite next actions |
| Answers and tool comparisons | Their own complete preparation | None from unrelated questions | Ready arms | Existing substantive acceptance evidence |

After each settled pass, freeze its checkpoint before selecting the next pass.
Do not overwrite predecessor dispatches, phases, grants, rejected responses or
attempt records. Reopening uses the same owner and retains all nine attempts.
Reconcile a reserved call before restart; never infer that disconnection means
the provider did not execute it. After exhausted recovery, report exact remaining
failures and drain all independently ready original work.

Implementation and execution evidence will be retained under
`artifacts/legal-mission-control/2026-10-19/failure-recovery/`. The fixed master
commands remain the entry points; no broad host permission rule is required.

## Implementation review

The production replay reconstructed all seven failed requests without a provider
call. It exposed an order-dependent wire table: saving and reloading JSON changes
column order and identity-hash alias allocation although the logical request is
equal. Exact provider replay therefore authenticates the retained wire binding,
checks all decoding maps and normalized source values against reconstruction,
and dispatches the original packet. It does not change provider parameters or
claim that ordering caused invalid_request. Each receipt is matched to the
failed dispatch timestamp, excluding older output for the same request.

Validated roots are rechecked against their retained request, result, source
citations, requirement hash and presentation. Their children are not recursively
reconstructed merely to rediscover the same successful root. Failed roots keep
their valid siblings and normal production constructors. Regression checks
exercise correction, source-gap preservation, repeated-failure holding,
immutable histories, independent continuation and restart without redispatch.

The fixed detached entry point is
`.venv-context/bin/python scripts/legal_integration_failure_recovery.py arm`.
It invokes the existing master `live`, then records refresh, verify and status
receipts. Its finite controller is inside the existing P10 owner; the hook does
not create live authority. Unknown worker outcomes require reconciliation.
