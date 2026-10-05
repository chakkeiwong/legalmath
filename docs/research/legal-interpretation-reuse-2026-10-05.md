# Reusing legal interpretation research for LegalMath

5 October 2026. This review addresses the substantive gaps in the
[product audit](../implementation/assurance-evidence-master/product-gap-audit-2026-10-05.md),
particularly case-law reasoning, under the
[research plan](../plans/legal-interpretation-reuse-review.md).

Established legal AI supplies useful methods for retrieving authorities,
representing legal propositions, comparing cases and evaluating arguments. The
inspected evidence does not establish a general solution to interpreting arbitrary
legal English. A system can reason correctly from an incorrectly encoded holding,
fact or exception. Our conditional programs still depend on supplied judgments
such as `responsibility_retained` and `ownership_records_proper`.

The strongest immediate combination is a source-linked semantic representation,
explicit rival arguments, and factor-based case comparisons. PyArg is a candidate
argument engine; LegalRuleML and Logical English supply representation ideas;
HYPO/CATO/AGATHA supply case-comparison methods. These are recommendations for a
bounded prototype, not validated new dependencies or a claim that the gaps are
closed.

## Evidence and scope

Technical sections of retained papers and selected official implementation files
were inspected. Public material was downloaded for local inspection; no downloaded
code was installed or executed, and no provider assessment round was started.
Runtime compatibility, repository maintenance and Hong Kong corpus coverage have
not been established by this review.

The controlling [product requirement](../implementation/proof-qualified-generalization/product.md)
excludes human answer keys, ratings and adjudication as product quality evidence.
Published legal texts remain valid premises. Some cited research uses
human-curated factors, rules or evaluation labels. Those results describe the
research; they do not qualify our product or authorize importing those labels into
local fitting, selection or correctness claims.

## What to borrow

| Work | Mechanism relevant to our gaps | Required limit |
|---|---|---|
| HYPO, CATO and AGATHA | Legally significant factors; analogies, distinctions, counterexamples and competing theories. Useful for explaining why a precedent bears on responsibility, supervision or adequacy. | Start from encoded factors and outcomes; do not establish those encodings from unrestricted judgments. No official reusable implementation was verified here. |
| ASPIC+ and PyArg | Arguments with premises and rules; challenges to premises, conclusions and inference rules; acceptance under declared semantics. | Acceptance depends on encoding and preferences. It does not establish legal correctness. PyArg has an ordering default that must be made explicit. |
| Carneades | Ordinary premises, assumptions, exceptions, pro/con arguments and burdens. Helps distinguish absent evidence from rebuttal. | Original paper and version 4 have different semantics. Numerical weights and proof standards are not automatically legal standards. |
| LegalRuleML | Alternative readings, source text, authority, jurisdiction and temporal context; constitutive versus prescriptive statements. | Represents interpretations but does not decide which is correct. Its concepts do not require adopting XML internally. |
| Logical English | Predicate templates, explicit variable binding and condition scope in executable controlled English. | Specifies a reading without establishing fidelity to original prose. Negation as failure and untyped variables require care. |
| SARA-IE | Extracted events and arguments linked to exact source spans before symbolic reasoning. | Uses a tax ontology and curated formal statutes. Missing arguments, date completion and closed-world assumptions affect results. Code reuse licence unverified. |
| CLERC and eyecite | Retrieve case passages, identify citations and resolve short references. | Citations do not establish substantive support, binding authority or current validity. Preserve opinion boundaries and check Hong Kong coverage. |

## Case comparison: HYPO, CATO and AGATHA

Primary sources are Bench-Capon's [HYPO retrospective](https://www.csc.liv.ac.uk/~tbc/publications/hypoLegacy.pdf)
and Chorley and Bench-Capon's [AGATHA paper](https://www.csc.liv.ac.uk/~tbc/publications/agatha.pdf),
especially AGATHA sections 2–3, 6–8 and 10. HYPO supplies analogy, distinction and
more-on-point counterexample moves. CATO adds factor hierarchies and ways to
emphasize or downplay distinctions. AGATHA constructs rival theories from
pre-encoded factors, outcomes, rules and value preferences.

