# Literature and implementation review for prospectus delivery

6 October 2026. The reviewed sources are retained locally. PDF/text hashes are
in [literature/manifest.json](literature/manifest.json). New text for three papers
was extracted through ResearchAssistant's bounded `extract_pdf_text` adapter,
using existing `pdftotext`. No download, package installation, model call or GPU
run was needed. The selected code was inspected, not installed or executed.

The design question is how to preserve the meaning of a selected, amended,
possibly bilingual contract while distinguishing textual features from applicable
law and actual events. None of the papers supplies a complete prospectus engine.
The useful results concern specific transitions in that problem.

## ContractNLI: evidence must preserve context

Koreeda and Manning (2021), *ContractNLI*, §§2.1–2.3, §3, §§4–5, and Appendix
A.1, especially A.1.1; printed pp.1908–1914 and 1917–1918. Local source:
`docs/papers/ContractNLI - A Dataset for Document-level Natural Language Inference for Contracts, Koreeda(2021).pdf`.

The task labels a fixed hypothesis as entailed, contradicted or not mentioned
and identifies supporting sentences/list items. The authors require evidence
to be self-contained even when it is discontinuous; a list item may need its
governing paragraph to establish the subject. Their model inserts span markers,
uses overlapping contexts chosen around complete spans and jointly trains
evidence identification and NLI. At prediction time it aggregates context
outputs; it is not a contract compiler.

The study covers 607 NDAs and 17 fixed hypotheses. Section 5.2 distinguishes
local and distant exceptions and definitions. In its annotated diagnostic set,
distant exceptions can occur pages away, and finding one supporting span does
not mean all necessary spans have been found. The oracle-evidence experiment
in §5.1 is useful for isolating retrieval from inference failures. Its numerical
performance is not transferred to prospectuses here.

Appendix A.1 is particularly relevant: the authors excluded PDFs without embedded
text and PDFs with more than one column because preprocessing was difficult.
Their reported task therefore does not validate our scanned BES or bilingual
Deutsche/BASF intake. Appendix A.1.1 also describes how annotations were assembled
and reviewed; this is a real annotation process, not an automatic label oracle.

**Use:** define question-specific evidence groups containing complete governing
context, annotate exceptions separately and compare inference with supplied
reviewed evidence against inference with automatically retrieved evidence.
**Do not infer:** that an NDA model, a span retrieval score or a “not mentioned”
label establishes the absence of a prospectus mechanism or applicable law.
Official model code is not retained in the inspected source set; this review
does not recommend adopting its model implementation. A model adoption phase
must first inspect and pin that code and license.

## SARA information extraction: arguments determine the legal calculation

Holzenberger and Van Durme (2023), *Connecting Symbolic Statutory Reasoning with
Legal Information Extraction*, §§3–5, Algorithms 1–2, Tables 1–3 and Appendices
A–F, with attention to B, D and E; printed pp.115–120 and 125–128. Local text:
`.localresources/legal-interpretation-reuse-2026-10-05/information-extraction.txt`.

The authors replace unanchored event/entity values with structured spans
`span(value,start,end)` and constrain the event/argument ontology. A span parser
predicts event nodes and their argument edges, then a human-curated Prolog
statute program consumes the extracted knowledge base. This explicitly
separates extraction from execution. Their analysis shows why correctly naming
an event is insufficient when its amount, actor or date argument is missing.

The ontology itself restricts what is extractable. Overlapping spans and dates
not directly expressible by the parser are removed from the “partial” dataset;
results on the full dataset are reported separately. The reasoning experiment
includes an empty knowledge-base control, which still answers some cases because
of Prolog's negation-as-failure and supplied statute statements. A high score can
therefore conceal missing information. The paper also reports a case whose
expected answer had been obtained for an incorrect closed-world reason (§3).

Official retained code was inspected at:

- `sources/SgfdDttt__sara-ie/sara/data/dataset/ground_case.py`, especially the
  predicate inventory, consultation of supplied statutes and generation of
  grounded events/arguments (lines 32–91 and 138–178).
