# Final cutover review: two continuation paths need repair

The real cohort and callback-interface tasks completed, and two subsequent
agent packages retained useful partial results. Tracing continuation from
those actual states found two material gaps in the authority implementation.

1. A `RECORD` event is permanently non-selectable. Changing its task makes it
   `INVALIDATED`, and recording again returns early. Consequently a reviewed
   next package cannot continue that task with its remaining original budget.
2. An external task is always `WAITING_EXTERNAL`; no supplied-evidence path
   can make it admissible. The controller correctly refuses to invent human
   evidence, but also cannot process genuine evidence if it arrives.

These are our controller implementation problems, not native-package failures
or evidence against the prospectus program. The original cutover test did not
exercise them. Record failing focused regressions first, then make one bounded
repair and recheck all controller tests and real accepted workers. Preserve
the older test artifacts and every previous attempt.

## Repair contract and skeptical audit

Baseline: active revision 2, retained `native-layout-cases` and
`native-candidates` partial packages, accepted cohort attempt 003 and interface
attempt 001, and the current controller code. Pass requires a reviewed task
refinement to select a new attempt under the same budget; an unchanged partial
result must not loop. Changed controller code alone must not dispatch all
partial packages again. Recorded output corruption must remain a repair state,
not become a way to retry. Existing partial results remain unaccepted.

For external work, a reviewed task revision may bind specific supplied files
by path/hash. Missing or changed files stay waiting. All supplied files must
also be admitted task inputs. The external handler and independent acceptance
requirement stay unchanged; file presence permits inspection, never completion.
An arbitrary supplied document must still remain `RESULT_RECORDED` unless its
separate substantive validator accepts it. No external message or request to
a person is implied or authorized by this repair.

Vetoes: a false COMPLETE state, new attempt without reviewed task refinement,
missing/corrupt evidence admission, budget reset, duplicate work or stale
worker acceptance. Counts and elapsed time are explanatory. Source authenticity,
legal truth and package quality are outside this software repair's conclusions.
Use isolated test fixtures; never mutate sealed production evidence for a test.

The audit finds that core-method hashing necessarily makes the two successful
worker receipts stale after a controller change. Do not hide that change or
silently relax current-method checks. Revision 3 grants exactly one further
cohort admission (maximum 3 to 4), retaining its two earlier failures and one
success. The interface has one original admission left. Run both actual
source validators under the repaired method. This is a separately reviewed
local cutover detour, not a reset or new research scope. No further extension
is authorized by this review; a failed repair must remain visible.

This repair does not implement every remaining domain validator. Agent/source
and external tasks still need their reviewed task-specific validators before
acceptance. It supplies the missing continuation path for doing that work.
Audit verdict: execute after the two defects are reproduced. Use bounded
120-second pytest/worker calls, one-second tool yields, retained logs and
ordinary sandboxed edits. No new environment, install or external action.
