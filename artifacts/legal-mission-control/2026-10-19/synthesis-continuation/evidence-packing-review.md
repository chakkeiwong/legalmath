# Evidence branch: a feasible pair was missed

The exact production-capacity diagnostic refutes the explanation that no pair
of the final four summaries can fit. Combining `reduce-evidence-3-0` with
`reduce-evidence-3-2` measures 137278 bytes and 32355 local tokens at dispatch,
inside the existing 200000-byte / 32768-token bounds. Provider-visible
measurement also passes: 136171 bytes and 32161 local tokens. The other five
pairs exceed the token bound, not the byte bound. All four singletons fit.

The production `pack_items` algorithm considers only contiguous groups in the
current order. The feasible pair is nonadjacent. Once each singleton has been
normalized, `PhasedProduct.reduce` sees four singleton groups and raises
`Synthesis cannot contract without losing support`. On this retained input that
is wrong as an assertion that no legal transport grouping can contract: there
is an exact capacity-feasible grouping with three groups. No model call or
legal acceptance is needed to reproduce this scheduling error.

Proposed bounded repair: keep the existing contiguous packing whenever it
contracts or still has a permitted normalization. Only at its no-progress
boundary inspect pairs of unchanged retained members under the actual
measurement callback. Use a deterministic first fitting pair, preserve every
member and all source/citation data, carry all other groups, and retain the
original-order membership audit. Do not repeatedly normalize the same summaries
or silently raise the input ceiling. Limit the pair search to a reviewed small
frontier, initially these four groups, with six measurements maximum.

Success criterion for a local prototype: the actual final four groups become
three; exact member hashes and count are preserved; every proposed group passes
the production measurement; unchanged greedy-success cases are unchanged.
Vetoes: altered/missing/duplicate input, changed limits, dispatch, or use of an
approximate measurement. A passing prototype does not establish that the next
model synthesis will validate or that subsequent groups can be combined.

This local proposal is independent of P10's current model work but shares its
bound source files. Therefore production code and registration are not changed
while P10 runs. Adoption requires a reviewed same-master transition, exact reuse
of all 86 evidence accounts and all 135 successful synthesis calls, a fresh
phase directory and a preserved eighth evidence-owner attempt if authorized by
that reviewed continuation. The current owner allowance remains seven of seven.

Skeptical audit: PASS for the read-only diagnosis and isolated prototype. The
finding identifies a local packing error; it does not show that arbitrary
context can fit or that larger models solve legal interpretation. No proxy test
is being used to promote legal output. The saved original result remains FAILED.
The unchanged wire-size contract, source coverage and downstream source review
remain required. Other branches retain their own prerequisites.
