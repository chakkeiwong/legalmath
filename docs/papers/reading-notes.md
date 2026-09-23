# Technical reading and adoption notes

These notes distinguish inspected technical material from discovery-only leads.
Section references refer to the exact editions in `manifest.json`. They are a
review record, not a claim that published proofs or benchmarks were reproduced.

## Statutes, exceptions and review

- **Sergot et al. (1986)**: inspected the Horn-clause representation, AND/OR
  explanations, treatment of time and negative information, and implementation
  discussion. Borrow decomposition and inspectable inference. The reported system
  formalizes selected nationality provisions; it is not a general legal reasoner.
- **Merigoux et al. (2021), Catala**: §§2.7, 3, 4 (including compilation argument),
  5, 6 and the extended technical material. Default terms distinguish no applicable
  value from conflicting exceptions. More than one active exception conflicts even
  if values agree. The F* result concerns a core translation; the production
  compiler is separately implemented. The repository formalization notes contain an
  admitted supporting lemma. No proof replay was performed. The exploratory lawyer
  study does not establish bank-reviewer accuracy. Borrow literate source alignment,
  explicit exceptions, and a restricted executable core.
- **Huttner and Merigoux (2022)**: §§2–5, especially §4.2's account of legal/programmer
  pair work and §5's implementation. Borrow the review process and the diagnosis of
  translation loss. Their broader legal and cost claims concern their jurisdictions
  and examples; no Hong Kong legal conclusion or ROI is inferred.
- **Monat et al. (2024)**: §§2–4 semantics and analysis, §5 housing-benefit application,
  §6 library comparison. Rounding mode changes legal outcomes. F* mechanizes the
  date semantics and selected properties; the complete static-analysis implementation
  is not thereby fully verified. Borrow explicit calendar operations, ambiguity
  cases and program slicing; day-level work does not solve intraday bank ordering.
- **Goutagny et al. (2025), CUTECat**: §§2–4 concolic semantics, exception-order
  reduction and human-readable inputs; §5 ablations, 20 seeded defects and larger
  housing example. Borrow branch-directed tests and mutation patterns. Tests cover
  encoded paths, not omitted law. Full example generated 186,390 cases in 6h37m;
  small-example speed is not a scalability promise. Official artifact README and
  license files were inspected; the 1.48 GB execution image was not downloaded/run.

## Duties, discretion and contract behaviour

- **Athan et al. (2014)**: §§2–4, including the worked alternative interpretations,
  Context/Alternatives structures, source associations and selected adjudication.
  Borrow provenance for competing interpretations. LegalRuleML is representation,
  not a turnkey runtime; compare against the separate 2021 OASIS standard.
- **Arias et al. (2024), s(LAW)**: §§2–5, translation patterns, strong/default negation,
  six school-admission cases and positive/negative justification traces. Possible
  models can depend on assumptions. A hypothetical model is not established client
  evidence. Borrow explicit unknowns and counterfactual explanations. The linked
  benchmark host was unavailable; its implementation was not executed or fully audited.
- **Crafa, Laneve and Sartor (2021), Stipula**: §§3–6 syntax, transition rules,
  legal bisimulation and centralized/distributed implementation discussion. Agreement,
  party permissions, assets and scheduled events model interaction. Events have
  precedence at equal time in this semantics; this is not automatically the bank's
  legally correct deadline convention. The 2021 preprint has three authors; the
  later journal edition adds Adele Veschetti and is a distinct version.
- **Crafa (2022)**: legal-calculus examples and discussion of external intervention,
  enforceability and code-driven normativity. Borrow the need to retain external
  adjudication and amendment. Do not equate what a system permits with all lawful
  actions or what it prevents with all possible real-world behaviour.
- **Hähnle et al. (2025)**: §§2–4, Appendix A's disjoint-cycle procedure and Appendix
  B's generated examples. Translation uses Java/JML and KeY; event conditions are
  symbolic booleans, and loop inputs stay constant across iterations in the automated
  encoding. Four examples support feasibility, not arbitrary event/calendar fidelity.
  Inspected official `Translator.java`, example paths and README. No KeY replay.
- **Delzanno et al. (2026)**: §2 fragments and reachability definitions, §3 Minsky-machine
  reductions, §4 well-structured transition-system argument, and relevant appendices
  for reduction/monotonicity structure. General and several restricted fragments have
  undecidable reachability. The decidable DI fragment has disjoint function/event
  source states AND immediate events. Do not conflate this with the different
  disjoint-cycle condition of the Java/JML paper. Use explicit bounds and incomplete
  analyses where appropriate; no complete all-contract verifier is promised.
- **Khoja et al. (2025), ContractCheck**: §§3–5 ontology/constraints and separate
  claim/contract executability checks, §§6–8 case study, seeded errors and threats.
  Borrow structured clause blocks and source-linked inconsistent constraints.
  A satisfying execution is not universal compliance; an unsat core is not necessarily
  minimal unless explicitly minimized. Input translation in the study was manual.
