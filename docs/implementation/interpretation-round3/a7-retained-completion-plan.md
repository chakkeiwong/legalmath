# Complete independent checks after a transport interruption

Attempt 07 passed all 391 tests and completed the 90-row source/candidate matrix
for 23EC46. One batch returned an extra row; the single permitted output repair
corrected it. The final criticism request then failed with `stream disconnected
before completion`. The attempt correctly remained FAILED, consuming five new
calls and bringing the authorized ledger to 70/100. All input and artifact hashes
were checked without mismatch. This is a transport failure, not evidence that the
completed matrix or interpretation method is invalid.

The seven-attempt stop has fired. Inspection found a specific no-new-call repair:
attempt 06 contains a returned criticism response for exactly the same request
hash and schema as the failed call. The original reservation is already counted.
Use the manifest-verified attempt-07 responses for source, generation and fidelity,
and the manifest-verified attempt-06 response for criticism. Revalidate every
response against current code and rerun Java checks. The earlier transport
failure remains in attempt 07; its reservation is not refunded or relabelled.

This explicitly revises the supervisor to **eight** failed attempts maximum,
solely to complete this retained-evidence repair and the previously unexecuted
independent checks. The increment ceiling remains **93** and the total authorized
ceiling remains **100**. The 23EC46 route permits **no live dispatch**. 24EC16
replays its attempt-05 prefix and permits only missing fidelity and criticism
plus their bounded output repairs. The paired challenge remains fresh. A fixed
reviewed JSON replay plan records the source-specific paths and task override;
all of its manifests are supervisor inputs. Unexpected replay misses stop that
investigation rather than spending calls outside its route.

## Correct the continuation decision

The previous pilot stopped after a failed source investigation, leaving the
independent second source and paired challenge unexecuted. That ordering confused
an acceptance veto with a continuation veto. Complete both source investigations
and the independent challenge while their input integrity and hard budgets remain
valid. The final Boolean acceptance criterion remains their conjunction. A failed
source cannot pass merely because the challenge succeeded. Source corruption,
invalid replay provenance or exhausted shared limits still stop dependent work.

## Required preflight and acceptance

Test task-specific routing with exact identities, wrong-task/wrong-schema refusal,
unchanged allowance and retained source manifests. Run the complete 23EC46
investigation once with a provider that raises on **any** live invocation; require
all 90 checks, completed criticism, fresh local Java checks and unchanged ledger.
This diagnostic supplies engineering replay evidence only, not an independent
model observation. Execute the final full regression, then both sources and the
paired seeded omission/clean control under the fixed supervisor.

The first no-live preflight found that the unused failed criticism has the same
request hash as the earlier successful invocation, so its reservation cannot be
inferred uniquely from that hash alone. Preserve the refusal to guess. The task
router excludes the overridden task from the base replay index, while still
verifying every byte against its manifest. Only the explicit alternate manifest's
returned response and recorded successful reservation may supply that task.
Excluded entries cannot themselves replay or authorize a new dispatch. A regression
must retain these refusal paths and reject tampering even in an excluded entry.

The primary criteria, sources, candidates, model route, evaluation date and seeded
challenge definitions are unchanged. This is not an English-accuracy experiment.
The 24EC16 continuation needs six primary calls; four reservations cover the
paired challenge with repairs, so require at least ten at startup. There are 23
below the unchanged increment ceiling. Additional failures remain counted and
bounded by per-source actions and time. Model self-consistency, response reuse and
passing software tests cannot supply a legal correctness probability.

Evidence goes to `artifacts/interpretation/round3/A7/attempt-08/`; the no-live
preflight goes to `.localresources/interpretation-round3/retained-completion-probe/`.
Record actual completion or failure, all residual questions and the updated
successor plan. Do not erase any earlier stop, response, failure or reservation.
