# Policy-to-ODRL review and implementation proposal in LaTeX

## Objective, scope and reader

The user asks whether the completed ODRL survey is already in the LaTeX document, requests a thorough review and concrete feature proposal there, and wants the PDF. Inspection found no ODRL coverage in the canonical LaTeX sources. `docs/proposal/proposal.tex` is a compatibility entry point into the ten-chapter unified monograph. Add the review to its language/literature chapter and the implementation proposal to its implementation chapter, with a focused PDF built from the same two new source files.

The reader is a technically informed banking/compliance researcher or engineer who knows the suitability problem but need not know RDF, ODRL or its evaluator semantics. The reader should be able to explain the source-to-policy choices, reproduce the FAQ 6 distinction, distinguish structural checks from source fidelity, identify existing code, and implement the proposed bounded extension without reconstructing premises from an appendix. Human readability feedback remains pending; the user has requested drafting through PDF delivery, so that feedback does not block this draft.

This is document work and a proposal for future implementation, not implementation of the legal-interpretation product or continuation of its mission/campaign. No live model calls, external messages, subagents, installations, application experiments or runtime changes are planned. Reuse the completed retained survey rather than duplicate literature searches. Preserve all unrelated changes and all substantive existing manuscript content.

## Evidence and assumptions

The recommendation must follow the inspected circular, technical papers, pinned code and actual repository capabilities. The shared interpretation is richer than its ODRL projection; no source-to-ODRL or Catala equivalence theorem is assumed. Independently specified scenarios are diagnostics for declared interpretations, not proof of natural-language legal truth. A successful build establishes document integrity and rendering only.

Protect the actual worktree baseline, including source and PDF hashes, before edits. The current main PDF has 402 pages and the proposal alias 397; they are already out of sync. Synchronize the final aliases only after a successful canonical build. Do not overwrite the frozen historical baselines or silently update historical research verdicts. Preserve exact old citation contexts and judgments; review added citations against retained sources with their actual reading limits.

## Dependency map

| ID | Result/evidence | Requires success | After completion | Failure recovery | Attempt bound |
|---|---|---|---|---|---|
| D1 | Protected baseline, source/format discovery and claim inventory | none | none | Locate canonical inputs and latest retained survey | One discovery pass plus focused follow-up |
| D2 | Narrative review and proposal outline, API/semantics choices verified against code | D1 | none | Narrow unsupported claims; name future work explicitly | One substantive draft and focused review |
| D3 | Two shared LaTeX units, bibliography, main-document integration and standalone wrapper | D2 | none | Fix only new material or necessary integration points | One draft plus two correction passes |
| D4 | Added citation/archive evidence and source-preservation checks | D3 | none | Preserve unavailable-paper status; do not invent reading | Two focused passes |
| D5 | Canonical and focused PDFs with resolved references | D3 | D4 | Repair demonstrated LaTeX/layout errors; continue independent claim checks | Initial build plus three bounded repair builds |
| D6 | Render review, final aliases, delivery and reset note | D4, D5 | none | Repair new clipped/illegible pages and recheck affected pages | Two focused passes |

D4 and D5 can proceed independently after drafting; source edits serialize with builds of those sources. One root agent writes all files. The finite outcome is a sourced, buildable review and implementable proposal, with both PDFs, not execution of the proposed feature. An unavailable historical original limits that paper's use and does not block the chapter. Only invalid authority or damaged common evidence is a global stop. At each checkpoint persist the result and refresh the ready set.

## Narrative design

Begin with the intermediary deciding whether streamlined procedures apply. The FAQ 6 counterexample makes naive permission/prohibition extraction insufficient. Teach the ODRL entities and profile contract before examining extraction research, then semantics and software. Compare Catala routes only after their distinct jobs are clear.

The proposal returns to that case: retained source graph, reviewed norm record, exact calculations, explicit supported ODRL projection, event/evidence adapters, and independent checks. Include a small worked JSON-LD fragment whose custom predicate and missing-fact behavior are explained, not presented as a completed translation. Follow it through consent, withdrawal and review. Finish with concrete modules, deliverables, dependency order, acceptance scenarios and bounded fallback when an evaluator cannot express a construct.

## Skeptical audit

PASS for document execution. The plan uses the canonical manuscript rather than the obsolete proposal chapters, protects the 402-page baseline rather than assuming the older alias is current, retains source and software limits, and does not treat generated ODRL, SHACL conformance, shared-output agreement or human labels as proof of legal fidelity. There are no benchmark comparisons or default changes to justify experimentally. Full-document checks may expose stale historical citation bindings; diagnose their baseline state before changing them and keep any repair within the added material. The user receives the PDF without waiting for a separate human-style approval.

