# Current-route integration gaps and root causes

11 October 2026, Hong Kong time. This is a read-only trace of the admitted
`product-contribution` route, using the current dirty worktree, the frozen
55-unit P10/evidence pilot and its retained offline diagnostics. It does not
rerun a paid call, repair production code, accept an old failed response, or
change the four original questions, 46 obligations or 35 readings. The
[audit plan](../current-route-audit-plan.md) passed its skeptical review before
the trace. Its comparator is the present `CompleteInvestigation` plus
`dossier_answer` path, not the older 492-pair illustration.

## Actual path and terminal state

`scripts/legal_mission_sol_inventory_window.py:136-149,278-343` builds the
same core method for baseline and six-tool candidate, except for the optional
backend. It calls `CompleteInvestigation.run` and requires its dossier to be
complete before `dossier_answer.propose`. The baseline runs first; the candidate
cannot establish a matched answer pair when that prerequisite fails.

The inner provider path is `Assurance`'s `JournalProvider`, then
`CompactProvider`, source-reference/readable preparation, `CachedEvidenceProvider`,
`ContextProvider`, and the granted provider (`engine.py:104-109`,
`integrated.py:64-70,119-126`, `transport.py:36-75`,
`source_references.py:152-215`, `workflow.py:142-216`). The journal sees a
logical request before compaction and an expanded response after span resolution
(`journal.py:25-49`). This order matters more than the small provider wire size.

The sealed fourth piece response selected 25 full-unit quotations. Its raw
source-reference output was 25,681 bytes, but exact resolution produced
475,806 bytes against the 200,000-byte journal output limit. The baseline
stopped at slot 13, before search produced candidates, and the candidate arm
never ran. See [terminal result](sol-inventory-window.md) and
[capacity audit](inventory-capacity-audit.md). The grant still records 13/400
calls, all baseline/core; seven enabling detours remain counted. These are
hard engineering vetoes, not evidence that a legal reading or tool failed.

## Gap and root-cause register

