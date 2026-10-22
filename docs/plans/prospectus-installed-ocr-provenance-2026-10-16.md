# Complete the installed OCR provenance comparator

Baseline132/006 failed before launching any process. The corrected product
hash checks pass; the complete source comparator finds exactly four leaf
differences after its two declared receipt substitutions. source_graph.py stores
the fresh OCR runtime twice, both in document.runtime and
document.ocr_extraction.runtime. retained_ocr_units computes ocr_sha256 from
the complete worker JSON after extraction.scan adds the installed receipt and
worker/interpreter/model identities. The installed worker path and manifest
therefore change three fields of the duplicated receipt and the derived OCR
hash. The native input/output streams themselves match the complete comparator.

The prior plan's receipt-difference inventory was incomplete. Repair the
comparator by reconstructing the entire fresh OCR JSON from the actual retained
native stdout plus independently verified manifest/interpreter/worker/model
identities and the actual receipt. Require both runtime copies and ocr_sha256
to equal that reconstructed JSON. Perform the same reconstruction against the
comparator's own manifest and receipt. Only then substitute the duplicate
receipt and derived hash, followed by exact whole-graph equality. Do not delete
OCR metadata or broadly ignore provenance. Add controls for forged OCR hashes,
changed runtime fields and source text, plus a real005-source regression with
zero native calls. This addresses our incomplete comparator, not a package bug.

Seventh same-task admission retains001–006, including005's real source and
006's zero-call failed preparation. Continue from005 exact source bytes using
the unchanged004 installation and profile. All132 cumulative process limits
remain:29 prior outer commands,6 prior installed native calls, exactly8 remaining
outer commands and2 native calls, no fresh-source repeat or retry. The seventh
admission is explicit; no admission or call counter resets. Freeze reviewed
current helper/test methods after at most two test starts. First perform complete
offline source/provenance validation, then fresh construct/finish/verify; only
that passing canary permits retained extraction. Retain actual failure or full
result, record and refresh, then continue current acceptance review.

Skeptical audit: PASS with the material comparator omission repaired before
execution. Current source streams and exact recursive differences identify
the mismatch; reconstruction checks the derived value instead of weakening
comparison. The real-source no-native regression tests the previously missed
integration, while negative controls retain content sensitivity. All evidence,
time/storage, independent-review and noncompletion limits of132 remain. No
additional native work beyond the original four-call campaign is introduced.
