# The optional geometry repair is complete for the reviewed cohort

The new, explicitly selected `pymupdf-hybrid.v2` profile preserves source text
when a finite, ordered OCR box extends outside the page. It retains the raw
coordinates and image identity, marks the word and affected line geometry as
unknown, and makes both layout consumers refuse spatial projection on that
page. The original strict profile continues rejecting the source. Malformed,
non-finite, inverted and incorrectly bound inputs remain errors.

The actual Portuguese 2009 intake preserves all 31,256 native units and 1,311
OCR words. Its audit and committee reports reach the final source-use consumer,
while contractual questions and dependencies remain unchanged. Nine of eleven
frozen passages match the raw OCR. Two independently image-reviewed punctuation
maps change `S.A,` to `S.A.` and `Lisboa.` to `Lisboa,`, producing eleven assisted
display matches. Final source-scope quotations remain raw; the correction maps
are retained separately. Classifying `grau de segurança aceitável` as reasonable
assurance remains a supplied translation judgment.

## What the validation establishes

The focused suite passes 67 checks, including a substantive legal word with
invalid geometry, strict rejection, malformed inputs, anchors, correction
provenance and both spatial entry points. Four earlier actual report consumers
preserve their final answers, readings and dependencies; all forty adverse
controls continue rejecting their designated corruptions. A separate current
intake rebuild reproduces all four complete source graphs, sealed P1 products
and frozen input identities exactly. Retained downstream replay alone was not
treated as proof that intake remained compatible.

The finite controller completed R0–R8 in 3492.46 seconds. Its R4 selection
contains the same 428 checks as the preceding report-scope method. The new
geometry tests were added to R3. After completion, a wording/next-action
attribution revision invalidated only R8; that phase passed again in 0.73 s.
The current attempts are:

| Phase | Attempt | Engineering result |
| --- | --- | --- |
| R0 | 026 | PASS |
| R1 | 024 | PASS |
| R2 | 024 | PASS |
| R3 | 022 | PASS |
| R4 | 022 | PASS |
| R5 | 019 | PASS |
| R6 | 020 | PASS |
| R7 | 019 | PASS |
| R8 | 025 | PASS |

`final-current-status.json` and `verification.json` validate the current
bindings and retained evidence. The controller attempt's last `progress.json`
records the R8 dispatch; its final `result.json` records completion. No worker
remains active. The program has no unfinished engineering stage for this
bounded repair. R1–R8 substantive criteria remain PARTIAL, and independent legal
acceptance remains NOT_ESTABLISHED.

## The producer defect is now located

The installed native recognition callback returns a valid colon box,
`[2211, 3002, 2217, 3022]` pixels. It is six pixels wide, inside the image.
All 1,409 nonspace characters match in the same order. Fresh PDF generation
with the same library reproduces all 266 retained words and the oversized box.
The diagnostic matches source raster, model, grayscale conversion, padding and
300 dpi, and retains the actual version-suffixed native-library hash.

The inspected writer first joins `E`, `É` and `:` horizontally. A later `E`
below the left end passes its vertical-join rule, changing the group's output
axis. The vertical emitter stretches each glyph over the full group width.
The retained float32 replay predicts `21099 Tz` and a 506.37632195-point
advance, against 506.37640381 in the PDF. This explains the overrun introduced
after recognition. It does not certify the semantic recognition of the colon
or establish how frequently this occurs on other layouts.

The earlier failed writer replay stays `REPLAY_NOT_ESTABLISHED`: its extra
expectation that the colon itself joined vertically was wrong. Its saved
sequence shows that the colon joined horizontally and a later word changed
the axis. `NATIVE-WRITER-REVIEW.md` records the corrected explanation rather
than relabeling the failed attempt. The initial consumer harness failure also
stays failed: it omitted `include_artifacts=True`, then was repaired in a new
attempt. No native patch or production direct-recognition adapter is included.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Limit |
| --- | --- | --- | --- | --- | --- |
| Retain the optional product profile | PASS: actual text-preserving intake and final consumers | Strict, spatial, source-identity and adverse controls PASS | Wider unseen pages and recognition errors | Extend frozen source/layout coverage | No new default or automatic geometry recovery |
| Attribute this overrun to native PDF grouping/placement | PASS: matched callback, fresh PDF reproduction, exact scale/advance mechanism | Source/model/library checks PASS; original failed replay control preserved | Native repair safety across writing directions/layouts | Compare isolated axis-state repair and direct-recognition adapter | No package-unsuitability or validated-native-fix verdict |
| Keep substantive acceptance open | Required independent/source evidence is incomplete | Acceptance remains NOT_ESTABLISHED | Authority, dates, onward sources and unexposed legal readings | Acquire and review the missing evidence | Engineering totals do not supply legal acceptance |

The strongest alternative explanation for the native attribution was different
recognition input or library drift. Matched preprocessing, exact character order
and fresh PDF word equality constrain that explanation. A source/model/library
hash mismatch or a failure to reproduce the producer output would overturn
the attribution. Its weakest part is generality: this is one exposed page.
Likewise, supplied corrected readings cannot establish automatic extraction or
independent interpretation accuracy. No statistical package ranking is made.

## Documentation and remaining work

The monograph chapter is updated. Its post-pagination isolated proof builds to
nine pages; pages 5–6 were visually inspected and the split opening paragraph
was repaired. The isolated build retains one unresolved external section
reference, `sec:prospectus-delivery`. It is not a full-monograph validation or
a certification of human prose. `document-review-002/REVIEW.md` records scope.

The reviewed next plan is
`docs/plans/prospectus-native-geometry-followup-2026-10-12.md`. It starts with
frozen source/layout coverage and candidate interfaces, then compares an
isolated native axis-state fix with direct-recognition geometry. Wider
image/vector/table coverage, Portuguese 2008 report consumption, fourteen
onward dependencies, authenticity/publication dates, native read confinement,
second-host portability and qualified independent readings remain open.

All work is retained locally and uncommitted on
`feature/prospectus-evidence-master`. No merge, push, installation or external
message was performed in this completion step. The whole prospectus program
remains incomplete despite completion of this finite repair.
