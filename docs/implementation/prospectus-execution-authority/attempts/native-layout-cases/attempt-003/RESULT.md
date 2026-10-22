# Mixed-script failure reproduced in actual source intake

The current Poppler source route processed all 198 pages into 8,453 source
units. Ordinary P2 through P5 construction and the complete answer consumer ran
against that source. Q1, Q2, Q4 and Q6 remain UNKNOWN, Q3 PARTIAL and Q5
UNSUPPORTED. An exact reconsumption produced an identical full answer; both
altered-product and wrong-parent controls were refused.

None of the four visibly inspected page-6 URLs occurs exactly in the current
source units. The native XML splits URL text and punctuation into words; our
`source_graph.pdf_units` joins every word with a space. Retained PyMuPDF page
text and words contain each complete URL once. The diagnostic can reconstruct
the visible URL only by removing the generated spaces, and explicitly records
that this is not an exact source match.

On the three selected development pages, 2,210 token pairs have rectangles
matching within 0.001 point and strings that are exact reversals. The reversed
strings are already present in the retained Poppler XML; our importer preserves
those token characters. This establishes a difference between extraction
observations, not full Arabic correctness of either engine. Native glyph order,
logical language order, diacritics and paragraph order need exact independent
reading. These are deterministic observed counts, not a package ranking.

The proposed geometry-only adapter would leave these earlier text differences
untouched, so it was not implemented. The next discriminating repair is an
optional, explicit native-source choice that retains complete original line
text, word offsets and extraction provenance, with both original outputs kept
for comparison. It must run through the actual downstream consumer, preserve
unknown legal results and refuse missing/altered occurrences. Blind reversal
or whitespace removal is not an acceptable Arabic repair.

Two supervised native launches were reserved. The first failed at Bubblewrap
network-namespace creation under the outer sandbox, before Poppler execution.
The approved trusted retry succeeded in 3.31 seconds. Both receipts and native
streams remain retained; the historical visible reservation lower bound is 64,
including the sandbox refusal. No HTTP, OCR, model, GPU or installation calls
were made. The one local diagnostic repair corrected XML-control handling to
match the already recorded source importer; both versions remain retained.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Unsupported conclusion |
| --- | --- | --- | --- | --- | --- |
| Retain reproduced intake defect; broader layout task remains partial | Complete source-to-answer execution and exact attribution obtained; four URL checks fail on baseline | Full answer invariant and tamper controls pass; literal failure vetoes a claim of exact text preservation | Independent Arabic transcription and whole-page order | Explicit optional native-source alternative, with original line preservation and matched complete answers | Arabic accuracy, automatic completeness, package superiority or installed alternative readiness |

The strongest alternative explanation is the difference between visual/native
serialization and logical language order. Exact independent readings could
show additional defects in the PyMuPDF observations. The next repair therefore
must preserve its output as a selected extraction observation rather than
promoting it to a legal quotation verified by a reader.
