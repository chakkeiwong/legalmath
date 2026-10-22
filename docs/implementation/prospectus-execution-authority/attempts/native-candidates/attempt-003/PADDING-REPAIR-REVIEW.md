# One changed usage repair: alignment pixels must be white

The comparison failure is retained in invocations/compare/result.json. Coordinate
inspection localizes it to the international clockwise/counterclockwise arms;
all domestic arms and the international unrotated arm have valid crop boxes.
The initial progress message's attribution to an unrotated arm was incorrect.

The original international rotated derivative is321 by80 pixels. The reused
native_page_v2 callback converts RGB to grayscale and allocates its aligned
array with zeros, then copies only the321 real columns. It passes the padded
324-pixel width as the recognizer's actual image width. The remaining three
columns are therefore visible black pixels. The native `|` box is exactly
[321,0,324,80] in both rotated arms. No original-source pixel exists there.
The domestic rotated width288 and unrotated width80 are already aligned.

This is our callback usage/preprocessing defect. It is not evidence of a
fundamental OCR package failure. The recognizer is seeing a black strip that
our wrapper added. Removing a reported glyph or clipping its box would hide
that defect; neither is permitted.

Skeptical audit PASS for the single allowed changed usage repair. Add white RGB
columns on the right solely to make the input width a multiple of four before
calling the unchanged callback helper. The helper then adds zero extra columns.
Verify pixel-for-pixel equality on the321 original columns, exactly three added
white columns, and unchanged grayscale values on all original pixels. Preserve
the source crop,10px border,300dpi,model,library,chosen directions and transforms.
No tuning or target changes. Run only the two arms whose source geometry failed,
once each, and preserve all six original native results. Reject any new glyph
in padding; no clipping, selective text deletion or silent recovery.

Evidence criterion remains both complete clockwise readings through actual
source/layout consumption, all mapped character events and adverse controls.
Retain a before/after comparison showing the two original invalid-geometry arms
as failed; compare the changed arms against their actual original bytes. Existing
successful native arms are reused under unchanged hashes. All consumer failures
remain visible and cannot establish package unsuitability. If this one repair
fails, stop this local experiment with its actual residual failure; no additional
parameter search or repair admission is granted.

The original frozen plan and runner stay unchanged. The separate repair runner,
review, preparation manifest, exact commands and newly padded derivatives become
additional immutable evidence. Each stage has an exclusive invocation marker.
