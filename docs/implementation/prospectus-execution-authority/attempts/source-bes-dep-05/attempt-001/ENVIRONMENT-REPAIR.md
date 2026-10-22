# Bounded inspection interpreter correction

`timeout 120 .venv/bin/python .../inspect_source.py` exited 1 at `import fitz`
with `ModuleNotFoundError: No module named 'fitz'`, before creating outputs.
The project runs PyMuPDF through a separate reviewed OCR interpreter. The first
repair incorrectly used the fallback `.localresources/prospectus/ocr/bin/python`
from `successor/extraction.py`; that command exited 127 because the path is absent.
Inspection of the actual successful page-coverage `prepare_2010.py` and
`partition_2010.py` identifies `/home/chakwong/miniconda3/envs/tfgpu/bin/python`
as the installed runtime. Both interpreter assumptions were wrong. This is a harness
usage failure, not evidence that PyMuPDF is broken or needs installation.

Use the same unchanged inspection script with that evidence-backed OCR
interpreter. Its CPU-only variable is set before importing PyMuPDF. Native
source/consumer work continues under `.venv` with the worktree imports pinned.
`pdfinfo` successfully identified a 175-page PDF. This one bounded interpreter
repair preserves the original failed command and returns directly to source
identity/page review. The source plan's evidence criteria remain unchanged. The
failed path lookup did not run a package or create any output; record both
failures instead of treating the fallback default as the deployed runtime.
