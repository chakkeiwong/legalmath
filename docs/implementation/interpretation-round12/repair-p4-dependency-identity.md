# P4 repair: repeated references and nested harness failures

The third live attempt completed the margin and eIP workflows. Both retained
unresolved interpretations. The STR inventory then completed both source readers,
including all pieces and cross-piece checks, but search intake failed with
`E_DUPLICATE_ID`. Inspection found two identical unresolved-dependency records for
the same referenced document. All 27 source-unit IDs were distinct. This is an
implementation failure in assembling the search input, not evidence against an
English interpretation. The shared ledger contains 231 reservations at the stop.

The wrapper also failed to distinguish a nested `FAILED_INTEGRITY` report from
ordinary incomplete interpretation. The master was interrupted before proceeding
further. This defect must be repaired, not recorded as a successfully investigated
ambiguity.

Repair the boundary between raw source inventory and search intake. Preserve the
original inventory requests and all source occurrences. After context collection,
coalesce only exactly identical dependency records. Reject one dependency ID with
different bindings. Record the original and normalized dependency records and
packet hashes. No source text, quote, source-unit ID, distinct authority or
unresolved question may be removed. Previously completed inventory responses
remain exact request replays and are revalidated against the unchanged units;
subsequent search receives the valid normalized packet.

A nested integrity failure must fail the integrated action and stop further live
cases. Arbitrary sidecar failures must not be reclassified as provider outages.
The tests must exercise the real STR packet and the complete source-to-search
boundary, and must show that an inner integrity failure cannot reach independent
checks or an incomplete-evidence pass.

The source action identity also needs its own processing profile. It currently
includes every interpretation setting and every source-code module, causing
unrelated repairs to re-extract identical bytes and exhaust the source issue's
three-action bound. Bind source bytes, extractor/region/sidecar/helper code and
tool locks instead. The initial transition from the broad legacy identity is a
new, explicitly versioned source-processing issue. Retain every old action and
the global 100-action limit. The three-per-issue limit, model request limits,
30-action case caps, elapsed deadline and shared ceiling of 273 are unchanged.
Subsequent interpretation-only changes must reuse the bound source action.

The previous three phase attempts remain failed records. This diagnosed harness
repair adds exactly one reviewed P4 attempt, increasing only its phase-attempt
bound from three to four. It does not issue any new model allowance, change the
provider or erase spent calls. Other phases keep their existing bounds. The
master must read the declared phase bound rather than a hard-coded constant.

Skeptical review: deduplication of source text or merely similar references would
hide evidence, so only equal dependency records may coalesce. Replaying old
inventories as fresh votes would overstate independence; retain original call
provenance. An unbounded phase retry would evade the program's stop condition;
allow exactly this additional attempt, with focused executed checks and a refreshed
plan. A further unsupported harness failure remains a continuation veto. Candidate
uncertainty alone remains a promotion veto, not a failed engineering run.

Focused execution: `.venv/bin/python -m pytest
tests/assurance/test_investigation.py tests/assurance/test_integrated_workflow.py
tests/assurance/test_closure_master.py tests/assurance/test_decomposition.py
tests/assurance/test_sources.py -q` passed 59 tests in 20.20 seconds. The actual
STR source packet now enters search with all source units retained and one
duplicate dependency record coalesced. A conflicting binding remains an error.
The nested-failure test confirms no independent action runs after an integrity
failure. The source-reuse test confirms an interpretation-only settings change
reuses completed source processing. These are engineering repairs; they do not
resolve any legal interpretation. The reviewed fixed master command is unchanged.
