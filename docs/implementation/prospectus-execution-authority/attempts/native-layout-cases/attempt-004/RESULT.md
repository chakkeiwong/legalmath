# Optional native-text selection repairs the four literal failures

The new optional `native_text_choice` API constructs a separate P1 from the
retained PyMuPDF observations on Riyad PDF pages 5, 6 and 14. All 168 observed
lines, their whitespace, and 2,682 words are preserved exactly. The final
selected answer contains each of the four visibly reviewed page-6 URLs once.
The original Poppler answer contains none of those complete literals.

All 195 unselected pages retain exactly the same source units. The baseline
full answer is unchanged on reconsumption. Both complete answers are retained.
The selected answer differs in source text, source and parent hashes, assembly,
clause graph and unresolved source identifiers. Q1, Q2, Q4 and Q6 remain
UNKNOWN, Q3 PARTIAL and Q5 UNSUPPORTED. The recursive question comparison keeps
every value, witness, qualifier and subquestion structure equal, allowing only
explicitly retained differences in unresolved occurrence lists. Q4 through Q6
are completely equal. No supported legal conclusion is added.

The implementation handles the observed API difference in page5 block numbering:
dictionary block14 includes two preceding image blocks, while the corresponding
word block is text-block12. It records both identities and requires all line
characters and word ordinals to match. It does not reverse Arabic, strip
whitespace, infer reading order, or silently replace the original extraction.

Verification: 76 focused tests pass and14 actual-data adverse controls refuse.
One comparison harness repair was needed for nested Q2 unresolved lists; the
failed method/result and reviewed comparison are retained. No product repair
or native re-extraction occurred. There were no network, OCR, model, GPU or
installation calls. The native reservation lower bound remains64.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Unsupported conclusion |
| --- | --- | --- | --- | --- | --- |
| Retain optional native-page selection as a source-preservation repair; broader task partial |168 exact lines,2682 word intervals,4 exact downstream URLs and195 unchanged pages |All14 actual controls refuse; baseline answer unchanged; broader language/independent review still outstanding |Correct full Arabic transcription and order; unseen cases; installed use |Evaluate the optional route in an installed package and retain independent full-page reading requirements |Whole-page Arabic correctness, automatic legal interpretation, package superiority or production default readiness |

The strongest alternative explanation is that PyMuPDF preserves these literal
strings while making other language or ordering errors. This repair does not
remove that possibility: the original native observations, image identities and
baseline remain available. Independent page readings could reject the selected
observation for legal use without invalidating its exact preservation checks.

The selection is explicitly retained replay. Existing default current-mode
extraction differs and requires reassessment. The optional route has not yet
been evaluated as an installed package.