| Boundary | Status and precise gap | Root cause / code path | Consequence |
|---|---|---|---|
| Raw versus expanded response | **Reproduced.** 25,681 raw bytes became 475,806 expanded bytes; 200,000 is the current output cap. | `source_references.complete` resolves span IDs to full `Quote` text, then `JournalProvider.complete` applies the same output limit to that returned object (`source_references.py:194-216`; `journal.py:40-49`). The provider's small wire response is not a bound on expanded evidence. | An authentic, fully returned fourth piece is rejected. Raising one cap alone would expose later failures. |
| Logical versus encoded request | **Code-structural and measured.** The existing readable codec can reduce coverage and span tables, but the journal checks the original request before it reaches the codec. | `journal.py:29-31` precedes `transport.py:42-62`; `readable_tables.py:9-16,77-132` tables only coverage/reference records and preserves literal source, question and schema. `ContextProvider` separately checks the final qualified wire size (`source_context.py:151-180`). | Core fidelity inputs above 200,000 bytes fail even when an encoded version fits. A new codec needs distinct bounded logical, encoded, raw and expanded identities at every wrapper. |
| Piece inventory aggregation | **Reproduced.** Four retained pieces already have 78 claims and 45 uncertainties over 53 units; a single `Inventory` allows 80 claims, 40 authorities and 30 uncertainties. | `merge_pieces` combines all rows and calls `validate_inventory` on the result (`decomposition.py:47-62`); `apply_cross` then appends cross-review text to the same uncertainty list (`decomposition.py:90-94`). The single-response schema (`semantics.py:48-52`) is being used as an aggregate schema. | The current method cannot finish even if transport accepts the fourth response. Both readers need separate aggregate records, complete unit/claim accounting, and separate cross issues. |
| Cross-piece source review | **Measured partial failure and structural gap.** The current whole-inventory cross-check wire was 787,776 bytes with only four pieces; the full fifth piece was not received. | `cross_request` attaches the whole packet and whole merged inventory (`decomposition.py:64-73`). No staged claim-view and interaction contract exists in this executing route. The offline compact prototype's full-pressure request still exceeded the wire cap; its 20-claim views used instructions that falsely presumed a whole inventory. | Byte reduction cannot substitute for a source-aware review contract. Each view must name what it did and did not see, retain contrary and remote qualifications, and be followed by interaction/omission review. |
| Search and source reductions | **Code-structural; full-target size unmeasured.** Refinement can receive uncited source units plus all merged claims and findings. | `SourceCheckedSearch.retrieve` appends the entire `source_claims` and `source_findings` lists to `Search.retrieve`, whose result already contains uncited units (`engine.py:77-94`; `search/engine.py:267-274,332-347`). `generation_request` carries those diagnostics with the whole packet and parent (`search/models.py:143-165`). | The next model call can exceed the cap or rely on an unqualified reduction. The first pressure fixture was 578,122 bytes without the actual parent/tool payload; that is not an actual full-target dispatch measurement. |
| Core fidelity | **Measured conditional veto.** The hybrid fixture has 67 non-CONTEXT claims and twelve readings: 402 model-review pairs plus 402 explicit unformalized diagnostic rows. At 32 pairs, conservative admission reserves 2,760,033 bytes against 2 MiB; at 64 it reserves 1,560,033 but still fails the original-input journal check. | Core filters claims/candidates for each `required_pairs` batch (`semantics.py:264-301`), yet aggregate reservation counts one possible 200,000-byte response per pending batch (`engine.py:194-310`). `bundle` failures become retained `NOT_ESTABLISHED` rows, not discarded candidates (`engine.py:240-256`). | Neither larger batch nor incremental admission has qualified actual model outputs. The hybrid is not a completed same-run dossier; do not infer production feasibility or legal entailment. |
| Scoped fidelity | **Arithmetic veto at current settings.** The same hybrid has 936 pairs including CONTEXT claims. Twelve-pair batches require at least 156 two-perspective calls, beyond 82. | `CompleteInvestigation` defaults here to batch 12 and 82 actions (`scripts/legal_mission_sol_inventory_window.py:143-149`); `scoped_investigation.capacity` computes `2*ceil(pairs/batch)` (`scoped_investigation.py:72-86`). Its per-batch request retains the whole source but narrows assigned claims/candidates (`scoped_investigation.py:127-151`). | Batch 32/48/64 fits measured inputs and minimum calls only. Actual augmented requests, outputs, reasoning, retries and the 4,096-pair ceiling remain unqualified. Core and scoped tests answer different questions and cannot silently be collapsed. |
| Cross-stage admission and call envelope | **Code-structural and measured mismatch.** Downstream capacity is learned after earlier calls have been spent. The baseline has only 23 of its 36 core slots left, whereas the first staged design's ten piece reads plus 28 claim reviews need 38 calls before interactions, search or core fidelity. | `CompleteInvestigation.run` calls `core.run` before scoped admission (`complete_investigation.py:174-195`) and calls no final-answer admission; the pilot invokes the answer only after the dossier (`scripts/legal_mission_sol_inventory_window.py:301-328`). `stage_for` charges unmapped tasks to core (`scripts/legal_mission_live_pilot.py:178-184`); separate abstraction, criticism, question assignment, repair, authority-context passes and final review can also consume calls (`engine.py:435-558,584-710`; `complete_investigation.py:197-236`). | A method change must cost and admit all remaining stages at each transition, including both arms and the original deadline. Reclassifying tasks or relying on unused candidate slots would hide, not solve, the shortfall. |
| Final answer consumer | **Unqualified on a genuine full-target dossier.** It retains occurrence identities and dependency closure, but meaningful review output and synthesis capacity have not been measured on the actual generated dossier. | `dossier_answer.partition` fits assigned records under 200,000 bytes and at most 64 groups (`dossier_answer.py:264-355`). `capacity_budget` reserves 4,000 bytes per review and 8,000 for interaction as hypotheses (`dossier_answer.py:394-451`). The interaction/synthesis stages consume fallible reductions; raw evidence is archived but not wholly supplied to synthesis (`dossier_answer.py:456-510,572-600`). | A small synthetic receipt can pass packing while losing legal reasoning. `STRUCTURALLY_VALID_PROPOSAL` expressly sets legal quality and tool consideration to false (`dossier_answer.py:587-600`). |
| Tool execution and legal warrant | **Locally integrated, answer effect unmeasured.** Six selected adapters run candidate, criticism and retrieval checks and their feedback can enter provider requests. | `ToolSession` binds backend/check inputs and augments source-bearing requests (`optional_tools.py:86-178`); `ProductToolBackend` runs BM25, Boolean/Logical English and graph adapters (`scripts/legal_integration_tools.py:20-190`). These tools evaluate supplied search text, expression or argument graph. The retained false-warrant control passed graph/XML checks until an externally supplied undercut changed the graph ([product contribution](product-contribution.md)). | Tool execution does not establish source-to-standard entailment. No complete matched baseline/candidate answer exists, so zero selected tools have an established answer-level effect; success, harm and no effect are all open. |
| Tool attribution in the answer | **Code-structural risk, not yet a demonstrated wrong answer.** A receipt account is not a per-tool causal account. | Candidate tools can be combined into one `candidates` check and graph engines into one `criticism` check (`legal_integration_tools.py:75-95,134-190`). `ToolAccount` and `validate_answer` require keys, hashes and a disposition, not a source-supported explanation of each adapter's effect (`investigation_answer.py:64-77,258-294`). `synthesis_request` adds only a key/hash tool index, while details may appear in review records (`dossier_answer.py:456-510`). | The product must inspect raw nested receipts, downstream consideration, unsupported cases and before/after answers per applicable tool. Structural validation alone cannot mark any tool fully evaluated. |
| Retrieval applicability in final accounting | **Code-structural risk.** The final applicability predicate for retrieval checks validates the packet but does not compare the query/target candidate to the question for which a tool row says `USED`. | `ToolSession.augment` binds retrieval to exact queries (`optional_tools.py:150-178`), but `prepare_request` labels a retrieval `MATCHES_SUPPLIED_BINDINGS` if its packet matches and it has no candidate binding (`investigation_answer.py:200-213`). `validate_answer` bars `USED` only when that broad applicability label fails (`investigation_answer.py:287-294`). | A same-packet retrieval for a different question can be structurally accounted as used for this answer. The next design needs question/target binding validation and an evidence-based use review. This has not been observed in an actual final answer. |
| Substantive interpretation | **Unmeasured product risk with known legal dependencies.** No current complete answer shows preservation of the P10 conduct/outcome distinction, P14 request/object/standard attachment, the reconciliation-versus-rights distinction, or Gatecoin's event-specific evidence and target-transfer limits. | Exact quotation, Boolean execution and graph agreement check location and computation, not the legal warrant. The retained source analyses identify missing authority/facts: [P10](p10-standard.md), [P14](p14-attachment.md), [Gatecoin](gatecoin-transfer.md). | Conditional analysis can continue without client facts, but no tool or capacity repair may be called closure of the original legal questions. A current-authority search and later treatment remain needed for the Gatecoin transfer claim. |

