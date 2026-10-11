# BES scan and worker-recovery documentation review

The monograph now explains the real BES qualification, the local correction-image
admission defect and its repair, the raw OCR misses, assisted source preservation,
and the separate crop/geometry observations. It explicitly distinguishes the
locally retained base/six supplements from their absence in the six-page request.
Historical regression totals and installed cases retain their original scopes.
The worker-recovery scan regression is now complete: all 685 collected
identities are covered exactly, R0--R8 and the 155-test remainder pass, and the
final attribution equals the R8 attribution.

Build 001 compiled both PDFs but failed the citation-binding check. Investigation
found six previously unregistered citations in an unchanged literature paragraph.
`citation-review-001` preserves the former register, the six individual scoped
judgments and verified primary-source hashes. All older exact citation contexts
are preserved. The unchanged document checker then passed in `check-002`: 137
cited documents, 325 occurrences, 207 original source-unit labels, no missing
equations/listings/reference targets and no LaTeX or page-geometry diagnostic.
After the BES paragraph and its six carried-over scoped citation judgments were
bound, the paired reader-facing build was rerun with the pinned CPU document
interpreter. It again passed with 397 monograph pages and 90 companion pages;
the standalone structural checker also passed. No protected baseline was
edited to achieve either result.

Actual monograph PDF pages 100–106 (printed 65–71) were rendered again at
110 DPI from the final 397-page PDF and inspected.
These include the complete changed subsection, its table, both BES footnotes,
the literature paragraph and adjacent section transitions. The qualification,
identifier, fractions, references, accented text and wrapped paths are legible;
no clipping or collision was observed. The principal BES discussion occupies
PDF pages 101–102. The subsection's six citations, label, reference and absence
of display mathematics/listings match the frozen subsection in
`fidelity-check.json`. The companion compiles and its document checks pass; no
companion prose was edited in this package.

The source discussion keeps facts, supplied interpretations and remaining work
distinct. In particular, 19/23 crop matches describe a diagnostic using supplied
cells and the same English model; they do not establish automatic segmentation,
Portuguese-model behavior or general package quality. The 23/23 assisted result
concerns preservation through the service, not independent legal truth.

This is executor source/style and rendered-page review. Human acceptance of
prose and independent legal adjudication remain pending. Complete current-method
engineering validation is recorded separately under `real-scan/validation-001`.
The current document and page checks are structural and source-binding checks;
they do not certify human readability, legal entailment or independent
acceptance. The 22 focused correction/service tests pass in the application
`.venv` (which supplies `pypdf`); the document checks use the pinned CPU
`tfgpu` interpreter (which supplies PyMuPDF). The first cross-environment test
attempt failed before assertions because those optional packages are split
between the two environments; it does not change the passing receipts.
