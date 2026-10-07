# Tools and literature for completing the prospectus engine

7 October 2026. Code baseline: `a05e18bbdeefbf278d29a6755e274124f97bda35`,
`feature/prospectus-evidence-master`.

We should adopt better source accounting, explicit document versions and stronger
invariant tests within the existing engine. We should then run three bounded
trials: Docling for document structure, INCEpTION for annotation and adjudication,
and QuantLib for schedules and day counts. Replacing the legal engine or installing
several new OCR systems would leave the most consequential defects unresolved.

The reason is visible in the BASF repair. The engine could execute the selected
coupon calculation while an intermediate construction wrongly removed its common
reference-period definition. A marginal instruction on printed p112 established
that the definition applied to every Actual/Actual option. More solver power
would not have recovered a premise that construction had deleted. The supplement's
two printed incorporation ranges, 195–209 and 209–290, present a different problem:
both can be transcribed perfectly while their legal relationship remains unresolved.

The [current repair result](../../implementation/prospectus-repair-2026-10-06/RESULT.md)
records 77 BASF operations and 83 unresolved brackets. It also distinguishes
installed-product integration from full construction, interpretation, settlement
and independent acceptance. This survey preserves those distinctions. No new
parser, annotation platform, solver backend or financial library was evaluated on
our prospectuses during the survey.

| Decision | Component or method | Gap it addresses | Local acceptance evidence required |
|---|---|---|---|
| Adopt the design | Web Annotation selectors, Akoma Ntoso document identities, PROV relationships | Ambiguous occurrences, editions, amendments and transformation history | Exact occurrence/edition round trips; explicit unresolved alternatives; justified exclusion and override accounting |
| Reuse installed tools | Z3 and Hypothesis | Correlated choices, finite predicates, controller and financial invariants | Agreement with the enumerating evaluator on a declared Boolean corpus; source-bound counterexamples; mutation and state-sequence checks |
| Adopt the evaluation method | ContractNLI evidence groups, SARA's separation of extraction and execution, DocLayNet split discipline | Missing distant exceptions, hidden defaults, leakage between related documents | Reviewed-evidence versus automatic-evidence arms; issuer/template/amendment-family separation; independent adjudication |
| Trial first | Pinned Docling sidecar alongside retained Poppler/PyMuPDF output | Columns, margins, lists, tables, reading order and text/box alignment | Every designated governing margin, footnote, number, negation and reference survives with correct attachment |
| Trial after occurrence mapping | INCEpTION with an explicit export bridge | Independent labels and review workflow | Lossless evidence-group round trip, blind assignments, recommendations disabled, separate adjudication |
| Trial after conventions are supplied | QuantLib v1.38 comparator | Coupon schedules, stubs, leap years and business-day adjustments | Independently derived dates/fractions and explicit source conventions; exact local monetary rounding retained |
| Borrow concepts; defer migration | ACTUS and FINOS CDM | Financial event/state and transfer representation | A demonstrated missing interoperability requirement, semantic mapping and targeted execution tests |
| Keep external evidence obligations | Primary legal/event sources and qualified independent readers | Actual applicability, exercise, client facts and acceptance | Dated, instrument-bound records and genuine independent readings |

The [adoption program](../../plans/prospectus-adoption-program-2026-10-07.md)
turns these recommendations into ordered implementation and trial obligations.
The [reading ledger](reading-ledger.json), [source manifest](source-manifest.json)
and [environment inventory](environment.json) preserve the supporting material.

## Preserve the selected contract before extending its reasoning

The current [occurrence binder](../../../src/legalmath/prospectus/successor/anchors.py)
already requires a source hash, document, unit, start/end positions and an exact
quote. That is a sound starting point. The missing part is complete accounting
for why source occurrences survive, are excluded, are replaced, or remain
unresolved in a particular construction. In
[construction_ast.py](../../../src/legalmath/prospectus/successor/construction_ast.py),
the renderer follows only the selected branch and records exclusions by option
name. Coverage is accumulated mainly by visited Text nodes and Field templates.
An excluded or overridden occurrence can therefore remain unaccounted for; a
shared definition also needs a disposition that respects all of its uses.

