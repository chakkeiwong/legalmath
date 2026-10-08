# Repair cross-unit quotation selection without changing legal judgments

Batch 17 stopped after its source-first reply selected paragraph 14 and
footnote 5 as one quotation. The two selected spans belong to different source
units. The existing source validator correctly rejected the reply with
`E_REFERENCE: Spans must adjoin in source order within one unit`. The response
arrived in 128 seconds; this is a returned format failure, not a timeout or a
finding against either legal reading. Keep the raw response and failed receipt.

## Remedy and evidence contract

Constrain each quotation in the compact response schema to one selected source
span. Every source unit already has a selectable full-unit span, so this does
not remove any original source text from the request or prevent quoting a whole
provision. Separate provisions require separate evidence entries. State this
rule explicitly beside the alias instructions. The internal source quotation,
executable and fidelity validators stay unchanged. Do not split, relabel or
otherwise turn the rejected reply into an accepted model proposal locally.

Replace the failed source-first response with a fresh request, then issue the
previously unissued qualification-first request. Neither perspective receives
the rejected legal answer or a peer answer. All twelve original pairs and their
typed questions remain. Future requests use the same constrained quotation
schema. Previously accepted responses and reviews remain immutable.

The primary engineering criterion is two independently requested, validated
perspectives for the original batch, with all four dimensions assessed.
Changed sources/questions, fabricated labels or missing pairs veto acceptance.
A further returned invalid response or dispatch failure stops live work for
another specific review. Timing and label changes are descriptive only. No
legal accuracy, tool ranking or closure follows from a format repair.

## Allocation within the existing user authorization

The ledger has 51 reservations: combined 34, baseline 3 and repair 14. Both
baseline pilots are complete. There are 24 combined batches left, including
the failed batch. Its replacement uses one repair call, its unissued second
perspective uses one combined call, and the other 23 batches need 46 combined
calls. Completion therefore projects to **99 total: combined 81, baseline 3,
repair 15**. No failed call is refunded.

The original plan's 14-call repair allocation is exhausted. It is an internal
allocation, stricter than the user's unchanged 100-call/20-repair authority.
Preserve the original authorization byte for byte and add a reviewed allocation
revision: combined 81, baseline 3, repair 16. This transfers the two unused
normal slots into repair reserve without increasing the total or changing any
past reservation. Preserve and hash the 51-call checkpoint; every later ledger
must retain that exact prefix. This remedy uses one transferred slot. The
remaining slot is not authority for an unreviewed retry. The absolute expiry
1791519402.34676 and 300-second per-call limit remain unchanged.

There are 16 repair entries before this remedy. The implementation revision
and its live replacement consume two more, projecting to 18/20. No new user
grant or time window is inferred.

## Skeptical audit before execution

PASS conditional on fresh tests and retained-evidence verification. The wrong
baseline risk is addressed by preserving the exact source/question matrix and
every completed batch. Schema validity remains an engineering criterion, not
a proxy for correct legal interpretation. The inherited source-span protocol
was checked: full-unit spans exist for every source unit, and multiple evidence
entries are supported. A cheap test must reject cross-unit multi-selection
while accepting the same citations as separate entries through the original
validators. Allocation tests must reject changed history, authorization,
ceilings and checkpoint data and must preserve expiry and nonrefundability.

The finite completion arithmetic fits the existing authority and remaining
time, but leaves only one extra call. That is a material reliability risk,
not a reason to conceal incomplete coverage if another remedy cannot fit.
The failure invalidated this response format, not the retained legal target.
The planned response-repair phase directly addresses it, so execution resumes
only after its checks pass.

Commands retain the already approved fixed prefix:
`.venv/bin/python scripts/run_legal_integration_coverage.py` with `test`,
`verify`, `repair`, then `execute`. Local checks use the sandbox; live actions
use the existing trusted wrapper approval. Artifacts remain in
`artifacts/legal-integration-coverage/2026-10-08/`, under revision v12 and a new
batch-17 attempt directory.
