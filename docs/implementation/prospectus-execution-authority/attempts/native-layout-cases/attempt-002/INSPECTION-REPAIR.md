# Preserve an inspection serializer failure

The first CPU inspection parsed the PDF and rendered the first nominated page,
then failed while serializing PyMuPDF's native dictionary: an image block contains
binary bytes. The empty first native JSON gzip file is invalid and remains as
failure evidence. This is our artifact serialization error, not corrupt PDF,
missing Arabic, OCR failure or a package-suitability verdict.

Keep the original inspector unchanged. A reviewed inspector records binary block
length and hash while retaining all native text spans/word coordinates; original
image bytes remain recoverable from the retained PDF and the rendered page.
It verifies/reuses any existing page render and writes distinct reviewed native
JSON filenames. No new acquisition occurs; the six HTTP starts are exhausted.
The source/400-page/120-second/six-render/80MiB bounds remain. One prior render
plus at most three reviewed render/verification operations stays within six.
