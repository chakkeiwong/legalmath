# Review of the failed product-identity comparison

The source trial passed all finite target screens (BES 8/8 and BASF's complete
margin relation) and 16 of 17 engineering checks. The extra check requiring
identical consumed product IDs failed. Preserve comparison.json, all four actual
answers, frozen methods and run_comparison.py exactly as executed.

Trace through service.py shows why the comparator was wrong: source_product
seals the complete request in P1's payload and request input hash; P2–P5 bind
their actual parent hashes. Selecting relation_discovery legitimately changes
P1's request, hence all descendant IDs, even when their semantic payloads are
identical. Suppressing this provenance would weaken the product contract.
The initial trial's only changed shared top-level answer fields are
request_sha256, consumed_products and report_sha256. That finding alone is not
enough to certify unchanged intermediate meaning.

Revised finite verification: recompute and retain all five actual phase products
for the exact default/v1/v2 requests using unchanged frozen product code. Verify
seals and consumed identities; rerun the final consumer and require exact
equality with the original retained answer. P1 must differ only by the explicit
profile field in its request, with an identical graph. P2–P5 payloads must be
strictly equal across routes. Every answer field except documented request,
product and report hashes and the optional suggestions must match. Preserve the
actual changed IDs in the retained products; no hash is waived or rewritten.

This audit revises an invalid harness assumption, not the candidate rule, source
targets, quality threshold or legal-isolation criterion. Any unexpected payload
or answer difference is a continuation veto requiring diagnosis. No predictor
tuning or new source score is authorized. One bounded 120-second deterministic
verification, CPU hidden and worktree-pinned, will retain its manifest and
reviewed comparison. The original failure remains part of the final result.
