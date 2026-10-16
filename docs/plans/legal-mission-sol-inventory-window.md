# Bounded inventory-response window after the repeated Sol timeout

10 October 2026. This is one reviewed resource-policy repair within the original
P10/evidence task, under the user's instruction to continue. The reproduction is
call 9: identical request, schema, model and CLI options to successful call 8,
but no complete response at 300 seconds. Read `results/live-pilot-sol.md`.
The failed comparison and all nine reservations are retained. This enabling
attempt is counted as the seventh cumulative detour, with one preparation
package ending by 11:30 UTC today and one matched execution. No further automatic
policy revision is included; the ordinary one-detour bound remains unchanged.

## Question and evidence contract

Does a longer bounded response window allow the existing source inventories and
full-source cross-checks to complete, so the original matched answer comparison
can proceed? The exact comparator is the preceding Sol method, except the
inventory-response policy and equal remaining core effort. All sources, source
selection qualifications, legal questions, model, tools, output schema, source
validators, substantive acceptance criteria and product implementation remain.
The 32-unit canary showed a 259.430-second successful response; it is evidence
for testing more time, not evidence that 900 seconds must work.

For `SOURCE_INVENTORY` and `INVENTORY_CROSS_CHECK`, including their existing
output-repair requests, permit up to **900 seconds** at the actual provider
boundary. All other calls retain their original timeout, at most 300 seconds.
Every core call is clipped to a **10,800-second absolute per-arm core window**
started before constructing that arm's runner, as well as the unchanged global
deadline. A validated settings subtype records the extended call bound; ordinary
product settings/defaults remain unchanged. Each dispatch retains the caller
settings, effective settings and remaining clocks so the override is inspectable.

The product's journal still supplies a nominal 300-second request timeout.
The reviewed provider policy deliberately overrides that value only for the two
named tasks. Its separate core clock starts before the product journal and is
therefore conservative. Do not describe the ordinary settings manifest alone as
the effective timeout. Bind the policy explicitly in the new immutable protocol
and record each effective dispatch. No product function is monkey-patched.

| Evidence | Role and decision |
|---|---|
| Complete inventory and cross-check responses validated under the unchanged source rules | Engineering pass for those stages only |
| Two complete answers preserving P10 fulfillment, P11 separation, contrary readings, factual unknowns and actual tool consideration | Required substantive evaluation target; structural completion alone nominates for review |
| Changed source/schema, unequal treatment, lost history, unregistered policy, corrupted evidence or exhausted core/global clock | Continuation veto |
| A 900-second timeout, absent response or transport failure | Reject this bounded timing attempt; stop the provider without retry |
| Invalid complete output | Existing same-stage bounded repair only; retain the exact defect |
| Actual fidelity/dossier capacity refusal | Stop affected comparison without pruning the legal target |
| Source-integrity checks, token use, call count, runtime and solver agreement | Explanatory only; no legal promotion or model ranking |

Both fresh arms receive at most **27 new core calls**. With unchanged other stage
caps, each has at most 178 new calls, 356 together. Nine already spent plus 356
gives a maximum 365 across all attempts. The candidate's nine otherwise unused
core slots stay withheld. The grant stays 400 calls ending
**12 October at 04:28:01 UTC**; no calls, repairs or time are refunded.
Two core windows take at most six hours, and the two 151-call downstream
allocations at 300 seconds take at most 25 hours 10 minutes, excluding bounded
local overhead. That fits the current remaining window; actual dispatch still
uses the original absolute deadline. The minimum inventories consume 12 calls;
actual later fidelity demand remains uncertain and must pass admission.

## Skeptical review and assumptions

The initial idea of merely increasing the timeout was incomplete: overriding
the journal timeout without a separate core clock could exceed the original
core deadline. The revised plan clips every core dispatch against a clock
started earlier than the journal, and records the effective settings. The
baseline is the real nine-call history; no restart or canary output reuse is
permitted. The historical Sol runner and failed result remain immutable.

The 900-second bound is a convenience hypothesis with provenance in the observed
near-cutoff success, not a latency guarantee or production default. The smallest
test is the first actual inventory request. A genuine service stall could still
consume the full window. Longer responses could also yield unsupported legal
claims; the source and semantic reviews remain necessary. Client model metadata
is unknown, and remote backend revision is unattested. No configuration warning
is assumed causal. One successful timed run would show viability on this case,
not superiority or general English interpretation correctness.

Review verdict: PASS for one bounded attempt after local timing/accounting tests.
The response-window hypothesis is distinct from legal quality. The same source
and method evidence will be checked, both arms have equal limits, and all stopping
conditions are explicit. No further parser, package, formalization or tool repair
is authorized by a timing failure. If this attempt cannot produce a valid first
piece, retain that failure and return to the substantive task with the exact
service constraint; do not launch another automatic configuration.

## Execution and phase refresh

Use a separate closed timing adapter so the previous Sol source/protocol can
remain unchanged. Reuse its actual product runner and grant implementation;
the ordinary product source must match the parent. Only the mission accounting
script is extended to count this named one-time seventh detour, with its prior
bytes retained in existing snapshots. Historical snapshots and result identities
must be verified from their retained files, never rewritten to current bytes.

```text
.venv/bin/python scripts/legal_mission_sol_inventory_window.py prepare
.venv/bin/python scripts/legal_mission_sol_inventory_window.py check
.venv/bin/python scripts/legal_mission_sol_inventory_window.py execute
.venv/bin/python scripts/legal_mission_sol_inventory_window.py status
```

Preparation freezes the actual methods, policy and nine-call prefix. Local tests
must check the 900/300-second task boundary, output repairs, core/global clock
clipping, preservation of both arm limits, stop after failure and forbidden
restart. Register the plan and count the seventh detour before dispatch. A fresh
baseline runs first; only its structurally complete answer permits the matched
candidate. Review the actual retained result at each phase boundary. A terminal
failure ends this attempt and triggers a recorded diagnosis, not another repair.

Keep evidence under `live-pilot-400/sol-inventory-window/`, with the actual model,
route, effective settings, source hashes, command arrays, usage, outputs, clock,
plan, commit/environment and terminal result. GPU devices are intentionally
hidden. The result note is `results/sol-inventory-window.md`. Preserve no-seed and
same-model dependence limitations. Update mission history and the reset memo,
then refresh. The four original questions, 46 obligations and 35 readings remain
the substantive denominator; this timing repair closes none of them.
