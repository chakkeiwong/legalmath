# Translating SFC circulars into reviewable, executable rules

This earlier feasibility note preserves the initial source and local-project
inspection. The current design is the [version 0.2 proposal](proposal/proposal.pdf)
and [implementation pack](implementation/START-HERE.md); use their fixed contracts
when implementing.

Research date: 21 September 2026. This is a proposed design based on selected
public circulars and inspected software; it is not an inventory of the bank's
obligations or an implemented compliance engine.

The useful product is a shared specification that compliance officers can read,
developers can execute, and verification tools can check. A language model can
draft that specification and locate relevant provisions. Each adopted rule
should retain its source, interpretation, dependencies, and examples, so that a
change in a circular produces an intelligible change in the bank's controls.

This belongs to the established fields of **Rules as Code**, computational law,
and formal methods. Much of the machinery already exists. The principal new
work is connecting Hong Kong regulatory sources to the bank's entities,
products, client information, and operational procedures.

The sources already expose three different translation problems. The joint
SFC–HKMA [SPI circular, 23EC35](https://apps.sfc.hk/edistributionWeb/gateway/EN/circular/doc?refNo=23EC35)
places detailed conditions in two annexes. The
[2023 tokenisation circular](https://apps.sfc.hk/edistributionWeb/gateway/EN/circular/doc?refNo=23EC53)
expressly links to a replacement,
[26EC22, revised 20 April 2026](https://apps.sfc.hk/edistributionWeb/gateway/EN/circular/doc?refNo=26EC22).
And [25EC48](https://apps.sfc.hk/edistributionWeb/gateway/EN/circular/doc?refNo=25EC48)
announces a thematic review; it should not be mechanically converted into a
new client eligibility condition. Retrieval, version management, and identifying
what kind of statement a paragraph makes all precede executable logic.

The supplied category covers product authorisation. For a private bank, the
initial source inventory should also consider intermediary supervision and
relevant HKMA material. Applicability depends on the regulated entity and the
activity: an obligation on a product provider is not automatically an obligation
on every distributor. The joint circulars inspected here demonstrate the need
to consider both authorities; they do not establish every rule applicable to
this particular bank.

## A concrete rule and the information it needs

Annex 1, paragraph 3.1 of 23EC35 sets out the financial condition using two
alternative thresholds. Let `P` be the qualifying portfolio value and `N` the
qualifying net assets after excluding the primary residence, both expressed in
HKD equivalents at the relevant date. For this condition alone, the proposed
formalisation is:

```text
financial_condition(P, N) = (P >= 40,000,000) OR (N >= 80,000,000)
```

This is a direct transcription of the two alternatives, with `>=` expressing
the inclusive thresholds. The inputs need their own definitions: paragraphs
3.2 and 3.4 govern ownership and aggregation; paragraph 3.3 defines the net
asset calculation. A field containing the bank's AUM is not automatically `P`.
The currency conversion method, valuation time, and evidence supporting the
ownership mapping must be explicit. The paragraph allows equivalent values in
other currencies; it does not by itself supply a bank's FX data policy.

The following examples assume the amounts have already been calculated under
the applicable definitions and the individual-client scope has been established.
They are expected results for this single predicate.

| Portfolio in HKD | Net assets excluding residence in HKD | Financial condition |
| --- | --- | --- |
| 40,000,000.00 | 0.00 | True: the first alternative is satisfied |
| 0.00 | 80,000,000.00 | True: the second alternative is satisfied |
| 39,999,999.99 | 79,999,999.99 | False: neither alternative is satisfied |
| Unknown | 80,000,000.00 | True: the known alternative suffices |
| Unknown | 70,000,000.00 | Unknown: the missing amount could change the answer |

The complete SPI assessment also involves professional-investor status,
knowledge or experience, and investment objectives. Applying the streamlined
approach adds product-category, exposure-monitoring, assessment, consent, and
review requirements. Annex 1 paragraphs 1, 4–8 and 12–14 explain those matters;
paragraph 2 supplies a separate corporate route. Passing the financial
condition therefore supplies one fact to the wider assessment. It does not
authorise a trade. See the official
[Annex 1](https://apps.sfc.hk/edistributionWeb/api/circular/openAppendix?lang=EN&refNo=23EC35&appendix=0).

The same circular illustrates why flattening everything into one flowchart can
mislead. Annex 1 paragraph 8.3 has two monitoring approaches. Annex 2, FAQ 6
explains treatment of designated accounts, transferred exposures, and operation
above the threshold with restrictions on added funds. A universal rule that
rejects every transaction whenever exposure exceeds the threshold would lose
those distinctions. The control needs an explicit monitoring mode and event
history. FAQ 7 also addresses leverage. See
[Annex 2](https://apps.sfc.hk/edistributionWeb/api/circular/openAppendix?lang=EN&refNo=23EC35&appendix=1).

The companion [JSON example](../examples/spi-financial-condition.json) represents
only paragraph 3.1, names the unresolved imported definitions, and has no trade
authorisation output. Its truth-table examples are design examples, not executed
tests of a translator.

## What the intermediate representation should contain

Use a small typed rule language, serialised as JSON or YAML. Its meaning must
be defined independently of the serialisation. A string containing English or
Python is not, by itself, a formal specification.

| Part of a rule | What must remain inspectable |
| --- | --- |
| Source | Authority, document identifier, retrieved version, paragraph/page, source bytes and digest, language, and linked annexes |
| Legal meaning | Definition, obligation, prohibition, permission, exception, guidance, or information; preserve the original modal wording and record the adopted interpretation |
| Applicability | Regulated entity, actor, activity, product, client class, jurisdiction, event and relevant dates |
| Conditions | Typed amounts, currencies, dates, sets, quantifiers, conjunctions and alternatives; explicit missing-fact behaviour |
| Consequences | Required action, responsible person, deadline, evidence of completion, or a derived eligibility fact |
| Exceptions | The rule modified, the condition for modification, and the source supporting its precedence |
| Dependencies | Definitions and other rules needed to evaluate this one, including unresolved references |
| Bank implementation | Data-field mappings, control owner, operational response, and any additional bank policy |
| Review and history | Interpretation decisions, reviewer, approval, change rationale and version validity |

Maintain separate publication, effective, and system-recorded dates. A circular
published today can change requirements at another date. Keeping both legal
validity time and the time the bank recorded a version permits two different
questions: which rule applied to a historical transaction, and which version the
system actually used then. Publication metadata alone cannot answer both.

Missing information should produce an unresolved result when it can change the
decision. Conflicting evidence needs a separately visible conflict. Being outside
one rule's scope is also different from satisfying that rule. An operational
policy might send unresolved cases to review, but that response must be labelled
bank policy rather than attributed to the regulator without support.

Open-ended terms such as reasonable satisfaction, adequate controls, or a
material change should remain explicit assessment tasks until an authorised
interpretation defines their use. Record who assessed the issue, on what
evidence, under which policy version. Replacing such a term with an invented
numeric threshold would change the rule.

The reviewer should see the source paragraph beside controlled language,
conditions, exceptions, unresolved questions, and worked cases. Generate decision
tables and diagrams from the adopted specification. Maintaining an independent
handwritten flowchart would introduce another place for meaning to diverge.

## Where mathematical proof helps

There are three distinct questions:

1. Does the specification faithfully represent the relevant sources? Legal and
   compliance review must resolve scope, interpretation, and source priority.
2. Does the implementation compute the specification? Types, model checking,
   solvers, and proof assistants can establish precisely scoped properties.
3. Do the input facts and operational records correspond to reality? Data
   reconciliation, evidence checks, and workflow monitoring address this.

For a deterministic decision, a possible verification goal is that the runtime
and the specified semantics return the same result for every input in the
declared domain. That domain must include missing values, relevant dates, and
exceptions where the specification supports them. For an ongoing obligation,
the target concerns sequences of events: issuing a task is different from
performing it before its deadline. A state machine or temporal model is needed.

Useful checks include conflicting rules, unreachable exceptions, uncovered
cases, threshold boundaries, expired consent, and whether changing only an
irrelevant fact leaves a decision unchanged. An SMT solver can seek an input
on which old and new specifications disagree, producing a concrete example for
the reviewer. Restrict the initial language so these checks remain tractable.

Tests should include cases independently constructed from the source by
compliance staff. If the same model mistranslates a clause and generates all
tests from its mistranslation, agreement proves little. Existing bank behaviour
is a comparison target for migration, not an unquestioned legal oracle.

Proof establishes consequences of the formal assumptions. It does not establish
that every applicable circular was collected, that the interpretation is legally
authoritative, or that a recorded client fact is accurate. Those questions remain
visible in the same review package.

## Reusing the three existing projects

| Existing project | Inspected capability | Proposed role and remaining work |
| --- | --- | --- |
| ResearchAssistant | Local PDF parsing, source storage/retrieval workflows, review records and export; its current documentation distinguishes structured source from fallible PDF extraction | Reuse document intake and literature handling. Add SFC/HKMA identifiers, annex links, amendment relationships, paragraph structure, and legal applicability metadata. |
| MathDevMCP | Source-bound obligations, external-tool routes, Lean target binding, counterexamples, bounded derivation branches, and explicit diagnostic/proof distinctions | Use after a rule or property is formalised. Add adapters for the legal rule language and its data types. Existing code/equation structural matching is not a semantic equivalence proof. |
| DynareMCP | Historical MCTS/UCB-style investigation records; current source graphs, decision-plan validation, model IR comparison, and proposed generated-code updates | Borrow the pattern for competing interpretations, evidence collection, impact analysis, and reviewable changes. Its macroeconomic model parser, numerical solver, and model-specific schemas do not directly evaluate circulars. |

ResearchAssistant was exercised in this investigation through `ra parse-pdf` on
both SPI annexes and the two papers below. The available extraction used
`pdftotext`; its outputs reported low confidence and required manual review.
The SPI threshold page and the FAQ page describing monitoring exceptions were
also inspected as rendered pages. This is evidence that the intake route is
usable here, not a benchmark of legal extraction accuracy.

DynareMCP's historical UCB100 record uses an investigation-value score and a
visit-count exploration bonus. It preserves open questions at budget exhaustion.
The current MathDevMCP derivation controller explicitly describes its ranking
as a partial order over evidence and assumptions, rather than MCTS. These are
useful search ideas, but neither a search score nor repeated successful
rollouts certifies a legal interpretation. Local code anchors:

- [ResearchAssistant extraction](../../ResearchAssistant/src/research_assistant/ingest/pdf_extract.py)
  and [MathDevMCP's ResearchAssistant bridge](../../MathDevMCP/src/mathdevmcp/research_assistant_pdf.py).
- [MathDevMCP branch controller](../../MathDevMCP/src/mathdevmcp/derivation_branch_controller.py),
  [Lean binding/checking](../../MathDevMCP/src/mathdevmcp/lean_check.py), and
  [result classification](../../MathDevMCP/src/mathdevmcp/high_level_workflows.py).
- [DynareMCP source graph](../../DynareMCP/src/dynaremcp/audit/source_graph.py),
  [model IR comparison](../../DynareMCP/src/dynaremcp/ir_diff.py),
  [decision-plan validator](../../DynareMCP/src/dynaremcp/decision_kernel.py), and
  [historical UCB100 record](../../DynareMCP/docs/FullRealLifeCaseStudy/10_final_latex/overnight_ucb100_2026_05_19/partial_thesis_candidate_v3_ucb100.md).

A legal investigation tree might have two proposed meanings for an exception.
One action retrieves the referenced FAQ; another asks a solver for a case where
the meanings differ; another records a compliance interpretation. Search helps
choose the next discriminating action. If both meanings survive, the system
keeps both and requests an interpretation decision. It should never choose the
meaning that authorises more trades merely because that branch scores well.

Start with a bounded work queue. Add MCTS only if a measured bottleneck in a much
larger investigation justifies its overhead. Transaction-time execution should
use the fixed, approved rules and a recorded fact snapshot.

## Open-source software and literature to borrow

| Resource | Why it fits | Practical boundary |
| --- | --- | --- |
| [Catala](https://github.com/CatalaLang/catala) | Keeps executable definitions close to statutory text and represents defaults and exceptions explicitly | A strong design starting point; assess its fit for conduct rules and event-based duties. Its formalisation covers a core translation, not the entire legal interpretation or deployed stack. |
| [DMN](https://www.omg.org/spec/DMN/1.5/About-DMN) and [Apache KIE / Drools](https://github.com/apache/incubator-kie-drools) | Standard decision models and tables; a DMN engine and Java integration | Define hit policies and missing-input semantics explicitly. Legal priority must not accidentally become table order. Workflow duties require more than a decision table. |
| [LegalRuleML](https://docs.oasis-open.org/legalruleml/legalruleml-core-spec/v1.0/os/legalruleml-core-spec-v1.0-os.html) | Vocabulary for obligations, permissions, prohibitions, exceptions, sources, jurisdiction and time | A representation standard. An execution profile and a reasoner are separate choices; borrowing the concepts does not require using XML as the review interface. |
| [Blawx](https://github.com/Lexpedite/blawx) | Visual rule authoring, explanations and hypothetical reasoning over s(CASP) | Useful for an authoring experiment. Its README explicitly describes educational/experimental, rather than production-quality, use. |
| [Z3](https://github.com/Z3Prover/z3) and the existing Lean route | Counterexample search and precisely scoped verification | They check encodings and assumptions, not the meaning of unformalised legal language. Preserve solver uncertainty and the exact property checked. |
| [OpenFisca](https://github.com/openfisca/openfisca-core) | An established implementation of computable tax/benefit systems | A useful architectural analogue; its microsimulation focus is less directly aligned with bank conduct workflows. |

The closest technical paper is Denis Merigoux, Nicolas Chataing and Jonathan
Protzenko, [*Catala: A Programming Language for the Law* (2021)](https://arxiv.org/abs/2103.03198).
Sections 3–4 explain the language, exceptions, and core compilation semantics;
section 4.5 states the proof; section 6 describes lawyer interaction and case
studies. The paper also limits the proof's relationship to the production
compiler. The inspected repository's formalisation README discloses an admitted
supporting lemma. The design lesson is to keep the legal text, executable
meaning, and human review close together; this is not evidence of a fully
verified SFC translator. The official verification-condition source and proof
source were also inspected and retained locally.

A foundational predecessor is Sergot and colleagues,
[*The British Nationality Act as a Logic Program* (1986)](https://www.doc.ic.ac.uk/~rak/papers/British%20Nationality%20Act.pdf).
Its worked rules and AND/OR diagrams directly address the proposed flowchart
idea. Its technical treatment of negation explains why failure to establish a
fact cannot universally be treated as its negation. The implementation was a
bounded experiment, not a complete system of legal reasoning. The method,
negation, counterfactual, and implementation sections were inspected; the old
Prolog implementation was not audited as reusable software.

LegalRuleML sections 4.1–4.2 provide the third useful reference. They distinguish
definitions from normative consequences, and explicitly cover exceptions and
alternative interpretations. This supplies vocabulary that a conventional
Boolean decision table alone lacks. Local copies and retrieval references are
recorded in [the source manifest](../.localresources/source-manifest.json).

## A practical pilot

Begin with one bounded business decision, such as whether an individual
client's proposed transaction can use the SPI streamlined approach. First
assemble the circular, both annexes, and the definitions and current guidance
they depend on. Confirm the actual regulated entity and business scope with
the bank's compliance owner. Treat unknown dependencies as unresolved work.

Create a small set of source-linked rules with a reviewer-readable table and
worked examples. The model proposes rules; compliance reviews interpretation;
developers review data mappings and execution. Keep regulatory requirements
and stricter bank policy separately attributable. Reuse ResearchAssistant for
intake and MathDevMCP for selected checks. Evaluate a Catala-style specification
and DMN review/execution on the same example before choosing a wider platform.

Run the reviewed rules against synthetic cases first. Include missing evidence,
ownership aggregation, equality at thresholds, category-specific experience,
consent changes, the two monitoring approaches, and version transitions.
Generate counterexamples and regression cases from proposed changes. Then run
in shadow mode against existing decisions using bank-approved data access.
Resolve disagreements against sources and reviewed interpretations, rather
than optimising agreement with the legacy system.

For an evaluation, predeclare a manual expert baseline, a fixed case set and
independently reviewed expected outcomes. Measure missed obligations, unsupported
rules, incorrect applicability, erroneous permission, unresolved cases, and
reviewer effort. Retain unresolved cases separately so abstention cannot inflate
apparent accuracy. Critical semantic defects prevent use of the affected rule;
the acceptable residual risk and operating scope are decisions for the bank.
No accuracy or time-saving claim has been measured in this research.

The initial deliverable should be a reviewed rule package and a proposed system
change: affected controls, changed decisions, source paragraphs, implementation
diff, and test evidence. That would already remove much repeated transcription
while allowing the bank to inspect exactly what is changing.
