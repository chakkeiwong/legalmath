# Both original labels reach the source/layout consumer after supplied orientation

The exact original “Negócio Doméstico” and “Negócio Internacional” readings now
project through retained_ocr_units and project_layout with complete character
maps and valid original-page word positions. The clockwise direction was fixed
from the inspected original image before recognition. The matched unrotated
crops and opposite-direction crops fail both complete readings. The original
whole-page callback also fails both. This establishes the usefulness of supplied
orientation for these two exposed regions, not automatic orientation discovery.

The initial international quarter-turn outputs contained an extra `|`. Its
native box was exactly[321,0,324,80], the three black alignment columns created
by our reused callback helper outside the321-pixel image. The initial comparison
refused that geometry. The failure, native events and partial consumer files
remain retained. Coordinate inspection corrected an initial progress-message
misidentification of the failing arm; PADDING-REPAIR-REVIEW.md records it.

One reviewed usage repair made those alignment columns white before invoking
the unchanged native helper. The321 original image columns and their grayscale
values remain exactly equal; precisely240 synthetic grayscale pixels change.
Only the two affected native arms ran again. The upright international output
then contains exactly the20 target characters; the domestic candidate contains
16. The opposite-direction international output still fails the frozen reading.
No glyph was dropped, source coordinate clipped, target changed or model tuned.

All14 adverse controls reject: wrong edition, swapped label, page, region and
accent on each positive consumer, plus four malformed/out-of-content box cases.
The inverse transform agrees with all pixels of a labeled nonsquare image under
all three image operations, and every accepted event/word box round-trips.
Every native character remains in its raw event sequence. Character positions
stay on the original300dpi image; rotated derivatives have separate hashes.
Candidate whitespace is declared formatting, as in the existing consumer.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Limit |
| --- | --- | --- | --- | --- | --- |
| Retain supplied orientation result | Both complete fixed labels pass actual source/layout projection | Original malformed padding refused; single reviewed repair and14 controls pass | Only two exposed regions with supplied crops/direction | Preserve bounded preprocessing evidence; test source-boundary migration separately | No automatic orientation, general OCR accuracy or package adoption |
| Attribute extra glyph to local callback usage | Exact synthetic black-strip location and lossless white-padding comparison | Old failed outputs remain visible | Other callback/runtime behaviors are outside this comparison | Use white alignment padding in any future reviewed callback integration | No fundamental package defect established |
| Keep native-candidates partial | Original full-question mismatch and missing direction/independent families unchanged | Native promotion remains blocked | Canonical character lineage, clause invariance, true vertical/bidi cases | Review next discriminating scope under cumulative authority | Full native integration, source authority, legal interpretation or completion |

The strongest alternative explanation for the two successful readings is the
supplied precise region and direction. Matched unrotated crops show cropping
alone did not recover either label, but independent unseen cases are still
needed. These are deterministic finite comparisons; no stochastic ranking or
population accuracy is claimed. Genuine vertical writing is a different family
from these rotated Latin labels. The historical group-axis patch and fresh ABI
trial remain separate, unchanged evidence.

There are12 retained stage invocations: preparation, six native arms, one failed
comparison, and four stages of the single reviewed repair. Eleven stage commands
passed; one failed. Every command completed synchronously in less than one second
of recorded stage time; there were no yielded sessions or duplicate starts.
The two repeated arms are explicitly changed white-padding variants. No successful
native arm was rerun. Exact commands, elapsed times, interpreter, HEAD, CPU-only
policy, deterministic seed status, plan and result paths are in invocations/.
Frozen source/runtime/method hashes and all native/consumer results remain local.
No production source or installed package changed. Native task completion and
all four broader delivery flags remain false.
