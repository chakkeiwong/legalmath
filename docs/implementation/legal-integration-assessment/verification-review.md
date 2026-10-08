# Historical verification and local continuation review

8 October 2026. A2 completed the controlled mixed product, checked its dossier,
proved exact restart with no new model requests, and rejected a forged backend
binding. It then failed while asking the current-root verifier to validate the
predecessor's replay dossier. That replay deliberately hashes every historical
source file; the changed `complete_investigation.py` correctly failed the hash
check. This is a harness-root error, not corrupted historical evidence or a
failed mixed product.

Implement the original plan's historical-root requirement explicitly: copy the
preserved source snapshot and the predecessor's immutable R2 receipts under a
separate local root, plus the two original Java executable files referenced by
the replay. Validate their original hashes, then run the current read-only
dossier verifier against that root. Historical report profiles stay unchanged.
Do not modify the predecessor source, receipts, or hashes. Preserve the root
and a copy manifest so subsequent verification can repeat the check.

Preserve the already completed controlled workflow. Its exact provider requests
are available in the core cache and transport/scoped request files; reconstruct
the missing local request summary with those exact retained objects, identifying
this reconstruction in a separate receipt. Reopen the controlled workflow using
its cache, finish the remaining retained-candidate tool check, and record A2's
result. No new controlled or live model requests are needed for this recovery.
The prior sequential suite's 264 distinct passes remain applicable: no product
source changes in this correction. The changed harness is tested by actual
historical-root verification and the completed A2 recovery.

Verdict: **PASS**. Retained records identify the precise mismatch; the repair
implements the planned source/evidence separation without weakening a hash
check. The current mixed dossier remains complete in the sense of processing,
with one executable comparison and one UNAVAILABLE assessment. It remains
unresolved for legal promotion. Preserve the initial and local-validation
reviews; seal this final harness revision separately. The same repair batch,
five-call ceiling, source pair selection and original grant/window remain.
There is no extra phase or automatic repair loop.
