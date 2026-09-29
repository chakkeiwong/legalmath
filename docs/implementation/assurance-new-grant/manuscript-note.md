# Bounded manuscript addition

Target reader: the bank's technical/compliance product team and an implementing
engineer familiar with the monograph's source, candidate and proof distinctions.
The added unit explains why additional resources preserve earlier failure
history, then why future observations must bind the interpreter before the
proof checker. It uses the actual 92/120 UCITS balance and the expired-pair
incident. These examples require no external paper or implementation file to
understand the argument.

The protected baseline is `artifacts/assurance-new-grant/2026-09-29/manuscript-before.zip`
with 275 TeX/Bib source files. The existing section is retained; new paragraphs
and one process chart teach the added mechanism. All prior mathematics,
citations, examples and qualifications must survive the final preservation
check. Page counts will be measured after building the unified manuscript.

The scholarly narrative skill is used for the explanatory addition. No human
feedback has been obtained on its voice; this is not a human-readability
certification. The controlling product policy excludes human legal quality
labels and approval gates; no such gate is introduced by the writing workflow.

A preliminary isolated rendering exposed an arrow too close to the new chart's
longer right-hand box. The merge node now sits below that box, and explicit line
breaks avoid splitting labels unnecessarily. The preview also caught an incorrect
PDFLaTeX command in the new controller: the manuscript uses `fontspec` and its
existing documented engine is XeLaTeX. The controller now uses that engine.
These are layout/build repairs; the final frozen PDFs still require inspection.
The final phase uses the existing `build_reader_facing_monograph.py` entry point,
which runs XeLaTeX for both volumes twice to settle their cross-references and
executes the reader-facing document check before exporting the guide.
