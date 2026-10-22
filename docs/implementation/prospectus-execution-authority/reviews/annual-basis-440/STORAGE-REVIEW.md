# Pre-admission storage forecast correction

The freeze stopped after retaining its inputs, freeze manifest and proposed
revision, but before cutover or admission. Its forecast was 135,508,848 bytes
before the required 2 MiB reserve, exceeding the unchanged 128 MiB new-material
bound. Retain this failed freeze and its original proposal. The failed wrapper
did not save elapsed time, so charge 60 seconds conservatively as unmeasured
preparation time; do not report that allowance as measured runtime.

The forecast added three entire 12,559,401-byte programs on top of the proposal
already counted in current usage. The authority code actually writes one full
revision, expands the existing current program by its size difference, and writes
an admission containing this task and its bindings, not the whole program. The
previous admission occupies about 320 KiB. This is a forecasting error in our
submission method, not a package defect or a failed source-meaning check.

Use one new, separately retained pre-admission accounting method. Keep the
original freeze, proposal and review unchanged. Retain a revised proposal and
review containing the additional accounting evidence, charge that duplicate
proposal in full, and forecast one full revision, the actual current-program
growth, a conservative admission allowance of 1 MiB plus the serialized task,
four full production-package copies, 12 MiB for results, and 2 MiB for remaining
authority metadata. The four package copies cover source, build output,
installed files and an uncompressed wheel allowance. Existing usage includes
all candidate files and the failed original proposal. Apply the original 2 MiB
reserve after this calculation. Do not delete evidence to make it fit.

Skeptical audit: PASS for this one pre-admission forecast recalculation. The
production baseline and all six candidate results remain unchanged. The complete
original 15-admission lineage, 600 new/2560 cumulative substantive seconds and
128 MiB new/448 MiB cumulative storage limits remain in force. This does not
reopen the consumed candidate recovery. If the corrected forecast still fails,
do not cut over or submit this proposal. The independent remaining-source review
route remains available subject to its own reviewed allowance.

The corrected proposal adds this note, the failed-freeze charge, the accounting
method and its forecast to the task's retained inputs. The original frozen
submission operations can perform cutover, ordinary/installed stages and sealing
unchanged; only the explicit proposal and review paths supplied to the authority
change. The authority admission checks those additional inputs.
