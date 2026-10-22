# Reviewed local pypdf6.8.0 diagnostic behavior

The available parser is the worktree .venv pypdf6.8.0 installation. The full
Python source inventory is pinned in history.json and again at prepare.
The inspected method is _page.py PageObject.extract_text in plain mode,
_extract_text, and _text_extraction/_text_extractor.py TextExtraction.

_extract_text walks each content-stream operation and invokes the before
callback before dispatch. It handles TJ, single/double quote operators and
Do explicitly, and delegates remaining operations to TextExtraction. Non-image
XObjects recurse through extract_xform_text with visitor callbacks. The exact
decoded page and form operators will be retained separately so recursion or
visitor ordering cannot obscure the original stream identity.

TextExtraction's operation_handlers include BT, ET, q, Q, cm, Tz, Tw, TL, Tf,
Td, Tm, T* and Tj. W, W*, re and arbitrary path/clip operators are absent.
process_operation ignores operations not in that map. q/Q retain matrices and
font/text state but no clipping path. Therefore plain extracted text is not
an image-visible-content oracle; it can contain encoded text hidden by clipping.
That makes it a useful causal diagnostic against the retained rendered image.
Raw stream operators, saved matrices and explicit unresolved limitations must
support any conclusion about what caused the truncation.

The public method documents content-stream order rather than guaranteed human
reading order and warns that extraction works differently across generators.
Visitor callbacks are ignored in layout mode, so this run explicitly uses plain.
The default orientations are0/90/180/270; no layout reordering is requested.
Default space_width200 is a fallback when font data do not establish it; inserted
spacing and line breaks are parser output, not original bytes. TextStringObject
and ByteStringObject provenance are retained where available. Unknown decoding
cannot be replaced with invented financial digits.

PdfReader strict=False is an explicit diagnostic tolerance choice inherited from
the parser's ordinary behavior; warnings remain in parser.log. A warning or
missing font/coordinate interpretation may make the diagnosis inconclusive.
The original PDF is never written. There is one PdfReader construction and one
page59 extract_text call; decoded content/form inspection belongs to that same
source parse. The source action is reserved before it starts. Content size,
form nesting, stage time and total evidence size are bounded. No native child,
network, OCR or rendering is used. A failure consumes this attempt and is not
automatically retried.
