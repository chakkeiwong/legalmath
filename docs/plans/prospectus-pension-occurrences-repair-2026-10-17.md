# Pension occurrence-schema repair

This is a changed repair of `basf-references/attempt-008`, under the same
original task and sole execution authority. Attempt008 and its failed outputs
remain sealed. The general-build direction and all59 obligations/44tasks remain.

## Reproduced defect and skeptical audit

Attempt008 passed103 focused tests, then failed after44.454676466seconds with
`TypeError: list indices must be integers or slices, not str`. The independent
verifier indexed `quantity['source']` as a dictionary. The retained005 public
consumer actually returns a dictionary for statement cells and a nonempty list
of occurrence dictionaries for pension-table cells. The synthetic fixture used
dictionaries for both. This is our integration/fixture defect; it provides no
evidence of a package defect or a failure of interval arithmetic.

Repair the verifier to inspect every occurrence, require the original source
shape, join the fragments in their retained order, and check the complete
literal, source identity, offsets and location against the graph before parsing
the number. Preserve the public consumer and its preceding answer. Correct the
fixture to the actual schema, test missing/corrupt occurrences, and include a
small retained005-schema regression. Retain a bounded traceback on any new
runner failure so a future repair can identify the failing line.

Audit verdict: proceed with this changed repair. The entire005 consumer remains
the comparator; neither fixture passes nor mutation counts are acceptance.
Actual public-consumer on/off execution and separate integer-scaled arithmetic
remain primary. No source, accounting-scope or rounding assumption has changed.
The original import mismatch is avoided with `PYTHONPATH=src` and runner-pinned
imports. Methods must be frozen before admission. No unchanged retry of008.

## Evidence contract and assumptions

Question: does the independent check handle the real source schema and validate
the actual public consumer without losing a source occurrence or unknown?

Primary criterion: actual normal consumer on/off, complete005 baseline equality,
all four dated relations/eight enclosures checked independently, and all declared
semantic/profile alterations rejected. Retained schema, source fragments and
unknown-dash checks must pass. Arithmetic hypotheses remain half-million and
one-million per amount, not a source-reported rounding algorithm.

Promotion veto/repair trigger: missing or corrupted occurrence accepted, changed
baseline, dropped unknown, invented complete scope/cause, or scoped completion
leaking into original-task acceptance. Continuation veto for the affected run:
corrupt baseline/original source, method mutation during execution, or180seconds
and32MiB additional-retention ceilings. Runtime/test counts are explanatory.
Passing does not prove the accounting bridge, actual rounding method, source
error, legal exhaustiveness, original task completion or whole-build completion.

The source list is a reviewed public-schema requirement, not a one-occurrence
assumption. A multi-fragment fixture checks joining; every occurrence is checked.
The independent integer lattice is retained, not replaced with the production
Fraction helper. Tests intentionally changing the data must repin the comparator
so they exercise source verification rather than only the outer digest.

## Bounded execution and refresh

Prepare focused checks with:

```
env PYTHONPATH=src CUDA_VISIBLE_DEVICES=-1 .venv/bin/python -m pytest tests/prospectus/test_rounding_enclosure.py tests/prospectus/test_basf_pension_reconciliation.py tests/prospectus/test_basf_pension_note.py tests/prospectus/test_build_contract.py tests/prospectus/test_execution_authority.py -q
```

Freeze a reviewed revision207, original BASF admission allowance8->9, retaining
all eight prior admissions and008's recorded44.454676466seconds. Historical
elapsed time not recorded remains unknown. This is one bounded changed repair,
not a new lineage. No network, external opinion, GPU or installation is needed.

After check/status/admit, read the admitted dossier and execute:

```
.venv/bin/python -m scripts.prospectus_pension_reconciliation --attempt docs/implementation/prospectus-execution-authority/attempts/basf-references/attempt-009
```

Use one-second tool yields and poll the original session. Retain actual outputs,
JUnit, independent verification, controls, manifest, failure trace if any and
decision note in009. Record, refresh and inspect the named conditional criterion.
Original reference completion stays pending. Continue to the BES printed-unit,
bilingual investing and property-comparative consumer gaps under reviewed
same-task refinements; do not stop at this checkpoint.