## Execution record

- Discovery complete: proposal is a wrapper; no existing ODRL discussion in the canonical LaTeX. Relevant prospectus/translation implementation and prior software inspection reread. Current canonical/proposal PDF page counts differ as recorded above.
- Ready set: protect D1 baseline, then D2/D3. No global veto.

- D1 completed: 51-file protected baseline and exact citation delta retained. D2/D3 completed: two shared narrative units, twelve bibliography additions, canonical integration and a focused wrapper. First focused build: 24 pages.
- D4 baseline discovery: eleven pre-existing unbound occurrences in the unchanged bounded-context unit also lack archive/reading-registry entries. The retained 12 October source manifest and paper/code snapshots exist. Bounded recovery: inspect those exact eleven contexts against the retained material and add nine scoped source/reading records plus explicit author judgments. Preserve the old prose and all old judgments. This necessary publication-binding repair is a reviewed scope revision; no product runtime or new external call is involved. Skeptical audit PASS: source identity and reading, rather than automatic support labels, determine the additions.
- D5/D6 first render check found an asymmetric architecture diagram and sparse forced-break page. Correct the diagram geometry and wrapper pagination; AMR dataset wording corrected to distinguish ten additional negatives from the roughly hundred positive examples.
- Ready set: D4 citation integration and D5 bounded rebuild; D6 detailed render review follows both. No global veto.
- D4 integration completed: twelve ODRL sources and nine bounded-context sources are retained in the archive and reading register. Added 53 ODRL and eleven repaired pre-existing occurrence judgments; all 325 prior judgment rows are preserved exactly. The integration manifest records the inspected scope and limits. Canonical validation remains pending.
- Ready set: D5 focused/canonical rebuilds, then D6 render and preservation review. The focused build and canonical build use separate output files and can run concurrently. No global veto.
- D5 checkpoint: focused PDF has 23 pages; canonical build/check PASS, 422 pages, 158 citation documents, 389 bound occurrences and 207 retained source-unit labels. Canonical/proposal/companion aliases match. All prior chapter content and all 325 earlier occurrence judgments are preserved.
- D6 render pass inspected all 23 focused pages and all new canonical chapter pages. The focused contents and JSON listing are now intact; canonical render exposed a sparse final page caused by the new software comparison table. Reduce that table one further type step and recheck the chapter boundary. A quotation probe found the new AgentODRL evidence excerpt stopped at a line-break hyphen; complete the quotation from the already-retained source and refresh its two new reading bindings. No substantive judgment changed. These are bounded D5/D6 repairs; ready set is rebuild, inspect affected/new canonical pages, then final manifest/reset note.
- Final D5/D6 checkpoint: both bounded repairs are complete. The final focused PDF has 23 pages; the canonical proposal has 422 pages. The canonical checker returns PASS with no errors, 158 citation documents, 389 occurrences and 207 retained source-unit labels. All 21 new reading-record quotation probes pass. All 325 previous occurrence judgments and all pre-existing chapter content remain preserved; PDF aliases are byte-identical.
- Final visual review: inspected all six fresh focused contact sheets, all six fresh canonical contact sheets covering the new sections and their boundaries, and detailed renders of the software table, architecture, JSON listing and module table. The software table is legible, the contents fits on one page, the JSON listing stays intact, and the canonical chapter boundary no longer has the sparse closing page. No further source correction is required. This is an author layout review, not human readability acceptance or legal validation.

## Final dependency state

| Item | State | Retained result |
|---|---|---|
| D1 | Complete | 51-file protected baseline and source/citation delta |
| D2 | Complete | Source-grounded narrative and explicit proposed semantics |
| D3 | Complete | Two shared LaTeX units integrated into the canonical proposal and focused wrapper |
| D4 | Complete | Scoped citation records; preservation and retained-quotation checks pass |
| D5 | Complete | Successful focused and canonical builds; synchronized PDF aliases |
| D6 | Complete | Fresh rendered-page inspection, final delivery manifest and reset note |

Ready set: empty for this authorized document task. Deliver `docs/proposal/policy-to-odrl.pdf` and `docs/proposal/proposal.pdf`. Human readability feedback remains pending and may justify a later revision. Implementation of the proposed ODRL feature is future work; it was not executed by this plan.
