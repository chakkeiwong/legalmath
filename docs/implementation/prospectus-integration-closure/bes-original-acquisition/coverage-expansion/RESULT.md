# BES report coverage repair result, 12 October 2026

This result completes the local repair package planned on 11 October; frozen
plan names and execution timestamps retain their original dates.

The actual corrected eleven-document service consumer passed. It retains
123,263 raw source occurrences, including 231 new occurrences from four
previously omitted report pages. All 123,032 prior occurrences, their order
within the expanded sequence, their native text and their geometry remain
unchanged. The new occurrences are 30 and 28 from the 2009 Audit Committee
report at PDF 176–177, and 95 and 78 from the 2010 sustainability assurance
report at PDF 88–89.

Nine exact, image-bound token correction maps survive the actual service.
They preserve raw text and geometry, and do not assign raw boxes to corrected
characters. One source-specific HEADER disposition removes the spurious
“§ 176” footer reference from considered legal dependencies while retaining
the raw occurrence. Removing that disposition reproduces the false reference.

The prospective v1 oracle matched 20/25 raw spans. Enlarged image inspection
showed that one v1 span was wrong: the source reads “unconsolidated and
consolidated”, which OCR read correctly. The retrospective v2 oracle therefore
matches 21/25 raw spans. Both oracle versions and both scores remain available.
The remaining four failed checks concern an issuer accent, a committee-member
accent, AA1000APS, and sidebar interruption of the negative-assurance phrase.
The nine token maps include repeated inspected issuer occurrences beyond the
single frozen issuer span. Supplied display corrections plus two explicitly
ordered original source spans account for 25/25 checks. This is assisted
review of a known case, not automatic OCR accuracy or independent validation.

Twenty v2 raw spans are absent from the matched native/previous-selection
consumer and present after adding OCR, with a gain on every added page. The
matched omission product exactly preserves the prior units of the selected
2009/2010 documents. This establishes a concrete extraction gain on these
pages, not full-report coverage or better legal answers.

Q1, Q2, Q4 and Q6 remain UNKNOWN, Q3 PARTIAL and Q5 UNSUPPORTED. All fourteen
original onward-source dependencies remain UNRESOLVED. The three annual-report
PDFs remain candidate originals without independent authentication or established
historical publication/knowledge dates. The 2010 report's translation clause,
limited assurance, criteria, purpose restriction and third-party disclaimer
remain distinct from the financial audit opinion.

## Decisions and evidence

| Decision | Primary criterion | Veto diagnostics | Main uncertainty | Next justified action | Unsupported conclusion |
| --- | --- | --- | --- | --- | --- |
| Accept four-page intake as current engineering evidence | Actual consumer; 231 new units; every prior occurrence preserved | Source/page/image guards and matched omission controls pass | Other unreviewed image/vector text | Expand coverage under a separate reviewed oracle | Whole-document completeness |
| Accept nine supplied display maps for these occurrences | Raw-image binding and exact reverse source mapping survive service | Wrong image and stale quote rejected; raw geometry unchanged | Other names/codes and language profiles | Compare pinned language profiles and inspect uncertain glyphs | Automatic OCR repair |
| Accept the exact footer HEADER disposition | False citation excluded, reproduced when disposition omitted | No prior dependency/answer evidence removed | Other page furniture and report scope | Review additional source-specific roles | General header detection or legal source relevance |
| Repair the consumer comparator | Expected additions enumerated; every old issue/content retained | Dropped prior issue, unrelated issue, changed answer and promoted status rejected | Future source additions need a new expected delta | Preserve this regression and derive each new delta from evidence | Identical statuses alone prove preservation |
| Retain legal incompleteness | Original questions and fourteen dependencies unchanged in status | No dependency promoted; no independent acceptance | Authenticity, dates, applicability, qualified review | Authenticate sources and obtain independent readings | Delivery completion or collateral eligibility |

The source inventory covers 771 page measurements and nominates 41 pages.
Six were previously selected audit pages, four are the newly recovered reports,
and 31 received contact-sheet triage only. The screen may miss smaller images
and vector-drawn text. It cannot certify their absence.

## Execution and manifests

All commands used the worktree `.venv/bin/python`, with
`CUDA_VISIBLE_DEVICES=-1` and `OMP_THREAD_LIMIT=1` set before runtime imports.
The OCR subprocess used the existing `tfgpu` interpreter in deliberate CPU
mode, PyMuPDF 1.27.2.2, 300 dpi and the pinned English model. No package was
installed and no external service called. The baseline commit is
`e8beb52b13399f18bbbff9aecea9636803729d5f`; each phase also binds the actual
uncommitted source and plan bytes. Seeds are N/A for deterministic extraction.

| Invocation after `timeout` and `.venv/bin/python` | Bound | Wall seconds | Result |
| --- | --- | --- | --- |
| `expand_report_coverage.py freeze` | 180 s | 1.232 | FROZEN |
| `expand_report_coverage.py continue`: OCR | 1,200 s shared invocation | 7.636 | RAW_OCR_RETAINED |
| same invocation: preflight | same bound | 64.622 | P1_P2_PREFLIGHT_PASS |
| same invocation: raw service and comparison | same bound | 297.371 | FAIL: wrong full-object equality criterion; report retained |
| `review_report_coverage.py prepare` | 1,200 s | 522.254 | REVIEW_PREPARATION_PASS |
| `review_report_coverage.py consume` | 1,200 s | 319.887 | PASS |

Scripts are in the parent `bes-original-acquisition/` directory. Exact complete
commands, environments, method/data hashes, timestamps and output paths are in
each `started.json`; each completed phase has `result.json` and `manifest.json`.
The two plans are `docs/plans/prospectus-bes-additional-reports-2026-10-11.md`
and `docs/plans/prospectus-bes-report-review-repair-2026-10-11.md`.
The historical failed attempt is `attempt-001/consumer/`; the passing final
report is `review-repair-001/consumer/report.json.gz`. The final visual review
manifest in `attempt-001/freeze/` covers the later 2010 images without changing
the earlier render manifest. The repair preparation binds every enlarged crop
in `image-review-001/`.

The final result separates three evidence classes: extraction/controller
correctness passes for these inputs; transcription is assisted and includes an
unrepaired automatic ordering problem; legal interpretation remains incomplete.
R0–R8 remain current under the unchanged product method. No phase ladder was
repeated to record this source-specific package.

## Post-run skeptical review

The strongest alternative explanation is that supplied selections and readings
solve this known source packet while unseen report layouts still fail. The
omission and mutation controls establish real, bounded effects; they do not
remove that limitation. A disagreement with an enlarged source image, a changed
prior occurrence, or independent re-extraction under the same bound environment
would overturn the relevant local result. The weakest evidence is broad
coverage and independent source/translation authority, which remain open.

The failures include our page selection, harness criteria, oracle transcription
and missing footer disposition, plus raw recognition/ordering limitations of the
current English profile. This evidence establishes no fundamental unsuitability
of any whole package. Automatic reading order, other language/layout families,
production native confinement, second-host portability and qualified legal
acceptance still require their own evidence.
