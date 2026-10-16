# Executing and inspecting the interpretation challenge revision

Use the existing environment and reviewed wrapper from the repository root:

```sh
.venv/bin/python scripts/run_assurance_gap_master.py status
.venv/bin/python scripts/run_assurance_gap_master.py phase G7
.venv/bin/python scripts/run_assurance_gap_master.py regression
.venv/bin/python scripts/run_assurance_gap_master.py phase G8
.venv/bin/python scripts/run_assurance_gap_master.py deliver
```

The phase runner reserves an immutable attempt before dispatch. A completed
phase returns its retained result; an interrupted phase cannot be silently
restarted. Every failed retry requires the prior manifest hash, causal repair
and an executed passing focused check. Source retrieval G5r is mandatory: G5's
successful accounting of attempts did not itself establish successful authority
acquisition. `next-phase-plan.json` is refreshed after each phase.

`regression` prepares G8 in parallel with G7 using the same frozen source and
separate outputs. It does not make G8 complete. G8 consumes its passing record,
checks current implementation identity and builds the updated documents. Delivery
requires a recorded inspection of those exact PDFs and preserves the old future
window before creating a new one. A window is an observation protocol, not an
observation or an accuracy result.

## Product entry point

The optional profile is enabled on `CompleteInvestigation` with
`input_profile='readable-tables.v1'`, the existing source/executable reference
protocol and `challenge_options={'batch_size':12,'rounds':3,'maximum_actions':24}`.
Machine qualification remains enabled. The concrete construction, selected
question and complete official source are in `scripts/assurance_gap_live.py`.
These numbers are reviewed pilot bounds, not a universal capacity recommendation.

The stage runs after source inventory, rival interpretation search and exact
question assignment. It builds nine challenges for each distinct substantive
candidate/question pair. Aliases share issue spending. Source cues are retained
as questions, never as proof of meaning. Both readers receive the whole original
source, candidate collection, question collection and challenge collection. Only
the requested response subset is bounded. First-round responses are blind;
later rounds receive the same prior-round evidence.

Every response may propose exact-source-supported formal obligations or new
interpretations. The independent total-Boolean checker replays each proposed
obligation and retains violating valuations. It does not remove legal
candidates. A new interpretation remains visible; it is not silently called
fully investigated when no corresponding downstream executable proof has run.
All differences, unassessed responses and missing authorities survive the
follow-up limit.

The dossier binds the actual stage files. Verification reruns the Lean kernel,
recomputes the finite certificates, rejoins the response history and checks
that no spent action has disappeared. Whole-method observation also binds the
input codec, provider route, local dependency files, toolchains, stage timing,
question and source. Remote model weights and publication chronology remain
unattested.

## Interpreting the evidence

`CONDITIONALLY_REJECTED` means that a candidate violates at least one declared
formal obligation at a replayed valuation. It does not establish that the
obligation follows from law. `NO_DECLARED_OBLIGATION_VIOLATION` means the finite
checker found no such violation in its complete declared Boolean domain.
`NO_FORMAL_OBLIGATIONS` and `UNSUPPORTED` are distinct qualifications.

`execution_complete` accounts for the required processing under the selected
profile; it never means legal correctness. New unprocessed alternatives or
missing perspectives prevent completion. An unresolved explanation difference
can remain after all permitted processing has been executed. The legal result
stays `NOT_ESTABLISHED`, with no release authorization.

The same grant and fixed arm pay for failures, timeouts and successful replies.
The new development arm is capped at 48 calls within the original 500-call grant.
The old 120-call future pilot allowance is reused, not duplicated. No old issue
limit or unresolved historical investigation is reset by this revision.
