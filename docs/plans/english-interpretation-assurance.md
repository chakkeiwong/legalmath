# Research note plan: correctness of the English interpretation

Date: 22 September 2026. Scope: a methodological answer and a concrete design
for source-to-specification assurance. This is not a new acceptance run or a
claim that a translator has been implemented.

## Question and evidence contract

The question is whether, and in what sense, we can establish that a formal rule
preserves the meaning of an SFC circular. The comparator is the present
23EC46 paragraph 10 example: manually supplied interpretation, source-first
cases authored by the same agent, and Python/Java agreement. Those checks do
not independently establish the interpretation.

The research output must distinguish (1) source authority and completeness,
(2) warranted interpretation, (3) formal preservation under explicit meanings
and assumptions, and (4) software execution and evidence classification.
Every borrowed method must have inspected technical sections in a retained
primary paper. A useful design must show a real interpretation disagreement,
how a distinguishing case is obtained, who resolves it, what is proved, and
what remains conditional.

Unsupported guarantees, circular validation, ignored source dependencies, or
misreported paper results veto adoption of a claim. An inaccessible paper is a
retrieval gap; existing inspected sources can still support the investigation.
Literature counts, solver agreement and model consensus are explanatory only.
No accuracy estimate, current legal opinion, production approval, or proof of
arbitrary English semantics will be inferred from this work.

## Assumptions and skeptical audit

| Choice | Provenance and reason | Failure mode / smallest check | Status |
| --- | --- | --- | --- |
| Reuse 23EC46 paragraph 10 | Retained official source and recent local example make the interpretation boundary concrete | Treating its example classifications or limited scope as legally approved; check source and unresolved dependencies | Illustrative baseline |
| Controlled language between source and RuleIR | Logical English and Catala's source-aligned review motivate a inspectable semantic bridge | The restatement can still omit or alter the original; retain source links, alternatives and independent source-based adjudication | Design hypothesis |
| Counterexamples between readings | Symbolic equivalence checking can isolate consequential disagreements | Agreement can be vacuous or alternatives incomplete; require satisfiable assumptions and record vocabulary/alternative coverage | Formal technique under explicit assumptions |
| Existing paper editions | Project-local manifest pins inspected editions | Stale summaries or claiming empirical “soundness” is a theorem; inspect methods, results, limitations and relevant appendices | Evidence source, not authority for local correctness |

Audit outcome before new methodological work: PASS with the above boundaries.
The wrong baseline would be another implementation test; the needed comparison
is against independently justified source meaning. No numerical experiment or
provider benchmark is planned. There is no stochastic ranking or GPU use.
Stop claiming a method is supported if its technical source cannot be inspected;
continue with the inspected subset and record that limitation.

## Work and outputs

Read the retained papers on policy vetting, controlled language, legal
interpretations, source-aligned programming and entailment annotation. Attempt
primary-source discovery for additional work directly about interpretation.
Use ResearchAssistant where practical and retain any new material paper locally.
Record exact inspected sections and distinguish literature results from our
proposed adaptation. Preserve the application, accepted evidence and proposal.

Planned output: `docs/research/english-interpretation-assurance.md`, including a
source-based example and a bounded implementation extension. Supplemental
retrieval/parsing records belong under
`.localresources/english-interpretation/`; new papers, if obtained and used,
follow the existing `docs/papers` naming and manifest convention.
