# The inventory-window comparison stopped at output and aggregate capacity

10 October 2026. The reviewed timing attempt is terminal, `PAIR_UNAVAILABLE`.
Four fresh baseline/core calls (slots 10–13) returned from explicit
`gpt-6.1-sol`; no call timed out. The first three source pieces passed the
unchanged inventory validator. The fourth returned a source-span response, but
the product journal rejected its expanded value with `E_RESOURCE_LIMIT:
Assurance response byte cap`. The outer `E_REFERENCE` reports the missing
required inventory, not a legal-reference ruling. Piece five, full-source
cross-checks, the second reader, downstream stages, the six-tool candidate and
both final answers were not reached.

The fourth request contained one 18,000-character unit from the 2023 Tokenised
Securities Circular. The returned wire value selected that entire unit for
25 quotations. Source-reference resolution passed its integrity check and
expanded those selections to **475,806 canonical bytes**, exceeding the
unchanged **200,000-byte** output limit. The raw wire value was 25,681 canonical
bytes. The raw and resolved values, references, source packet and failure status
remain in the fourth call's transport and provider evidence. An offline run of
the unchanged `validate_inventory` on the resolved fourth response passed its
one-unit schema, quote and account checks. That diagnostic does not convert
the rejected journal action into a completed product inventory, establish
entailment or authorize replay.

There is a second, independent deterministic blocker. The first three accepted
pieces contain 24, 23 and 10 claims, and 13, 12 and 7 uncertainty entries.
Together with the retained fourth response, the first four pieces cover 53 of
55 units and contain **78 claims and 45 uncertainties**. The current merged
`Inventory` contract permits at most 80 claims and **30 uncertainties**.
Running the unchanged `merge_pieces` offline on these four exact responses
failed `E_SCHEMA` at the 45-entry uncertainty list. Even if only the fourth
response's quote expansion were shortened, this aggregate would still fail.
The fifth piece could exceed the two remaining claim slots, but its output was
never generated, so that is a risk rather than an observed failure.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Reject this matched comparison as unavailable | No complete baseline or candidate answer | Fourth journal response exceeds 200,000 bytes; four-piece merge exceeds 30 uncertainties | Whether a source-preserving bounded representation can fit the entire target and later consumers | Stop live retries; review quote representation, aggregate inventory and downstream capacity together before any new method | Sol's legal ability, six-tool benefit, or paragraph-10 fulfillment |
| Retain partial source work as diagnostic only | Three pieces validated; the fourth passes an offline one-piece semantic check | Required fifth piece, both full-source checks and second reader absent | Omitted or remote qualifications in the unprocessed material | Use the retained responses to inspect a proposed method, not to promote an answer | Complete coverage or legal correctness |

| Inference status | Evidence |
|---|---|
| Hard veto | Journal cap and deterministic aggregate schema failure prevent the required complete inventory. |
| Statistically supported ranking | None; no model or tool ranking was tested. |
| Descriptive-only differences | All four returned calls took under 300 seconds (207.808, 134.276, 97.555 and 196.733 seconds). |
| Default readiness | No timeout, output cap, inventory cap or model default is promoted. |
| Next evidence | A reviewed full-target capacity proof or bounded failure test covering reference expansion, merged counts, cross-checks and later answer/review requests, followed by equal-arm source-grounded legal review if feasible. |

Skeptical post-run review: the timing hypothesis did not cause the observed
failure, and these four sub-300-second returns do not show that a 900-second
window was needed or beneficial. The strongest alternative explanation for
the apparent progress is that span IDs conceal a much larger resolved output.
Raising only the response cap would hide the already-proven merge failure and
could displace it into downstream requests. The next plan must preserve every
source unit, qualifier, uncertainty and contrary reading; treat bounded
summarization as a hypothesis whose fidelity must be checked, not as permission
to drop evidence. This is an invalid comparison/harness-capacity result, not a
failed legal candidate and not rejection of the research direction.

Exact command: `.venv/bin/python scripts/legal_mission_sol_inventory_window.py execute`.
Evidence root: `artifacts/legal-mission-control/2026-10-10/live-pilot-400/sol-inventory-window/`;
the fourth transport value is in
`baseline/product/revisions/fe77546e483dd7ea2225605147e9a2555e6ae173327a5f78e0ca000cb21ebb9b/core/actions/action-0001/transport/call-003/source-references/`.
The provider's raw output is under shared `provider-evidence/0013-0cb7b8c188d7f210/`.
The immutable protocol, call statuses, effective settings and run manifest retain
the method, source hashes, actual command, environment and clock. Commit was
`cde11a610cbd1e90eafecfa0cbda6efd51f9bef2`; Python 3.11.15 in `.venv`
ran with GPU hidden. No model seed is configurable. The monotonic wall time was
638.311 seconds; the manifest's UTC start/end labels differ from that monotonic
duration, so elapsed time uses the monotonic measurement.

Usage is **13/400**, all baseline/core; 387 calls remain within the original
grant deadline of **12 October 2026 at 04:28:01 UTC**. Seven cumulative enabling
detours remain counted and this one-time timing method cannot restart. No
original obligation is closed; all four questions, 46 obligations, 35 readings
and six unevaluated selected tools remain visible. The next admitted work is
offline diagnosis and a skeptical full-target capacity design. No further
automatic live configuration follows this attempt.
