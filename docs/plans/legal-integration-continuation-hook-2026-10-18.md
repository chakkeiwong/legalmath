# Automatic continuation amendment to the integration master

This is one bounded engineering repair to the existing 13 October integration
master, authorized by the user's instruction “do the automatic continuation
hook”. It neither replaces that master nor changes its task graph, historical
54 detours, exhausted recovery allocations, owner attempts, calls or deadlines.
The repair itself is one additional local engineering package: 54 prior detours
plus this repair, never a reset of that history. The
substantive objective remains four supported answers, 46 original obligations,
35 readings and evidenced dispositions of the six tools.

## Evidence contract and baseline

The actual predecessor is the detached settled-recovery supervisor started at
2026-10-17T11:48:56 UTC, with authenticated PID/start 2524450/292882965 and live
child 2531049/292940225. Its existing consumer drain already continues ready
answers and comparisons; its exit has no durable successor. The missing behavior
is a settlement hook on both success and failure, rather than another consumer
scheduler. Existing worker receipts, master state, binding and grant are the
comparator. Installation must leave their bound bytes unchanged.

Pass criteria: a detached hook is actually armed against this predecessor;
after settlement it runs the original refresh/verify/check/status/admit gates,
dispatches eligible existing master command/live work, retains every result and
reselects after failure as well as success. A failed branch cannot suppress an
independent ready branch. A restart must adopt a running or completed action
without executing it again. Tests must exercise real subprocesses and locks,
including supervisor death, rather than merely assert lists of commands.

Authority/integrity failures veto dispatch. An unknown external dispatch vetoes
further external execution until reconciled; it must never cause a blind retry.
The original live deadline and shared call ceiling veto new live execution but
permit local retention. Task-level failures and exhausted owner allocations
block their actual dependants. Tests and successful scheduling establish only
engineering behavior, not legal acceptance or tool benefit. Evidence is retained
under `artifacts/legal-mission-control/2026-10-18/continuation-hook/`.

## Dependency and failure handling

| Item | Result | Requires success | After completion | Failure continuation | Resources and limit |
| --- | --- | --- | --- | --- | --- |
| H1 | Reviewed standalone hook and focused tests | Current mission admission, actual predecessor dossier | None | Repair this implementation locally before arming | New files outside current binding; one engineering package |
| H2 | Registration and detached armed receipt | H1 passing tests and review; unchanged predecessor hashes | None; can coexist with P10 | Retain exact installation failure | Hook registration/launch locks; no live call |
| H3 | Authenticated predecessor settlement census | H2 | Existing supervisor and its child, on either outcome | Missing receipt is retained; unknown running dispatch cannot be replayed | PID/start identities and existing writer locks |
| H4 | Validated original ready set | H3 and unchanged common authority | Every master outcome, including failure | Retain gate failure; no unauthorized dispatch | Fixed local commands, 900 s check bound |
| H5 | Original local and live work drain | H4 and each node's existing readiness/authority | None beyond actual graph edges | Recompute ready set after failure; try independent executor work | Original master locks, attempts, call ledger and deadlines |
| H6 | Immutable result, mission history and refresh | Readable outcome | Every package and final blocked/settled outcome | Retain sync failure explicitly | Mission execution lock; idempotent history ID |

H1 and H2 are independent of P10's legal success. H3 waits for shared writer
ownership, not a legal dependency between questions. H5 reuses the existing
master executors. No unimplemented recovery, failed owner, spent review attempt
or proposed capacity increase becomes eligible merely because the hook exists.

## Restart, defaults and stop rules

The hook has its own single-supervisor lock and persistent per-action intents.
Each action runs in a detached receipt-writing child with an inherited lock,
authenticated PID/start records and fixed argv. Restart adopts the receipt or
waits for the same child/command. An intent without an authenticated outcome is
reported as uncertain, never automatically redispatched. File and directory
fsync preserve journal transitions. Terminal history and refresh retain the
same exclusive lifecycle lock; restarting after a saved terminal result only
finishes its outstanding retention. Exceptions retain an immutable diagnostic.
An ordinary watcher restart uses the same `arm` command. A host reboot or changed
PID namespace requires reviewed identity reconciliation; no machine startup
service is installed.

The 900-second check timeout comes from the active master: historical validation
can take minutes. The 15-second poll is an operational convenience, not a legal
criterion; it is tested with a short injected interval. Repeated selection of
the same action at the same substantive frontier is prohibited. A finite drain
bound derives from existing remaining task attempts, with no new owner budget.
Exact ready/exhausted nodes, failed prerequisites, unknown processes, grant
expiry and remaining calls are retained when no authorized action remains.
Hook status `BLOCKED` is distinct from master scheduler `COMPLETE`, and neither
asserts legal integration completion.

## Skeptical pre-execution review

PASS for implementing and testing this repair. The baseline is the actual live
settled recovery; no historical runner is substituted. Tests concern delivery
and are explicitly excluded from legal promotion. No stochastic comparison or
reliability ranking is proposed. The Python environment is `.venv-context`,
with `CUDA_VISIBLE_DEVICES=-1` set before product imports; mission commands keep
their required `.venv/bin/python` form. Common authority and changing state are
distinguished, the live grant's earlier deadline governs external work, and
owner attempts cannot be inferred from call headroom. The initial design risk
is an orphaned action after supervisor death; an independent receipt writer,
inherited lock and a fail-closed unknown outcome address it. Another risk is
repeatedly relaunching a failing runner: frontier/action deduplication and a
finite drain bound prevent that. A polling-only report would fail acceptance;
the tests must prove executor dispatch and installation must actually arm it.

## Exact public commands

```text
.venv-context/bin/python scripts/legal_integration_continuation.py register
.venv-context/bin/python scripts/legal_integration_continuation.py arm
.venv-context/bin/python scripts/legal_integration_continuation.py status
.venv-context/bin/python scripts/legal_integration_continuation.py record
```

Arming must use trusted execution because its future existing live executor
requires network access and host-process visibility. The environment audit
reproduced that sandboxed Python sees a different PID namespace: the two live
host workers were invisible, while trusted `ps` confirmed both and their common
namespace `pid:[4026532221]`. The reviewed registration pins that namespace;
wrong-namespace arming fails before dispatch, and status reports unobservable
rather than dead. `record` also needs host visibility for its liveness check.
Request one narrow prefix for `.venv-context/bin/python
scripts/legal_integration_continuation.py` if not already approved. Every action
is fixed and accepts no arbitrary paths or commands. This groups the arm,
status and record operations without a broad interpreter grant. Do not edit
protected global rules. Registration, tests and ordinary worktree edits use
sandbox permissions. Review and actual results are recorded separately before
registration, and installation results are retained after authentication.

## Implementation review

The initial tests exposed fixture setup errors: the isolated task command used
the wrong interpreter prefix and the production DAG constructor does not save
an initial state until an event is recorded. The fixture now follows the real
command contract and explicitly saves its isolated initial state under lock.
No production invariant was weakened. Twenty-three focused checks then passed,
including actual public detached arming, idempotent installation, failure
continuation, inherited locks and replay-free finalization recovery. The final
validation also includes the reproduced PID-namespace negative control.

All 521 current bound references were checked without modification. No actual
exhausted owner is left raw PENDING; failed owners remain terminal. This matters
because the existing master command runner refuses to start a spent task. The
hook excludes spent READY rows and retains the unchanged-frontier failure if
the original runner refuses; it never silently resets or retries those owners.
No claim is made that this sidecar repairs an arbitrary malformed task register.
