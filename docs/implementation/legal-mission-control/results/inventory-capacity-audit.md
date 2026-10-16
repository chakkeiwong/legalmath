# Full-target inventory capacity audit: current route cannot reach an answer

10 October 2026. The admitted [offline audit](../../../plans/legal-mission-inventory-capacity-audit.md)
is complete. It made **zero live calls** and changed no product method, grant,
historical result or legal source. The executable diagnostic
`scripts/legal_mission_inventory_capacity_audit.py` reads the terminal timing
run's exact source packet and four retained responses, validates each piece,
reproduces the product's merge failure, and measures the actual qualified,
compacted, source-span/readable transport path. Its bounded result is
`artifacts/legal-mission-control/2026-10-10/live-pilot-400/capacity-audit/diagnostic.json`.

The original target contains four documents and 55 source units. Calls 10–13
cover 53 units; the fifth piece, second reader and full-source checks did not
run. The fourth resolved piece independently passes the unchanged one-piece
inventory validator, but it was never accepted by the journal. Thus the
following is an engineering-capacity audit of retained partial evidence, not a
complete source inventory or a legal interpretation verdict.

| Boundary | Exact observation | Present limit | Result |
|---|---:|---:|---|
| Fourth wire response | 25,681 canonical bytes | 200,000 output bytes | Fits before source resolution |
| Fourth resolved response | 475,806 canonical bytes, from repeated full-unit quotations | 200,000 output bytes | Journal rejected it |
| First four merged pieces | 78 claims, 45 uncertainties, 53 unit accounts | 80 claims, 30 uncertainties | Unchanged `merge_pieces` fails `E_SCHEMA` on uncertainties |
| Full-source cross-check built from only these four pieces | 787,776 bytes on the actual readable wire path | 200,000 input bytes | Cannot dispatch |
| Atomic-reader claims from only these four pieces | 552,440 canonical bytes | 200,000 input bytes for later search requests | Would overrun if all are attached to an adversarial search request |

The cross-check figure includes the exact qualified source context, current
`compact_request(v2)`, source-reference table and readable-table encoding. Its
unqualified original request is already 747,591 bytes. It is not an estimate
based on a shorter excerpt. `SourceCheckedSearch.retrieve` later attaches all
independent source claims to a search request; the 552,440-byte claim list is a
code-derived lower-bound risk for that reached path, not an observed dispatch.
The fifth piece and independent reader can only add material to the full-target
account; their actual contents and any coalescing remain unknown. `apply_cross`
also appends reported cross-piece issues/questions to the same 30-entry
uncertainty field, with no reserved headroom. These later failures were not
spent calls or legal-candidate failures.

One lossless representation hypothesis was tested offline. Replacing each of
105 exact quotation occurrences in the partial aggregate with a source-unit
index and codepoint interval round-trips byte-for-byte to the original quoted
inventory. It reduces that inventory from 662,608 to 89,671 bytes. Even this
hypothetical compact form yields a **214,839-byte** qualified readable
cross-check request, above the same 200,000-byte cap, before the remaining two
units, second reader or any instructions explaining the new representation.
It is therefore **not an admitted repair**. It says nothing about whether a
model would use the references faithfully or whether a legal warrant is sound.

The reviewed solution must cover the whole route together. A shared-source
quotation ledger could retain source identity, Unicode offsets and exact text
once, with checked reconstruction for every claim and citation; simply raising
the journal cap would move the failure to the aggregate and cross-check stages.
A distinct aggregate inventory representation must preserve all per-piece
claims, authority dependencies, unit accounts and uncertainties without
pretending the single-response 80/30 limits fit the target. Full-source
cross-checks need bounded batches plus explicit all-unit/all-claim accounting
and a way to inspect dependencies across batches. Search, scoped review and
answer consumption must admit their actual dynamic inputs before dispatch and
reject any reduction that loses a rival, contrary source or unknown. Only after
an exact full-target capacity/fidelity qualification should a separately
reviewed, equal-arm live comparison be considered under the original grant.
These are architecture requirements, not proof that a particular redesign will
fit or interpret the law correctly.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Do not dispatch another full-target comparison on this route | Exact retained partial data fail output, aggregate and cross-request caps | Three independent pre-answer capacity vetoes; later consumers unqualified | Whether a source-preserving shared representation and bounded cross-batch checks can fit | Review one end-to-end architecture proposal and demonstrate capacity/fidelity offline before any live revision | That Sol, the six tools or the legal research direction failed |
| Reject quote-coordinate substitution as an immediate fix | Exact reconstruction succeeds but current transport is still 214,839 bytes | Input cap still fails before the target is complete | How much a coherent downstream representation can save without hiding substance | Keep it as a design component only | Legal support, model comprehension or production readiness |
| Keep the original legal work open | No complete source inventory or matched answer exists | Missing answer and source-to-warrant assessment | P10 fulfillment standard, evidential sufficiency, P14 attachment and Gatecoin transfer | Continue conditional source analysis while engineering is redesigned | Closure of any of the 46 obligations |

| Inference status | Evidence |
|---|---|
| Hard veto | 475,806/200,000 response bytes; 45/30 uncertainties; 787,776/200,000 cross-check wire bytes. |
| Statistically supported ranking | None. No method, model or tool ranking was run. |
| Descriptive-only differences | A coordinate-reference hypothesis reduced repeated quote bytes but remained 14,839 bytes over the input cap on partial data. |
| Default-readiness | No cap, source split, summary scheme, model or tool default is promoted. |
| Next evidence | An exact full-target, two-reader and downstream capacity proof with source/claim/uncertainty conservation, plus a matched source-grounded answer review if that passes. |

Skeptical post-run review: the attractive local fix is to shorten or pool the
fourth quotation. It would not cure the already-reproduced 45-entry merge
failure or the cross-check input cap. Raising the 30-entry aggregate cap alone
would not cure the repeated source text. Reducing source selection to an older
12-unit excerpt would change the comparator; dropping uncertainties would
change the legal target. A compact coordinate record is reversible as data,
but a model's understanding of it is untested. The strongest alternative
explanation for any later apparent success would be lost qualifications hidden
by the reduction, so the proposed design requires exact reconstruction and
substantive review. The current result invalidates this harness configuration,
not the underlying legal questions or any tool's legal contribution.

Actual command: `.venv/bin/python scripts/legal_mission_inventory_capacity_audit.py`.
Runtime was under two seconds on the local CPU; GPU devices were not used.
Input and method SHA-256 hashes are in the diagnostic JSON. The retained timing
manifest records commit `cde11a610cbd1e90eafecfa0cbda6efd51f9bef2`,
Python 3.11.15, source versions, absence of model seed control and the original
deadline. This offline audit has no data randomness. The audit script neither
imports a provider nor reserves the allowance. The frozen timing runner and
unrelated protected allowance were checked separately after execution.

Grant usage remains **13/400** with 387 calls left before **12 October 2026 at
04:28:01 UTC**. Seven cumulative detours remain. Four questions, 46 original
obligations, 35 readings and zero of six answer-level tool evaluations remain
open. This is `no_advance` for the legal answer. The prior plan's stop on
further automatic configuration is honored: an eighth live method requires a
separately reviewed program revision after an end-to-end offline qualification.
