# A horizontal group is later rendered as vertical text

The saved callback and the exact tagged writer source explain the excessive
advance. The writer initially joins three single-character observations,
`E`, `É` and `:`, horizontally. None supplies an internal character direction,
and the horizontal-join branch does not record a horizontal group constraint.
A subsequent `E` below the left end therefore passes the vertical-join test.
That branch marks the group vertical. `flush_words` then uses the full group
width to stretch every character, including the colon near the right edge.

The group's x bounds are 25.6800003 and 532.0800171 points. The colon's height
is 4.80000305 points. The vertical branch computes

`scale = group_width / character_height * 200`.

Its binary32 arithmetic and integer cast predict the observed `21099 Tz`.
With the PDF font's half-em advance, the predicted width is
`4.80000305 × (21099/100) × 0.5 = 506.37632195` points. The fresh PDF gives
506.37640381 points; the 0.00008186-point difference is compatible with float
and decimal serialization. The recognition box is only six pixels, or 1.44
points, wide. This explains how the generated advance extends beyond the page.

The first replay was retained as `REPLAY_NOT_ESTABLISHED`: it correctly
predicted the vertical group, exact integer scale and observed width, but its
additional hypothesis that the colon itself joined vertically was wrong. The
retained word sequence shows a horizontal colon join followed by a later
vertical join. No failed result has been relabeled. Reading that transition
against `queue_word` and `flush_words` supplies the corrected explanation;
no additional OCR run was needed.

| Decision | Primary criterion | Veto/repair diagnostic | Main uncertainty | Next action | Limit |
|---|---|---|---|---|---|
| Attribute this overrun to PDF grouping and scaling | Exact scale and width reproduced from saved callback under literal source logic | First transition hypothesis failed; corrected by retained join sequence | Wider layout behavior and native-patch regressions | Compare a direct-recognition adapter and an explicit group-axis fix on a frozen multilingual/layout cohort | No native patch or new default has been validated |

The plausible native repair is to preserve a group's established layout axis,
separately from character writing direction, so a later mark cannot turn an
already horizontal group into a vertical one. A direct-recognition adapter is
another candidate because valid word boxes already exist before PDF placement.
Neither candidate is yet implemented in production. Both need matched normal,
vertical, bidirectional, table, margin and critical-qualifier controls.

The strongest alternative explanation, an oversized recognition box, is
contradicted by the matched native callback and fresh PDF reproduction. The
remaining uncertainty is generality and the safest upstream repair, rather
than whether the local validator created this overrun. The optional product
repair handles the integration failure while leaving native correction open.
