# One bounded comparison-harness repair

The initial comparison returned FAIL: 107 of 110 checks passed. No production
failure was found. The complete failed comparison, endpoint and legacy records
remain under their original names; compare-initial.py preserves the executed
method before the one repair.

The same-input check wrongly compared the independent expectation table's
expected_numerator/denominator metadata against package request rows, which
correctly omit those expectations. Compare every actual request field exactly
after removing only those two named expectation fields. Exact rational
expectations and package tolerance checks remain separate and unchanged.

Both Shell v2 checks wrongly demanded byte-equivalent results from attempt001's
older output schema. Inspection shows only entitlement_basis differs: it did
not exist in those historical reports. Frozen pre-BondBasis and current outputs
are equal in full. Require that full equality, require exactly this one added
historical field, and require equality for every original retained field. Do not
alter or relabel the historical results. V3 direct/selected full comparisons
already passed and retain their original checks.

Skeptical audit: PASS for this repair. The comparator is the actual pre-edit
kernel, not the old report schema. Projection cannot conceal arithmetic or
event changes because every historical field is compared and frozen/current
outputs must also be equal in full. No production method, numerical tolerance,
endpoint expectation, product artifact or independent acceptance rule changes.
The initial run invalidated these three harness assertions; it did not reject
the numerical candidate or demonstrate a QuantLib defect. One corrected
comparison stage is permitted within the original eight-stage cap. No fresh
package/source call, repeated test suite or deadline/admission reset is used.
