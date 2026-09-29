# Executed repair for P4 abstraction dispatch

P4 attempt 01 was interrupted after 25 newly reserved calls. The live journal
retains the returned source inventories and every failed/unfinished proposal;
the reservation is not refunded. The immediate defect was in the abstraction
contract: `classification_assumptions` and `missing_information` were required
both as proposal fields and as reading fields, but valid model output sometimes
placed them only in the explicit proposal fields. The validator rejected the
response and spent a repair call rather than carrying the declared information
forward.

The repair unions these two explicit lists into the reading before quote and
source validation, preserving their exact text and deduplicating only repeated
strings. An abstraction failure now also prevents `execution_complete`; a live
case cannot be reported as complete when one required abstraction stage is
unavailable. The next run reuses completed exact model evidence and marks the
interrupted reservation before continuing under the same case journal. No
response, source claim or expected answer is synthesized.

Focused tests cover the carry-forward invariant and the existing journal,
source, abstraction, Java and authority checks. The P4 plan is refreshed before
retry; previous attempt artifacts remain immutable.

The allow list also names the fixed corpus, PIT and evaluation helpers used by
the closure route. The master still accepts only its exact interpreter and
script vectors; these names do not permit arbitrary shell execution.
