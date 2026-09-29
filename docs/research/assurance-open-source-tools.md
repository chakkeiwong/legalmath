# Open-source components for diverse interpretation assurance

25 September 2026. This is a capability and source inspection for the
[diverse-assurance design](diverse-interpretation-assurance.md), not an installation
or evaluation result. Official documentation and selected code were inspected;
retrieved copies are in `.localresources/assurance-tools-review/`. No new tool was
installed, no model service was called and the Catala worktree was not changed.

## Recommendation

Use open-source components to supply distinct checking mechanisms. The next
increment should prioritize Docling for a visual/document route, Inspect AI for
external evaluation, one argumentation or answer-set adapter, and PIT for Java
fault challenges. cvc5 can add solver diversity to the existing Z3 route. KeY and
MAPIE address later, more specific proof and calibration questions.

Selection is based on the concrete failure a component could detect, availability
of inspectable source and interfaces, compatibility with a bounded adapter, and
the additional integration work. Repository activity and an available feature do
not establish accuracy on SFC documents. No performance ranking is inferred here.

## Components and acceptance cases

| Tool | What its official material establishes | Proposed LegalMath use | First acceptance case |
| --- | --- | --- | --- |
| [Docling](https://github.com/docling-project/docling), optionally with a separately configured [Tesseract](https://github.com/tesseract-ocr/tesseract) route | PDF layout, tables, OCR and structured document representation; page/bounding-box and provenance information where available. Tesseract provides OCR with structured outputs such as hOCR and TSV. | Compare the existing text extraction against a page-linked inventory of paragraphs, tables, pictures and qualifications. Retain structured JSON and page regions, not only Markdown. | A scanned exception and a table footnote must enter the inventory or produce an explicit unresolved region. Check every retained page. |
| [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai) | Multiple model providers, multi-model evaluations, extensible tasks/scorers and evaluation records. Inspected `ModelAPI`, model-selection documentation and the custom `Scorer` protocol. | Run the same frozen source families through single-reader, same-method repeated-reader and diversified-method arms. Use our legal/reference and execution scorers. | Confirm no hidden reference reaches a proposing model; missing outputs remain missing; a shared wrong answer is scored as an error rather than rewarded for agreement. |
| [TweetyProject](https://github.com/TweetyProjectTeam/TweetyProject) | Java libraries for ASPIC structured arguments and abstract argumentation; an ASPIC reasoner constructs a Dung graph and delegates to an extension reasoner. | Add a separately implemented argumentation check and selected broader semantics, aligned to our premise/attack/preference contract. | Mutual defeat, strict-versus-defeasible attacks, cycles, empty/incomplete extensions and alternative arguments for one conclusion must preserve the intended status. See the query distinction below. |
| [s(CASP), SWI-Prolog port](https://github.com/SWI-Prolog/sCASP) | Constraint answer-set reasoning with models and justification trees. `scasp/2` exposes both programmatically; a supplied local HTTP example returns HTML/JSON. | Independently encode a bounded rule/exception fragment and retain its alternative answers and explanation trees beside RuleIR candidates. | An explicit exception, an unknown fact and two compatible alternative models must not be collapsed into a single unconditional conclusion. |
| [clingo](https://github.com/potassco/clingo) | Grounding and answer-set solving for logic programs. | An alternative to s(CASP) for finite argument/constraint problems, including enumerating admissible interpretations under a declared encoding. | Retain every required model within the bound; zero models and incomplete enumeration cannot imply skeptical acceptance. Finite grounding limits must be explicit. |
| [cvc5](https://github.com/cvc5/cvc5) | SMT solving with Python and Java APIs; inspected Python term/solver example and source licence. | Cross-check supported symbolic obligations with the existing Z3 implementation and replay concrete disagreements. | A satisfiable difference produces a replayable witness; timeout/unsupported/unknown is never treated as equivalence. Separate solver diversity from any shared encoding. |
| [PIT](https://github.com/hcoles/pitest) | Java/JVM mutation testing, including conditional-boundary and conditional-negation mutations documented in its mutator guide. | Challenge the generated Java/runtime and host tests with deliberate implementation faults. | A changed threshold or negated branch must cause a relevant test failure. Preserve surviving/equivalent/unsupported mutant distinctions. Source-level legal omissions require separate mutations. |
| [KeY](https://github.com/KeYProject/key) | Deductive verification of Java against JML specifications; standalone tool and library uses including symbolic execution. | Prove selected high-value Java properties once the intended semantics and supported Java fragment are fixed. | Prove a scoped property, then ensure a deliberately wrong implementation leaves an unclosed obligation. A completed tool invocation is not a closed proof. |
| [MAPIE](https://github.com/scikit-learn-contrib/MAPIE) | Conformal prediction sets/intervals and risk-control methods; inspected `SplitConformalClassifier` and its fit/conformalize/predict-set workflow. | Later calibration of explicitly defined interpretation classes or a review-selection score on separate reference data. | Hold out source families; verify labels, calibration separation, set construction and invalidation on method/source-population changes. No data means no calibrated confidence claim. |

Docling itself can use Tesseract. Running Tesseract directly and through Docling
does not make them two independent OCR models. Record backend and model identities
and compare distinct routes deliberately. Similarly, s(CASP), clingo and Tweety
only reason over the supplied formal statements; they do not discover that an
English definition was omitted unless the surrounding source/interpretation
process raises that issue.

## What the interfaces let us borrow

Docling's `DoclingDocument` separates text, tables, pictures, document structure
and furniture, and retains provenance/layout information when available. That is
a better fit for a source-region comparison than flattening the document into
Markdown. Its inspected full-page OCR example enables OCR and table extraction
with cell matching. The example deliberately limits pages under CI, so its
example configuration must not become our whole-document completeness policy.
This is an example-scope issue, not evidence of a Docling defect.

Inspect's scorer receives a task state and target and returns a score record. We
can use that interface for exact source-support dispositions, material omission
labels and Java witness checks. A generic model-graded scorer is an additional
diagnostic, not the legal reference. Its provider retry/concurrency behavior also
needs an adapter to preserve our counted calls, frozen inputs and bounded retries.
An evaluation framework does not establish independence among the models it runs.

s(CASP) exposes models and justification trees without requiring us to scrape
explanatory prose. The integration should generate an allowlisted formal fragment,
run it in a bounded process, parse all required results and map explicit unknown,
conflict and applicability states. Unrestricted model-produced Prolog is not an
acceptable adapter: the port permits calls to Prolog, and its ordinary negation
semantics must not silently replace our missing-evidence policy.

PIT supplies useful bytecode fault generation, while existing Hypothesis tests
and local semantic mutations already cover parts of the challenge strategy.
PIT cannot know whether a circular's exception is absent from every reference
implementation. We still need source-level mutations and scenarios constructed
without seeing the candidate formula. Generic mutation score is an explanatory
diagnostic; the required material-fault challenges are the acceptance conditions.

## A concrete reason to audit a library's semantics

The inspected Tweety `AbstractAspicReasoner.query` loops over arguments with the
requested conclusion and returns true when an individual argument is accepted
under the chosen inference mode. That interface is not automatically the same as
the monograph's conclusion-level skeptical acceptance.

Suppose the complete extension set is `[{a}, {b}]` and both arguments conclude
`p`. Every extension contains an argument for `p`, but no single argument occurs
in every extension. The desired conclusion-level test is therefore true, while
testing whether some one argument for `p` is skeptically accepted is false.
Formally, `for every extension E, there exists a in E concluding p` and `there
exists an argument a concluding p in every E` differ by quantifier order.

The source inspected is
[`AbstractAspicReasoner.java`](https://github.com/TweetyProjectTeam/TweetyProject/blob/main/org-tweetyproject-arg-aspic/src/main/java/org/tweetyproject/arg/aspic/reasoner/AbstractAspicReasoner.java).
This is a source-level adapter finding; the library was not executed. Use explicit
extension results to compute the desired conclusion semantics, with nonempty-set
and complete-enumeration guards. Verify the example in a real adapter acceptance
test before relying on it. The finding motivates a precise wrapper rather than
rejecting the library or assuming a familiar method name supplies our contract.

## Licensing and deployment facts inspected

The official materials inspected identify Docling and Inspect as MIT, Tesseract
and the SWI-Prolog s(CASP) port as Apache-2.0, clingo as MIT, PIT as Apache-2.0,
and MAPIE as BSD-3-Clause. cvc5's `COPYING` uses the modified three-clause BSD
licence and documents dependency/build variations. Docling explicitly separates
its code licence from the licences of the models used.

Tweety's README and the inspected ASPIC source headers state LGPLv3; the repository
API reports GPL-3.0 for the root. Pin and inspect the actual modules and bundled
dependencies before selecting distribution terms. KeY's README states GPLv2.
These are reported source declarations, not a legal clearance opinion. They are
relevant to selecting a validation service versus redistributing library code.

All eight repositories for which activity metadata was retrieved were non-archived.
The reported push dates ranged from June 2025 for the SWI s(CASP) port to September
2026 for several other tools. That is evidence of repository status only, not a
maintenance guarantee, security audit or recommendation to install a moving head.
Toolchains, dependencies and model weights need pinned versions in any prototype.

## What should remain our responsibility

LegalMath must supply the source-to-claim/fact/argument mappings, supported
semantics, dependency graph, required checks, discrepancy dispositions and release
conditions. Every adapter should return at least its claim and source identities,
input assumptions, method/version, evidence, support/contradiction/unresolved
status, supported fragment, shared dependencies and completion/limit status.
The deterministic controller then decides which evidence action to run next.

[LangGraph](https://github.com/langchain-ai/langgraph) provides stateful workflow
and durable-execution mechanisms if orchestration becomes a bottleneck. Its
framework is open source; associated hosted offerings are separate. We already
have queues, journals, counted retries and resume behavior, so replacing that
machinery is not the first error-reduction priority. It would also not provide
legal resolution rules or the reference corpus.

The existing Catala branch contributes a distinct execution route for its reviewed
fragment. It should enter the same adapter contract without counting shared input
preparation as independent evidence. The current Z3, Hypothesis, Java conformance
and retained source/case work should likewise be reused.

## Proposed adoption sequence

1. Define the common evidence-result contract and required-check policy; add
   adversarial fixtures in which all initial readers share a wrong interpretation.
2. Add Docling/visual reconciliation and an Inspect wrapper around retained
   source-family evaluations, keeping the existing allowance and reference rules.
3. Compare Tweety against the small local argument solver. Add s(CASP) or clingo
   for a separately encoded bounded rule fragment when the target clause benefits
   from alternative-model reasoning.
4. Extend Java challenges with PIT and symbolic checks with cvc5; integrate the
   reviewed Catala pilot through its own branch owner and combined regression.
5. Add specific KeY obligations and, after a suitable corpus exists, MAPIE-based
   calibration. Their pass criteria must refer to the intended claim, not tool
   completion, agreement count or an unvalidated confidence percentage.

The first prototype should demonstrate a few complementary routes and detected
shared mistakes. It should not install the entire catalogue at once. Each adapter
requires a bounded smoke test, semantic mismatch tests, failure/timeout tests and
fresh evidence before its results can support an assurance claim.
