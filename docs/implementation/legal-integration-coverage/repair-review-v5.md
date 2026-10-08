# Request-bound response aliases

The second large-batch attempt returned one validated perspective at 179.876
seconds (5,853 output tokens) and timed out on the second perspective. The
small diagnostic passed, but the original 12-pair representation has failed
twice to complete both perspectives within the existing cap. This is an
execution failure; its provider-side cause is not established. Another
unchanged retry is not justified.

Question: can short identity references reduce response overhead enough to
complete the same 12-pair assessments while preserving their exact semantic
content and downstream validation? Comparator: the retained original wire
request/schema and returned 12-pair proposal. Mechanism: a request-local pair
key names the exact claim ID, candidate ID and typed-question hash. Source
and executable span keys name the original full span IDs. The model still
selects every pair and every quoted span and supplies every dimension,
rationale, authority assessment, followup and additional concern.

The codec retains the original request verbatim inside an envelope, derives
all aliases locally, and emits an output schema with only those short keys.
It expands the model's choices against independently retained maps before the
unchanged source-reference and executable validators run. It cannot create
source support, choose statuses, prune a pair, change a quotation or repair
an invalid legal response. Text is never searched and replaced. Mapping
tables cannot be supplied or revised by the model. Pair/key coverage and
duplicate/foreign references are checked before acceptance. This is an
explicit new optional transport method, not historical evidence reuse.

Engineering pass: exact round trip for retained and controlled output,
unchanged judgments/rationales/followups, changed request/map rejection, foreign
and duplicate pair rejection, unavailable-executable and changed-question
controls still rejected by existing validators. Byte/token reductions are
explanatory nomination evidence only. Live pass: both complete perspectives
on unchanged pilot batches in both arms, using the alias codec in both arms.
A pass does not establish faster average service, legal accuracy, reliability,
or that long hashes caused the timeout. Full coverage still requires all 492.

Defaults: deterministic p/s/e keys ordered from the exact request/schema
(convenience indexing, not legal labels); original 180-second limit and route
(inherited unchanged bounds); no truncation or length cap on legal reasoning
(source-fidelity requirement). A supplied question hash becomes implicit in
the model-selected pair and is restored from the original question binding;
this does not establish that the rationale actually answers that question.

Skeptical audit: PASS conditional on engineering controls. Merely shortening
an answer or dropping fields would be an invalid remedy. This design reduces
identity spelling only. The two-pair live evidence is retained separately and
cannot be counted as a complete bulk batch. Nine calls are consumed; the
first alias baseline pilot can use at most two of the remaining six repair
calls, after which original combined/baseline allocations remain intact.
Stop at the first new dispatch/validation failure and inspect it. Do not
automatically expand timeouts or consume the allowance through unchanged
retries. Preserve old reviews, source snapshots, failed journals and raw output.
