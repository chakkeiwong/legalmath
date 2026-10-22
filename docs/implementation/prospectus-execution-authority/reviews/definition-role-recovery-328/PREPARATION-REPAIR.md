# Correct the recovery preparation's event expectation

The authority correctly retained attempt066with a REJECT event: its honest
INCOMPLETEresult is not a successful work package. The initial recovery
preparation wrongly required a RECORD event and failed before generating a
proposal or running candidate code. The original method is preserved as
preparation-initial.py and the failed stage receipt remains unchanged.

The corrected preparation requires the exact REJECT reason, the INCOMPLETE
result and all retained output hashes. It neither reclassifies066as successful
nor changes its outputs. The new prepare_reviewed invocation explicitly repairs
this predicate under the same accounting start and carries the failed stage's
measured time and bytes. It is not an unchanged retry or a new trial budget.
Freeze this note, both method versions and both preparation receipts. The
candidate, tests, oracle, original expectations and recovery criteria are
unchanged. Review verdict: PASS for this narrow preparation correction.
