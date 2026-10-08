# Existing solutions and their limits

This review extends the [seven-paper technical review](../prospectus-root-cause-2026-10-06/LITERATURE-REVIEW.md),
whose retained PDFs/text, section anchors and code inspections remain part of
the evidence. The added sources are in [literature/new-source-manifest.json](literature/new-source-manifest.json):
two papers, two official code sources and one official source archive, acquired
through five public HTTPS fetches. PDF text was extracted with the installed
ResearchAssistant adapter. No model, GPU, API evaluation or package installation
was run. The existing prospectus acquisition ledger remains 188/212; these five
additional literature/code fetches are recorded separately (193 combined if
using the same overall request ceiling).

## Document structure: Docling addresses a missing layer, not legal interpretation

Auer et al., *Docling Technical Report*, arXiv:2408.09869v5, 9 December 2024,
§§3.1–3.4, §4 and the output appendix.
[PDF](literature/docling.pdf), [text](literature/docling.txt),
[public source](https://arxiv.org/abs/2408.09869).

Section 3 describes extraction of tokens and geometry, page rendering, layout
and table recognition, and document assembly. The layout model's regions are
matched with text cells; the assembled document distinguishes paragraphs,
lists, headings, tables and other elements. Postprocessing supplies reading
order and relations such as figure/caption matching. OCR is optional. These
are precisely the kinds of intermediate representation absent when our code
passes printed lines directly to sentence regexes.

The evaluation has a narrower scope than the introduction's quality language.
Section 4 measures runtime and memory on 225 pages comprising three arXiv papers
and two IBM Redbooks, with OCR disabled. It does not establish accuracy on
German marginal instructions, bilingual bond terms or our scanned documents.
The output appendix illustrates structure rather than providing a prospectus
acceptance benchmark. Do not transfer its throughput or quality claims to our
application without measurements.

Official code inspected at commit
`570f956792fcfe8e51bde0f4a79a2ddabc1a061a`:
[readingorder_model.py](literature/docling-readingorder.py), particularly
lines 657–688 and 693–763. It groups container siblings, predicts their order,
links captions/footnotes and predicts merges. Its merge path creates provenance
character ranges, then may remove a hyphen; it also records explicit TODOs about
incomplete original-text preservation. The inspected code is a later source
snapshot, not asserted to be the implementation used in the 2024 measurements.
Its structures are useful; their source mappings still need local validation.

The retained full-page OCR example and document model were also inspected under
`.localresources/assurance-tools-review/`. They show how OCR and structured
documents can be selected explicitly. Existing ResearchAssistant tools are
adequate for a first controlled comparison. Installing another OCR backend
without paragraph/reading-order checks would leave the main defect intact.

**Decision:** make a geometry-preserving adapter, initially using existing
extraction with reviewed structure. Evaluate a pinned Docling path as an optional
candidate on the same real pages. Compare source order, boundaries, tables and
downstream answers, not text volume alone. Preserve raw source and independent
character maps rather than relying solely on exported Markdown.

## Incremental execution: Build Systems à la Carte

Mokhov, Mitchell and Peyton Jones (2018), *Build Systems à la Carte*,
Proceedings of the ACM on Programming Languages 2(ICFP), article 79,
DOI [10.1145/3236774](https://doi.org/10.1145/3236774).
[PDF](literature/build-systems.pdf), [text](literature/build-systems.txt).

Definition 3.1 (§3.6) defines correctness by unchanged inputs and results equal
to recomputation against the resulting store, under an acyclic task description.
Section 3.7 separates static dependency extraction from tracking dynamic reads.
Section 4.2.2 records the hashes of results and actual dependencies as verifying
traces. Sections 4.3 and 5 separate scheduling from deciding whether to rebuild.

These distinctions explain why a phase DAG plus a global method hash is
insufficient. P6 must consume the P3/P4/P5 products it purports to integrate.
Its old UBS bank request, rule implementation, interpreter/tool choices and
source-derived inputs also need binding. A result may be fresh but still fail
semantic acceptance; the build model does not confer legal acceptance.

Sections 6.3–6.5 are essential qualifications. Untracked dependencies,
nondeterminism and volatility change the correctness assumptions. Section 6.4's
“Frankenbuild” example shows inconsistent products when nondeterministic results
are reused through overly shallow input traces. Section 6.5 treats a task's own
definition as a dependency; a general-purpose language makes exact function
identity difficult. Section 6.6 bounds iterative steps rather than assuming
unlimited reruns converge.

The paper's official executable models are retained from
[Hackage build-1.0](https://hackage.haskell.org/package/build-1.0):
[archive](literature/build-1.0.tar.gz).
Selected code inspection covered
[Trace.hs](literature/build-models/src/Build/Trace.hs:42),
[Rebuilder.hs](literature/build-models/src/Build/Rebuilder.hs:96),
Scheduler, Task, and test correctness checks. The verifying trace compares both
the result hash and dependency hashes; the rebuilder tracks reads on execution.
The Haskell package was inspected, not compiled or tested here. No claim is made
that our Python controller inherits its correctness automatically.

**Decision:** use the scheduler/rebuilder distinction, actual dependency
bindings, immutable input snapshots and versioned task/tool identities. Keep
semantic acceptance and repair obligations separate. The local reference proof
uses a smaller static pure DAG; production dynamic reads need an explicit
capability or tracking mechanism.

## Legal extraction: ContractNLI and SARA localize different errors

Koreeda and Manning's *ContractNLI* (2021), §§2–5 and Appendix A.1/A.1.1, treats
evidence as complete governing context, including discontinuous spans and
distant exceptions. Its oracle-evidence comparison suggests the right
experiment for us: compare inference on reviewed evidence with inference on
automatic extraction. The study concerns 607 NDAs and 17 hypotheses, and its
preprocessing excludes scanned and multicolumn PDFs. It neither validates our
page types nor justifies treating “not mentioned” as contractual absence.
No model adoption is proposed; official model implementation must be inspected
before any later adoption.

Holzenberger and Van Durme's *Connecting Symbolic Statutory Reasoning with Legal
Information Extraction* (2023), §§3–5, Algorithms 1–2 and Appendices A–F,
makes spans and event/argument relations explicit before a supplied Prolog
statute program executes them. Retained official extraction and grounding code
was inspected in the earlier review. The ontology's restrictions and its
empty-knowledge-base control show how missing extraction can coexist with
apparently successful answers under closed-world assumptions. Its date-filling
defaults and tax-task ontology cannot be transferred unexamined.

**Decision:** occurrence-addressed evidence groups and typed actor/event/amount/date
relations; separate extraction, translation and execution tests. Do not train a
prospectus reader on convenient inherited settings or equate retrieval accuracy
with correct downstream legal answers.

## Legal rules: LegalRuleML, ASPIC and Catala solve specified subproblems

Athan et al., *Legal Interpretations in LegalRuleML* (2014), §§3–4,
equations (1)–(6), separates source text, interpretations, formal rules and
contexts. Its Italian benefit example represents alternative readings of a
temporal condition and an authoritative choice between them. This supports
explicit BASF/BES alternatives and source-backed overrides; it does not discover
the correct source set or adjudicate a dispute.

Prakken's structured argumentation framework (2010), §3, §6 and the appendix,
distinguishes attacks on premises, inferences and conclusions. Preferences
affect defeat and require justification. The retained correction resource and
related PyArg implementation were inspected previously. These results do not
justify inventing priority from text proximity or model confidence, nor claiming
a universal consistency theorem for our code.

Merigoux, Chataing and Protzenko's *Catala: A Programming Language for the Law*
(2021), default calculus and compilation sections, especially §4.1 and §4.5,
makes exceptions/defaults executable. Zero, one and multiple applicable
exceptions are distinct cases; the compiler checks structural constraints.
Its formal translation result concerns the defined calculus and translation,
not the completeness of natural-language premises or every line of the full
implementation. Retained official condition and F* translation excerpts were
inspected in the prior review.

**Decision:** first implement reviewed predicates and explicit priority/conflict
rules using the existing partial-information evaluator. A missing fact remains
unknown. Reuse qualified RuleIR/Catala/Lean paths for formal consequences when
the translation is fixed. A general argumentation engine or whole LegalRuleML
XML adoption is unnecessary for the first slice. No formal backend can correct
P4 silently ignoring a declared court-order condition.

## Financial conventions: date theory and QuantLib expose hidden choices

Monat, Fromherz and Merigoux (2024), *Formalizing Date Arithmetic and Statically
Detecting Ambiguities for the Law*, §2/Figures 2–3, §3.2, §4.3 and §§5.2–5.3,
separates duration addition from rounding invalid dates. Sequential month
addition can differ from adding the combined period. The static analysis finds
rounding-sensitive calculations; it does not select the legally correct
rounding rule or supply current local calendars. The retained reading includes
its implementation/analysis limitations, including approximate counterexample
hints and manual work for missing interscope analysis.

The new [QuantLib v1.38 schedule.cpp](literature/quantlib-schedule.cpp)
is an official implementation comparator, not an academic proof.
Inspected constructors and schedule-adjustment code distinguish generation
direction, stubs, end-of-month behavior, calendars, regularity and business-day
conventions. Lines 97–114 also infer a missing effective date using global
evaluationDate in one constructor path. Lines 592–634 supply convenience
defaults such as Following when a calendar is present, and default the
termination convention to the regular convention.

Those defaults are unacceptable substitutes for contractual evidence.
The source demonstrates why schedule construction requires explicit parameters.
Only schedule code was audited here; day-count engines, holiday datasets,
settlement functions and the full test suite were not audited or executed.

**Decision:** keep exact local kernels for verified subcalculations, validate
schemas/units/identities, and specify all contractual date/rounding choices.
Use pinned QuantLib calculations as optional differential checks after those
choices and the relevant implementation have been reviewed. Agreement between
libraries is not independent validation when they share the same wrong premise.

## Formalization still needs a translation check

The earlier review of Wang et al., *Know Your Limits* (2026, retained arXiv v2),
§§3–5 and Appendix A, distinguishes formal translation from solver execution.
It also records unreconciled dataset counts and manual corrections in the paper.
Its reported rankings should not set adoption thresholds. The useful lesson is
to inspect assumptions and execute the formal program, then assess separately
whether it answers the intended question. No new model/API work is required.

## Result of the survey

Existing work supplies credible components for layout, evidence extraction,
exceptions, temporal rules, exact arithmetic and dependable incremental
execution. No inspected source supplies a complete, validated prospectus engine.
The concrete proposal combines those components around a reviewed selected
contract, with separate evidence for extraction, legal translation, calculation
and integration. The [proofs](PROOFS.md) concern that explicit representation.
The [repair program](../../plans/prospectus-phase-repair-2026-10-06.md) specifies
the real-document and independent evaluation still needed.
