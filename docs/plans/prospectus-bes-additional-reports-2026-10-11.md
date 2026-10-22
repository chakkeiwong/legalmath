# BES additional report coverage, 11 October 2026

## Question and evidence contract

Can the existing product's selected-page OCR recover four newly identified
report pages without changing any previously retained occurrence or promoting
an unresolved legal answer? The exact comparator is
`bes-original-acquisition/conditional-consumer/attempt-001/report.json`,
with 123,032 occurrences from eleven documents. The earlier six-page OCR
selection missed the 2009 Audit Committee report (PDF 176–177, printed
175–176) and the 2010 sustainability assurance report (PDF/printed 88–89).
The statutory financial audit opinions are different reports.

The primary engineering criterion is actual `service.assess` consumption of
the expanded request, exact identity-and-content preservation of all comparator
units, new OCR units restricted to those four pages, and preservation of the
supplied assembly, corrections, meanings and fourteen unresolved dependencies.
Native units on the added pages must remain present. Frozen image-based
critical spans test OCR usefulness; a mismatch vetoes transcription acceptance
and triggers a separate image review, not abandonment of the consumer repair.
The consumer must expose each observed matching span through actual source
units. A matched omission control must remove these new occurrences and their
missing body passages while preserving every previous occurrence.

Wrong source, selection, image, prior unit, method or manifest identity,
non-PASS preflight, unexpected changed questions/dependencies, and incomplete
artifacts veto the run. Wall time, occurrence counts and raw OCR match fraction
are explanatory diagnostics, not legal acceptance or package ranking. A
failed OCR span triggers review; an invalid comparator or method stops dependent
execution. No unchanged failed phase is retried. A repair needs a new reviewed
attempt with its failed predecessor retained.

This run cannot establish source authenticity, historical availability, complete
771-page text coverage, native confinement, second-host portability, translation
equivalence, financial audit validity or independent legal acceptance. The
question statuses and all fourteen onward-source statuses remain unchanged.
Expected source content is supplied assisted evidence, not a blinded oracle.

## Code trace and skeptical audit

`extraction.scan` invokes the existing CPU worker. `source_graph.hybrid_units`
rerenders retained image identities, preserves native occurrences, and adds
OCR occurrences under original page numbers. `service.source_product` binds the
result to the correction/layout admissions; construction and annotation
admissions then require fresh graph/assembly hashes. New 2009 OCR is inserted
before the 2010 document, so a prefix comparison with the previous full graph
would be wrong. Compare all previous units by unique ID and complete content,
and check the order of their subsequence as well.

The historical conditional runner compares the preflight manifest hash to its
result member hash, and its fallback does not enforce PASS status. Leave that
sealed method unchanged. The new runner independently requires the expected
status and mandatory manifest members, checks every member, and exercises
validly rehashed failed-status, corrupted-result, missing-member and path-escape
controls before accepting a preflight. It also checks method drift before and
after each phase, binds direct product source files and original inputs, and
requires complete previous results before progressing.

The earlier inventory scanned all 771 pages but only nominated 41. Six were
known audit pages; four additional substantive omissions were confirmed in
enlarged images. The other 31 remain contact-sheet triage only. Photos,
advertisements, maps and logos can contain unextracted words. Small images and
vector text can escape the screen. Treating the inventory or known-six recall
as completeness would be wrong. The prior render manifest predates the two
enlarged 2010 images; preserve it and create a new final review manifest.

Audit verdict: PASS for this bounded engineering repair after correcting the
baseline comparison and preflight guard. There is no unexamined package default
being promoted. A command succeeding without new source units, preservation
checks and negative controls would not answer the question.

## Default and assumption audit

| Choice | Provenance and status | Failure risk and first check |
| --- | --- | --- |
| PDF identities and page numbers | Existing issuer-archive receipts; required input identities | Wrong edition or off-by-one page; bind source SHA and page count and inspect rendered text |
| 300 dpi, English pinned model | Existing product profile; comparator setting, not a multilingual optimum | Portuguese names/diacritics may fail; retain strict Unicode span mismatches |
| Prior 2009 pages 174–175 plus new 176–177 | Retained old OCR plus fresh OCR for newly selected pages | Regeneration could change old words; keep old page records byte-for-byte in combined evidence |
| 2010 pages 88–89 | Enlarged visual review; source-specific selection | Confusion with financial opinion p190; retain report types and source anchors |
| Whitespace folding and Unicode NFC only | Matching convenience hypothesis | Hiding accents or numeric errors; no case, accent, punctuation or digit repair |
| CPU PyMuPDF 1.27.2.2 | Existing reviewed environment; integration baseline | Runtime/model drift; bind worker, interpreter, model, package files and rendered images |
| Identical statuses | Required preservation criterion | Mistaking added text for legal resolution; compare full question objects and existing dependencies |
| One 1,200-second bounded attempt | Four OCR pages and existing consumer runtime | Timeout leaves incomplete attempt; preserve started/result and require reviewed repair |

## Executable sequence and refresh

The coordinator is
`docs/implementation/prospectus-integration-closure/bes-original-acquisition/expand_report_coverage.py`.
Its fixed output is `bes-original-acquisition/coverage-expansion/attempt-001/`.
Run with `.venv/bin/python` and CPU hiding set in the program before imports:

1. `timeout 180 .venv/bin/python docs/implementation/prospectus-integration-closure/bes-original-acquisition/expand_report_coverage.py freeze`
   freezes the source/image-bound oracle and records the completed visual triage.
2. `timeout 1200 .venv/bin/python docs/implementation/prospectus-integration-closure/bes-original-acquisition/expand_report_coverage.py continue`
   runs OCR, preflight and the actual consumer sequentially. It verifies retained
   phases on resume and refreshes `progress.json` after each phase with the
   actual decision and next reason. Detailed evidence goes to files; stdout
   contains one compact result per phase. Poll long commands at short intervals.
3. Inspect every mismatch against its image. Preserve raw output and oracle;
   record corrections separately before any transcription can be admitted.
   Update `RESULT.md`, `RESET.md`, `MASTER-SUMMARY.md` and `NEXT-PROGRAM.md`
   with the result, explanation, remaining limits and next justified phase.

Each phase retains start time, Git commit, dirty-method hashes, exact invocation,
CPU environment, source version, deterministic seed status, wall time and a
manifest. No external calls or installations are needed. Do not modify R0–R8
inputs to record these source diagnostics; current passing receipts remain
valid unless bound product inputs change.

## Result review requirements

Separate engineering correctness from transcription fidelity and legal
interpretation. Retain a decision table and strongest alternative explanation.
Raw mismatches distinguish limitations of this English-model configuration
from an implementation omission; they cannot reject the whole OCR package.
If engineering passes, continue to image review and exact assisted correction
maps where needed. Broader page coverage and Portuguese-language originals
remain separate work; external legal acceptance requires qualified review.
