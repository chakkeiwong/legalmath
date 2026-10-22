# Independent source corrections retain independent regression invariants

One historical whole-profile assertion failed because H28 was intentionally
corrected after the H38 repair. H38 now compares all its unchanged fields with
its original baseline;H28 independently compares its unchanged fields with its
pre-correction baseline. Exact quotes,offsets and negative controls remain.
The combined suite passes. Production and complete043 evidence are unchanged.

| Decision | Criterion | Veto status | Uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain test-only scope repair | Both field invariants and adverse tests pass | No production/evidence drift | Wider source application | Return to substantive requirements | New legal result or whole build |

The failure belonged to an overbroad test assertion,not the corrected sources or
packages. A changed source field outside the approved record transformations
would still fail the scoped regressions. No independent legal claim is added.
