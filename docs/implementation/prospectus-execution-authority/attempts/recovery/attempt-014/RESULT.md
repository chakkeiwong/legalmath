# Retained recovery validation completed

All eight complete actual/clean comparisons from recovery013 pass the original
finalizer, including the three required refusals and exact final restoration.
The unchanged focused suite passes all 44 tests with no failures or skips.
Recovery014 copied 86 original files byte-for-byte; original started metadata
and state commands still identify013 as the source execution. Separate stage
manifests identify014 as the retained-validation execution.

Recovery013 remains REJECT1150: its isolated workspace occupied 2,409,550,339
bytes against its declared 2 GiB limit. This is a measured local resource-planning
failure. No package or OCR defect was established. This repair creates no new
uncompressed fixture and makes no new OCR, native, subprocess or network calls.
Every completed stage reports zero process starts and zero blocked actions.

Reconstruction took 1.3000730141066015 seconds, tests 3.466672700829804 seconds,
and complete comparison 33.34151517227292 seconds, totaling 38.10826088720933
seconds before sealing. The original eight state executions took
578.3167790099978 seconds; those are retained historical work, not new execution.
The seal stage will record its actual time and storage after byte-preserving
internal deduplication. It must pass the reviewed 115-second stage, 400-second
aggregate and 64 MiB packed bounds before this evidence can be submitted.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain current recovery evidence | Eight complete comparisons, original source identities, refusals and restoration pass; 44 focused tests pass | No changed source/method, omitted state, test skip or unexpected process action observed | Both executions share the same product implementation | Seal; bind all original and validation methods and outputs for separate recovery-sequence.v1 acceptance | Independent legal accuracy, source authenticity, portability or whole-program completion |
| Preserve013 rejection | Actual recorded storage failure remains unchanged | Old cap remains exceeded and is not revised retroactively | The previous review missed the original fixture's available size | Retain measured capacity explanation and zero-OCR repair | A fundamental third-party package failure |

The strongest alternative explanation for agreement is a semantic error shared
by both products. Original image/source-unit checks constrain this possibility
without eliminating it. Changed complete products, unexpected accepted malformed
inputs or a different original source would overturn the corresponding result.
No stochastic ranking applies. The original failed execution arrangement has
been rejected; the recovery mechanism remains supported only within this finite
same-host test. Authority recording alone is not acceptance. All four delivery
flags remain false; substantive source work follows the current authority audit.