A LegalMath comparison should identify the proposition at issue, factors
supported by each opinion, material similarities and differences, and contrary
authority. A similar outcome alone is insufficient. Retained decision-making
authority must be distinguished from supervisory conduct and operational results.

AGATHA evaluates explanatory power, simplicity and completeness. Its advocacy
setting permits arbitrary preference moves; its heuristic search need not find
the best theory. Borrow the representation and argument moves, not a desired-party
win objective, arbitrary priorities or theory simplicity as legal correctness.
The evaluation uses reconstructed structured cases, not extraction of holdings
from new judgments. These are literature recommendations, not verified installable
dependencies.

## Rival arguments: ASPIC+ and PyArg

Prakken's [2010 paper](https://webspace.science.uu.nl/~prakk101/pubs/aspicAF.pdf),
sections 2–3 and its rationality conditions, distinguishes undermining a premise,
rebutting a conclusion and undercutting an inference. Grounded semantics has one
extension; preferred semantics may yield several. Neither is automatically the
legally appropriate decision procedure.

The author's [correction to definition 6.8](https://webspace.science.uu.nl/~prakk101/corr.html)
is retained locally. Formal rationality results require their stated assumptions;
they cannot be claimed for an arbitrary graph using ASPIC+ terminology.

The official [PyArg repository](https://github.com/DaphneOdekerken/PyArg) is MIT
licensed. Inspected files include `argumentation_theory.py`, grounded and
preferred extension algorithms, examples and the licence.
`create_abstract_argumentation_framework` selects `LastLinkElitistOrdering`
when no ordering is supplied. LegalMath must declare its semantics and preferences,
with source support for any claimed legal precedence. A library default cannot
decide priority between paragraph 14 and footnote 5. Bound argument construction
and preserve alternatives when a priority is unavailable.

PyArg is the first argument-engine candidate to prototype. Compatibility and
correct operation on the intended finite theories still require focused checks.
No runtime validation is claimed here.

## Evidence and burdens: Carneades

Gordon, Prakken and Walton's [2007 paper](https://webspace.science.uu.nl/~prakk101/pubs/GordonPrakkenWalton2007a.pdf),
sections 3–5, distinguishes ordinary premises, assumptions and exceptions and
evaluates arguments against proof standards. The paper explicitly does not claim
that its proposed standards adequately model legal proof standards.

The official [Carneades 4 implementation](https://github.com/carneades/carneades-4)
is MPL-2.0 licensed. Its CAES semantics extend beyond the original acyclic model,
including cycles and cumulative arguments. Inspection of
`src/engine/caes/caes.go` shows a default PE proof standard and resolution using
argument weights. Unsupported propositions can receive an `Out` label; that
label must not become a factual assertion that the proposition is false.

Borrow the premise distinctions now. Treat the engine as an alternative requiring
a deliberate semantics choice, not a second interchangeable solver to combine
with PyArg. Numerical thresholds require applicable authority before being
presented as Hong Kong law.

## Meaning and context: LegalRuleML and Logical English

Athan and colleagues' [Legal Interpretations in LegalRuleML](https://ceur-ws.org/Vol-1296/paper2.pdf),
sections 3–4, represents rival readings of a temporal ambiguity with their sources
and contexts. The [OASIS specification](https://docs.oasis-open.org/legalruleml/legalruleml-core-spec/v1.0/os/legalruleml-core-spec-v1.0-os.html)
is the standard reference. Borrow explicit alternatives, authority, jurisdiction,
temporal applicability, and the distinction between rules imposing duties and
rules constituting legal classifications. These address actor, time, modality and
ownership gaps.

Kowalski and colleagues' [Logical English for Law and Education](https://www.doc.ic.ac.uk/~rak/papers/Logical%20English%20for%20Law%20and%20Education%20.pdf),
sections 1–2, explains predicate templates and restricted variable binding.
The official [Logical English repository](https://github.com/LogicalContractsOrg/LogicalEnglish)
is Apache-2.0 licensed; inspected material includes syntax documentation and parser
source. Controlled English can make a proposed interpretation inspectable and
executable from one semantic representation.

The paper's basic syntax is untyped: a mnemonic variable noun is not a type
constraint. Negation as failure also needs review before handling incomplete case
evidence. Missing proof of supervision must not silently mean proof that it did
not occur. The repository roadmap includes further deontic conflict and priority
work; it is not a complete solution to our SHOULD and consequence questions.

## Evidence extraction: SARA-IE

Holzenberger and Van Durme's [Connecting Symbolic Statutory Reasoning with Legal Information Extraction](https://aclanthology.org/2023.nllp-1.12/),
sections 3–5 and 7 and appendices B, C and E, connects event/argument extraction to
Prolog reasoning. The representation
`span(Value, Start_index, End_index)` records the text from which a value came.

The [SARA-IE repository](https://github.com/SgfdDttt/sara-ie) was inspected through
grounding, extraction and postprocessing code. Its postprocessor turns predicted
tuples into Prolog facts while retaining selected existing formal context; it is
not unrestricted end-to-end statutory interpretation. Its ontology is
task-specific. The paper documents a closed-world exception problem and date
completion using January 1, December 31 and a fallback year. Do not inherit these
for regulatory dates. The extraction code also includes a missing-span-probability
fallback explicitly described as inflating probability; these values cannot be
imported as legal confidence.

No root licence was found in the inspected repository tree. Treat permission for
code reuse as unverified. Reimplement the published span-linked representation
rather than copying code or adopting its trained model.

For judgments, a span additionally needs its role: allegation, party submission,
factual finding or judicial reasoning, including an unresolved state. A quotation
establishes that words occur, not that an alleged event occurred or that the court
adopted the claim.

## Retrieval and citations: CLERC and eyecite

The inspected [CLERC paper](https://arxiv.org/abs/2406.17186) is arXiv v2,
27 June 2024, not a verified reading of the later proceedings version. Sections
3–5 describe retrieval and generation with citation-derived retrieval labels and
text/citation evaluation. Section 5.2 identifies a central limitation: a correct
citation can accompany incorrect analysis or omit the relevant proposition, so
citation metrics can overestimate substantive quality.

Section 3.1 concatenates majority, concurring and dissenting opinions when
constructing case documents. Preserve those distinctions in LegalMath. Court,
jurisdiction, date, procedural posture, the proposition necessary to the decision,
and subsequent treatment also require explicit support. Storing those fields
alone does not solve their interpretation.

The official [CLERC repository](https://github.com/abehou/CLERC) was inspected
through query filtering, relevance-label construction and generation evaluation.
An MIT licence is present at `retrieval/src/LICENSE`; a licence covering the
entire repository was not established. Do not generalize that nested licence to
all code or assume it covers the corpus.

[eyecite](https://github.com/freelawproject/eyecite) is BSD-2-Clause licensed.
Its `get_citations` and `resolve_citations` functions extract and reconcile
citation forms, including short references. Resolving actual cases requires a
corpus or lookup mechanism. Its principally US citation support requires a Hong
Kong coverage check. It is not a citator establishing that a case remains good law.

## What commercial systems establish

Magesh and colleagues' [Hallucination-Free?](https://arxiv.org/abs/2405.20362)
provides historical evidence against equating legal retrieval with reliable
interpretation. The retained manuscript is arXiv v1 with a June 3, 2024 update
note. Its methods, sections 5–6 and evaluation material describe 202 queries
graded for correctness and grounding and report hallucination rates of 17%–33%
for tested versions of Lexis+ AI, Westlaw AI-Assisted Research and Ask Practical
Law AI.

These are the authors' results on that sample under their human grading rubric,
not current 2026 measurements, population error estimates or local acceptance
criteria. The study does not prove that future systems cannot solve particular
interpretation tasks. It shows why working citations or a legal brand do not
establish correctness.

## Recommended first implementation

Start with paragraph 10 and paragraph 14/footnote 5: existing consequential
ambiguities with different executable consequences.

1. Represent clauses and proposed readings using a typed, source-linked structure:
   actor, action, object, modality, condition, exception, effective interval,
   authority and unresolved premises. Distinguish retained responsibility,
   exercised supervision and achieved adequacy; separate confirmation,
   demonstration, verification and legal opinion.
2. Express supporting and opposing arguments using an ASPIC+-style model.
   Prototype PyArg behind a small interface with declared semantics and
   source-supported priorities. Missing authority leaves an unresolved issue.
   Generate controlled-English explanations and program inputs from the same
   structure.
3. Add case factors and analogy/distinction moves when relevant judgments are
   acquired. Preserve opinion identity, procedural context and sources for each
   proposed factor or holding. Expose missing premises for transferring a
   precedent to the facts or jurisdiction.
4. Check distinguishing inputs: retained authority with deficient records, good
   operations without retained authority, no regulator request, provider
   replacement, conflicting ownership records and incomplete evidence. Derive
   expected consequences from declared semantics. These checks establish scoped
   program behavior, not English fidelity.

The product should explain which conclusion follows under which reading, why a
competing reading remains, and what missing premise matters. It need not force a
unique answer where authority leaves the issue open. Existing downstream formal
machinery can verify consequences of specifications; fidelity between source and
specification remains a separate obligation.

## Defaults and decision record

| Choice or inherited convention | Status and risk | Required early check |
|---|---|---|
| PyArg as first engine | Prototype candidate selected for accessible Python implementation and structured arguments; not runtime-validated. | Finite theories with explicit premises, rules, priorities and semantics; check computed extensions against stated definitions. |
| Grounded versus preferred semantics; last-link ordering | Unselected semantic choices; uniqueness can hide unresolved legal choices. | Expose consequences of admissible settings; require premises for claimed legal preferences. |
| Carneades PE/weights and `Out` labels | Implementation conventions, not legal standards or factual negation. | Missing and conflicting evidence under explicit label meanings. |
| SARA date completion, ontology and closed-world rules | Rejected as silent transfers. | Unknown dates, absent arguments and unresolved exceptions. |
| Citation-derived relevance and merged opinions | Research conventions insufficient for authority or holding fidelity. | Opinion boundaries, proposition support and jurisdiction. |
| Agreement, benchmark score or compilation | Diagnostics, not English-fidelity promotion evidence. | State the proposition actually established; preserve unresolved source premises. |

Decision: the research acceptance criterion is met. Recommendations have
inspected technical sources, concrete gap mappings and explicit assumptions.
The justified next action is a bounded substantive prototype. SARA-IE and CLERC
licence uncertainties limit code copying, not study of published methods. No
product gaps were closed by this review and no natural-language correctness or
default readiness was established.

The strongest alternative explanation for future apparent improvement is a
consistent formal encoding that still misreads the source. Source-linked
counterarguments and preserved alternatives are therefore essential. The weakest
current evidence is applicability to Hong Kong precedent and our actual disputes;
a prototype must expose that limitation rather than bury it in an aggregate score.

## Retained versions and provenance

Selected code, PDFs, text extracts, receipts and metadata are archived under
`.localresources/legal-interpretation-reuse-2026-10-05/`.
`review-manifest.json` records hashes and retained-paper provenance. The original
`docs/papers` catalogue and paper count were not changed. Archiving an additional
lead does not imply review or recommendation.

| Official repository | Inspected commit | Licence finding |
|---|---|---|
| DaphneOdekerken/PyArg | `f907bac94cbdd663839300b3b7523d4d958ff36f` | MIT |
| carneades/carneades-4 | `d19d5431b36da16ffdc2c7ebe4dded784e65b49a` | MPL-2.0 from licence and README |
| LogicalContractsOrg/LogicalEnglish | `1b31805c917d2e857e95ad66352d1465658fa3e6` | Apache-2.0; former URL redirects |
| SgfdDttt/sara-ie | `88832cca607a34432f4e36870134e3531f5a2547` | Code reuse licence unverified |
| abehou/CLERC | `6cd120625f6e86187d4f1064170393ac056834b3` | MIT at `retrieval/src/LICENSE`; broader scope unverified |
| freelawproject/eyecite | `0513e7fec46db49d86d9c8f6a854feba231b50a3` | BSD-2-Clause |