The W3C [Web Annotation Data Model](sources/web-annotation/source.html), §§4.2.4–4.2.5
and §4.3, supplies complementary text-quote and position selectors and a way to
identify a representation's state. Use these ideas in our existing JSON format:
keep the immutable source edition, half-open character interval, quote and
surrounding context, plus page geometry and the relevant construction operation.
Do not silently replace the current exact binder with a generic annotation match.
The standard permits normalized text and recommends treating multiple quote
matches as multiple matches. A legal occurrence must remain ambiguous until its
particular location is established. Normalized display text needs a separate map
back to raw text.

There is a concrete interoperability trap. Web Annotation counts Unicode code
points; INCEpTION's TSV format counts UTF-16 code units. A supplementary-plane
character occupies one position in Python strings and two units in that TSV
format. The adapter must explicitly convert offsets, reject boundaries inside a
surrogate pair, and check the recovered quote. Combining characters, line endings,
hyphenation and duplicate clauses need separate tests. A common string is not an
occurrence identifier.

[Akoma Ntoso 1.0](sources/akoma-ntoso/source.html), §4.1.3 and §5.7, separates the
legal work, its expression or version, its physical/electronic manifestation and
an individual copy. It also represents amendment events, validity and efficacy.
Those distinctions fit our need to identify a prospectus, its language/version,
the PDF bytes and subsequent supplements without conflating them. Adopt the
identity and amendment concepts, with explicit governing-language and precedence
premises; retain the current JSON rather than introducing an XML database.
Akoma Ntoso assumes identifiable dated amendment events. Where their date or
effect is disputed, preserve the dispute. It does not determine which BASF range
is legally operative or supply our separate knowledge and observation times.

[PROV-DM](sources/prov-dm/source.html), §§2.1 and 5.1–5.3, distinguishes entities,
activities, agents, usage, generation and derivation. These names clarify the
relation between source bytes, OCR, a corrected transcription, a construction
decision and its reviewer. Its own discussion cautions that use and generation
alone do not establish derivation. Our logs must record the actual transformation
and source intervals. An attribution record is also not authentication of a
reviewer's identity. Full RDF/PROV serialization can wait for an exchange need.

The engineering condition is precise: within the admitted question and document
scope, every relevant raw occurrence must have a compatible terminal disposition
or remain explicitly unresolved. Every emitted character must be copied from a
bound occurrence or attributed to a declared transformation, field value or
separator. Excluding one branch must not exclude a definition shared by another.
This condition detects missing accounting; it does not establish that the
admitted scope or a supplied legal exclusion is correct.

## Document tools: test the features that have actually failed

The existing OCR installation is sufficient to start. The application venv
contains Hypothesis 6.151.9 and Z3 4.16.0.0; the pinned OCR interpreter contains
PyMuPDF 1.27.2.2 and ResearchAssistant 0.1.0. They are different Python environments
even though their executable symlinks resolve to the same base Python. The four
retained OCR outputs still match their admitted hashes. Their English
`eng.traineddata` is retained. Absence of a standalone `tesseract` executable
does not negate the existing embedded OCR results. It also does not establish
accuracy on Portuguese or German text: the current retained OCR profile accepts
only the recorded 300-dpi English configuration.

The [previous Docling technical/code review](../../implementation/prospectus-phase-roots-2026-10-06/LITERATURE-REVIEW.md)
supports an isolated structure-preserving trial. Its report, arXiv:2408.09869v5,
§§3–4 and the output appendix, describes token geometry, layout regions, reading
order and assembly. The inspected implementation at commit `570f956792fcfe8e51bde0f4a79a2ddabc1a061a`
also has merge/dehyphenation paths whose original-text mappings need checking.
The report's 225-page timing evaluation used arXiv papers and IBM Redbooks with
OCR off. It is not a prospectus accuracy result.

