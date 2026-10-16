# Integration master: repaired live canary result

13 October 2026. The approved bounded recovery ran all eight new canary calls.
Two responses validated, but no question passed both its reading and review.
The recovery therefore dispatched no full acquisition, baseline, candidate or
matched assessment. The persistent master ledger has **175 charged calls**,
preserving the first 167 unchanged. The historical expired grant's 41 calls
remain separate. Each of the four acquisition nodes has used its second and
last registered attempt. No counter, deadline or prior result was reset.

The traceable diagnostic is
`artifacts/legal-mission-control/2026-10-13/master/live-repair/canary-diagnosis.json`.
All raw responses, request-bound selection tables and rejected results remain
under `live-repair/live/canaries/calls/`.

| Question | Reading | Reviewer | Dependent work |
| --- | --- | --- | --- |
| P10 | Validated source reading | Invalid overlapping selections; locator strings also outside canonical labels | Acquisition and all answer arms blocked |
| P14 | Invalid selection combining different source records into one quotation | Validated review | Acquisition and all answer arms blocked |
| Evidential sufficiency | Invalid overlapping selections | FN1 both cited and reported absent from its delivered index | Acquisition and all answer arms blocked |
| Gatecoin | Upstream HTTP 502 | Upstream HTTP 502 | Acquisition and all answer arms blocked |

## Root causes and what the evidence supports

The source-reference resolver correctly rejects a quoted span assembled from
overlapping regions or different source units. The wire schema nevertheless
permits arrays of any offered span IDs and leaves valid combinations to prose
instructions and post-validation. It exposes a complete-record span beside
overlapping subspans. P10 and evidence responses selected both. P14 treated
two documents' support as one span list, although the contract requires separate
quotation objects. These are actual invalid responses, accompanied by a
representation design that makes invalid choices easy to express. The earlier
summary that called all three failures overlapping spans was too coarse: P14
crossed source records.

The P10 reviewer also supplied `26EC22 P10` and `26EC22 footnote 1` in locator
fields whose intended values were `P10` and `FN1`. They were not accepted; the
earlier span rejection masked further validation. Its prose included numbered
references and directly copied quotations. No editing of that response can be
represented as an observed successful call.

The evidence reviewer correctly rejected the broad compliance shortcut in its
reasoning, but simultaneously listed the delivered FN1 as missing. The integrity
check rejected that contradiction. This is not proof that the substantive
reasoning was entirely wrong; it is an invalid complete response under the
declared contract. The two Gatecoin calls failed at the upstream service with
HTTP 502. They provide no answer-quality or native-tool evidence.

The local rehearsal supplied well-formed selections by construction. Its 1,822
scripted calls and 604 reviewer-capacity checks established mechanical behavior
within those inputs, not the model's ability to follow the wire protocol. The
local tests should remain, but passing them was insufficient qualification for
reliable live output. Service usage also includes substantial unmeasured CLI
framing: one retained response reports 14,092 input tokens against 2,372 local
visible-input tokens. Neither tokenizer nor framing equivalence is established;
this comparison is not itself evidence that a local limit was breached.

## Concrete reopening requirements

These are acceptance requirements for a reviewed reopening of the **same**
master, not a newly authorized repair or grant. The current two-attempt bound
prevents further live dispatch. The unused global call balance does not override
it, and no new authority is created by this document.

| Work | Success prerequisites | Concrete acceptance |
| --- | --- | --- |
| Reference representation | Retained failing requests and responses | Use request-bound complete quotation selections or schema-constrained contiguous spans; represent support from different records as separate references; foreign, overlapping and changed bindings still fail |
| Legal locator and source-gap representation | Verified per-request index | Offer exact canonical locators and genuine unavailable-provision choices; reject citing and declaring the same delivered provision absent; preserve typed uncertainty |
| Actual-failure qualification | Both representation fixes | Replay every retained malformed pattern offline, exercise multiple-source reasoning and meaningful findings, then pass fresh bounded canaries without rewriting outputs |
| Route availability and capacity | Same approved route, independent of source repair | Retain a successful bounded service response and measured framing/usage; distinguish 502/timeouts from legal or adapter failure |
| Complete source package | Independent source supplement | Add material Handbook provisions equally to baseline and candidates; update identities, locators, acquisition inventory and actual all-stage capacity before binding a revised campaign |
| Original integration evaluation | Successful relevant source/route qualification and explicit reviewed attempt/resource revision | Complete independent acquisition, baseline, six native-tool arms and source-backed matched assessments for each eligible question |

Do not weaken exact source identity, accept invalid results, shorten original
coverage or silently create a third acquisition attempt. A single-quotation
selector is a proposed simplification, not an implemented or qualified fix.
There may still be output-size, semantic-loss or supported-target failures
after this boundary is repaired; the complete original-route evidence remains
necessary.

## Acceptance decision

| Decision | Primary criterion | Veto evidence | Main uncertainty | Next action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Reject repaired live route qualification | Zero of four required canary pairs passed | Three invalid span results, one contradictory gap report, two 502s | Fresh response reliability and full-route behavior | Preserve diagnosis and settle independent source/release work | All language interpretation is wrong or impossible |
| Keep all six tool evaluations open | No complete valid matched pair ran | Missing acquisition and answer evidence | Contribution of each native tool | Reopen only with a reviewed concrete repair and finite resources | No benefit, harmful, or fully integrated |
| Preserve local engineering evidence | Focused checks and original-input rehearsal passed | Live protocol failure prevents production qualification | Whether simplified output references improve reliability | Require actual-failure controls and fresh canaries | Production readiness from test counts |

There is no statistically supported ranking of tools, models or response
designs. The counts describe this run; they are not an estimated general
failure rate. The strongest alternative explanation for the failure is a poor
wire representation rather than inability to reason over the legal passages.
A matched test that changes only the reference representation could test that
explanation. Successful qualified responses after that change would support it;
continued semantic failures despite valid references would point to additional
causes. Only the subsequent full original-input run could qualify the complete
integration.

The installed narrow rules file matches the reviewed repository file by SHA-256.
The installed CLI confirms that the exact command
`.venv-context/bin/python scripts/legal_integration_master.py live` is allowed.
Official rules documentation fetches returned HTTP 403; this report relies on
the observed installed-policy check, not an unsupported documentation claim.
No broad interpreter/edit permission or new protected-path write was needed.
The current blocker is evidence and exhausted node attempts, not missing host
permission for that exact command.
