# Repair installed validator hash-domain mismatch and continue existing calls

Revision131's005 failed in the outer source validator after the actual installed
source command passed. It used one outer command and two native calls. The new
driver incorrectly called execution_authority.digest for a product parent;
that serializer uses compact separators, while successor.contracts.digest uses
the product's established JSON serialization. The same request therefore has
authority hash3a2f0f72f9a5e1e7061c8377cc677911487ee067a0b176cc4f4e31300b101e2d
and product hashe9e0ae013c9565d3b05391ec3bc3a5ff175f9744162f1d11fa2d8938ce4cb5bb.
Direct verification with the product hash succeeds. This is our integration
harness defect, not evidence against the extraction packages.

Retain the failed005 manifest, source stages, streams, receipts and both ledgers.
Repair all three product-domain hashes in source_evidence: request parent,
execution request and profile pin. Add a regression built with the actual
product seal and the non-ASCII original-source request; ensure it rejects a
wrong parent even if the product body is rehashed. Keep authority task/method
hashes in their existing domain.

The sixth same-task admission continues the identical finite campaign after a
reviewed repair. It grants only the original remaining two native calls for
source-retained, and eight outer commands (three fresh downstream, four retained
lifecycle, controls). Historical installed counts are now29 outer and6 native.
Do not repeat source-fresh. Copy its exact product/native/stage bytes into the
new attempt, retaining an explicit005 origin map; do not alter any copied byte.
Run the corrected full source validation offline before any downstream work.
The imported fresh source plus newly constructed/finished/verified answer remains
the canary for retained source. Failed005 is never relabeled a passing run.

All other evidence criteria and limits from the revision131 plan remain:
exact native streams, exact source except separately verified receipt fields,
complete downstream meaning and own-parent consumption, actual installed module
paths, no dependency/package/profile mutation,120s stages,512MiB evidence,
128MiB private workspace, no network/install/GPU. Tests have at most two starts
before freeze. No new native repair/retry reserve. New failure seals evidence
and requires another discriminating review; no unchanged source retry.

Skeptical audit: PASS for this repair. The positive installed source result and
correct product verification isolate the failure to our hash-domain usage.
Retaining source bytes avoids an unnecessary new extraction and keeps cumulative
accounting exact. The old failed stage remains a real failure; accepting imported
source requires corrected validation, full stream/receipt checks and new
downstream consideration. No acceptance or package conclusion follows from the
unit regression alone. Full lifecycle evidence and the reviewed current
acceptance registration remain required. Independent legal truth, portability
and whole-program completion remain unestablished.