Keep the baseline's raw words and boxes, and add paragraph, language, column,
list/table and margin-attachment relations as a separate layer. Export that layer
into [source_graph.py](../../../src/legalmath/prospectus/successor/source_graph.py),
then compare the same clause graph and questions with either baseline or candidate
structure. Do not feed only exported Markdown into the legal engine. The first
trial should include BASF p112 and supplement p12; Deutsche's bilingual terms;
the four retained BES extractions; and the BBVA/SEB financial-profile pages.
Review the evidence groups before comparing candidate outputs.

Two new benchmark readings explain how to evaluate this trial. Pfitzmann et al.'s
[DocLayNet](sources/doclaynet/source.pdf), §§3–5, uses 80,863 pages and eleven layout
classes, with redundant annotation on part of the corpus. Financial reports and
laws/regulations are included, but the corpus is predominantly English and avoids
scans where possible. Its document-level split experiment found that a naive
page split inflated the authors' layout results by roughly ten mAP points.
The [official dataset documentation](sources/doclaynet-readme/source.md) also
distinguishes image-coordinate annotations from PDF-derived text-cell coordinates.
Borrow the split and annotation discipline. Add governing-margin and clause-scope
relations, which are not supplied by the layout labels.

[OmniDocBench](sources/omnidocbench/source.pdf), §§3–5 and supplementary §V,
separates text, tables, formulas and reading order, using normalization and fuzzy
matching to compare heterogeneous outputs. The retained manuscript describes
981 pages; later dataset versions must be treated separately. Crucially, its
ignore handling excludes headers, footers, page numbers, page footnotes and
captions from specified metrics. The inspected
[official matching code](sources/omnidocbench-matching/source.py), commit
`f133a71e9e91c3621c7ce8994200a7b394a06eb3`, filters these categories too.
That is a reasonable benchmark scope but an unsafe acceptance rule for BASF.
Borrow the decomposition and matching diagnostics, while checking legally
governing margins, footnotes, repeated punctuation and references explicitly.
Aggregate edit distance remains explanatory; it cannot excuse one lost exception.

