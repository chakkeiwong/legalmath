# Receipt-schema defect after a passing full product comparison

The194 tests passed. The baseline stage completed in115.20536764105782seconds,
retaining complete reconstructed products and answer. Independent source checks
passed all54 groups and522 original occurrences, with48 unresolved governing
dependencies and five groups containing unknown body spans. Its stage result
incorrectly uses `status: COMPLETE_REVIEWED_SCOPE` rather than `status: PASS`.
In `save_case`, the independent scope summary overwrote the runner status through
dictionary expansion. The next stage requires PASS and therefore cannot proceed.
This is a harness receipt error, not a failed source or consumer result.

No successor was launched, no baseline was rewritten and no product method was
changed during the attempt. Seal this attempt FAIL for execution completeness.
A separately reviewed same-task continuation must correct the receipt field,
test its schema and verify/reuse the completed baseline. Remaining omission and
adverse consumers have not run. This attempt establishes no task acceptance.
