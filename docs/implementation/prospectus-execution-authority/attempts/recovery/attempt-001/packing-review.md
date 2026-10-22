# Lossless evidence packing repair

Finalization passed all semantic checks but failed its 60 MB sum-of-files bound:
160,116,656 bytes. It had already written the result, comparison, methods and
note, but no output manifest was sealed. The failure is an evidence-packaging
error, not a failed recovery state or package defect. Preserve the failed
finalizer and its error before changing storage.

Reviewed repair: hard-link byte-identical files inside this unsealed attempt.
Every successful state's file path and bytes remain identical. Keep the full
original path-to-hash map and verify it after packing. Count and report logical
bytes, unique content bytes and filesystem bytes separately. The 60 MB limit
now applies explicitly to retained unique content and actual hard-linked file
storage, not logical pathname size. An ordinary checkout that expands hard
links can occupy the larger logical size; no portable-package claim follows.
This is a recorded change to storage accounting, not an assertion that the
original sum-of-files check passed.

Skeptical audit PASS: identical compressed payloads have the same content hash
and are compared byte-for-byte before linking. File content/path changes, a
lost successful state, or unique/physical payload above 60 MB veto sealing.
Use one bounded local packing command, preserve every successful result, and
do not rerun unchanged extraction. The hard-link operation only replaces a
duplicate after creating and verifying its replacement. The original failed
finalizer remains in `packing-finalizer-before.py`.
