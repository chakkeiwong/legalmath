# Reproduced geometry blocker and bounded diagnostic

The first five-page Portuguese OCR worker completed, but P1 rejected one of its
word boxes on PDF page 177: the token `:` has x coordinates 530.64–1037.02 points
against an original page width of 640.63 points. This is too large to attribute
to raster rounding. All other retained boxes pass the current geometric bounds.
The failed worker, images, request and P1 failure remain immutable. No critical
span pass is claimed because actual P1 intake failed.

The checked worker calls `Pixmap.pdfocr_tobytes` and then extracts words from
the generated OCR PDF. The installed PyMuPDF implementation delegates the PDF
writing to MuPDF and exposes `TEXT_ACCURATE_BBOXES`. The next bounded diagnostic
uses the exact retained 300-dpi image and Portuguese model: reproduce the OCR
PDF, compare its default word extraction with accurate bounding boxes, and run
the installed Tesseract CLI TSV output on the same pixels/model. This separates
recognition from generated-PDF text geometry; different library/runtime
versions will be retained and prevent an identical-engine claim if they differ.

Primary diagnostic: locate where out-of-page geometry first appears, compare
full recognized tokens and all frozen page-177 critical spans, and retain
every raw output. Pixel/model mismatch, malformed output or lost required span
invalidates a proposed repair. Word counts/timing are explanatory only; they
cannot rank OCR packages or establish legal correctness. Any geometry variant
that drops text is not a source-preserving fix. No clipping, token deletion,
changed production default or mutation of the active R4 method is authorized
by this diagnostic. One attempt only; review the result before a product repair.

Command: `timeout 300 /home/chakwong/miniconda3/envs/tfgpu/bin/python docs/implementation/prospectus-integration-closure/bes-original-acquisition/portuguese-2009-reports/probe_geometry.py`.
The script sets `CUDA_VISIBLE_DEVICES=-1` before PyMuPDF import. It saves all
output under `geometry-probe-001/` and returns a compact result. This is the
single reviewed diagnostic/repair investigation for the newly reproduced P1
blocker; an unresolved result is retained rather than hidden with ad hoc
geometry corrections.
