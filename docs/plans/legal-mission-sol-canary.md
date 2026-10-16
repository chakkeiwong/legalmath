# User-requested GPT-6.1 Sol canary

10 October 2026. The user explicitly requests a canary using Codex GPT-6.1 Sol.
The admitted task remains `product-contribution`. This bounded service diagnostic
does not restart a failed pilot or create a new repair program.

The last two Astra requests reached the service but produced no complete output
before the 300-second application deadline. The smaller request also failed, so
input size alone is not an established cause. Earlier literal responses failed
source-integrity checks. Plugin catalogue warnings occurred on successful and
unsuccessful calls and cannot explain the difference on current evidence.

## Evidence contract and skeptical review

The question is whether the same configured service accepts an explicit
`gpt-6.1-sol` request and returns usable strict JSON. First send a tiny fixed JSON
canary. Only if it passes, replay the exact request and output schema retained
from call 6, changing only the requested model. Preserve the existing source-span
decoder, source text, source accounting validator and 300-second replay limit.
The historical comparator is call 6 on `gpt-6-astra`, not a concurrent randomized
latency comparison. The requested backend model is not independently attested.

| Item | Role and decision |
|---|---|
| Tiny response equals the requested JSON and satisfies its schema within 60 seconds | Pass criterion for basic service availability only |
| Exact call-6 replay satisfies its schema, source-reference decoder and inventory validator within 300 seconds | Pass criterion for this first source-inventory piece only |
| Changed retained bytes, changed grant history, missing authorization/time, forbidden tool use, or an uncertain prior execution | Continuation veto; no further dispatch |
| Timeout, missing output, malformed schema, or invalid source references | Candidate failure; stop this two-call diagnostic and retain the precise failure |
| Runtime, token usage, plugin warnings and event counts | Explanatory only; no statistical model ranking |

At most two fresh calls are charged to the original baseline/core allocation:
slots 7 and 8 of the 400-call grant. The original deadline is
2026-10-12T04:28:01+00:00. No retry, refund, fallback model, candidate call, or
unallocated call is permitted. Require a fresh start at six retained calls and
refuse restarting a manifest. A subsequent complete-answer comparison must
review equal remaining effort for both arms; canary output is diagnostic evidence.

Assumption audit: `gpt-6.1-sol` is the user's requested model and is exposed in this
agent environment, but support on the configured service is a hypothesis to test.
Official model documentation returned HTTP 403 even with trusted network access.
The 60-second tiny-response limit is a convenience screen, not a documented model
SLA; failure means this bounded attempt failed. The replay's 300-second limit and
200,000-byte input/output caps come from the retained baseline settings and remain
unchanged. Sources and the existing validators are the baseline, not new legal
ground truth. Early checks verify the exact request round trip and retained hashes.

Pre-mortem: a service recovery or routing difference could make Sol succeed even
if Astra's model is not the cause. A tiny JSON pass might coexist with failure on
real source work. A valid inventory can still contain unsound legal propositions.
The conditional exact replay discriminates basic availability from this workload;
neither result establishes general English understanding or tool contribution.

Review verdict: PASS for this bounded diagnostic. The baseline, response checks,
stop conditions, fixed environment and evidence limits are explicit. No product
implementation or semantic acceptance criterion changes. Six earlier enabling
detours remain counted; the diagnostic authorizes no further engineering repair.

## Execution and retained evidence

Run from the repository root with the existing `.venv`:

```text
.venv/bin/python scripts/legal_mission_model_canary.py check
.venv/bin/python scripts/legal_mission_model_canary.py execute
```

Only `execute` needs trusted service access. One bounded command handles both
conditional calls; children have tools disabled, read-only sandboxes, no inherited
conversation and explicit model selection. CPU-only operation sets
`CUDA_VISIBLE_DEVICES=-1`; no GPU is needed. The script refuses a second execution.

Evidence is retained in
`artifacts/legal-mission-control/2026-10-10/live-pilot-400/sol-canary/`:
the immutable protocol, actual command arrays, per-step results, run manifest,
resolved inventory and final result. Raw transport evidence uses the original
shared `provider-evidence/` directory. The result note is
`docs/implementation/legal-mission-control/results/sol-canary.md`.
Update mission history and the reset memo, then run the normal mission refresh.

The scientific target remains the four original questions, 46 obligations and
35 readings. No complete legal answer, obligation closure, tool benefit, backend
attestation or model superiority follows from this canary.
