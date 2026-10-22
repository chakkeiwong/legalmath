# The oversized word is encoded in the generated OCR PDF

Read-only inspection of the saved `geometry-probe-001/ocr.pdf` places the
failure before ordinary word extraction. The page is 640.80 by 858.96 points
after raster rounding; the original is 640.63 by 858.898 points. The offending
colon extends to x=1037.016 points under either page size. Its content stream
contains the following consecutive operators:

```text
/F0 4.800003 Tf
21099 Tz
440.64 -7.199997 Td
<003a>Tj
```

`Tz` sets horizontal text scale in percent. With the generated GlyphLessFont's
half-em advance, the expected colon width is
`4.800003 × (21099 / 100) × 0.5 = 506.376316485` points. The retained word spans
`1037.016357421875 - 530.6399536132812 = 506.3764038085938` points. The small
rounding difference agrees with the generated text instruction. The box is
therefore already represented by the PDF's text placement; the strict P1
validator did not invent it. An accurate-bbox extraction flag leaves the
horizontal stretch in place.

The installed runtime reports PyMuPDF 1.27.2.2 and MuPDF 1.27.2. The exact
official tagged writer source was downloaded and retained from
`https://raw.githubusercontent.com/ArtifexSoftware/mupdf/1.27.2/source/fitz/output-pdfocr.c`.
Its `flush_words` (lines 542–675) sets a horizontal word's scale from its
width, font size and character count. The vertical branch instead fills the
line bounding width with each glyph (lines 576–610). `queue_word` combines
overlapping horizontal or vertical groups (lines 698–746); `char_callback`
receives and transforms recognition boxes (lines 755 onward).

This source explains mechanisms capable of producing the observed stretch,
but the saved PDF does not retain the callback's original word/line boxes or
direction flags. It does not distinguish an invalid recognition box from
line grouping or PDF placement. A direct recognition callback/TSV comparison
is still needed to locate that cause. The installed Python wrapper exposes
MuPDF OCR-device APIs but no standalone Tesseract CLI was found in the checked
locations. No native patch or alternative engine was executed in this trace.

Decision: retain strict rejection for the current profile and investigate a
versioned optional path that preserves text while explicitly withholding
invalid spatial evidence. Do not clip, stretch, erase, or silently repair the
colon. No claim of a fundamental OCR-package limitation follows from this
one local route. This trace changes the proposed repair from an extraction
flag to a producer/geometry-contract investigation.
