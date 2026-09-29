# D0–D1 implementation review

The engineering target is exact preservation of a complete request while
reducing repeated representation. The source, interpretation, questions and
output schema remain literal. The encoder is optional; existing recorded routes
and source-reference responses retain their old contracts.

The pre-execution skeptical audit is in
`docs/plans/assurance-capacity-execution.md`. This code review checked the
following concrete failure mechanisms before isolated execution:

| Mechanism | Implemented check | Remaining limit |
| --- | --- | --- |
| Lost concern, field, ordering, question or explanation | Decode and compare canonical bytes of the entire request; strict known columns/widths and hash of the independently retained original | A model may misunderstand a complete input |
| Changed source edition or quoted text | Exact source hash, Unicode codepoint ranges, unique substring check; regenerate source-span table | Location does not establish entailment |
| A shortened representation claims its own authenticity | Decoder requires a caller-supplied original-request hash; dispatch retains and compares actual original bytes | Receipts need the existing trusted file/identity boundary |
| Changed encoding reuses old evidence as a fresh call/vote | Protocol in the single-reader journal binding; cache replay consumes no new simulated provider response | Live behavior of the new representation is untested |
| Revision leaves stale coverage | Existing revision loop repeats every coverage piece and rebinds interpretation/coverage hashes | Repeated model mistakes remain possible |
| Too much genuinely different text | Preserve request and exact round-trip receipt, reject before provider dispatch at 200,000 bytes | No universal future-size guarantee |
| Exhausted retries produce an impossible recommendation | Old and new controllers expose `ATTEMPTS_EXHAUSTED`; no fourth attempt or limit reset | Later work needs a separately reviewed engineering continuation |
| Process crash refunds an engineering attempt | Reserve the phase in persistent state before subprocess execution | Interrupted attempts require a bound repair record |
| Concurrent unrelated changes invalidate attribution | Test an isolated material-input archive; verify source hashes after execution | A result applies to its snapshot, not every later workspace change |

The first focused test invocation failed to collect because `Settings` was
imported from the provider module instead of the models module. The next run
exposed two test-harness mistakes: an oversized unit violated the source schema
before it could test request capacity, and the old synthetic respondent marked
an unencoded reading executable. The repair used multiple schema-valid units
for the overflow case and explicitly unresolved question dispositions for the
unencoded exercise. The rejection validator was retained. All failed XML
reports remain in the phase artifact directory. The subsequent focused run
passed 37 tests; the separate controller run passed 12 tests. These overlapping
counts are not added as independent evidence.

The first actual retained-request measurement was 175,016 bytes, down from
382,396; reconstruction matched exactly. That measurement is not an estimate of
token use, model reliability or English accuracy. Structurally different tests
include empty concerns, context dispositions, Unicode and combining marks,
partial quotations, distinct long rationales, multiple evidence links, and
deliberate mutations of fields, indices, source identity and cross-piece links.
The deliberately oversized case must fail capacity while preserving its text.

The implementation uses an executable decoder and request-by-request equality,
not a claimed Lean theorem. The model's table comprehension has not been tested
live. No human labels, adjudication, ratings or acceptance are used to convert a
proposed reading into a quality result. The full D2–D6 successor obligations
remain visible after this increment.
