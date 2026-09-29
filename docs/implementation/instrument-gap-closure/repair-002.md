# Execution-count and input-binding audit

Inspection of I3's individual runtime receipts found that the inherited
assurance summary's `executed_target_cases` includes pre-execution evidence
abstentions. I3 attempt 001's `native_executions: 370` label was therefore wrong.
There are 370 checked target cases: 350 actual compiled evaluations and 20
missing/conflicting-input abstentions. The individual receipts were correct.

The runner now derives and reports all three counts separately. A focused
mixed-result test ensures that abstention is not counted as native execution.
The input identity now also includes the retained citation reading and occurrence
review records used by the document checker. This strengthens reproducibility
after the document repair; it does not change any contract model.

The changed driver/test and review identity require fresh I0–I4 predecessors.
Earlier attempts remain immutable, including the original I4 citation failure.
Final reporting uses the new bound counts, not the old misleading field name.
