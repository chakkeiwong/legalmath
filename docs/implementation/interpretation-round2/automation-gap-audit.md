# Automation needed to reduce interpretation review

Audit date: 23 September 2026. Baseline: accepted P12 implementation, with 310
recorded passing tests and 41 of 100 live invocations used. This audit did not
rerun the tests, invoke a model or commission external advice.

## Finding and corrected product priority

**The monograph's full interpretation-assurance design is not implemented.**
P0–P12 completed their restricted engineering scope. They did not implement all
the surveyed legal-reasoning methods, demonstrate their combined effectiveness,
or establish that routine interpretations need little human work. Describing
independent legal review as the immediate next step understated the remaining
automation opportunity.

The user's commercial constraint is now explicit: a broad external consultancy,
estimated by the user at 0.5–1 million, is a last resort. No currency or actual
quotation is inferred. Development and automated evaluation must proceed without
making that purchase a prerequisite. The product objective includes reducing
the number and scope of questions reaching a person, and rerunning the relevant
checks on future inputs and changes. A one-time review cannot supply that
continuing detection mechanism.

Two activities must be separated. Checking every generated interpretation
manually is an operating model we should work to avoid. Evaluating whether an
automatic checker detects errors is a measurement problem: begin with public
authoritative examples, explicit rule boundaries, existing authorized decisions
and controlled fault injection, preserving their different evidentiary limits.
Independent evidence need not be a newly commissioned legal opinion for every
case. Some genuinely unresolved legal choices may ultimately need targeted
expert input; the software should first isolate the exact question and exhaust
the applicable bounded automated checks.

This priority change does not itself approve a production rule or remove an
existing institutional release control. It changes what we build next and how
we economize on evidence gathering.

## Monograph-to-code comparison

This is a capability audit of the main error-reduction mechanisms, not a claim
to reproduce every cited paper or to have searched every external repository.
The chapter and function references identify the evidence inspected.

| Method described in the monograph | Current implementation | Missing work that matters |
|---|---|---|
| Competing readings and bounded tree investigation; chapter 5, ToT/LATS discussion | **Implemented adaptation:** `search/models.py:generation_request`, `engine.py:select_node`, `backpropagate`, `_drive`; three roles, BFS/UCT, preserved parentage and limits | More calls alone do not test shared omissions. No measured superiority or calibrated search reward |
| Independent source inventories and dependency completion; chapter 6 | **Partial:** source import/extraction, exact source spans, packet dispositions, stored dependency closure and bounded official discovery | Search inventory copies supplied packet IDs. No second independent layout inventory or integrated acquisition of missing authorities before semantic resolution |
| HYPO/CATO analogy and distinction; chapter 5 | **Not implemented as case reasoning:** a scope/distinction prompt exists | No provenance-bound case/factor records, authority treatment, counterprecedent retrieval or executable legal analogy operators |
| AGATHA theory construction and adversarial moves; chapter 5 | **Partial inspiration:** three named prompt moves and a generic interpretation tree | No typed theory constructors or checked preconditions, rule/value preferences or actual case-based adversarial dialogue. BFS/UCT is not an AGATHA reproduction |
| ASPIC+ structured arguments and attack types; chapter 5 | **Not implemented:** `search/arguments.py` evaluates a bounded abstract Dung graph; `engine.py:material` makes mutual edges for differing outputs | No generated premise/inference/conclusion argument structure, undermining/rebutting/undercutting distinction or explicit source-backed preferences. `engine.py:add` submits `arguments=[]` |
| Carneades premise types, critical questions and proof standards; chapter 5 | **Not implemented:** the old proposal contract stores basic argument fields, and reviews store assumptions | No executable ordinary-premise/assumption/exception evaluation or critical-question dialogue. The existing Dung solver cannot substitute for these semantics |
| Original-English fidelity and stage-specific roundtrip repair; chapters 3, 5 and 6 | **Partial:** compile, render controlled English, reconstruct in a fresh context, compare formal outputs; bounded schema/quote repair | No separate source-versus-reconstruction entailment check, first-failed-stage diagnosis, or tested semantic repair at each translation stage |
| Clause-level entailment with evidence, including remote exceptions | **Partial source validation only:** `validate_generation` checks exact quotations, references and unit dispositions | A quote's presence does not establish support. No explicit per-claim supported/contradicted/not-established evaluation or independent atomic-obligation coverage check |
| Discriminating questions; chapter 5, generalized binary search discussion | **Partial:** `questions.py` ranks existing formal witnesses by separated candidate pairs | Generic question text; no attempt to answer from authorities, cost-aware action selection, reusable question-answer library or incremental evidence-based elimination |
| Semantic uncertainty and calibration; chapters 5 and 9 | **Partial descriptive reporting:** retained-branch entropy and checked behavioral groups | No implemented NLI semantic-entropy estimator or legal calibration study. Conformal coverage cannot be claimed from the current branch distribution |
| Fact correspondence and output meaning | **Partial:** exact aliases and explicit conditional total bijections, with original Java witnesses and separate reviews | Derived facts, differing decompositions and machine-readable output conventions remain missing |
| Mutations and metamorphic checks; chapter 7 | **Partial:** meaningful fixed rule/Java mutants, missing-data tests, source invalidation and adversarial regressions | No general source-level challenge generator or per-circular common-omission campaign covering harmless edits and meaning-changing edits |
| Change impact and continuing assurance; chapter 10 | **Partial:** `discovery.py` refresh/diff helpers, `dependencies.py:closure/affected_bundles`, invalidation and retained histories | No integrated scheduled source-to-reinvestigation workflow; no complete source/model/prompt/definition change replay and measured detection latency |
| Human-effort reduction and paired evaluation; chapter 9 | **Partial:** annotation/evaluation bookkeeping and unresolved reports | No observed reduction in review effort, cost-sensitive escalation policy, held-out comparison or measured false-clean rate |

