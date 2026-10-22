# One bounded original-answer comparator repair

The initial original baseline check failed after9.436seconds. Complete P3,
phase-product identities, questions and source reports agree with attempt001.
The only differences in its complete answer are the later-added
`native_text_gaps` diagnostic and the resulting report hash.

The retained original graph contains exactly one blank-or-unread occurrence:
`bes-base-2010:p287:blank`. `source_graph.native_text_gaps` reports this lack of
native text without asserting that the page is blank. This is a source-backed
diagnostic that the older answer omitted. It must not be removed from current
answers or ignored as an arbitrary differing field.

Use the one permitted comparator repair: verify the original occurrence is
visible, has the original source hash, uses `blank-or-unread`, and contains no
native text. Derive the exact documented gap from that source and add it to a
copy of the original historical answer; recompute only its report hash. Then
require complete equality with the retained failed-check answer. Preserve the
original failed result and code unchanged. Compare the corrected source scope
against this explicit current baseline and the exact retained corrected-original
report explanation. No production edit or focused-test rerun is warranted.

This is the fourth and last allowed stage once the final matched stage runs:
focused, initial baseline, comparator repair, matched consumer. Each remains
<=120seconds,480seconds total; storage is prechecked against20MiB. Any further
failure is retained without another automatic repair. Native extraction and
independent source/legal review remain unestablished.
