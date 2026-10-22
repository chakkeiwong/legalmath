# Bounded request reuse repair

The first reusable-entrypoint smoke reached the 120-second timeout (exit 124).
No result was written and no source/consumer evidence changed. The prospective
wrapper recursively rebuilt every status/pledge predecessor, repeating whole
construction and reference admission. This is an orchestration failure; the
actual baseline, candidate and eight adverse controls already passed.

Repair: reuse the immutable latest status/pledge request, checking its exact
compressed bytes, full request digest and freshly supplied source graph digest.
Reconstruct and check the selected assembly once, then apply the new packet.
The candidate must equal the request already consumed successfully. Changed
source or request identities veto reuse. This preserves the tested comparator
and removes repeated historical preparation; it does not claim independent
validation of earlier legal readings. One bounded smoke will check equality.

The unsealed attempt temporarily used 41,602,813 bytes, above the 40 MB retained
evidence bound. Before sealing, losslessly compress the diagnostic prose index
and deduplicate the actual-request copy against actual-P1's request payload.
Retain both original byte hashes and restoration instructions. This changes
storage only; verify round-trip equality and require the final sealed directory
to meet the original 40 MB bound. No authority budget or limit is reset.

Skeptical repair review: proceed. Exact equality with consumed input is the pass
criterion; faster preparation alone is not. Record the original timeout and
resource excess even if the repair passes.