The most important implementation limitation is visible in
`engine.py:retrieve`: it supplies uncited units already inside the frozen packet
and lists missing dependency IDs. It does not acquire those missing documents.
Likewise, all three initial readers share the same supplied inventory and model
route. Their isolated conversations reduce anchoring but do not create an
independent source check or demonstrate independent errors.

## What to borrow from the literature

**Case-based challenge.** AGATHA defines five moves with explicit preconditions
over already factorized cases and constructs rules and preferences as the
dialogue proceeds. Its heuristic and adversarial searches are separate designs.
Borrow inspectable constructors for analogy, distinction and counterexamples;
do not import a desired party's victory as the bank's objective. Raw-text factor
extraction remains a separate task. Technical basis: sections 3–4, 6–11 and the
evaluation discussion in the retained paper; sections 3–5 were reinspected for
this audit. [Chorley and Bench-Capon](https://www.csc.liv.ac.uk/~tbc/publications/agatha.pdf).

**Structured criticism.** ASPIC+ distinguishes attacks on premises, defeasible
conclusions and inference steps, then uses explicit preferences to determine
defeat. This permits a critic to target why a proposition follows. A generic
"these programs differ" edge supplies none of that information. Any
implementation claiming the paper's rationality properties must satisfy their
conditions, including the correction to definition 6.8. Technical basis:
section 3.3, definitions 3.12–3.19, section 6 and the retained correction.
[Prakken](https://webspace.science.uu.nl/~prakk101/pubs/aspicAF.pdf).

**Questions and assumptions.** Carneades distinguishes ordinary premises,
assumptions and exceptions, allowing a challenge to identify the missing support
and its burden. Its 2007 graph is acyclic; newer Carneades software implements
a different evaluation model. Reuse the explicit critical-question structure
under a locally specified policy rather than importing numerical proof
standards as regulatory approval. Technical basis: sections 3–6 and the retained
`carneades-caes.go`, inspected alongside the paper.
[Gordon, Prakken and Walton](https://webspace.science.uu.nl/~prakk101/pubs/GordonPrakkenWalton2007a.pdf),
[official software](https://github.com/carneades/carneades-4).

**Source fidelity beyond a closed loop.** The roundtrip paper compares original
and reconstructed formalizations, diagnoses the failed stage and regenerates
downstream translations after a repair. It separately measures bidirectional
natural-language inference between the original and reconstructed text. Its
limitations explicitly include shared omissions and isolated-rule processing.
Our proposal is to add those source-facing checks and connected context as
additional diagnostics, not to treat consistent translations as a proof of
meaning. Technical basis: sections 3–5, Algorithm 1 and Limitations.
[Amrollahi, Lopez and Barrett](https://arxiv.org/abs/2604.25031v2).

**Evidence-bearing language checks.** ContractNLI combines an entailment,
contradiction or not-mentioned classification with evidence spans. Its analysis
of non-local exceptions directly motivates testing distant qualifications.
Borrow the task contract and difficult cases; an NDA-trained model's accuracy
does not transfer automatically to SFC circulars. Technical basis: sections 2.1,
3, 4 and 5.2; task and exception analysis reinspected. Its original-model code
has not been audited in this turn, and no model import is authorized by this
finding. [Koreeda and Manning](https://arxiv.org/abs/2110.01799).

**Reduce question count.** Generalized binary search selects questions that
separate a finite set of hypotheses; its guarantees depend on the hypothesis
and oracle assumptions. Borrow discriminating-question selection, adding
estimated acquisition cost as a local heuristic. First try retained official
material; ask a person only when the unresolved answer could change a material
decision. Do not infer legal probabilities or query-complexity guarantees for
open-ended interpretation. Technical basis: Figure 1 and sections I–III.
[Nowak](https://arxiv.org/abs/0910.4397v5).

Catala, Stipula and related specification languages address additional formal
representation and execution checks. Integrating every language is not a
completion criterion for English interpretation. A second encoding can be
valuable where it provides an independently implemented semantic check, but
the same omitted exception can survive in two perfectly executed encodings.
The appropriate unit of reuse is a justified error-detection mechanism.

## A concrete shared-error test

Use the retained 23EC46 development case and explicitly label the challenge as
a seeded defect. Make every initial candidate omit the fee-discount exception,
while preserving well-formed formulas and exact source quotations. Agreement,
Java conformance and formal roundtrip may all pass. The new source-facing
extractor must identify the exception span independently of the candidates;
the claim checker must report its absence from their meaning; the challenger
must request a case in which the omission changes an outcome. If every channel
still misses it, the campaign fails even if every generated program agrees.

Add a qualification far from its main clause, a product-type link removed from
scope, a negated obligation, an effective-date boundary and a missing annex.
Pair these with harmless formatting and identifier changes. The goal is to
detect the material edits without escalating all harmless edits. Labelled
challenge transformations must have an explicit expected relation; arbitrary
paraphrases cannot be presumed meaning-preserving.

This campaign can expose important failures without buying new legal opinions.
It measures sensitivity to specified defects, not the natural error rate on all
future law. Public worked examples and authorized existing decisions can add
external anchors. Reserve untouched source families and a subset of challenges
for acceptance so repairs cannot continuously rewrite their own standard.

## Continuing detection and economical escalation

For each new circular, source amendment, referenced-definition change, relevant
bank fact-schema change, or model/prompt upgrade, identify the affected controls,
rerun the relevant semantic and executable challenges and preserve the old
result. A retrieval failure, stale dependency or unexamined required unit must
remain visible even if models agree. New document types and unresolved input
classifications trigger investigation. Scheduled acquisition needs a recorded
cadence, retry bound and detection-latency target; none has yet been validated.

Every issue should identify its next useful evidence action. Automatically
retrying the same generic prompt is insufficient. Search should choose among
source acquisition, alternate extraction, premise challenge, distinguishing
case, formal check or stage repair. Give each issue a budget and preserve
unresolved findings at exhaustion. Reuse a previously supported answer only
when its source version, scope, assumptions and operational bindings still
apply; retain the dependency chain and invalidate it when any premise changes.

Deduplicate equivalent questions and report the smallest set whose answers
would distinguish the remaining material alternatives. Existing compliance
knowledge and authorized prior decisions may answer some of them. An external
consultant, if eventually needed, should receive a narrow unresolved issue
with competing readings, exact passages, attempted checks and its consequence.
Neither a majority vote nor a low numerical uncertainty score should close it.

## Evidence contract for the next increment

The next plan must compare the current P12 engine with each added checker on
the same frozen sources and challenge set, followed by an equal-budget live
comparison when justified. Define distinct outcomes: a detected material defect,
an undetected seeded defect, a supported clean example, an unnecessary
escalation, an unsupported profile and unresolved source evidence. Do not count
abstention as a correct interpretation or treat every generated difference as a
true defect.

Primary engineering acceptance is detection of each predeclared mandatory
challenge without a silent pass, plus passing the harmless-control checks and
preserving all historical evidence. A later effectiveness comparison must
jointly measure missed defects, useful coverage, reviewer time, model cost and
escalation volume. Thresholds, samples and uncertainty analysis must be declared
before ranking procedures. Public examples, synthetic defects and actual bank
review decisions remain separate evidence classes. The latter require their
own authorized access; this audit uses no bank data.

| Decision | Criterion status | Veto status | Main uncertainty | Next action | Unsupported conclusion |
|---|---|---|---|---|---|
| Correct the coverage claim | Code and monograph show substantial missing mechanisms | P12 success cannot stand for the full design | Which mechanisms yield the best cost/error trade-off | Implement and compare the missing source-facing checks | All literature implemented |
| Continue automation before consultancy | Local engineering and public-source testing can proceed | No required external opinion blocks these tasks | Residual ambiguity after better checking | Build bounded source and criticism loops | Zero need for expert judgment |
| Retain P12 engineering evidence | Existing manifest and tests unchanged by this documentation audit | No new test result asserted | Legal fidelity and future performance remain unmeasured | Preserve baseline for a discriminating comparison | Production readiness |

No statistical ranking is supported by this audit. The strongest alternative
explanation for future apparent success is teaching the checker the same seeded
errors used to evaluate it. Held-out challenge families and external public
anchors can challenge that explanation. A second risk is shifting all cases to
the unresolved queue; harmless controls and measured review effort must prevent
that from masquerading as useful error reduction.

The [revised next-phase plan](next-phase-plan.md) makes automation and continuing
detection the immediate work. It preserves independent reference evaluation as
a progressively acquired evidence source, and external consultancy as a last
resort rather than the starting dependency.
