# Recovery checkpoint, 20 October 2026

**Continuation checkpoint, 20 October 13:31 Hong Kong:** all four calls in
`reduction-gatecoin-5` are VALIDATED. The supervisor has advanced automatically
to `reduce-gatecoin-6-0`, with 3,441 cumulative calls at that observation. The
direct host process check matches PID 90887 and start identity 1165063.
`replay-repair/validated-recovery-checkpoint.json` records these observations.
The worker remains active; subsequent calls, failures or completion must be read
from current receipts rather than inferred from this historical checkpoint.

**Verified recovery, 20 October 13:28 Hong Kong:** slot 3437 completed the exact
pending `reduce-gatecoin-5-0` request through `gpt-6.1-sol`. Its ordinary product
result is **VALIDATED**, decoded at 134,601 bytes / 28,612 local tokens. Provider
usage was 56,804 input tokens and 2,819 output tokens; provider wall time was
57,408 ms. The worker then automatically dispatched `reduce-gatecoin-5-1` at
slot 3438 under the same phase. PID 90887 remains the single owner. Read the
current journal for subsequent outcomes; do not re-arm either recovery adapter.
The service request recovery is established. Complete Gatecoin synthesis and
answer review, independent P10/evidence execution, P14's product repair, corpus
qualification and full tool evaluations remain distinct unfinished work.

Latest dispatch checkpoint: at 2026-10-20T05:26:37Z the repaired worker reached
the original pending request. Global slot **3437** was charged at about
05:26:41Z with the exact original request hash
`5f314faaa345c9318c75cbf867d18fcce493dcf0c447c5c3a4b22c35a7b1fcb7`
and stage hash `d4e969e8344b3bd3b286b26de42adb148c8fddd1c02ac4826efb3ad3351f2cec`.
The original 146 validated results and attempt-14 terminal record were rechecked
and remain unchanged. Activation refresh passed at 05:14:17Z. At this checkpoint
the provider response and ordinary product validation are pending; do not
resubmit or re-arm. Read later receipts before interpreting this checkpoint.

## Current recovery, 20 October at 13:09 Hong Kong

The first reboot worker (56883) settled at 05:00:01 UTC with no new provider
calls. Gatecoin attempt 14 failed during replay with `Changed phase on resume`.
That terminal attempt and all its original files remain unchanged. P10/evidence
were deferred before dispatch for the open service circuit; their last unused
owner attempts remain available. Do not restart the first adapter.

A bounded, reviewed replay repair is now active: **PID 90887, process start
1165063**, armed at 2026-10-20T05:09:24.953255Z. Its fixed command is
`.venv-context/bin/python scripts/legal_integration_reboot_repair.py arm`;
the exact prefix is approved, but **do not arm it again**. Check
`replay-repair/worker.json`, `activated.json`, `activation-refresh.json`,
`node-result.json`, `result.json`, `worker-error.json` and `supervisor.log`
before any further recovery. Activation succeeded at 05:09:28 UTC and mission
refresh is in progress. No new provider dispatch is claimed at this checkpoint.

The defect is deterministic JSON reconstruction: canonical storage changes
object field order, affecting source-record and locator traversal. Thirty
actual requests were checked; three had order-only differences. The repair
authenticates full record populations and every other field, restores the exact
saved request, and recovers response field order from authenticated original
provider messages. Full replay passed all five completed synthesis levels
(146 validated calls) and the pending four-call sixth level, including unchanged
phase identities and measurements. It made zero provider calls. All 115 focused
tests passed. The diagnostic and review are retained in this directory.

The operational repair is a single documented recovery segment of the already
interrupted attempt 14. The original attempt record remains byte-for-byte equal
to its prior value; the recovery segment is a separate row-level record. The
original phase admission, service reservation, 3,436 charges, 8,100-call ceiling,
24-replacement reserve and deadline remain unchanged. The saved boot UUID is
unchanged; its reported UTC start shifted by 75 seconds. The repair authenticates
the kernel boot UUID and preserves both timestamp observations without changing
the deadline or retry schedule.

After Gatecoin settles, the worker releases only the original P10/evidence
pre-dispatch service deferrals if the circuit has actually recovered, then runs
the ordinary master. Production code, current binding and grant remain untouched.
Do not edit the new repair script, its review, bound checks or either adapter
while it is active.

P14's exact candidate failure is now reproduced with its real request identity.
It measures 76,966 bytes / 18,841 tokens against the ordinary 12k input limit.
An isolated proposed downstream transport preserves the request/schema and
measures 66,026 bytes / 15,422 tokens (provider-visible 64,919 / 15,228). This
establishes local fit only. The production candidate and criticism constructors,
optional-phase dependency, finite owner registration and live validation remain
unrepaired. P14 is still FAILED at 11/11. Full legal answers, corpus applicability
and all six complete matched tool evaluations remain open.

The prior checkpoint below is historical.

The approved command `.venv-context/bin/python
scripts/legal_integration_reboot_resume.py arm` started the host worker at
2026-10-20T03:58:25Z (11:58:25 Hong Kong). PID 56883 has start identity 747297,
on boot 03526cb5-5413-485c-ae59-518cba7e4eb7. The exact arm prefix is approved
for future use, but the adapter is one-shot: **do not arm it again while this
worker runs or after a partial reconciliation**. Read its receipts first.

Reconciliation completed at 03:58:26Z. Gatecoin attempt 14 remains the same
attempt. The pending no-output dispatch `reduce-gatecoin-5-0` is archived under
`before/`; its request hash remains
`5f314faaa345c9318c75cbf867d18fcce493dcf0c447c5c3a4b22c35a7b1fcb7`.
All 146 earlier Gatecoin results, 109 P14 results and the first 3,436 global
charges were rechecked against their retained hashes and remain unchanged.
The original retry due time was 08:32:38 Hong Kong; it is overdue, so normal
wait validation can release it without starting another two-hour cooldown.

Mission check/status/admit passed after the second boot. The master `run`
command found no ready command nodes; the ready items are agent/live owners.
The recovery checkpoint was appended to mission history and its exact mission
`refresh` command passed at 04:03:22Z. The detached worker then entered normal
master reconstruction and Gatecoin adoption. Check `resume-started.json`, the
global call ledger and ordinary provider receipts to establish dispatch;
`armed.json` alone does not establish a provider call.

The worker resumes Gatecoin's existing reservation first, then invokes the
ordinary live master to continue independently eligible P10/evidence and
answer/tool work. No budgets or deadlines were reset: 8,100 total master calls,
24 delayed replacements (17 previously charged), and deadline
2026-10-20T18:55:16Z / 21 October 02:55:16 Hong Kong remain controlling.
Production code and provider class identity are unchanged. The 82 focused
tests passed; they establish local recovery controls, not legal acceptance.

P14's earlier overload recovered at slot 3404; slot 3405 finished synthesis.
Its separate candidate request was refused locally at 18,841 tokens against a
12,000-token default. The larger capacity profile does not cover its direct
constructor. The product saved a PREPARED baseline, but the diagnosis treats
the optional candidate failure as a preparation blocker. Details and a bounded
repair proposal are in `p14-diagnosis.md`. Do not edit bound production files
under the active worker or erase the failed owner attempt.

All four legal questions, 46 obligations, 35 readings and six complete matched
tool evaluations remain governed by the existing integration master. This
recovery makes no completion or legal-correctness claim.
