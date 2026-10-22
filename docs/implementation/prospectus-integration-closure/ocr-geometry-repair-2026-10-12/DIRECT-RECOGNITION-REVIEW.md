# The overrun is introduced after recognition

The direct native callback returned the colon's word and character box as
`[2211, 3002, 2217, 3022]` pixels: six pixels wide and entirely inside the
original rendered image. Its line box was `[108, 2968, 2217, 3025]`. All
1,409 nonspace characters match the retained PDF extraction in exactly the same
order. A fresh PDF produced by the same installed native library reproduces
all 266 retained words, including the oversized colon box. Input hashes did
not change. The diagnostic took 3.98 seconds.

This comparison locates the out-of-page advance after the recognition callback,
in MuPDF's PDF grouping/placement path. It rules out an oversized recognition
box as the cause of this particular overrun. It does not certify that recognizing
a colon was semantically correct. The source image, model, integer grayscale
conversion, padding and 300 dpi resolution were matched to the inspected writer.
The actual exported `ocr_recognise` wrapper was used, avoiding a different CLI's
default settings. The native library hash is retained; a fresh producer replay
controls for the earlier manifest's omission of version-suffixed library hashes.

The previous trace established only that the bad advance was encoded in PDF
operators. Its unresolved recognition-versus-placement attribution is now
superseded for this one case. No native patch has been implemented. The tested
optional product behavior remains appropriate: preserve text and provenance,
withhold the invalid box, and refuse unsupported spatial projection. Independent
source review and wider recognition/geometry testing remain necessary.

| Decision | Primary criterion | Veto checks | Main uncertainty | Next justified action | Limit |
|---|---|---|---|---|---|
| Locate this overrun after recognition | PASS: matched fresh PDF and exact character sequence; valid callback box | Image/model/library bindings and fresh reproduction PASS | Exact grouping transition and generality | Replay the inspected writer grouping on the saved callback; design a bounded direct-recognition adapter comparison | No whole-package unsuitability or native repair verdict |

The strongest alternative explanation was a different recognition run caused
by preprocessing or native-library drift. Exact character order and fresh PDF
word equality substantially constrain that explanation. A mismatch in the
saved image/model/library identities or failure to reproduce the PDF would
invalidate this attribution. The weakest part of the evidence is its scope:
one reproduced page does not establish how often the writer fails elsewhere.