## Root-cause synthesis and decision

The common engineering root is a mismatch between a lossless, growing evidence
object and several independently bounded single-call interfaces. The current
code moves exact evidence through those interfaces, but it has no separate
aggregate inventory type, staged source-review semantics, or whole-route
resource admission. Compression improves a local byte count without changing
the number of claims, source dependencies, model-review pairs or necessary
reasoning. The separate scientific root is that the installed tools operate on
provided text, formalizations and argument premises; they cannot validate the
legal premise that was supplied to them. The evaluation root is that baseline
generation has not completed, so downstream tool effects and legal-answer
quality have never been observed in a matched run.

The [consolidated repair specification](staged-capacity.md) covers the main
journal/codec, aggregate, staged review, search, both fidelity stages, tool
augmentation and answer-capacity boundaries. A successor method review should
make three currently implicit acceptance conditions explicit: (1) budget all
other model constructors and possible authority-context passes, not just the
named fidelity/review stages; (2) bind retrieval use to the actual question and
target, and preserve per-adapter nested status through answer review; (3) test
whether any reduction and tool result changes a source-supported inference,
including no-benefit and false-warrant controls. These refine the same repair;
they are not permission for a cap-only eighth configuration or a new detour.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Reject current full-route dispatch | Exact terminal failure plus structural aggregate/cross and budget blockers | Output 475,806/200,000, uncertainties 45/30, partial cross input 787,776/200,000 | Full fifth piece and actual later-stage responses | Review one coherent method revision against the complete remaining equal-arm envelope before any production change or live call | Failure of the legal research or installed tools |
| Retain the consolidated design as a candidate | It names the interacting boundaries without dropping source units or pair IDs | No exact full-route offline implementation or actual response qualification yet | Whether a staged review can preserve legal interactions within resources | Add the three explicit acceptance conditions above and qualify locally before seeking a separately reviewed live method | Production readiness or legal correctness |
| Keep all substantive tasks and tool evaluations open | No complete baseline/candidate answer pair or verified per-tool answer effect | Missing warrant and final-answer evidence | Which tool, if any, helps on each original question | Resume source-supported P10/evidence analysis and only then a bounded matched evaluation when the route is admissible | Any original obligation closed, any of six tools fully evaluated, or a stochastic ranking |

Post-run red team: the strongest alternative explanation of a future engineering
PASS is a concise but unfaithful legal reduction. An exact record count or a
correct solver result cannot rule it out. A source-reviewed full-target answer
with contrary readings, inspected warrants and a matched tool/no-tool comparison
would address that alternative. This audit
made no production edit, provider request, tool-worker call or stochastic
comparison; byte figures come from retained diagnostics and code inspection.
