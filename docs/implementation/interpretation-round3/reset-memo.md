# Assurance implementation reset memo

**A0–A7 are complete for their recorded engineering scope.** Attempt 08 passed
on 24 September 2026 Hong Kong time: **394 tests**, completed investigations of
23EC46 and 24EC16, and the paired shared-omission/clean-control challenge. The
supervisor records every phase as PASSED. See [execution-report.md](execution-report.md)
and [evidence-summary.json](evidence-summary.json) for verified results and limitations.

Both circular reports remain UNRESOLVED and deny release eligibility. The first
has 90 claim/program results and 70 residual question entries; the second has
384 results (224 deterministic unavailable-program rows) and 222 entries.
The live checker detected all three seeded omissions and accepted the separate
clean control; Java and Python replayed the distinguishing witness. These are
bounded engineering results, not natural English accuracy or a production approval.

Implementation: `src/legalmath/interpretation/assurance/`. Entry points:
`legalmath interpretation-assurance` and `legalmath assurance-monitor`. Read the
[operator guide](operator-guide.md) and [method profile](method-profile.md) for
actual contracts and limitations. The existing search/Java core is reused.
Neither all surveyed papers nor a complete legal language has been implemented.

The fixed master command is
`/home/chakwong/python/legalmath/.venv/bin/python /home/chakwong/python/legalmath/scripts/run_interpretation_assurance_plan.py`.
Use its `status`, `refresh`, `review`, `repair` and `run` operations. Its exact
prefix has been approved; [allow.rules](allow.rules) records it. Model/API calls
and the full API regression use that runner in the trusted context. Do not launch
unbounded workers, use another provider, contact a consultant or send bank data.

The persistent authorized ledger is
`artifacts/interpretation/round2/live-allowance.json`: maximum **100** total calls.
The increment started at 41 and now stops atomically at **93**, including failures.
The earlier four-, six- and seven-attempt stops remain recorded. The latest
`a7-retained-completion-plan.md` revision permits attempt 08, keeping the 93/100
ceiling unchanged. At completion, **78/100** calls were consumed: eight new in
attempt 08 and 37 across this increment. The previous 77-reservation
ceiling is historical; the ledger remains authoritative. Do not silently reset
counts or extend the reviewed limits.
Read the ledger for current consumption; this memo is not a quota counter. Each
pilot source permits 15 journaled actions. Recovery of an already-counted result
does not consume a new invocation and is explicitly labelled in provenance.

Preserved history: A7 attempt 01 passed 369 tests, then the first source inventory
timed out at 180 seconds. It was stopped before spending dependent calls. The
second inventory completed as an orphaned process; its valid response and source
request are preserved at `artifacts/interpretation/round3/recovered-source-inventory.json`.
Both original reservations (42, 43) remain consumed. Attempt 02 passed 375 tests
and failed one stale command-argument assertion; no live calls ran. The named
argument check was repaired and attempt 03 passed all 376 tests.

Attempt 03 completed all 36 source/candidate checks but its critic abbreviated
quotations and then confused candidate IDs with argument IDs in preferences.
Its failure is preserved. The repair makes namespaces explicit and aggregates
independent reference errors. Manifest-verified replay reuses only identical
request/schema responses and preserves the original failed refinement. A no-live
probe reproduced every pair and requested only the missing criticism. The new
tests cover replay tampering, no hidden dispatch and failed-reader visibility.
The ledger stood at 53 at this repair; read it for current consumption.

Attempt 04 repeated an invalid rebuttal target; exact attack diagnostics repaired
that interface. Attempt 05 then completed 23EC46 criticism but hit an invalid
24EC16 expression in the semantic renderer. Unsupported programs now remain
explicitly NOT_ESTABLISHED while valid siblings, including retained deferred
proposals, receive checks. Attempt 06 reached the six-attempt stop: two fidelity
responses used the wrong field names after a generic error. The parser had
discarded the useful validation details. Attempt 07 retains located diagnostics
and includes the response schema directly in fidelity and output-repair requests.
The original malformed response still fails; no judgment was renamed or coerced.
Twenty-three targeted schema/replay/limit tests passed before final execution.

Attempt 07 completed all 90 source checks, repairing one extra-row response, but
its criticism stream disconnected. The same criticism request/schema already
has a valid response in attempt 06. The fixed task-specific replay plan selects
attempt 07 for source/generation/fidelity and attempt 06 for criticism, with no
new live task permitted for 23EC46. A no-live preflight completed that full source
investigation and fresh local Java checks with the allowance unchanged. Fourteen
targeted replay, sequencing and supervisor tests passed. 24EC16's attempt-05
prefix remained frozen; its six missing checks and the two paired-challenge
calls completed in attempt 08 without an output repair. All earlier failures remain.
The corrected pilot continues independent checks after a source execution failure,
but final acceptance still requires every source and challenge to pass.

Repairs also bound fidelity output to exact batches, stop dependent work after
missing inventories, reserve final checks before optional repairs, cap a call by
its remaining deadline, and invalidate monitoring when the evaluation date
changes. The repaired live timeout is 300 seconds with the same model route.
Prior histories and failed evidence remain unchanged.

The final live contract is [live-pilot-contract.md](live-pilot-contract.md).
23EC46 and 24EC16 are development sources. Acceptance requires completed source
and argument checks, reported uncertainty, a detected predeclared exception
omission in three agreeing candidates, and retention of a separate clean control.
It does not measure natural English accuracy, review-time savings or superiority
of one stochastic method. See [next-phase-plan.md](next-phase-plan.md) for further
public-authority resolution, complementary-rule composition, discriminating
questions, sourced cases and withheld
evaluation; external consultancy is a separately authorized last resort.

The worktree contains substantial pre-existing round-2 and monograph work. Preserve
it. The assurance runner checks 191 frozen baseline files and 2,776 historical
evidence files. Do not overwrite old attempts, reset the allowance or infer a
clean result from an incomplete report. Continue a required repair when the
harness is valid; uncertainty alone does not veto further engineering.
