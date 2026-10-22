# Source-primary validation: regression blocked by a wrong inherited expectation

Revision251, entitlement admission007. The reviewed preparation reproduced both
production defects before editing. Its immutable evidence and repaired methods
remain unchanged. This admission ran only the regression stage once. It failed:
381 tests passed and one failed; zero tests were skipped. Primary and current
stages were not run. This is a failed validation package, not task acceptance.

The failing assertion is
`tests/prospectus/test_closure_mechanisms.py:78`. With Bank CET1=10% and Group
CET1=5.125%, it expects no conversion. The original SEB memorandum PDF65 states
distinct strict thresholds: Bank<5.125% OR Group<8.00%. The expected result is
conversion. The source excerpt, original PDF/extraction bindings and old method
are retained under `reviews/conversion-source-primary-251/`. The new independent
Decimal threshold controls passed. This failure does not show a package defect
or disprove the repaired predicate. It shows our inherited test encoded the
same source-reading error as our original implementation.

The revision251 audit missed this stale assertion. Its test-count preservation
rule did not make the old expected value correct. Correct the expectation with
both an affirmative conversion assertion at Group5.125% and a strict-boundary
no-conversion assertion at Group8%, retaining the zero-principal/economic-recovery
checks. Do this under a changed reviewed plan, retaining the failed run and all
previous admissions. Do not edit frozen methods or rerun this admission.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Conclusion excluded |
| --- | --- | --- | --- | --- | --- |
| Retain regression failure | 381 pass; one wrong inherited expectation | Regression veto fired; later stages withheld | Primary and fresh-current behavior remain untested | Review source-based expectation repair, freeze and explicitly revise cumulative allowance | Whole entitlement/build completion |
| Keep source-semantic repair as candidate | Original PDF65 distinguishes the two thresholds | No source disagreement found in the inspected clause | Wider contract and legal consequences remain open | Validate downstream Q5 and independent prices/shares after test repair | Actual conversion or external-package defect |

The regression process completed in1.08s; the retained stage measured
3.8707225588150322s including authentication and checks. Preparation measured
15.686658074148s. Total measured substantive time so far is19.557380632963032s
against the existing480s cumulative ceiling. Four native PDF calls were used in
preparation; zero additional calls occurred here. The original six-call ceiling,
80MiB incremental storage ceiling and all closed parser-campaign bounds remain.
Historical unmeasured time is UNKNOWN. No network/OCR/model/GPU/install call,
git publication or external message occurred. CPU devices were used with
CUDA_VISIBLE_DEVICES=-1; deterministic checks need no random seed.

Strongest alternative explanation: the excerpt could be the wrong edition or
the test could intentionally target another instrument. Both are inconsistent
with the retained profile/source bindings and this test's SEB fixture; the
8% Group threshold applies to the inspected original. The wider contract and
any actual regulatory determination are not established by this clause check.
Publication/knowledge uncertainty, supplied prices/FX, holder versus registered
name aggregation, and the other original obligations remain open.

Attribution: our source interpretation and insufficient distinguishing tests,
followed by an incomplete regression audit. No fundamental package limitation
has been demonstrated. The next smallest discriminating result is the same
frozen-source primary/current validation with the source-correct expectation;
no production arithmetic or admission repair is authorized by this failure.
