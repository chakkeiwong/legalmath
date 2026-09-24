# Circular-to-Java process and technology guide

The requested guide is implemented on physical PDF pages **4–10**, immediately
after the executive summary and before the contents. The monograph is now
**252 pages**, the companion remains **76 pages**, and the same seven guide
pages are available separately in [process-guide.pdf](../../process-guide.pdf).
The approved interpretation evidence remains the round-four scope of the
preceding edition.

The guide contains fourteen flowcharts. Its overview has eight linked steps;
the following pages expand every step and locate the technology by its purpose.
The original chapter explanations remain in place. The guide is a visual
orientation to their argument, not a replacement for the assumptions and
derivations.

## Technology and evidence mapping

| Guide page | What the reader can locate | Inspected support and important distinction |
|---|---|---|
| 1 | The circular-to-Java process, return paths and bank adoption | Chapters 2, 5–8 and 10. A draft can retain unresolved interpretation; bank authority is a separate decision. |
| 2 | Original sources, pypdf/Poppler extraction, two web parsing paths, authority catalog and context | `sources/extract.py`, `interpretation/assurance/sources.py`, accepted authority work and Chapter 2. Extraction agreement does not read scanned qualifications or establish historical applicability. |
| 3 | Separate model readings, source inventory, breadth-first/UCT search, challenges and executed cases | `interpretation/search/engine.py`, `search/formal.py`, assurance methods and Chapters 5–6. Search can call draft compilation inside its loop; a work limit leaves uncertainty. |
| 4 | RuleIR validation and composition; Catala's design influence; Stipula/Java/JML/KeY research | `java/emit.py`, composition records and Chapter 4. The current emitter uses RuleIR. Stipula is not integrated, and the retained translator discrepancy and absent local KeY replay remain explicit. |
| 5 | Java policy generation, shared evaluator, javac, Python/Java comparison, boundary and mutation tests | `java/emit.py`, `search/formal.py` and Chapter 7. Agreement checks execution of a proposed rule; it does not establish the source interpretation. |
| 6 | Restricted Z3 comparison and selected Lean/SymPy mathematical checks | `analysis/compare.py`, Chapter 3, `MonographLogic.lean` and its retained manifest. Unsupported operations, unknown results and inconsistent domains remain separate from agreement. The Lean audit is not an automatic proof of the compiler. |
| 7 | Java delivery, host use, bank approval, monitoring and comparative evaluation | Chapters 8–10 and round-four method boundaries. Implemented local mechanisms do not supply institution validation, a method ranking or measured reviewer savings. |

Technology names are introduced by their function before appearing in the
relevant diagram. The discount/voucher example connects source coverage,
alternative readings, tests and unresolved judgment. Dashed boxes mark the
Stipula research route or institution work beyond the demonstrated local route;
captions explain the distinction without requiring colour recognition.

## Verification and repairs

The pre-edit [plan](../../../plans/monograph-process-map.md) rejected a false
Stipula-to-production architecture, unqualified formal verification and a
search score presented as legal correctness. Source inspection fixed the
technology mapping before drafting. No implementation code or model-call
allowance was changed, and no new model or scientific experiment was run.

All seven final guide pages received author/executor visual inspection, with
the executive-summary and contents boundaries checked as well. Layout repairs
kept the explanatory paragraphs and qualifications on the same pages as their
charts, shortened diagram labels and removed labels that overlapped box edges.
The body font was not reduced to force the material into seven pages.

The guide's eight overview links lead to its detailed steps. Its standalone
export rebuilds named links explicitly: local guide links remain local, and
chapter and companion references point to the full books. This avoids a PDF
slice silently dropping named destinations. The exporter is invoked by the
normal document build and can also run independently.

The current build and document checks pass. The protected checkpoint contains
247 files, verified unchanged. Every one of the 236 existing main-body and
bibliography pages has identical extracted text and identical raster output
at the recorded comparison scale. All 76 companion pages retain identical
extracted text. All 37 pre-existing display groups, 39 equation labels, 24
listings across the pair, 207 original source-unit labels and 216 citation
contexts survive. There are still 85 archived cited sources. No new formula
or source theorem is asserted by the guide; its summaries point to the
existing scoped explanations and inspected implementation.

The [preservation record](preservation.json), [navigation check](navigation.json),
[rendered review](rendered-review.json) and [delivery manifest](delivery-manifest.json)
identify the exact outputs and checks. The preceding
[round-four integration review](../round4/integration-review.md) belongs to the
protected 244/76-page pair; its physical page numbers describe that earlier
edition.

## Review conclusions

| Review | Result and limit |
|---|---|
| Reader comprehension | The process and technology choices can now be followed from the opening. This is author review; naturalness and comprehension still need target-reader feedback. |
| Mathematical integrity | Existing displays and derivations are preserved. The new charts distinguish testing, solver reasoning, selected proved propositions and the stronger unproved compiler goal. No new mathematical proof is claimed. |
| Source fidelity | Current RuleIR execution is distinct from the studied Stipula route; source, interpretation and execution remain separate evidence targets. Existing citation contexts are unchanged. |
| Rendering and navigation | All added pages are inspected, the short export matches them, and internal/remote destinations are checked. The full book remains necessary for the linked detailed argument. |
