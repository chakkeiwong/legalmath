# Exact source references without asking a model to retype the source

Status: specified continuation; not implemented by this campaign.

The authentication investigation returned quotation strings in which ordinary
spaces, and later null characters, replaced source nonbreaking spaces. The
current validator correctly rejected them. eDDA also repeated source-unit
coverage rows. These are response-construction failures. They do not establish
that the model's substantive reading was wrong, and they cannot be counted as
successful legal error detection. The original responses and exhausted issue
allowances remain unchanged.

The next transport protocol should make exact copying a deterministic software
operation. It must preserve the separate question of whether a selected passage
supports the proposed interpretation. A correct location is not entailment.

## Source identity and coordinate convention

Before dispatch, create a reference table from the retained packet. Each entry
contains the packet digest, source-unit ID, complete unit-text digest and exact
Unicode text. A source selection contains `unit_id`, `start_codepoint` and
`end_codepoint`, plus the packet and text digests. Offsets use Python Unicode
codepoints into the unchanged unit string, half-open `[start, end)`. They are
not UTF-8 byte offsets, UTF-16 Java character offsets, normalized-text offsets
or PDF coordinates. Conversion to another coordinate system needs an explicit
checked adapter. Do not normalize whitespace, case, punctuation or combining
characters before resolving a reference.

The deterministic resolver accepts only an existing unit with matching hashes
and integer offsets satisfying `0 <= start < end <= len(text)`. It constructs
the quotation as `text[start:end]`, records the reference and resolved string,
and then applies the existing quotation and semantic validators. If the existing
quotation profile requires uniqueness within the unit, retain that requirement;
an ambiguous short fragment must select a longer distinguishing span. The
resolver must never choose a nearby fuzzy match or infer the intended clause.

For sources already divided into short units, selecting a complete unit can be
an explicit option. It resolves to offsets zero and `len(text)` with the same
hash checks. Returning a whole unit rather than a minimal fragment may reduce
copy errors, but its semantic relevance still requires assessment. Long units
must not silently exceed evidence limits; they need bounded selections.

Do not assume that a model can count character offsets more reliably than it
can copy a quotation. The initial implementation should expose short whole-unit
identifiers and, when a smaller selection is required, precomputed span
identifiers whose exact coordinates are retained by the resolver. The model
selects from that request's closed identifier set. The software supplies the
digests and coordinates from the bound reference table. An optional raw-offset
route needs its own observed validity check before becoming a default.
Deterministic segmentation must preserve a way to select adjoining spans and
the full surrounding provision; a convenient sentence boundary cannot remove
an exception. This reduces copying and counting work without preselecting the
legally correct passage for the model.

## Coverage is a separate bounded obligation

Partition the complete list of required unit IDs deterministically. Give each
response a closed requested-ID set and require one disposition for every ID in
that set. A merger rejects omissions, duplicates, invented IDs and a different
packet or reading identity. Distinct pieces may share contextual text without
claiming to own each other's coverage rows. Retain the full source for the
global consistency check described in `capacity-repair-contract.md`.

This protocol can reduce transcription and bookkeeping burdens. It cannot
deterministically supply a missing legal qualification or settle whether a
reference is an exception, an example, a definition or nonbinding commentary.
That interpretation remains a model proposal subject to rival readings and
source-directed criticism.

## Implementation and discriminating checks

Add a versioned response schema and a pure resolver in a separate module.
Keep the existing internal quotation objects and source validators. Store the
original response, reference table, resolver version, resolved response and
validation result. Every response binds the exact candidate or inventory under
review. A change in packet, unit bytes or candidate meaning invalidates the
corresponding checks. New schema requests are not cached as identical older
requests and do not count as independent corroboration of those requests.

Before live use, exercise nonbreaking spaces, combining Unicode sequences,
astral characters, CR/LF, repeated phrases, footnotes, table continuations and
cross-unit exceptions. Mutate hashes, offsets, coordinate conventions and
membership. A span identifier from another request or source revision must fail,
and adjacent-span reconstruction must equal the retained original characters.
Invalid references must fail before semantic evaluation. A valid
but irrelevant quote must still be rejected or questioned by the semantic
stage; exact extraction alone must not make its label SUPPORTED.

Freeze the failed authentication and eDDA workloads plus structurally different
sources before model responses. Compare response validity and complete source
accounting against the retained literal-quotation protocol. Report actual
invocations and incomplete tasks. Do not rank legal accuracy from quotation
validity. Live execution needs an explicit allocation and reviewed issue
identity policy: the new protocol cannot silently reopen the old exhausted
questions, refund reservations or create extra legal votes.
