# Establishing that an executable rule preserves the circular's meaning

22 September 2026. Research and proposed extension; no new translator, proof
engine, legal approval or application release is asserted by this note.

The main unresolved problem in LegalMath is the translation from the circular
to its executable interpretation. Our second-circular exercise established
agreement between manually specified expected outcomes, RuleIR and generated
Java for a limited reading of SFC circular 23EC46. The same agent supplied the
interpretation and expected outcomes. It therefore did not independently
establish that the interpretation was correct. The drafting provider still
returns fixtures rather than interpreting arbitrary circulars.

There is substantial literature addressing this gap. Its most useful methods
combine precise, readable specifications, explicit competing interpretations,
source evidence and counterexamples. They support a product that makes legal
interpretation inspectable and checks its consequences. They do not provide an
unconditional theorem that an arbitrary English circular has been understood
correctly. The practical design is to make the judgment about meaning explicit,
then prove as much as possible downstream of that judgment.

## What the proof would have to establish

A proof requires a stated proposition and rules for deciding what it means.
For ordinary English, choosing the definitions, relevant context, scope and
exceptions is already part of the interpretation. Writing a formula for the
English and then proving that generated code implements that formula leaves
the original question unanswered: why is this the right formula?

This distinction also arises in mathematics. A proof assistant can check a
theorem about a formally defined object while the formal theorem misstates the
informal problem. A checked proof of that theorem does not repair the mismatch.
In a circular, the potential mismatches include legal definitions elsewhere,
qualified language, exceptions, effective dates and facts that require judgment.

We should distinguish three outcomes. Some provisions support a clear rule once
their references and vocabulary are fixed. Other provisions admit consequential
alternative readings that require an interpretation decision. Still others
deliberately require judgment, such as whether a communication is misleading.
The last group can be represented as a duty or a classification question without
pretending that a precise automatic classifier has been supplied.

Let `S` be a controlled-English specification accepted for a stated source
version, `F` its RuleIR translation, and `A` the explicit assumptions and
vocabulary definitions. Let `D_A` contain the inputs and histories allowed by
those assumptions. Once both languages have formal semantics, the desired
preservation property is

\[
  \forall x\in D_A,\qquad
  \operatorname{eval}_{\mathrm{CNL}}(S,x)
  =\operatorname{eval}_{\mathrm{IR}}(F,x).
\]

The equality must include meaningful result distinctions: a condition being
false, missing evidence, conflicting evidence, being outside the reviewed scope,
and any supported obligation or event behavior. It cannot compare only a final
Boolean after discarding those distinctions. This is a proposed proof
obligation; it has not been established for our implementation.

The separate proposition that `S` faithfully represents the official source
requires a justified interpretation. A reproducible record can identify the
words and references supporting each choice, the alternatives considered,
the examples that distinguish them and the responsible review decision. That
is substantive evidence, but the fact that someone approved it is not a
mathematical proof of uniquely correct legal meaning. An unresolved source
dependency or ambiguity must remain visible. A stricter bank policy can be
adopted separately, with its own authority, rather than attributed to the SFC.

The earlier [verification report](../implementation/second-circular-verification.md)
describes the present engineering evidence. The preservation theorem above and
the source interpretation record are additional work, not new descriptions of
the tests already run.

## A concrete disagreement in circular 23EC46