- `sources/SgfdDttt__sara-ie/sara/models/ie.py`, the span/tree extraction and
  associated training/inference structure.

Both paths are under `.localresources/legal-interpretation-reuse-2026-10-05/`.
This is task-specific research code, not a drop-in open-world contract reader.
Appendix B's date defaults (first/last day of year, nearest year and fallback)
must not be copied into contractual or statutory time calculations without a
separate source basis. Missing dates in our service remain missing.

**Use:** typed event/actor/amount/date relations anchored to source spans; separate
extraction, semantic and downstream tests; an empty/missing-input baseline to
detect accidental answers. **Reject as a default:** closed-world inference from
failed extraction and transferred date-filling heuristics. Training its model
is not needed for the first delivery slice and would require prospectus-specific
labels, protocol and budget if later proposed.

## LegalRuleML and structured argumentation: preserve competing readings

Athan et al. (2014), *Legal Interpretations in LegalRuleML*, §§3–4,
equations (1)–(6), and the association/context/override representation; local text
`legalruleml-interpretations.txt` in the same retained-literature directory.

The worked Italian benefit dispute separates three interpretations of the
temporal phrase “earned and reported.” The court's choice is an additional
authoritative event. Section 4 represents textual sources, formal rules,
interpretations and contexts separately rather than treating one translation
as the statute itself. We should apply that distinction to BASF's report-range
discrepancy and BES's duplicate 1.17 references: retain the alternatives and
their source context until an authoritative or reviewed interpretation selects
one. The representation does not discover applicable documents or settle the
interpretation automatically. Adopting the whole XML vocabulary is unnecessary
for the current bounded service.

Prakken (2010), *An abstract framework for argumentation with structured
arguments*, §3 definitions of strict/defeasible arguments and premise types,
attack/defeat distinctions, and the stated restrictions on rationality results
in §6 and the appendix, supplies a useful vocabulary for disputes. An attack
on a premise, a competing conclusion and an attack on the inference are different.
Preferences affect defeat; a method must not invent them from text proximity
or model confidence. The retained correction resource was also inspected;
no universal consistency theorem is being asserted for our future implementation.

The retained PyArg implementation was inspected in
`sources/DaphneOdekerken__PyArg/src/py_arg/aspic_classes/argumentation_theory.py`
and `algorithms/semantics/get_grounded_extension.py`. The former makes the
attack/defeat and preference choices executable; the latter obtains the grounded
extension via a least fixed point. These routines require the arguments, attacks
and any ordering as inputs. They do not supply the legal authority for those
inputs. PyArg is a related implementation, not original-author validation of
every theorem in the 2010 paper.

**Use:** explicit alternatives, source-backed priority/override edges and
unresolved disputes. **Defer:** a general argumentation engine. The first
implementation needs a bounded dependency/exception graph with transparent
conflict handling; additional semantics require a concrete case that it cannot
represent and a reviewed mapping to the chosen logic.

## Catala: execute reviewed rules without losing exceptions

Merigoux, Chataing and Protzenko (2021), *Catala: A Programming Language for the
Law*, §§3–4, especially §4.1, §4.4 and §4.5/Figures 11–12, and §6.1. Local text:
[catala.txt](literature/catala.txt).

Catala encodes a static tree of definitions and exceptions. The scope-language
semantics distinguishes no applicable value, one applicable exception and a
conflict between exceptions. Its compiler orders dependencies and rejects
cycles in the supported representation. These are useful execution properties
once a reviewed legal model has been supplied.

The proof in §4.5 concerns translation from a formal default calculus to a
lambda calculus with exceptions. It does not prove that a natural-language
contract was correctly translated. The paper explicitly describes simplifications
in the mechanization and the distinction between the proof implementation and
production compiler. Section 6.1 also argues for lawyers and programmers working
together from the start, because a natural-language specification can leave
material choices unresolved.

