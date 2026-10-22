# Complete OCR provenance review

checked_fresh_ocr reconstructs the full OCR JSON from the actual stdout and
manifest-pinned interpreter/worker bytes, the bound model identity and verified
receipt. It checks both runtime copies and the complete derived product hash.
The original017 comparator is reconstructed with its own receipt and manifest.
Only those validated fields may be substituted before exact graph equality.

The regression now exercises the real005 source and complete retained streams
without native calls, and rejects forged OCR hash/runtime. Earlier tests retain
text/unknown/receipt sensitivity. This closes the previously missed duplicated
provenance, not a source-content mismatch. PASS to test and continue under the
unchanged remaining two-call grant.005 and006 remain failed immutable attempts.