[SFC circular 23EC46](https://apps.sfc.hk/edistributionWeb/gateway/EN/circular/doc?refNo=23EC46),
24 October 2023, paragraph 10, discusses the gift restriction in Code paragraph
3.11. The text covers promotion of an individual investment product and a
product type, and excludes discounts of fees or charges from the gift
restriction. Paragraph 9 raises the possibility that additional returns fall
within the gift provision. It does not supply an automatic classification of
every additional-return arrangement.

For the following comparison, assume the distributor/fund scope has been
established and consider one incentive component. A reviewer has supplied the
classifications of the component and its promotional link. Let `G` mean a gift
is offered, `P` a specific-product link exists, `T` a product-type link exists,
and `D` the component falls within the fee/charge-discount exception. These are
defined facts, not classifications inferred by the following formula.

The current proposed trigger is

\[
  F_A=G\land(P\lor T)\land\neg D.
\]

A translator that overlooks the product-type wording could produce

\[
  F_B=G\land P\land\neg D.
\]

To expose the difference, a solver can search for an input satisfying
`F_A != F_B`. One witness is `G=true`, `P=false`, `T=true`, `D=false`:
a gift promotes a fund category without naming an individual fund.
`F_A` triggers and `F_B` does not. This is an elementary checked-by-substitution
derivation of disagreement; no solver run is claimed here. The source wording
about product types is the reason to challenge `F_B`. The solver itself has
established only that the two candidates disagree.

A second error concerns the unit to which the exception applies. Compare a
reading that exempts the assessed discount component with a reading that exempts
an entire offer whenever any component is a discount. A voucher accompanied by
a fee waiver separates them. Under our proposed component-level treatment, the
voucher needs its own assessment. A whole-offer exemption would clear it merely
because the waiver is present. The reviewer must confirm the unit of assessment
against the source and referenced materials; a variable named `discount` is
insufficient to express this decision.

A third error would replace the qualified classification in paragraph 9 by
`additional_return -> gift`. If the evidence has not settled whether an
arrangement is a gift, our proposed system must retain an unresolved
classification, not invent either a gift finding or a clearance. The modal word
here concerns possible classification; it must not be translated as permission.

These examples show why the source-to-specification interface needs more than a
flow chart. It must expose the connective, the object being classified, the
exception's reach and the evidence supporting the classification. It must also
preserve the source's normative wording. Mapping a regulatory expectation to a
bank blocking control is a recorded operational choice, not permission to
silently rewrite every occurrence of “should” as an identical legal modality.

This remains a selected historical source example. The cited Code provision and
FAQ are unresolved dependencies in our test packet; the complete current legal
position has not been established. A false trigger result does not authorize
the offer under the circular's other provisions or other requirements.

## Literature that addresses the interpretation step

**Amrollahi, Lopez and Barrett (2026), *Faithful Autoformalization via Roundtrip
Verification and Repair*.** This is the closest newly located paper to the
user's question. It translates source English into a formula, translates that
formula back into English, and formalizes the reconstructed English. A solver
then compares the first and last formulas. A model diagnoses which translation
stage may have introduced a difference; repair of that stage regenerates the
dependent stages. Sections 3–4 and Algorithm 1 specify this procedure. Section 5
adds bidirectional natural-language entailment as a diagnostic.

The method offers an implementable disagreement detector. It does not prove
source fidelity: an initial omission can survive both later translations.
The paper explicitly acknowledges this in its limitations. Its evaluation uses
two Texas statutory corpora and a single run per configuration, while its
semantic diagnostic is a general-purpose NLI model. Reported drift is not an
expert-adjudicated legal error rate. Cross-referenced rules are also outside
the evaluated single-rule treatment. We can borrow bounded repair and formal
comparison, but require source review and dependency closure. Appendix E
promises a code release; the inspected edition does not supply an auditable
implementation. [Preprint v2, 9 May 2026](https://arxiv.org/abs/2604.25031v2).

**An et al. (2025 preprint, 2026 revision), *A Neurosymbolic Approach to Natural
Language Formalization and Verification*.** ARc separates policy-model
construction and vetting from checking individual claims against that model.
Section 3.1 describes consistency checks, template-generated structured English
and examples supplied by users or generated symbolically. Section 3.2 compares
redundant claim translations and returns distinguishing assignments when they
disagree. We can borrow that review interface and verify reusable policy models
before deploying them. The reported 99.4% “soundness” is an empirical metric
defined as one minus false positives divided by all samples. Table 1 still
reports ten false positive decisions, 94.4% precision and 14.9% recall for that
configuration. It is not a theorem about translation correctness. The authors'
human-vetting example in Appendix A.1 reinforces the need to resolve
assumptions and exceptions. [Paper v2](https://arxiv.org/abs/2511.09008v2).

**Kowalski, Dávila, Sator and Calejo (2023), *Logical English for Law and
Education*.** Controlled natural language is a deliberately restricted language
whose sentences have defined computational meaning. In Logical English,
predicate templates fix argument positions; determiners introduce and reuse
variables; restrictions on pronouns and sentence forms reduce ambiguity.
Sections 1–2 explain translation into logic programming. Section 3 works
through alternative readings of citizenship rules and distinguishes explicit
negative information from lack of information. This suggests a readable review
language between circular and code. It does not mean arbitrary English is
parsed unambiguously. Nor should we import Prolog's negation-as-failure into
RuleIR's missing-evidence semantics. [Author-hosted paper](https://www.doc.ic.ac.uk/~rak/papers/Logical%20English%20for%20Law%20and%20Education%20.pdf)
and [official software](https://github.com/LogicalContracts/LogicalEnglish).

**Athan et al. (2014), *Legal Interpretations in LegalRuleML*.** Sections 3–4
show how a provision can have alternative formal readings, each connected to
source and context. Their example concerns whether the relevant year is the
year income was earned or the year it was reported. LegalRuleML can retain
incompatible readings and identify a selected interpretation. This directly
supports our need to preserve competing candidates, rather than overwrite one
when a model or reviewer chooses another. The contribution represents
interpretations; it does not discover or adjudicate the legally correct one.
[Primary proceedings paper](https://ceur-ws.org/Vol-1296/paper2.pdf).

**Huttner and Merigoux (2022), *Catala: Moving Towards the Future of Legal
Expert Systems*, together with Merigoux, Chataing and Protzenko (2021),
*Catala: A Programming Language for the Law*.** Huttner and Merigoux's section
4.2 directly addresses the translation gap through source-aligned programming
by a lawyer and a programmer. Readers can inspect how the code treats each
provision and exception. The programming-language paper separately studies
formal preservation for a core compilation step. That is a valuable division
of responsibilities. It is not a proof that the original legal text was
correctly interpreted, or a verified version of our Java backend.
[Legal-method paper](https://doi.org/10.1007/s10506-022-09328-5),
[language paper](https://arxiv.org/abs/2103.03198v2).

**Koreeda and Manning (2021), *ContractNLI*.** The task pairs a contract with
a hypothesis, labels the hypothesis as entailed, contradicted or not mentioned,
and identifies supporting text. Section 5.2 examines exceptions and evidence
spread across different passages. We can use this structure to require evidence
for each proposed interpretation and to test unsupported additions. The paper
supplies a dataset and learned baselines, not a decision procedure for legal
truth. Its NDA task and annotation assumptions need replacement by an SFC
review protocol. [ACL proceedings paper](https://aclanthology.org/2021.findings-emnlp.164/).

**Wang et al. (2026), *Know Your Limits: On the Faithfulness of LLMs as Solvers
and Autoformalizers in Legal Reasoning*.** Sections 3–5 examine how assumptions
change entailment labels and how formalizations introduce unsupported axioms.
The useful lesson is to review assumptions as part of the interpretation, not
hide them in a solver's background theory. This is a preprint with contestable
annotation choices; it does not establish a universally correct policy on
implicit legal assumptions. No reported accuracy is transferred to our system.
[Preprint v2](https://arxiv.org/abs/2606.16118v2).

Stipula and Java contract verification remain relevant downstream: they help
state and check what parties, assets, events or generated programs do under a
formal specification. They do not eliminate this source-to-specification
problem. We should therefore develop the interpretation work alongside our
existing execution language rather than expect a switch of formal language to
settle the English meaning.

## The proposed interpretation workbench

The review unit should be a provision together with the definitions, exceptions,
footnotes and external references needed to understand it. The source must be
fixed by version and effective context. Retrieval supplies candidate supporting
material; a reviewer decides which material controls the interpretation. A
missing reference must not silently become an empty set of requirements.

For each unit, the workbench should prepare a source-linked controlled-English
restatement and a typed vocabulary. The vocabulary needs definitions and units,
not just labels: whether an incentive means one component or a whole offer,
what constitutes a fund-category link, who supplies a classification, and how
dates and evidence histories apply. Qualitative judgments remain named review
inputs unless a separate defensible decision procedure exists.

A deterministic renderer should show the formal candidate in English using
fixed templates. This avoids having a second model conceal a coding error by
producing a fluent paraphrase of the original source. But a faithful rendering
of the formula can faithfully display a wrong formula; it must be reviewed
beside the original source. A parser/renderer round trip establishes a
representation property, not source correctness.

The workbench should then generate alternative readings and plausible errors:
different exception attachment, missing disjuncts, changed quantifiers, altered
dates, implicit assumptions and expanded scope. Model proposals are hypotheses.
Agreement between models is not independent evidence when they share training,
prompts or a mistaken vocabulary. At least one source-based review should be
prepared before viewing the generated candidate, to reduce anchoring.

For two formal readings `F_1` and `F_2`, ask a solver for a possible scenario in
which their results differ:

\[
  A(x)\land
  \bigl(\operatorname{out}(F_1,x)\ne
        \operatorname{out}(F_2,x)\bigr).
\]

A satisfying assignment is a distinguishing case. An unsatisfiable result
establishes equivalence only under the encoded domain, assumptions and solver
semantics. A timeout or `unknown` is unresolved. Before accepting an
unsatisfiable difference query, establish that the background assumptions have
a model and that relevant triggering situations remain possible. Otherwise
contradictory assumptions, or assumptions that exclude every gift offer, can
make comparison vacuous. Store the query, assumptions, solver version and
result; stronger assurance requires a checkable proof certificate where the
selected solver/theory supports one.

The reviewer should see concrete contrasting outcomes, not a formula alone.
For each disagreement, the record should identify the decisive source words,
the applicable reference or definition, the accepted interpretation and the
reason the alternative fails or remains unresolved. This is a structured legal
argument. Case examples sharpen it, but do not replace whole-provision review:
a test derived only from the candidate cannot reveal a requirement that both
candidate and test omitted.

It is possible to retain several readings without immediately selecting one.
For a particular input, the tool can report that all retained readings give the
same outcome, or that they disagree. Agreement is conditional on the represented
set of readings; it does not establish that the set is complete. Pending issues
that could change operational decisions must block automatic release or route
the decision to review. A case-level robust result is not approval of the whole
policy bundle.

Finally, compare the accepted controlled specification with RuleIR under their
defined semantics, then verify the Java delivery against RuleIR. Keep the
source-interpretation decision, formal preservation result, tested Java behavior
and operational fact evidence as distinct records. A single green “verified”
badge would conceal which link was actually checked.

## A bounded extension to the existing program

The first slice should reuse the 23EC46 example as a development case, then
evaluate on independently adjudicated provisions not used to design the
translator. It should introduce the following components in this order.

| Component | Concrete deliverable | Acceptance condition |
| --- | --- | --- |
| Interpretation packet | Source version and dependency list; vocabulary and definitions; original normative wording; scope, time, exception attachments; candidate readings; assumption sources; reviewer decisions and unresolved questions | Every operative source passage in the declared unit has a disposition, every added restriction has a source or explicit policy authority, and no unresolved controlling reference is treated as satisfied |
| Readable formal specification | A restricted typed grammar with a deterministic parser and renderer for the currently supported RuleIR fragment | Unsupported constructs are rejected; bindings and exception scopes are visible; renderer/parser correctness is specified separately from legal approval |
| Counterexample service | A translation of supported expressions into a solver representation, with reproducible difference queries and scenario explanations | Agreed examples distinguish the missing product-type route, whole-offer discount exception and unsupported gift classification; inconsistent or unsupported encodings return unresolved/error rather than equivalence |
| Review workflow | Source-first independent readings, adjudication of disagreement, reusable reviewed definitions, and invalidation when sources or assumptions change | Approving a compiler test cannot approve source meaning; unresolved meaning questions survive export and prevent release where material |
| Translation evaluation | A frozen set of source packets, adjudicated interpretations and cases, with a real drafting provider | Report critical unsupported restrictions and omissions, disagreement, abstention and review effort separately; the present fixture provider cannot pass a translation evaluation |

The first solver fragment should be explicit and small. For the current gift
example, complete Boolean inputs are sufficient to demonstrate alternative
readings. Extending the checker to actual runtime behavior requires encoding
RuleIR's `UNKNOWN`, `CONFLICT`, scope and temporal/evidence rules. In particular,
RuleIR uses three-valued operators: `A OR NOT A` remains unknown when `A` is
unknown. Replacing unknown with an unconstrained classical Boolean would change
that semantics. The existing special-case truth oracle is not a general proof
of a future SMT encoding.

The bank's acceptance threshold for a translation pilot must be set before
evaluation and distinguish material omissions from inconsequential wording
differences. All critical adjudicated errors should be reported individually.
Multiple cases from one clause are not independent circulars; uncertainty and
coverage should be reported at the appropriate document/requirement level.
Passing a small pilot supports only its stated population and scope. No pilot
or stochastic comparison was run for this research note.

ResearchAssistant is useful now for retained sources, paper parsing and
citation/version records. MathDevMCP could support formally stated preservation
lemmas once the controlled language and IR semantics are defined. Proof or tree
search ideas from DynareMCP might propose competing readings or prioritize
discriminating cases. These are possible adaptations, not integrations inspected
or implemented here. A search reward based only on agreement or proof success
would encourage an easily proved interpretation, which may be the wrong one.

## Reading, retrieval and evidence record

The pre-work audit is in
[the research plan](../plans/english-interpretation-assurance.md). No runtime
source, accepted delivery, application test or original proposal was changed.
The following sections were inspected for the claims above; papers were not
merely selected from abstracts.

| Work | Inspected material and use |
| --- | --- |
| Amrollahi et al. 2026, v2 | Sections 3–7, Algorithm 1, limitations, Appendix A diagnostic prompt, Appendix B schema design, Appendix D NLI categories and Appendix E availability. Borrow comparison and bounded repair; preserve fixed-point failure, noisy NLI and single-rule limits. No executable replication. |
| An et al. 2025/2026, v2 | Sections 3.1–3.2 and Algorithm 1, section 4/Table 1 metric definition, section 5 limitations and Appendix A.1 policy vetting. Interpret metrics as observed classification results, not proof. |
| Logical English 2023 | Sections 1–3: variable/template semantics, Prolog translation, exceptions and citizenship alternative readings. Official repository README inspected for language and implementation description; parser implementation and conformance not audited. |
| Legal Interpretations 2014 | Sections 2–4: interpretation scope, earned/reported-income example and formal representation. Borrow explicit alternatives and provenance, not the example as Hong Kong legal reasoning. |
| Huttner and Merigoux 2022 | Sections 4.1–4.2: formal specification and literate lawyer/programmer cooperation. A proposed methodology, not measured local review effectiveness. |
| Catala 2021 | Core translation correctness statement, simulation qualification and implementation boundary, PDF pp. 19–20. Prior retained official formalization README was rechecked: it documents an admitted supporting lemma. No proof replay or claim of a completely verified production compiler. |
| ContractNLI 2021 | Task/evidence definitions, section 5.2 on exceptions, and appendix annotation process. Borrow evidence-backed labels; do not import NDA ground truth into SFC interpretation. |
| Know Your Limits 2026, v2 | Sections 3–5, including reannotation, explicit assumptions and hallucinated axioms. No quantitative generalization: annotation judgments and denominator inconsistencies require separate investigation. |

The newly downloaded roundtrip paper is retained under
`docs/papers/Faithful Autoformalization via Roundtrip Verification and Repair, Amrollahi(2026).pdf`.
The library manifest pins its 14-page v2 and SHA-256
`776b328e3fa4aee9f692f2e821bd7e246700f80040e8ef5b6cceccd293496b2e`.
ResearchAssistant's parse, extracted text and official landing page are retained
under `.localresources/english-interpretation/`. Its parser identified an
affiliation as an author; the author list was checked against the actual title
page rather than accepted from that parse.

Web search returned an upstream 502. ResearchAssistant discovery initially
failed DNS in the sandbox and succeeded when rerun with trusted network access;
its source report records a Semantic Scholar rate limit and available OpenAlex
results. Direct primary-source downloads supplied the paper and software README.
Discovery also identified Bench-Capon and Coenen's *Isomorphism and legal
knowledge based systems* (1992), but its publisher download returned HTML.
Lawsky's *A Logic for Statutes* repository page was retrieved, but the PDF returned
403. These are further reading leads, not inspected technical foundations for
this note. The failed responses are not counted as papers in the library.

The strongest remaining weakness is source judgment: a precise vocabulary and
consistent set of formulas can still share an incorrect legal assumption. An
independently justified source reading or authoritative clarification that
contradicts our proposed trigger would overturn its acceptance even if every
software test continued to pass. The next justified development step is the
interpretation packet and disagreement workflow, with the real provider and
independent review required before any claim of translation accuracy.
