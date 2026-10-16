# GPT-6.1 Sol returned a valid source inventory

10 October 2026. Both user-requested canaries passed on the configured Codex
service with explicit `--model gpt-6.1-sol`. The tiny JSON response took 16.156
seconds. Replaying the exact 32-unit source request that had timed out on Astra
took 259.430 seconds and passed the unchanged schema, source-span and inventory
validators. It returned 26 claims and accounted for all 32 source units.

This establishes a working route for this source-inventory piece. It does not
establish a complete answer, legal entailment, overall model superiority, or any
selected tool's contribution. All four original questions, 46 obligations and
35 original readings remain visible in the mission; zero of the six selected
tools is fully evaluated at the answer level.

## What was wrong, and what the canary establishes

The first four calls encountered invalid source accounting and exact-quotation
failures. Calls 5 and 6 selected `gpt-6-astra` and exceeded the 300-second
application deadline without complete structured output. The source-span method
was therefore untested live, and the tool-enabled candidate was never reached.
The timeouts do not establish that the packages or legal reasoning failed.

Call 8 uses the exact call-6 request hash
`54e0a372e0d886d2826c3880c407cc49da6f78bc974d19224682eee0c6b58c5a`
and the exact retained schema. The service route, source text, response format,
validators, byte limits and 300-second policy are unchanged. The requested model
is the deliberate difference. All 32 source units have one valid disposition;
21 link to claims and 11 are explicitly contextual. Quotation selection resolves
back to the retained Unicode text without normalizing it.

The CLI reports missing local metadata for `gpt-6.1-sol` and uses fallback
metadata. This is a client metadata warning, not evidence of a different model
being requested: the retained argument arrays explicitly select `gpt-6.1-sol`.
It did not prevent either response. The remote backend model is not independently
attested. Official model pages returned HTTP 403, including trusted fetches.

The exact cause of the Astra timeouts remains unisolated. These are sequential,
single-response observations; service recovery could also explain the successful
replay. The plan's phrase “reached the service” was stronger than the failed
requests' retained CLI events establish. There is no server trace proving receipt
or identifying their timeout cause. The source replay also used 86% of the
five-minute response allowance; larger or slower stages can still time out.

## Evidence and decisions

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Accept basic Sol availability on this route | Exact tiny JSON and schema passed in 16.156 seconds | No transport, output or forbidden-tool veto | One request; backend revision unattested | Use explicit Sol for the source workload | General availability or performance |
| Accept this source-inventory piece as structurally valid | Exact replay passed schema, source-reference and inventory checks in 259.430 seconds | No missing/repeated unit, unrelated claim link or invalid quotation detected | Legal support was not adjudicated; later stages untested | Select Sol for the next reviewed matched continuation | Complete source analysis, English correctness or tool benefit |
| Keep the complete-answer mission open | Neither full baseline nor candidate answer exists | Missing complete matched answers blocks contribution findings | Capacity, latency and downstream fidelity | Freeze equal remaining effort on both arms before dispatch | That integration is complete |

| Inference status | Result |
|---|---|
| Hard veto screen | Both bounded canaries passed; earlier Astra timeouts and quotation failures remain retained. |
| Statistically supported ranking | None; one sequential replay per model is not a model comparison study. |
| Descriptive-only differences | Sol returned this source response in 259.430 seconds; Astra call 6 had no complete output at 300 seconds. |
| Default readiness | Sol is selected explicitly for the next reviewed pilot; no global configuration default is changed. |
| Next evidence needed | Complete matched baseline/candidate answers with actual downstream tool consideration and source-grounded review. |

Post-run red team: transient service recovery is the strongest alternative to a
model-dependent explanation. Repeated matched observations would be needed for a
latency ranking. A later-stage failure would limit continuation without negating
the present successful response. The weakest evidence is semantic completeness:
source integrity checks do not decide whether a claim follows legally from its
quotation. No repair to the legal research direction is justified by this canary.

## Accounting and next execution

The exact command was
`.venv/bin/python scripts/legal_mission_model_canary.py execute`.
The [reviewed plan](../../../plans/legal-mission-sol-canary.md) and immutable
protocol retain the checks and assumptions. The run used `.venv`, Codex CLI
0.153.4, and commit `cde11a610cbd1e90eafecfa0cbda6efd51f9bef2` with the retained
dirty worktree. It ran from 07:29:23.995733 to 07:33:55.299192 UTC, wall time
275.596 seconds. GPU devices were intentionally hidden. No seed is exposed by
the provider. The source request hash identifies the data version.

Evidence root:
`artifacts/legal-mission-control/2026-10-10/live-pilot-400/sol-canary/`.
`run-manifest.json` preserves the environment, clock, exact command, plan and
result locations. Each step retains its actual argument array, response,
provenance and result. The source step additionally retains the validated
inventory. Raw provider evidence is in slots 7 and 8 of the shared
`provider-evidence/` directory. Reported source-replay usage was 33,656 input
tokens and 10,212 output tokens; this is provider usage, not independently
verified billing.

The original grant now records **8/400 calls**, leaving 392 in total before
**12 October at 04:28:01 UTC**. Both new calls were charged to baseline/core;
there were no retries, refunds, candidate calls or transfers from other stages.
Six previous enabling detours and all immutable failed evidence remain. This
user-requested diagnostic made no product-source repair and creates no new repair
allowance. The protected historical allowance hash is unchanged.

The next reviewed continuation must explicitly select `gpt-6.1-sol` for both
arms. At most **28 new core calls per arm** can preserve equal remaining effort:
baseline/core has used 8 of its original 36. The other original stage caps remain
3 question-assignment, 82 scoped, 64 dossier-review, 1 interaction and 1 synthesis
per arm. Review whether the retained five-piece method fits that envelope before
dispatch; do not prune sources, silently enlarge limits, or treat the canary as a
completed full-source inventory. Retain the three failed pilots and do not restart
their sealed configurations. No worker remains running after this diagnostic.
