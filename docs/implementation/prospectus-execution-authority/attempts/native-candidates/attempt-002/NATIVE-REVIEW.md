# Review before compiling or executing the isolated writer

The exact retained MuPDF 1.27.2 writer has no separate group-axis state. A group
of individually directionless characters can join horizontally, retain zero
direction flags, then accept a vertical join and render all prior words using
the group's full horizontal span. The retained native trace establishes this
transition on the original page. Candidate A will introduce line_axis with
0=unestablished, 1=horizontal and 2=vertical; a successful join establishes the
axis, incompatible later joins flush, and flushing uses that axis without
rewriting per-word character-direction flags. Emptying the group resets it.

An additional inspected condition, else-if (ay < ax) after if (ax > ay), is
unreachable. Its intended replacement and writing-direction effects are not
tested by the group-axis repair. Preserve that source line in this patch and
report it as a separate possible direction-detection defect, without claiming
vertical/bidirectional support. The inspected source is retained upstream code,
not a statement about every release of the package.

Compile the unmodified translation unit and a small exception-catching wrapper
against the installed matching MuPDF development headers/library. Bind local
writer functions with -Bsymbolic-functions and fail linking unresolved symbols
with -z defs. The wrapper catches native exceptions and releases its output.
Load the resulting module locally in a bounded Python child and use pointers
from the same already loaded PyMuPDF library/context. A version/hash mismatch,
segmentation failure, unresolved symbol or unequal unpatched words/boxes stops
the native-patch arm for diagnosis. It does not authorize changing the installed
library or treating a failed build as package unsuitability.

Audit PASS for this finite hypothesis: a compiled unpatched control precedes
the patch; actual emitted PDF and downstream positions are checked; shared
recognition errors remain possible; missing true writing-direction cases block
promotion. The complete-distribution rebuild remains untested. The official
header acquisition command is curl --fail --location --max-time 30 --silent
--show-error --output <attempt>/tessocr.h
https://raw.githubusercontent.com/ArtifexSoftware/mupdf/1.27.2/source/fitz/tessocr.h.
