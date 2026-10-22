# Entitlement010: retain the source-incorrect regression baseline

The actual regression command ran432 tests:431 passed, one failed, no errors or
skips. BBVA and SEB primary controls were NOT_RUN. The complete XML/stdout and
actual stage failure are retained. This is a failed admission, not a passing
repair and not a package rejection.

The failed test requires separate rounding for different legal-holder IDs that
share one exact registration name, without an explicit registration partition.
The unchanged253 repair refuses this ambiguous legacy input. Original BBVA6.11
and SEB5A.10 aggregate shares registered in the same name under their delivery-
notice premises. The old expectation conflicts with the source and the declared
safe input domain. The254 pre-run review missed this second old baseline.

| Decision | Primary criterion | Veto | Main uncertainty | Next action | Limit |
| --- | --- | --- | --- | --- | --- |
| Retain010 FAIL; no production change | Primary controls NOT_RUN | One source-incorrect regression expectation | Complete repair remains unvalidated | Review all registered grouping expectations, preserve old test and amend it to require ambiguity refusal plus conditional explicit grouping | No whole-task, package or legal-completeness conclusion |

This is our test-baseline/source-model integration error. It does not establish
a fundamental package defect. The strongest alternative explanation remains an
incorrect caller partition; actual notices and beneficial allocation are unknown.
No automatic retry, new extraction or historical evidence rewrite is permitted.
