# Failed verification trial retained

The201 focused tests and ten-target independent P3 reconstruction passed.
The candidate-answer stage failed with KeyError('dependencies') after ordinary
consume returned. Its full answer was never retained and is not verified.
Dependencies are exposed only by artifact export; the ordinary API does not
promise that field. This is a local verifier defect, not a production or package
limitation. No later stage ran, and no unchanged retry is authorized.

| Decision | Primary criterion | Veto status | Uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain and diagnose failed trial | Tests/P3 evidence retained; full-answer criterion unfulfilled | Harness validity failed | Returned ordinary answer unavailable | Separately reviewed corrected continuation | Complete internal integration or whole build |

PASS in result.json classifies retention/diagnosis only; trial_status is FAIL.
All preparation, preflight and stage costs remain cumulative. Original methods
and source evidence are unchanged. Continuation requires a reviewed revision of
the same task, not a retry or a new task with reset counters.