- **van Binsbergen et al. (2026), eFLINT**: §§3–5 language and evolving semantics,
  §§6–7 implementations, realistic scenarios and bounded model checking. Important
  distinction: an impermissible action can still have effects and create a violation.
  Open types model unknown facts. The paper explicitly notes missing fine-grained
  explanations and no formal semantics/type system for v4; the clingo implementation
  has different formal grounding. Borrow concepts; do not assume one version's
  guarantees apply to all. Read current official reference-interpreter README.
- **Ghose and Koliadis (2007)**: §§2–4 effect accumulation, compliance constraints
  and process-repair patterns. Borrow the separation of activities, effects, actors
  and temporal ordering. This framework paper does not establish extraction accuracy.
- **Colombo Tosatto et al. (2015)**: §2 definitions of achievement, maintenance and
  punctual obligations; §§3–4 NP/coNP completeness arguments and assumptions.
  Partial compliance means some trace; full compliance means every trace. Borrow this
  distinction and the motivation for bounded questions. Do not generalize the exact
  complexity class beyond the paper's process/obligation language.

## Language models, facts and evaluation

- **Holzenberger et al. (2020), SARA**: §§2–3 corpus construction and Prolog oracle,
  §§4–5 models/evaluation. Simplified nine-section US tax corpus, hand-crafted cases,
  not current tax advice or representative SFC data. Borrow paired text/rules/facts/
  answers; avoid presenting an oracle constructed from a model as independent evidence
  of that model's legal correctness.
- **Holzenberger and Van Durme (2023)**: §§3–5 span-aligned event/fact extraction and
  downstream reasoning, §7 limitations, Appendices B/E dates and error cases. Borrow
  facts with source spans and downstream tests. Do not copy default year-zero or
  year-boundary imputations into bank facts without an explicit data contract.
- **Koreeda and Manning (2021), ContractNLI**: §§2–4 annotation/model/evaluation,
  §5.2 references, exceptions and discontinuous evidence; annotation appendix.
  Borrow linked evidence and a distinct not-mentioned outcome. 607 NDAs and fixed
  hypotheses evaluate document inference, not executable SFC rule fidelity.
- **Pan et al. (2023), Logic-LM**: §3 formulation, solver routing and syntax-error
  refinement, §4 experiments and relevant prompt appendix. Borrow tool separation
  and bounded repair. Successful parsing/execution cannot validate intended meaning.
  Official repository README inspected; experiments not reproduced.
- **Olausson et al. (2023), LINC**: §§2–5, experimental setup and error-analysis
  appendices. FOL/Prover9 plus majority voting. Borrow a formalization boundary and
  failure taxonomy, not a universal legal guarantee from a majority vote. Official
  repository README inspected; no solver experiment reproduced.
- **An et al. (2025; v2 2026), ARc**: §3 policy creation/vetting, Algorithm 1 and
  finding precedence, §4 Table 1 evaluation, §5 limitations, Appendix A.1 human
  vetting and experimental details. Soundness is 1-FP/N, not a proof theorem or
  precision. Table 1: 10 FP in 1,689 decisions, precision 94.4%, valid recall 14.9%.
  The 563 items were each run three times; these are not 1,689 independent policies.
  Borrow reviewed reusable policies, semantic disagreement witnesses, consistency
  checks before entailment, and deterministic verbalization. Source code not offered
  by the paper as an open implementation; service is a commercial comparator.
- **Jurayj et al. (2026) and extended preprint**: methodology and Tables 2–3,
  cost function, discussion/limitations, additional preprint material. Gold rules and
  five retrieved annotated cases change the task and human-effort budget; compare
  separately from zero-shot rule generation. The cost model is US-tax-specific.
  Table 3's $15.78 belongs to GPT-5 Few-Shot, not its paired-vote configuration;
  the narrative's association with self-checking should not be copied uncritically.
  Official extraction/Prolog-processing source inspected, not executed.
- **Wang et al. (2026), Know Your Limits**: §§3–5 methodology, annotation and error
  taxonomy plus example/prompt appendix. Useful failure cases, under-review evidence.
  The text describes 400 re-annotations and 610 augmented examples while Table 1's
  total labels sum to 500; denominators require clarification before quantitative
  reuse. The annotation choice about implicit legal/ordinary-language assumptions
  is itself contestable. No benchmark ranking or general error rate is imported.

## Additional software and standards

Inspected OMG DMN 1.5 §8.2.11 on hit policies and its FEEL treatment; OASIS
LegalRuleML 1.0 requirements on modalities, provenance and alternatives; official
Catala, Apache KIE/Drools, OpenFisca, Z3, Blawx, Stipula workbench/KeY, eFLINT,
Logic-LM, LINC, Accord Cicero and OPA documentation. Documentation inspection is not
an installation, security review, license clearance, or bank integration test.

Local MathDevMCP, DynareMCP and ResearchAssistant capabilities were inspected in
the earlier feasibility review; precise file/commit identities are in
`.localresources/source-manifest.json`. The proposal does not copy their code.
MathDevMCP's inspected derivation controller explicitly is not MCTS. DynareMCP's
UCB-style historical investigation is a search scheduling pattern, not a legal
truth criterion. ResearchAssistant was used for discovery and local PDF extraction.