Inspected retained official source excerpts:
`.localresources/projects/catala-conditions.ml` (nonempty/conflict verification
conditions, especially lines 136–176 and 230–267) and
`catala-translation.fst` (formal translation and its correctness lemma), with
`catala-formalization.md`. The locally named compiler archive contains these
selected excerpts, not the full current compiler. No new compiler run or proof
reproduction was performed.

**Use:** the existing qualified RuleIR/Catala/Lean paths for formal consequences
and exact numerical invariants. Explicitly encode unknown/conflict before
lowering into any formalism with defaults. **Do not infer:** source meaning or
legal completeness from successful translation, agreement between engines or a
proof over the same supplied premises.

## Date arithmetic: a library default can be a substantive legal choice

Monat, Fromherz and Merigoux (2024), *Formalizing Date Arithmetic and Statically
Detecting Ambiguities for the Law*, §2/Figures 2–3, §3.2's counterexamples,
§4.3's rounding-sensitivity definition and §§5.2–5.3; local text
[date-arithmetic.txt](literature/date-arithmetic.txt).

The paper separates adding a period from rounding an invalid day to a valid
date. Adding months or years can be ambiguous; sequential additions need not
be equivalent to adding the combined period. Its counterexample for March 31
plus one month twice differs from adding two months once. Section 5.2 explains
why choosing a rounding direction requires a legal basis. The analysis detects
computations whose outcomes differ by rounding mode; it does not select the
legally correct mode or supply local business-day calendars and service facts.

**Use:** source-bound counting/rounding conventions, explicit operation order,
calendar coverage and boundary counterexamples. Keep calendar-day subtraction,
business-day movement and contractual accrual periods as distinct operations.
The official standalone date-library code was not available in the inspected
retained excerpts, and no library adoption or equivalence claim is made. Before
replacing any existing date implementation, inspect its pinned implementation
and prove/test the precise required operations. A new package is not needed to
record missing legal conventions correctly.

## Autoformalization: formal validity does not repair a changed question

Wang et al. (2026), *Know Your Limits*, retained arXiv v2 preprint, §3.1–3.2,
§§4–5 and Appendix A.1–A.2; local text `know-your-limits.txt`.

The authors distinguish translation to formal premises from reasoning over those
premises, and compare actual solver execution with model-reported formal answers.
Their workflow and examples illustrate unsupported assumptions, wrong predicate
scope and code-generation failures. These are useful failure categories for a
future model-assisted reader.

This paper needs caution even as a design source. In the inspected version,
§3.1 says 400 examples were reannotated, Table 1's final class totals sum to 500,
and the augmented dataset is said to contain 610 examples. Its limitations also
describe manual corrections to some generated programs. Without reconciled
data/code accounting, its numerical comparisons should not set our thresholds
or rank models. Its stricter logical labels are a different target from ordinary
legal interpretation; neither can replace the other silently.

**Use:** retain all proposed assumptions and interpretations, execute formal
code rather than accepting a model's claim of execution, and test the translation
separately from the solver. **Do not use:** its reported model ranking as an
adoption criterion. No model/API work is proposed for the initial deterministic
delivery baseline. A later optional model must emit constrained candidate data,
not executable code or automatically accepted law.

## Decisions for this project

The design takes the supported representational ideas: complete contextual
evidence, typed relations, source/interpretation separation, explicit exceptions,
dated applicability and downstream evaluation. It does not transfer benchmark
labels, learned weights, date defaults, proof claims or argument preferences.

The smallest discriminating experiment is an end-to-end prospectus slice with
independently reviewed structure and meanings, then the same slice using proposed
automatic extraction. This locates the failed transition. If reviewed inputs
still produce the wrong result, adding a stronger extractor is irrelevant; if
reviewed inputs work but extracted inputs do not, the repair belongs in source
construction or interpretation. The [delivery program](../../plans/prospectus-delivery-program-2026-10-06.md)
makes this distinction explicit in its acceptance tests.
