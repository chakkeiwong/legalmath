# Make missing required table regions explicit

Question: can the consumer distinguish retained page-number text from coverage
of the visible tables required by a source review? The reproduced counterexample
is page84 of the278-page original Hypo/Adriano prospectus, SHA256
3d0b4bb3ba56014512e34779bb91bb891c037bbb02345a0db5de7e30f5bc3341.
Retained P1 has only `6` and `84` on that page. The original render visibly has
four loan-cohort tables, two headed Time to Default and two Prepayment Rates.
The existing native_text_gaps diagnostic reports pages with no native text; it
cannot identify missing content on this mixed page. That limitation is already
documented in page-coverage002; do not misattribute native-only failure to OCR.

Implement an optional declared-region coverage API outside frozen successor
methods. A source reviewer supplies the page/render identity, finite rectangle,
content kind and reason for requiring each region. An optional exact reading
permits projection through the actual layout consumer. No supplied reading
means content is untranscribed, not empty. The API binds the exact source graph,
PDF, render and complete inventory. Every region returns its retained-word
anchors and either absent words, unresolved geometry, no supplied transcription,
or matched/mismatched source projection. Partial word intersections must not
silently disappear through center-point selection. Unknown geometry remains
unknown. Neither positive page text nor a matched region establishes full page,
table-cell or document coverage. There is no automatic image detector here.

Freeze the four table rectangles against the retained displayed792x612 page
and source render; preserve rotation metadata. Record table titles only where
legible; do not invent cell readings or treat grey areas as zero. Positive
comparator: the retained HETA English maturity paragraph, including its full
edict qualification and non-payment sentence, using the corrected reading from
page-coverage002. Keep its first failed transcription unchanged as historical
evidence. All judgments are agent-authored exposed development review.

Primary engineering pass: all four required table regions report absent retained
words despite positive page text, and the HETA paragraph maps every supplied
nonspace character through the actual layout consumer. Candidate output carries
source/render/graph/inventory identities and all region outcomes. Missing,
duplicate, foreign, stale or geometrically invalid inventories must refuse.
Wrong HETA negation/qualifier and partial-word cases must remain unresolved.

Actual downstream contract: reuse exact source019 P1, compute current P2–P5
without extraction, and retain the full baseline answer. Consume those identical
products through the optional coverage wrapper. Its full answer must equal the
baseline exactly; the separate coverage report must name all four missing
regions and must never authorize a completeness claim. Repeat the coverage
consumer on the retained HETA P1–P5 with its correct reading. No document scope,
source transcription, layout admission or legal result may be invented.

Intent ledger: primary pass is the exact finite region outcomes and unchanged
answers. Lost source characters, hidden partial overlaps, false completeness or
answer drift veto promotion. Corrupt source/render/graph or changed admitted
methods veto continuation. A reproducible implementation/fixture failure triggers
one bounded local repair with original failures retained. Region counts and
native character counts are explanatory, not a completeness metric. Missing
independent inventory prevents general promotion but does not stop this repair.

Default audit: supplied rectangles are an exposed review hypothesis, justified
by the actual original image and checked by exact source/render identity. They
could omit another region; accordingly page/document completeness remains false
even when every declared reading maps. TOPLEFT displayed-page coordinates follow
the retained rotation descriptor, not guessed image dimensions. No text-count,
confidence or image-density threshold is introduced. The same local interpreter
uses pure Python and retained products; no OCR, native child, installation,
network, model call or GPU framework is needed.

Skeptical audit: PASS for explicit required-region reporting, not extraction or
full table interpretation. This fixes a reporting/coverage-interface gap while
preserving the genuine extraction gap. HETA is a positive source comparator;
four absent tables alone cannot prove the API handles represented text. One
additional admission extends the original page-coverage budget2 to3, retains
001/002, and permits120seconds per stage and40MiB of new retained evidence.
Keep source/method hashes, actual commands, products, answers, controls and result
notes. Seal, record and refresh; select the next independent route without
treating a finite package or empty dispatcher queue as whole completion.
