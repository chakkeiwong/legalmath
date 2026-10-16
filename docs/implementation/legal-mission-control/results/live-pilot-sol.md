# The fresh Sol baseline exceeded the response deadline

10 October 2026. The matched continuation stopped on its first source-inventory
request. Call 9 explicitly selected `gpt-6.1-sol`, but no complete output existed
at the 300-second application deadline. The provider recorded `E_RESOURCE_LIMIT:
Codex call deadline`; the outer `E_REFERENCE` means the required inventory was
unavailable. It is not evidence that a returned legal proposition was rejected.
The candidate tools were not invoked and neither arm produced a complete answer.

The request and schema are byte-identical to successful canary call 8, and the
actual Codex options are identical after ignoring temporary paths. The shared
request hash is `54e0a372e0d886d2826c3880c407cc49da6f78bc974d19224682eee0c6b58c5a`.
The request is 56,087 bytes with 32 source units. The CLI recorded a reasoning
event and the same missing-model-metadata warning seen in the successful canary.
It did not record a complete answer or completion usage. Both startup metadata
and plugin warnings therefore remain explanatory evidence, not an identified
cause. The earlier valid canary took 259.430 seconds, close to the same cutoff.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Reject this complete-answer comparison as unavailable | Full baseline/candidate answers absent | Missing required inventory and response deadline fired | How long this exact request would need to finish | Review a bounded inventory response-window change before another dispatch | Sol is unavailable, tools are ineffective, or a legal argument failed |
| Preserve the successful canary separately | Earlier exact response passed source and inventory checks | No retroactive invalidation of that result | Variable latency or transient service behavior | Use that evidence to justify a timing hypothesis, not a model ranking | The canary guarantees workflow completion |

| Inference status | Evidence |
|---|---|
| Hard veto | No complete response within 300 seconds in call 9. |
| Statistically supported ranking | None. |
| Descriptive-only difference | Call 8 completed in 259.430 seconds; the next identical Sol request did not finish within 300 seconds. |
| Default readiness | No timeout or model default is promoted. |
| Next evidence | One explicitly reviewed policy that permits more time for the same source work, with identical treatment of both arms and the original absolute deadline. |

The strongest alternative explanation is a service stall rather than an
insufficient time allowance. A longer window may still fail, which would reject
that response policy without proving the legal research direction invalid. The
weakest evidence is absence of a server-side trace or partial-output timing.
The model's reasoning event does not prove that a complete response was imminent.

Exact command: `.venv/bin/python scripts/legal_mission_sol_pilot.py execute`.
Evidence: `artifacts/legal-mission-control/2026-10-10/live-pilot-400/sol/`, plus
shared `provider-evidence/0009-54e0a372e0d886d2/`. The immutable protocol records
matched methods and source identities. `provider-commands/0009.json` records the
actual invocation. `run-manifest.json` records commit, environment, data, plan,
actual clock and terminal result. Measured monotonic wall time is 300.992 seconds.
UTC labels were 09:31:33.925753 to 09:36:12.969561; these differ from the monotonic
duration, so elapsed-time interpretation uses the monotonic measurement. The
absolute grant continues to use its original UTC deadline.

Local validation before dispatch passed 25 tests. The initial new test collection
failed due to an import path, corrected before the passing run; no product source
was changed. Both arm methods matched except tools, and actual source sizes and
history were checked before execution. GPU devices were intentionally hidden.
The provider exposes no reproducible seed. No complete answer, legal closure,
full tool evaluation or statistical model ranking is established.

Usage is **9/400**, all baseline/core, leaving 391 total and 27 baseline core
slots. The deadline remains **12 October at 04:28:01 UTC**. Six previous enabling
detours and all previous reservations remain. No automatic transport retry ran.
The protected historical allowance hash is unchanged. This process is terminal;
its source, protocol and failed result must not be overwritten or restarted.

The next review should address a longer inventory response allowance directly,
with a precise bound, both-arm equality, the core clock and original grant clock.
It must retain capacity vetoes and source/semantic checks. It must not assume
that a larger time budget proves source completeness or tool benefit.
