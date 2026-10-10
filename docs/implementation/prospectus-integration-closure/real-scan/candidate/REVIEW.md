# Isolated image-binding repair review

The candidate fixes a reproduced local validation error: the actual OCR
producer's method name bypasses a substring check. It recognizes both retained
OCR output forms and image-bearing units, checks that their retained identity
is a SHA256 string, and requires the supplied identity to match. Plain text
without an image remains available. Rendering, raw text and geometry are
unchanged; corrected display keeps `bbox: null`.

The before/after evidence is `candidate-check/baseline-002` and
`candidate-check/candidate-001`. The unchanged implementation fails exactly
16 adverse controls and passes four legitimate cases. The candidate passes all
20. Tests use actual adapter output, the explicit text fallback, and actual
service intake with the protected PDF and retained worker data. They do not
repeat OCR or infer correctness from a synthetic method name alone.

The first baseline fixture error remains in `baseline-001` and the original
test bytes in `versions/before-visibility-repair.py`. Its missing visibility
flag stopped adapter tests before the target boundary. The separate complete
service controls already reproduced the image error. Correcting that fixture
does not change the image oracle or the candidate patch.

Decision: retain the candidate for integration after the active R6 validation
finishes and is committed. The primary guard and service criteria pass in
isolation; active-method integrity checks pass; no package limitation is
established. The main uncertainty is the unexecuted real BES correction
consumer. The next justified action is its current raw baseline, followed by
integration and real occurrence/qualification controls. This is not independent
legal acceptance, OCR accuracy evidence or validation of the unmodified
production source.

Post-run challenge: all comparisons use the same protected small English scan.
The real-producer method and full-service controls expose the dispatch defect,
but cannot establish correct region selection or readable transcription on a
six-page table scan. The frozen BES oracle and exact wrong-occurrence controls
must test that next. A missing-image acceptance on the integrated real consumer
would overturn the candidate's boundary pass.
