# The selected equity strings are already incomplete in the encoded content

The original page59 image cuts the final column and unit label at a common
edge. Attempt008's saved text operands contain the same incomplete strings as
the earlier native extraction. For the five examined locations, no complete
value is hidden behind the local clip in those operands. The classification is
`ENCODED_STRINGS_TRUNCATED`, limited to those representative strings. This does
not establish every financial value in the table or the upstream cause of the
PDF's defective content.

All2258 saved page operators match all2258 before-operation callbacks when
compared by their original bytes and numeric operands. There are73 Tj and123
TJ text-showing operators, no quote-form text operators or marked-content
operators, and no Form XObjects. The saved page stream and full operator
inventory remain available; selected traces do not replace them. Text operands
in the five traces are ASCII and match their original byte strings exactly.
This is a comparison of the source representation with parser callbacks,
not an independent parser validation.

| Original occurrence | Encoded prefix operator | Final character operator | Joined encoded text, without inferred characters |
| --- | --- | --- | --- |
| p59:l35, unit label | 86 | 97 | `(in thousands of eu` |
| p59:l244, second-half2009 fair-value changes | 686 | 697 | ` 332 03` |
| p59:l247, second-half2009 total gains/losses | 801 | 812 | ` 639 66` |
| p59:l320,31December2009 balance | 981 | 992 | `6 938 88` |
| p59:l455,30June2010 balance | 1348 | 1359 | `6 914 97` |

The first occurrence's exact identifier is checked in the retained original
occurrence inventory. The other native text differs only in whitespace from
these joined operands; for example p59:l455 reads `6 91 4 97`. No arithmetic
has supplied or corrected a digit. A source-specific accounting inference
could be separately labelled, but it could not become this PDF's transcription.

Each prefix is followed by the exact operation sequence
`ET q i re W n BT Tm Tc Tw Tj ET Q`. Thus the last encoded character is drawn
inside a local rectangular clip. The four numeric clip rectangles end at
source coordinate y=666.231. Their final-character origins have y=665.5105,
leaving0.7205 source-coordinate units before that edge. The unit label's final
`u` starts at y=665.8705, leaving0.3605. The actual text matrices have positive
second component and zero first component, consistent with advance along
source positive y; the saved CTMs at these text operators are identity. These
coordinates are the unrotated content coordinates, not image-pixel coordinates.

The image's visible cutoff, the local clips and the incomplete operands are
consistent with a PDF whose exported content was already truncated. The exact
upstream cause is not established. Font widths/outlines and page boxes were
not retained, so this analysis does not compute how much of the final glyph
lies outside the clip. It also does not assert that expanding a crop box,
removing a clipping operator, or applying OCR would recover an absent digit.
No such operation was performed.

The decoded text callback itself is unsuitable as the sole coordinate oracle:
callbacks107,122 and149 flush their final character with an identity text
matrix, whereas the raw Tm and before-operation callback retain its actual
location. The finite trace therefore uses the raw local operations. Both
callback records remain unchanged, making this limitation inspectable.

Attempt008 failed after saving these data because our wrapper called the
JSON-value helper `digest(raw)` on bytes. The traceback points to that exact
line. pypdf had already returned the text and operators; the exception is not
evidence of a pypdf extraction failure. Attempt009 uses SHA256 file hashing,
checked against hashlib, and makes no additional PDF parse or extraction.
Attempt008's failed result and missing success receipt remain unchanged.

The original PDF,007 image and463 native occurrences retain their identities.
The source diagnostic is adequate to reject automatic digit recovery from the
selected saved strings. A complete authentic version of this statement is
needed for a source-transcribed total-equity column and full unit line.
Conditional interpretation of readable columns, periods and footnotes remains
possible and is the next substantive route.
