# OCR context and geometry comparison

The original word-centre rule reproduces all 23 protected target selections
and 16 exact text matches. Selecting every positively intersecting word box
reduces exact matches to 15: it adds `Not Applicable` from the neighbouring
day-count row and includes signature noise with the responsibility sentence.
Reject that candidate as a replacement for the centre rule.

Running the same installed English OCR on the exact reviewed cell crops gives
19 exact matches, retains all 16 previous matches and recovers the responsibility
sentence, ISIN and intended-arrangement label. Cropping changes source context;
these results support further study of supplied segmentation on this case.
The cropped path remains a diagnostic and has not been integrated into intake.
It discovers none of the eight relationships.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Limit |
|---|---|---|---|---|---|
| Reject box intersection as the replacement | 15/23 exact; loses day-count | Candidate promotion veto fired | Can a separately justified ambiguity-aware geometry rule help? | Preserve current centre rule and explicit reviewed selection | Geometry rejection does not reject OCR |
| Retain crop OCR for further study | 19/23 exact; no prior exact target lost | Full-text promotion veto remains: four misses | Supplied boundaries and one exposed source | Test a supported mixed-language profile and additional source family before considering an optional derivative route | No automatic layout, general accuracy or default change |
| Accept validity of both diagnostics | All fixed inputs and baseline selections verified; active regression method unchanged | No continuation veto | Host-native dependencies still unbound for complete reuse | Preserve complete outputs and model/runtime identities | A valid diagnostic can contain a failed candidate |

Four crop misses remain. `S&P:` lacks the printed internal spaces; the ratings
qualification still joins `using a`; the clearing label loses punctuation in
`S.A./`; and the English model substitutes Portuguese characters in `Liquidação`
and `Mobiliários`. These are distinct recognition errors under the fixed exact
comparison. Do not erase them by changing normalization after seeing results.
The absence of a retained Portuguese model limits the language comparison; this
trial does not establish a fundamental package limitation.

The public installed PyMuPDF wrapper forwards language, tessdata and compression
to MuPDF. Its inspected source slice and whole-file hash are retained under
`api-source/`; it exposes no page-segmentation-mode parameter. Both actual OCR
routes use the same interpreter, distribution files, English model and DPI.
Crop-local boxes are retained as crop-local coordinates and have no admitted
semantic mapping. Production source, its reviewed correction packet and all
active phase bindings remain unchanged.

`geometry/attempt-001` passes diagnostic validity in 0.049 seconds;
`crop-ocr/attempt-001` does so in 1.958 seconds. These concurrent elapsed times
are explanatory only. Manifests retain commands, commit, uncommitted method,
CPU-only environment, source/model hashes, complete comparisons and results.
There is no stochastic ranking; these are deterministic observations on the
predeclared targets. No new external request or model installation was made.

Post-run challenge: a reviewer selected every crop, so the 19 matches cannot
measure automatic segmentation. The unchanged character oracle and retained
failures prevent a favorable display from becoming the pass criterion. A new
source family losing critical text or an unbound crop-to-page mapping would
invalidate promotion of an optional cropped-input path. The weakest evidence
is generalization beyond this document and the untested Portuguese profile.
