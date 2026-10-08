# Capacity review of the inherited call deadline

The compact-alias baseline pilot completed both perspectives on all twelve
pairs at approximately 138 seconds each. The matched combined-tool pilot then
timed out at 180 seconds with no completed output. The service sentinel and
four smaller scoped calls succeeded. An earlier original-format large response
required 179.876 seconds and 5,853 output tokens. These observations do not
establish the provider-side timeout cause or a speed advantage for aliases.
They establish that the inherited 180-second limit has little margin on this
actual task and has not admitted a full combined pilot.

The 180-second cap came from prior finite diagnostics, not a user-specified
per-call limit or a qualified full-matrix latency study. Treating it as an
unquestionable default would reject the execution budget without investigating
that assumption. The user's original overall expiry is binding and remains
unchanged. This review explicitly revises only the new continuation's large
batch cap to **300 seconds**, with a 720-second two-perspective journal limit.
The route, model, source, questions, aliases, pair partition and validators stay
unchanged. Existing completed and failed attempts retain their original limits.

Evidence contract: can the same twelve-pair combined assessment return both
valid and fully assessed perspectives within a bounded task-appropriate time?
The exact comparator is the retained combined batch 0 deadline failure. One
reviewed successor attempt may consume at most two repair calls. Pass requires
all twelve original pairs and dimensions validated, actual tool context bound
to their inputs, and no missing reading. A timeout, invalid response or lost
identity is a continuation veto for this design; no automatic retry follows.
Latency and output size remain explanatory. No service reliability, tool
superiority or legal correctness claim follows from a pass.

Resource audit before execution: thirteen calls are consumed (baseline 1,
combined 1, repair 11). The repaired combined batch needs two repair calls,
the other forty combined batches need 80 calls, and the remaining baseline
pilot needs two calls: **97 total**, within 100. Repair calls would be 13/14
under the stricter planned allocation, within the user's 20 maximum. The
84 future calls have a 25,200-second worst-case dispatch budget at 300 seconds,
less than the more than 55,000 seconds remaining in the unchanged window at
this review. Local tool/check overhead must also fit that original expiry;
every reservation still checks it. No time-window renewal is inferred.

Skeptical audit: PASS after revising an unqualified inherited default. Another
180-second retry was rejected. A 300-second cap is a bounded hypothesis with
provenance in the measured task latency and sufficient overall budget, not a
new universal default. Fresh checks must confirm the new per-call cap and
original absolute expiry. If the pilot passes, continue the existing full
combined phase with this reviewed cap. Preserve the complete 492-pair target
and all failed evidence; do not equate execution completion with legal closure.