MinerU and olmOCR remain alternatives to screen if the first trial fails on a
named layout family. Their current official READMEs were inspected, not their
technical papers or inference implementations. [MinerU's README](sources/mineru-readme/source.md)
describes CPU/accelerated paths, a document-library parse default of ten pages,
and an Apache-based license with additional conditions. A future adapter must
consume continuation locators and check total page coverage. [olmOCR's README](sources/olmocr-readme/source.md)
describes a 7B VLM, local GPU requirements and past corrections to blank-page
hallucinations and rotation. Neither has local accuracy evidence here. Marker,
PaddleOCR, OCRmyPDF and GROBID were not technically audited in this extension;
there is no basis to claim that they outperform the current path. ResearchAssistant
can continue acquiring and parsing literature without making them production
dependencies.

## Rules, law and evidence require different checks

The current [predicate evaluator](../../../src/legalmath/prospectus/successor/predicates.py)
enumerates completions over at most twelve Boolean facts. Z3 is already a pinned
dependency. It can support larger correlated choice constraints and give concrete
satisfying assignments or contradictory named constraints. That is a focused
extension; it does not require replacing RuleIR, Catala or the legal service.

The proposed Boolean adapter has a small, checkable argument. Let C contain the
admitted observations and choice constraints and let q be the translated query.
Handle explicitly conflicting observations before simplifying q, as the existing
evaluator does. If C is unsatisfiable, report a conflict or reject an invalid
construction admission; never obtain a vacuous YES. Otherwise, q holds in all
admissible worlds exactly when C AND NOT q is unsatisfiable, and fails in all
worlds exactly when C AND q is unsatisfiable. Satisfiability of both yields UNKNOWN
with two witnesses. This follows directly by taking the satisfying assignments
as the admissible worlds. Translation of Boolean constants, fact names, negation,
conjunction and disjunction must preserve their truth tables recursively.

This argument concerns the encoded finite Boolean problem. It supplies neither a
legal interpretation nor a proof of our future adapter. Any required solver call
returning `unknown` or timing out must preserve an unresolved result with the
computational reason. The [official Z3 guide](sources/z3-guide/source.html) and
the retained installed API source document these outcomes. The existing enumerator
is the comparator on its supported domain; unconstrained inputs must retain its
YES/NO/UNKNOWN/CONFLICT behavior. A satisfying model is not an actual event, and
an unsat core is not automatically minimal.

The prior [ContractNLI/SARA review](../../implementation/prospectus-root-cause-2026-10-06/LITERATURE-REVIEW.md)
remains directly useful. ContractNLI (Koreeda and Manning, 2021, §§2–5 and
Appendix A.1) requires self-contained evidence, including distant and discontinuous
exceptions. Its reviewed-evidence comparison separates retrieval from inference.
Its 607 NDAs and seventeen hypotheses, with scanned/multicolumn PDFs excluded,
do not validate a bond classifier. SARA information extraction (Holzenberger and
Van Durme, 2023, §§3–5, Algorithms 1–2 and Appendices A–F) supplies typed
event/argument spans before an explicit statute program executes. Its empty-input
control and date defaults warn against obtaining answers from missing facts.

Adopt evidence groups containing the governing clause, definition, condition,
exception, amendment and applicable priority source. Compare execution on reviewed
groups with execution on automatically assembled groups, using the same inference
method and facts. If both arms fail, investigate translation or reasoning. If only
automatic input fails, investigate extraction and reference closure. Do not
convert ContractNLI's “not mentioned” label into proof of contractual absence.

Catala, LegalRuleML and structured argumentation remain useful within those
boundaries. The retained Catala paper's compilation argument concerns an explicitly
defined calculus, not the translation from a prospectus. LegalRuleML represents
alternative interpretations and their contexts. Prakken's argumentation framework
distinguishes attacks on premises, conclusions and inferences, with justified
preferences affecting defeat. None authorizes priority based on proximity, model
confidence or an unexplained “later text wins” rule. Preserve unresolved priority
and cycles explicitly; use the existing formal backends only after translation.

[law_facts.py](../../../src/legalmath/prospectus/successor/law_facts.py) already
separates effective, knowledge and observation dates. Its results still say actual
exercise is not established. Akoma Ntoso identities can improve the legal-source
registry, but actual closure requires the applicable statute and commencement or
transitional provision, regulator order, operative judgment and any appeal/stay,
issuer notice, and entity/security identifiers. The 25 hypothetical law scenarios
remain development tests. An open-ended validity interval cannot certify current
law. A jurisdiction adapter should record the authority, edition and known
publication history, then leave missing applicability or event facts UNKNOWN.

## Financial tools are comparators, not missing contractual premises

QuantLib is the most useful first financial trial. The earlier schedule review
found convenience defaults for evaluation dates, business-day conventions and
termination conventions. This extension inspected v1.38
[ActualActual](sources/quantlib-daycount/source.cpp),
[day-counter tests](sources/quantlib-daycount-tests/source.cpp) and the
[TARGET calendar](sources/quantlib-calendar/source.cpp).
The implementation distinguishes schedule-based ISMA/ICMA from an older path
that estimates reference periods when they are absent. The tests cover short/long
coupons and also show that ISDA, ISMA and AFB can give different fractions for the
same dates. The calendar implements specific holidays; it is not a live source
of every local or exceptional closure.

Require the schedule generation rule, first/last stub, end-of-month rule, holiday
calendar edition, adjustment conventions, accrual basis and reference periods
before calling the comparator. Check actual payment dates and source-derived
fractions, then compare exact rounded amounts with the local kernels. A missing
reference period must prompt an unresolved convention, not trigger the older
fallback. Full settlement additionally needs entitlement/record and ex-coupon
rules, event ordering, notices, currency/FX basis, taxation where in scope,
holder aggregation, and a complete cash/security transfer trace. None is supplied
merely by a matching year fraction. Only the schedule/day-count/calendar slice
has received source inspection here; QuantLib's full settlement machinery has not.

The [ACTUS specification](sources/actus-spec/source.pdf), retained v1.1,
§§2.4–2.10, §3, §§4–6 and §7.1's principal-at-maturity tables, makes useful
distinctions between contract terms, changing state, scheduled/unscheduled events,
payoff functions and state transitions. Equal-time event ordering matters.
Borrow this separation for an explicit financial event trace. Its conventions
also require care: the specification has no timezone support, supplies a
NoHoliday default, and obtains external events/risk factors through observer
interfaces. These are inputs, not discovered legal facts.

Defer adopting the ACTUS runtime. The retained
[service build](sources/actus-service-build/source.txt) requires Java 17 and
`actus-core:1.1.0`, while its [README](sources/actus-service-readme-fixed/source.md)
contains older webapp instructions and says to request an access token for the
core. The core itself was not audited or executed. Its
[custom license](sources/actus-core-terms/source.md), particularly §§2.3–2.5,
also contains conformance, attribution and distribution terms distinct from the
specification's CC BY-SA license. Runtime access, the intended use and the exact
version need resolution before integration; the public wrapper is insufficient.

FINOS CDM supplies an exchange model rather than a prospectus reader. The retained
[settlement types](sources/cdm-settlement/source.txt) require asset, quantity,
units, payer/receiver and settlement date, with explicit cash/physical choices.
Its [bond execution example](sources/cdm-bond-input/source.json) includes delivery
versus payment, security identity, counterparties and clean-price/accrued-interest
components. These are useful mapping requirements. The example supplies the
accrued component; it does not derive our selected bond's legal entitlement.
Defer a complete CDM adapter until a bank/system needs that exchange format.
No Rosetta runtime, full event calculus or round-trip implementation was tested.

## Test changing evidence and obtain independent readings

Hypothesis is already installed and pinned. Its
[stateful testing documentation](sources/hypothesis-stateful/source.html) and
retained implementation support sequences of actions against a simpler model,
with invariants checked between steps. Use it for construct–amend–withdraw–query
sequences and execute–mutate–interrupt–recover–replay sequences. Predeclared
mutations should include a lost margin, moved negation, repeated occurrence,
wrong source edition, changed required legal premise, identical holder names with
different identities, changed language data, corrupt product and relevant or
irrelevant input change. Store the minimized failures as permanent examples.
Generated tests cannot expose a legal obligation omitted from both models.

The retained CUTECat paper (Goutagny et al., 2025, §§2–5) adds branch-directed
concolic testing and exception-order reduction. Its larger example generated
186,390 cases in 6h37m. Borrow the mutation and branch-coverage ideas now; defer
its separate execution image until a concrete Catala path needs it. The existing
reading inspected the official artifact README/license, not the complete runtime.
The [earlier broader survey](../../papers/reading-notes.md) also covers Stipula,
eFLINT, Symboleo and ContractCheck. They offer useful lifecycle or consistency
models but have different semantic domains and bounds. Nothing inspected justifies
migrating the prospectus service wholesale.

Build Systems à la Carte (Mokhov, Mitchell and Peyton Jones, 2018, §§3–6) supplies
the controller design: separate scheduling from the decision to rebuild and bind
actual dependencies, task definitions and results. The
[previous technical and official-code review](../../implementation/prospectus-phase-roots-2026-10-06/LITERATURE-REVIEW.md)
includes the paper's hidden-read and nondeterminism qualifications.
[controller.bindings](../../../src/legalmath/prospectus/successor/controller.py)
currently hashes broad source and environment sets. That is conservative for
declared dependencies, but it neither proves absence of hidden reads nor avoids
unnecessary invalidation. Add an explicit read capability and immutable phase
inputs; test filesystem, environment, subprocess and clock inputs separately.
A Python wrapper alone cannot establish that native tools have no hidden reads.
Use process isolation or retain that limitation before claiming hermetic execution.

[INCEpTION](sources/inception-paper/source.pdf) (Klie et al., 2018, §§2–4) supports
typed annotation, relations, curation and annotation assistance. The retained
[v38 user guide](sources/inception-curation/source.html), curation section,
Appendix A and Appendix D, adds material integration constraints. Anonymized
curation hides names from curators but not managers and does not randomize the
order. Discontinuous spans have no immediate native support; the guide suggests
linking separate annotations. TSV is UTF-8 text with UTF-16 offsets. The inspected
[TSV adapter](sources/inception-tsv/source.txt) even marks the format as prone to
inconsistencies. Its code snapshot is a later 43.0-SNAPSHOT, not the v38 guide's
release. Pin a matched release, documentation and export format before a trial.
The v38 guide says Java 11 or higher; this is not evidence that every later
release runs on our Java 11 installation.

Use separate read-only source packets and reviewer assignments. Disable
recommendations, shared model explanations and automatic vote-based pre-merging
for independent acceptance. Preserve each reader's labels and evidence groups
before adjudication by a separately assigned reviewer. Measure disagreement on
meaning and source scope as well as labels. INCEpTION may make this work easier;
it cannot supply qualified readers, verify their independence or turn a majority
vote into legal authority. An exportable local form remains the fallback if its
bridge cannot preserve the evidence.

## Recommended order and limits of this survey

First finish occurrence/disposition accounting and source-backed reference closure,
including the BASF common definition. Introduce the Z3 comparator and Hypothesis
invariants around that representation. Then test document structure on frozen
development pages, complete the financial convention/event trace, and exercise
actual dependency changes. Prepare the annotation bridge early enough to freeze
independent labels before acceptance results are shown. P7/P8 remain blocked
until real bound labels, scope and sign-offs exist.

| Decision | Primary evidence status | Veto or uncertainty | Next justified action | What is not established |
|---|---|---|---|---|
| Complete source accounting | Mechanism and current code mismatch inspected | Legal selection and priority still supplied | Implement interval dispositions and shared-definition regressions | Complete contract construction |
| Reuse Z3 and Hypothesis | Installed versions and relevant APIs inspected | New adapter and tests not yet implemented | Compare against finite enumeration and an independent state model | Correct natural-language translation |
| Trial Docling, INCEpTION and QuantLib | Relevant methods, implementation slices and limitations inspected | No local candidate evaluation | Run each predeclared trial after its input prerequisites | Tool superiority or readiness as a default |
| Defer ACTUS and CDM runtime changes | Relevant specification and wrapper/model slices inspected | Core access and version; additional integration scope | Revisit only for a demonstrated event or exchange requirement | Complete settlement or regulatory approval |
| Continue independent acceptance work | Existing admission interfaces available | Real independent labels and actual facts absent | Supply and adjudicate genuine evidence | Release acceptance |

ResearchAssistant's repaired metadata search used eighteen provider requests,
yielding 96 provider rows and 45 distinct records, with twelve automatically
nominated leads. The broad wording retrieved mostly blockchain, unrelated
contracts and general prospectus law. All nominations have explicit dispositions
in [discovery-disposition.json](discovery-disposition.json); none is used as
technical adoption evidence. The earlier discovery failed its aggregate-record
limit and lost its partial bundle; it is conservatively charged as 33 possible
requests. Exact-title/official-source acquisition and the retained technical
literature provide the substantive coverage. The manifest records failed URLs,
version distinctions and the bounded retrieval count. This is a thorough review
of the named engineering gaps, not a systematic-review claim of literature
saturation or proof that no other useful tool exists.

The strongest alternative explanation is that an untried document model could
solve more of the extraction problems than expected. The paired Docling trial
can test that without weakening source requirements. The weakest present
evidence is local comparative performance and independent legal interpretation;
neither was measured here. The survey supports an adoption order and concrete
tests, while leaving production promotion to their results.
