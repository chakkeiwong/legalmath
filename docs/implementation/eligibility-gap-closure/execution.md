# Execution record

The audited plan is `docs/plans/eligibility-gap-closure.md`. The material dirty
baseline is preserved in `baseline.zip` and `baseline.json`; the Git commit alone
does not describe that baseline. Historical live grants remain exhausted and
unchanged. All work in this increment is offline and uses no human quality labels.

## Focused development checks

G1/G2: `.venv/bin/python -m pytest -q tests/prospectus/test_joined_eligibility.py`
passed 8 tests. These check conditional equations and evidence handling, not
English-law correctness or real transaction eligibility.

G3 initial check: the executable/source reference suites returned 3 failed,
26 passed. A missing concatenation operator in the new transport instruction
caused a Python `TypeError` before provider dispatch. The scoped journal stopped
without making a call, as intended. Repair: add the concatenation operator and
rerun those same two focused suites. The criteria and historical records are
unchanged; this is an implementation failure, not evidence against references.

The repaired G3 suites passed 29 tests. The initial calendar proof attempt
exposed an omitted equality rewrite in a hypothesis and a tactic unavailable in
the pinned Lean standard library. The repair substituted the year equality in
that hypothesis and used `Classical.byContradiction` explicitly. Lean then
checked the year-step, ordinal-order and rank/ordinal equivalence theorems;
their disclosed standard axioms are `propext`, `Classical.choice`, `Quot.sound`.
There is no `sorryAx`. The date and existing constructor suites passed 29 tests,
including changed-date/comparison/fact/source attacks against certificates.

Before the full run, the controller was reviewed for stale predecessor reuse.
It now verifies predecessor output hashes even when reusing a successful phase.
The fixed local runner reserves attempts before work, stops on failed criteria,
requires a causal repair note before retry and refreshes the next-phase plan on
success or failure. Its focused failure/reuse tests precede the native campaign.

G0 attempt 001 passed. G1 attempt 001 stopped on a malformed generated conflict
case after seven cases had executed on each backend. The fact's conflict IDs
were `a,b`, while its snapshot index still named the earlier single observation.
The production evidence validator correctly rejected the inconsistency. Repair:
make the generated conflict fact and its evidence index agree; add a focused
test that every generated challenge passes integrity before testing abstention.
The failed attempt and both native reports are retained. Since the method/input
identity changed, G0 must also run again before the repaired G1 can be accepted.

G0 attempt 002 and G1 attempt 002 passed. G1 checked all seven models with
136 native executions, eleven independent Boolean equivalence obligations and
twenty-one detected mutations. G2 attempt 001 stopped before issuing a report:
the archive's `retrieved_on` field contains both date-only and precise timestamp
values. Its adapter incorrectly appended midnight to an existing timestamp.
Repair: preserve precise values, normalize only date-only values, and validate
all retained archive rows in a focused test. This preserves source currentness
as unknown. The failed attempt remains available for inspection.

## Accepted computational results

The timestamp repair passed six controller checks and an integration preflight
for all three prospectuses. The subsequent complete run passed G0 attempt 003,
G1 attempt 003, G2 attempt 002, G3 attempt 001, G4 attempt 001 and G5 attempt 001.
Each phase checked that its method/source identity remained unchanged across
execution. The method snapshot is under G0 attempt 003. Tests used the application
`.venv`, intentionally CPU-only.

- Seven conditional models: eleven full-domain Boolean equivalence obligations,
  twenty-one detected mutations and 136 actual target executions.
- Bank integration: three prospectuses, fourteen obligations each, qualified
  outcomes; 110 integration and adjacent tests passed.
- References, scheduling and capacity: 64 tests passed without live calls.
- Dates: three Lean propositions with disclosed standard axioms; 3,652,059 valid
  dates checked against an independent ordinal codec; 49 cases per backend,
  giving 98 executions; eight unchanged encoded readings certified and one
  unencoded reading retained; 29 focused tests passed.
- Final affected regression: 338 passed, zero failures/errors/skips.

Test suites overlap and their counts are not added. The native campaigns total
234 executions; they do not measure legal accuracy or establish a backend
ranking. No stochastic ranking was attempted.

The G5 freeze records the revised method and known sources. Its future
observation list is empty. `python3 scripts/build_reader_facing_monograph.py`
passed, retaining 133 cited documents, 288 citation occurrences and 207 source
labels. The monograph has 345 pages, companion 78, exported process guide 21.
Rendered inspection and file identities are in `document-review.json`.
