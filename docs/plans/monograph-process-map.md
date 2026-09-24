# Process and technology charts after the executive summary

Executed: seven guide pages, fourteen flowcharts, a 252-page monograph and
76-page companion. The guide is also exported as `process-guide.pdf` by the
document build. The [review](../monograph/review/process-map/review.md) records
the exact scope, preservation checks and pending human acceptance.

The user requested a few pages that expand every box of the circular-to-Java
overview and identify the technologies, including tree search, mathematical
verification and Stipula. Implement a seven-page illustrated guide immediately
after the executive summary and before the contents. The baseline is the
244-page monograph and 76-page companion protected under
`.localresources/monograph-process-map/baseline/`.

The audience includes management and readers new to the implementation. After
the guide they should be able to locate source extraction, interpretation,
search, precise rule construction, verification, Java delivery and bank use;
explain the principal return paths; and distinguish implemented mechanisms from
the Stipula research route and institutional work. Introduce a technology by
its job before naming it. Use the discount/voucher case to give the diagrams a
continuous subject. Preserve the full chapter explanations and mathematics.

## Skeptical audit before execution

The material risk is a visually persuasive but false architecture. The current
Java emitter uses RuleIR and a shared Java evaluator; it does not compile
Stipula. Stipula-to-Java/JML/KeY is a published research route with a retained
reproducibility problem, not an integrated or locally replayed KeY proof.
Breadth-first and UCT search select work on proposed interpretations. They do
not exhaust English meanings or assign legal truth probabilities. Z3 compares
supported encodings within declared domains; unknown, unsupported and empty
domains must remain distinct. Selected Lean proofs belong to the mathematical
audit, not an automatically executed whole-compiler proof. Java/Python
conformance is not independent legal validation.

The plan passes with those boundaries made explicit in the charts. No new
scientific results, literature claims, model calls or runtime experiments are
needed. Existing retained sources and code determine the labels. Whole-program
proof, production approval and post-round-four implementation must not be
implied. The source/PDF checkpoint protects concurrent work. A successful build
is a geometry/reference diagnostic, not human readability acceptance.

## Page design

1. One overview, with eight numbered steps and return arrows. Each number links
   to its expansion. Bank approval/use has a visibly distinct boundary.
2. Steps 1–2: original circular, PDF/web text extraction, two extraction paths,
   visual warnings, authority editions, referenced sources, dates and scope.
3. Steps 3–4: isolated language-model readings, source inventories, breadth-first
   or UCT tree search, typed challenges, official examples and executed
   distinguishing cases. Retain unresolved and resource-limited outcomes.
4. Step 5: explain RuleIR, type/dependency checks and component composition;
   locate Catala's design influence and the separate Stipula/Java/JML/KeY route.
5. Step 6: Java policy generation, compilation, reference replay and mutations.
6. Step 6 continued: give Z3 symbolic comparison and the separate selected
   Lean/SymPy mathematical audit their own explanatory page. Keep source
   judgment outside their proof claim.
7. Steps 7–8: the Java program and its accompanying evidence; independent legal
   and bank approval, supervised integration, versioned facts and continuing
   source review. Include a compact comparison-study branch so reader savings
   and empirical interpretation quality are located too.

The seven-page estimate is a layout hypothesis. If the charts become crowded,
allow another page rather than shrinking the text. Solid/dashed borders and
explicit labels must carry meaning without relying on colour. Arrows name
conditions where the process branches; detail diagrams explain their return
paths. Do not reproduce schemas, file paths, phase identifiers or test counts.

## Inspected support and verification

- Source extraction: `sources/extract.py` and `interpretation/assurance/sources.py`;
  authority and dependency handling: the accepted round-four method boundaries.
- Interpretation/search: `interpretation/search/engine.py`, `search/formal.py`,
  assurance questions, composition and example records, and Chapters 5–6.
- Java: `java/emit.py`, the shared Java runtime and Chapter 7.
- Solver: `analysis/compare.py`; supported fragment and proof-certificate limits.
- Stipula: Chapter 4's source-scoped account and retained translator diagnostics.
- Lean/SymPy: `review/revision/math-obligations/manifest.json` and
  `MonographLogic.lean`; these checked selected propositions, not the compiler.

Build both documents, inspect every added page and its front-matter boundaries,
check internal/companion links and preservation against this immediate baseline.
Existing citation contexts and mathematical displays must remain unchanged.
Update delivery pointers, page counts and the recovery memo. Record author
review of comprehension, mathematical scope, source fidelity and rendering;
human-reader acceptance stays pending. No implementation files are edited.
