# Consume the retained Portuguese 2009 reports

The Portuguese PDF was already fully downloaded on 11 October and has now
passed retained receipt/file-hash verification. Its contents page independently
places the statutory report at printed 173 (PDF 174) and the committee report
at printed 176 (PDF 177). Native page text shows image-bearing report pages
174–178; it does not expose the report body. The English audit uses two pages,
whereas this Portuguese audit occupies three. Assuming identical pagination
would lose the last page and is rejected before execution.

Question: can the newly integrated source-report consumer retain the original
Portuguese audit/committee subjects, conclusions and date wording, separately
from the English readings? The baseline is the same retained PDF with native
extraction. Candidate: the existing pinned Portuguese selected-page OCR profile
and, only if image review requires it, explicitly supplied source regions.
Use actual P1 intake, P2 report reading and P3/final consumption; do not infer
the source claims from English OCR or its page numbers.

Before OCR, inspect source-bound images/crops and freeze the report titles,
financial-statement subject, reasonable-assurance qualification, complete
conclusion, committee concurrence and internal dates. Promotion of this optional
case requires exact frozen spans after whitespace folding, complete retained
character ownership and matched Q1–Q6/dependency preservation in the final
consumer. Changed source, omitted qualification, wrong date and swapped
classification controls must reject. A raw miss is a repair trigger, not a
fundamental Tesseract failure; retain the raw result and use one separately
reviewed correction attempt if justified. Source corruption, unbound images or
missing required comparison are continuation vetoes for the case.

Skeptical review passes with explicit restrictions: the Portuguese model is a
known-case candidate, not a changed default; the cohort is exposed development
evidence; internal report dates are not publication dates; Bank reports cannot
replace BES Finance reports or executed agency agreements. Existing authentic-
ity and incorporation gaps remain unresolved. The active R4 controller's
source files stay fixed. This work adds only independent evidence scripts and
artifacts and uses CPU, with no network or new package installation.

Provenance: original receipt `attempt-001/bes-2009-pt-resumed/receipt.json`,
source hash `9c3172f2cbb7f566be41985bee38d0d1393ab87fcf897a53d0cbc233ecf37c19`;
Portuguese model `language-profile/acquisition-001/por.traineddata` with hash
`c4932b937207a9514b7514d518b931a99938c02a28a5a5a553f8599ed58b7deb`.
Copy the reviewed existing Portuguese OCR profile and explicitly change only
source identity and selected original pages. Check those fields before launch.

Artifacts: `bes-original-acquisition/portuguese-2009-reports/`. Each stage gets
a new immutable directory, exact command, source/code hashes, CPU-only setting,
wall time and result. One foreground command per short tool call, launch with
one-second return, no large output or repeated images. OCR/consumer commands
will use `timeout 600` and the project `.venv`; image rendering uses the existing
CPU-only research interpreter. Review results before advancing, and freeze
the next command in the stage note. This does not change the fourteen original
dependency dispositions or authenticate an independent legal reading.
