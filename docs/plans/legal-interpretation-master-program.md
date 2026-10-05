# Master program: source-grounded legal interpretation and precedent

Revision 1 — 5 October 2026. Status: **reviewed implementation specification;
product phases not executed**. Claude's independent review is pending.

Start with the [phase index](legal-interpretation-program/README.md), the
[program review](../implementation/legal-interpretation-program/program-review.md)
and the [Claude handoff](../implementation/legal-interpretation-program/claude-handoff.md).
The research argument is integrated into the monograph at
`sec:legal-interpretation-reuse`. The
[literature review](../research/legal-interpretation-reuse-2026-10-05.md) retains
paper sections, software versions and licence findings.

## 1. Background and problem

LegalMath can investigate alternative readings, attach source quotations, express
some readings as programs and check their conditional execution. These mechanisms
are useful, but the current product has not established that its inputs or rules
faithfully capture the English legal sources.

The [5 October product audit](../implementation/assurance-evidence-master/product-gap-audit-2026-10-05.md)
is the starting evidence, not a new result of this program. Its baseline is
revision-22 and the package selected by
`artifacts/assurance-gap-continuation/2026-10-02/additional-100-repair-20/current-post-review-repairs.json`.
At inspection, the selected directory was
`post-review-repairs/a1ed4180b665d213f27d465f/`; the original obligation map was
`local-recovery/abc7952787bceb734607c614/`.

There are 35 reading identities represented in two roles, not 70 independent
interpretations. All 46 original challenge obligations remain open. The recorded
20 mechanical guards and 1,040 synthetic checks concern declared program
behavior. Thirteen editorial changes, 38 date corrections and ten reopened
question statuses did not establish a substantive interpretation repair. These
are historical baseline counts; P0 must rebind them if the active pointer changes.

Throughout this program, paragraph references identify the retained SFC circular
26EC22, revised on 20 April 2026, including its eight footnotes. Its archived
source is `docs/papers/Circular on tokenisation of SFC-authorised investment products_SFC(2026).json`.
P0 must verify that this source identity matches the selected investigation;
it must not silently substitute the 2023 edition or another circular's paragraph 10.

The product gaps fall into seven connected questions:

1. Does paragraph 10 concern retaining responsibility, exercising supervision,
   achieving adequate operations, or a combination? These propositions can have
   different truth values.
2. Which particular duty is conditional on a request in paragraph 14, and how
   does that interact with footnote 5? Confirmation, demonstration, verification
   and legal opinion cannot share one inherited trigger.
3. Which actor, product, provider, component and time interval does a duty cover?
   Publication time, effective time, event time and knowledge time differ.
4. What observed evidence warrants a factual classification? Supplying
   `ownership_records_proper=true` does not establish record propriety.
5. What establishes legal or beneficial ownership, settlement finality,
   materiality and the consequences of an incident or remediation?
6. What force does SHOULD have in the particular authority? A satisfied predicate
   does not establish overall compliance, statutory liability or absence of risk.
7. Which supported and unsupported readings remain, and what can be carried into
   unfamiliar sources without inventing a completeness guarantee?

Case law can constrain these questions, but only through a justified account of
the issue, material facts, holding, reasoning, authority and applicability.
Retrieval and similarity are candidate-discovery mechanisms. A quoted submission
or dissent cannot automatically become the court's holding.

## 2. Objective and deliverable

Build an optional interpretation layer that takes an exact legal source edition,
an explicit question and declared evidence; represents supported proposals and
unresolved alternatives; explains their arguments; and carries supported
executable branches into the existing qualification route.

A useful output states the proposed conclusion, the reading and premises under
which it follows, the supporting passages, contrary arguments, missing evidence,
applicability limits and the exact formal checks performed. When the evidence
cannot settle a premise, the result remains qualified. A system that always
abstains is also inadequate: mechanically checkable consequences and supported
branches must actually be computed and exposed.

Success is a scoped implementation and a faithful account of what it establishes.
Unrestricted English correctness, completeness of all possible readings, complete
case-law coverage and future legal accuracy remain NOT_ESTABLISHED unless
separate evidence establishes an exactly stated proposition.

This program adds no human answer keys, model-vote acceptance rule or human
quality approval. The [controlling product requirement](../implementation/proof-qualified-generalization/product.md)
applies to fitting, model selection, validation and claims. Legal texts and
formal specifications are premises; source authorship is not a prohibited label.
Claude reviews the program and can expose errors; its approval cannot prove a
legal interpretation.

## 3. Proposed solution and literature choices

HYPO/CATO/AGATHA supply factor hierarchies, analogy, distinction and counterexample
moves. Their pre-encoded cases explain why we need a separate source-to-factor
justification. Do not import a desired-party winner, arbitrary value priority or
simplicity score as truth.

ASPIC+ supplies premise, rule and conclusion attacks. PyArg is the first bounded
engine candidate, behind an optional adapter. Neither grounded semantics nor
preferred semantics is selected as governing law. Compare their consequences
under explicit settings; use grounded acceptance only as a conservative
computational report when that setting is declared. Missing priority remains
missing. Validate the intended theory conditions, including the corrected
ASPIC+ well-formedness requirement, before invoking a rationality theorem.

Carneades supplies useful distinctions between ordinary premises, assumptions
and exceptions. Its engine is an alternative, not a second interchangeable
decision authority. Do not import PE weights or equate its Out label with false.

LegalRuleML supplies source, temporal, jurisdictional and alternative-reading
structure. Logical English supplies controlled templates and explicit binding.
Use these concepts in a small typed internal representation. Full XML compliance
and the full Logical English runtime are not first-phase requirements. The
renderer specifies a reading; it cannot verify the original English by roundtrip.

SARA-IE supplies span-linked event/argument extraction. Reimplement the published
representation while its repository licence remains unverified. Reject silent
date imputation, confidence thresholds and closed-world negation as defaults.

CLERC supplies retrieval task design; eyecite supplies citation parsing where its
jurisdictional coverage is checked. Keep majority, concurrence and dissent
separate. Citation linkage is independent of holding support and later treatment.
CLERC's nested MIT licence does not establish repository-wide or corpus rights.

Candidate construction in P2 consumes the actual source packet, question and
retained investigator proposals through a planned `clauses.propose(...)`
interface. It nominates clause structures and competing condition attachments;
it does not merely import manually settled legal answers. Each nomination keeps
its source warrant and unrepresented concerns. The offline pilot uses retained
proposals; any fresh model generation remains separately budgeted and supplies
candidate material, not acceptance evidence.

No dependency is installed or enabled by this document. P3 records PyArg's
runtime/API compatibility and transitive licences before optional adoption.
A failed dependency candidate triggers a smaller interface-compatible local
reference implementation; it does not invalidate the interpretation objective.

## 4. Architecture and exact boundaries

All following paths under `src/legalmath/interpretation/semantics/` and
`tests/interpretation/semantics/` are **planned new files**, not existing code.
The existing `assurance/semantics.py` remains a separate module.

| Planned module | Responsibility | Existing integration point |
|---|---|---|
| `records.py` | Typed source editions, propositions, facts, readings and unresolved premises. | `interpretation/contracts.py`: Packet/Proposal validation; `search/models.py`: Reading. |
| `clauses.py` | Actor/action/modality/condition/exception scopes and cross-reference relations. | `assurance/source_references.py`: verified Unicode spans. |
| `arguments.py`, `pyarg_adapter.py` | Finite arguments, attacks, explicit preferences, extensions and resource-qualified results. | Existing proposed arguments; no implicit replacement of historical contracts. |
| `precedent.py` | Opinion-aware case propositions, factors, analogy and distinctions. | Retained source packets and explicit authority premises. |
| `evidence.py` | Observation-to-predicate derivations with identity and temporal scope. | Existing event/evidence records and declared formal facts. |
| `lower.py`, `render.py` | Supported branch lowering and explanations derived from the same semantic records. | `translation/model.py`: from_reading; supported RuleIR/Catala profiles. |
| `integration.py` | Optional complete-investigator route and scoped qualification. | `assurance/complete_investigation.py`, `qualification_adapter.run/verify`. |

Use one source of semantic identity, with a versioned adapter into existing
contracts. Do not add ad hoc fields to strict old schemas or mutate old retained
responses. Avoid an import cycle: the interpretation adapter can call the
translation boundary; the translation model must not import the investigator.

Each proposition must retain its source hash and edition, locator, exact quote,
speaker/opinion role, question identity, actor/activity scope, validity interval,
reasoning warrant, dependencies and status. The span coordinate convention is
the existing Unicode-codepoint half-open convention. For an unsupported source
format, return an explicit unsupported locator; do not manufacture offsets.

Keep five evidence axes distinct: quotation identity; proposed interpretation;
applicability; factual support; formal consequence. A verified quotation cannot
automatically establish the other four. A model confidence is diagnostic only.

Represent positive and negative factual support independently, preserving neither
supported, positive supported, negative supported and conflicting support. These
are support states under declared evidence rules, not a claim that all evidence
is true. Distinguish a source's assertion from a court finding, an observation
from an inference, and absence of evidence from evidence of absence. Do not put
argument acceptance and factual truth in one enum.

A reading branch is the relevant interpretation plus all semantic settings and
assumptions needed to evaluate it. Shared premises and jointly applicable duties
retain their dependencies; do not form an unconstrained Cartesian product of
incompatible actor, temporal or priority assumptions. A conclusion uniform over
the retained, successfully evaluated branches is labelled uniform over those branches only.
An empty set, unsupported branch, unvisited frontier or timed-out evaluation
prevents a completeness claim. Missing evidence still appears in every
downstream report; a concise summary cannot drop it.

## 5. Research intent and evidence contract

| Item | Contract |
|---|---|
| Main question | Can explicit source/evidence/argument structure repair specified interpretation defects while preserving unresolved meanings and executable consequences? |
| Mechanism | Typed semantic records, source-linked warrants, competing arguments, precedent distinctions and checked lowering. |
| Exact comparator | P0-frozen operative package and existing qualification behavior, with identical source edition, question and declared facts. |
| Expected failure | A plausible source-linked encoding still omits or misinterprets a premise; an engine default then makes it appear settled. |
| Primary engineering criterion | The declared invariants and phase-specific behavioral obligations pass, the actual complete-investigator route uses the new structures, and unsupported cases retain exact reasons. |
| Source-fidelity criterion | Every claimed consequence states the formal proposition and unresolved source premises; no unproved natural-language proposition is relabelled proved. Specific legal closure requires source-bound reasoning plus an independently checkable scoped guarantee, otherwise qualification. |
| Promotion veto | Lost alternatives, unsupported priorities, conflated evidence states, dropped applicability, inconsistent explanation/code, false universal claim, unverified dependency permission. |
| Continuation veto | Corrupted baseline/evidence, invalid checker, unbounded execution, unauthorized expenditure or inaccessible required input with no valid qualified path. A blocked dependency stops its dependants, not unrelated development. |
| Repair trigger | Concrete counterexample, stale operative field, unsupported compiler construct, mismatched source role, or candidate library failing its declared API/semantics. |
| Explanatory only | Citation counts, coverage counts, runtime, graph size, reader/model agreement and retrieval scores. |
| Not concluded | General legal correctness, all possible readings covered, superiority of a model, production readiness or actual client compliance. |
| Retained result | Immutable attempt directory with inputs, semantic assumptions, actual commands, observed outputs, checks, decision and next-phase revision. |

No statistical comparison or learned-model training is authorized by the phase
sequence as drafted. If added, first write a task-specific protocol with tuned
comparators, seeds, uncertainty analysis, downstream criteria and the
machine-only evidence restrictions. A convenient pretrained extractor is a
hypothesis, not a validated factual bridge.

## 6. Phase sequence

| Phase | Concrete product result | Dependencies |
|---|---|---|
| P0 | Bound baseline, obligation identities and corrected current prose in a new candidate overlay. | Documentation package |
| P1 | Typed source, meaning, evidence and uncertainty records. | P0 |
| P2 | Explicit clause-level alternatives for paragraph 10 and paragraph 14/footnote 5. | P1 |
| P3 | Bounded argument evaluation with explicit semantics and priorities. | P2 |
| P4 | Opinion-aware precedent propositions and justified analogy/distinction. | P1, P2, P3 |
| P5 | Evidence-derived predicates with actor, activity, time and modality scope. | P2, P3, P4's result, including an explicit unresolved-authority result |
| P6 | Explanations and executable branches through the actual investigator and qualification route. | P3, P4, P5 |
| P7 | Independent invariant checks, formal statements and targeted fault tests. | P6; focused checks already run in each earlier phase |
| P8 | Coverage extension, unfamiliar-source observation design and maintained next-phase plan. | P7 |

P4 may finish with an explicit missing-authority result if no relevant judgment
can be acquired. P5/P6 then carry that unresolved premise and may implement the
conditional branch; they cannot claim a precedent-supported answer. P8's future
observation component stays pending until genuine post-freeze publications exist.
Development and plan completion do not require fabricated observations.

The [individual phase plans](legal-interpretation-program/README.md) give
implementation actions, inputs, expected interfaces, test commands, acceptance,
repair and continuation conditions. These are work instructions for an executor,
not evidence that any phase has run.

## 7. Assumption and default audit

| Choice and provenance | Justification/status | Failure mode | Earliest diagnostic |
|---|---|---|---|
| Two disputed clause groups from current gap audit | Pilot, chosen for consequential divergent outcomes. | Success on the pilot mistaken for broad coverage. | Preserve all 46 obligation IDs and report pilot scope beside every result. |
| Finite explicit argument theories from ASPIC+ | Engineering hypothesis permitting reproducible checks. | Omitted arguments mistaken for exhaustive legal reasoning. | Report unresolved frontier; test adding a contrary argument. |
| Grounded/preferred/ordering choices from PyArg | Alternatives to inspect; none is legal authority. | Silent library default resolves a legal dispute. | Same theory under declared settings; inject unknown preference. |
| Four factual support combinations | Proposed evidence interface preserving contradiction and ignorance. | Supplied evidence mistaken for truth; downstream Boolean coercion. | Missing/conflicting evidence through actual serialized and compiled boundaries. |
| Partial dates with event/knowledge/validity distinctions | Target-specific requirement from current gaps and existing event work. | Publication dates or year-zero imputation create applicability. | Partial date, later recording, backdated correction and provider replacement. |
| Controlled English generated from semantic records | Reviewed engineering design, not translation proof. | Two consistent outputs share a source error. | Source challenge plus changed condition attachment; no roundtrip promotion. |
| Existing Unicode spans | Current implementation baseline; deterministic location evidence. | Quote integrity mistaken for entailment. | Valid quote used for an incompatible proposition remains disputed. |
| Pilot limits: 64 alternatives, 500 argument nodes, 30 seconds per query | Existing contract ceilings are a convenience baseline, not calibrated defaults. | Truncation yields a confident partial answer. | Lower the cap deliberately; require incomplete result and visible frontier. Refresh caps after measured bounded probes. |
| US/tax methods applied to Hong Kong | Design hypotheses only. | Foreign hierarchy, ontology or citation syntax becomes governing law. | Unknown jurisdiction, dissent, later treatment and inapplicable time tests. |

The 500-node prototype bound comes from `interpretation/contracts.py`, not
`search/models.py`: the latter's current Settings allow only 16 argument nodes.
Keep these as distinct profiles and do not pass new semantic limits into the
legacy search schema. Any new configuration requires a versioned boundary.
Exhaustive preferred-extension reference checks start with at most eight abstract
arguments; the bound is a tractability convenience, not a legal or coverage claim.

## 8. Repair, refresh and resume between phases

Use `artifacts/legal-interpretation-program/<run-id>/<phase>/attempt-<n>/`
for future actual execution. Keep the present documentation review under
`docs/implementation/legal-interpretation-program/`. Do not write successful
phase receipts during planning.

Before each phase, verify the active baseline, prerequisite result hashes, current
code and source identities, licence/permission conditions and remaining resource
budget. Refresh the phase plan before executing if any changed. Save the exact
plan revision used with the run.

After each phase:

1. Persist inputs, source/assumption identities, actual commands, outputs,
   elapsed time, environment, errors and all unfinished work.
2. Recompute every applicable invariant and gap disposition from observed files.
   Maintain separate engineering, formal-validity and source-interpretation
   decisions. State whether a failure invalidates the harness or rejects a
   candidate.
3. Mark each obligation implemented-conditionally, unresolved-meaning,
   unresolved-fact, unsupported, invalidated or independently-established within
   an explicitly proved scope. Never count mere formatting as semantic closure.
4. Classify each failure as a repair trigger, promotion veto or true continuation
   veto. A failure that the next planned phase repairs is not a reason to
   abandon the program.
5. Rewrite the next phase's inputs, concrete work, tests, budget and stop
   conditions using the result. Retain both old and new plans with hashes and a
   reason for the revision. A fixed generic next-step paragraph is insufficient.
6. Review that revision against the master question. Resume only from verified
   completed work; a crash cannot convert a started action into a completed one.

A local engineering issue gets a bounded causal repair, its failing example and
a targeted rerun. Initial convenience limit: two repair attempts per distinct
engineering cause before a plan revision. This is not a provider-call allowance
or a limit on documenting genuine legal uncertainty. At that limit, record the
counterexample and choose a justified alternative implementation or a qualified
unsupported result. Do not recycle the same legal ambiguity through repeated
prompts. Every phase must compute useful conditional results or specific
unresolved reasons; a blanket abstention fails its behavioral criterion.

Any change to source edition, branch semantics, code used for a checked claim or
method configuration invalidates dependent receipts. Narrow downstream
invalidation follows actual dependency IDs; do not erase unaffected evidence.
A resumed executor must read the current plan and latest result, not merely the
latest successful log.

## 9. Resources, exact commands and approvals

The documentation task uses zero model/provider calls. P0–P3's core development
and synthetic checks require no live model or GPU. P4 first uses retained official
sources; missing judgments are acquired through a named, bounded official source
request. No crawling budget or new model allowance is granted by this plan.

Historic 100-call/50-repair/48-hour limits belong to their recorded campaign.
Check the actual allowance and expiry before any future live action; do not copy
remaining capacity into this program. Preserve reservations and failed attempts.
If live assistance is later justified, specify endpoints, caps, exact command,
per-attempt limits and output paths together before dispatch. Model agreement
still supplies no quality evidence.

Run commands from `/home/chakwong/python/legalmath`. Command policy:

- `.venv/bin/python -m pytest <existing-test-path>`: phase regression only after
  the named test file exists. The phase files list **future** paths explicitly.
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error -cd docs/monograph/monograph.tex`:
  canonical document build, with the linked companion built as required.
- `.venv/bin/python scripts/assurance_evidence_master.py ops-run` is an existing
  provider-campaign command and **is not this program's execution entry point**.
  Do not run it to execute these phases.

The program is an implementation specification with a machine-readable phase
manifest. It does not claim a new autonomous runner exists. Build and test the
product route in P6 using the existing complete investigator; add a narrow offline
CLI only if an actual integration need remains, and document it before use.

Use direct argument vectors and repository-relative paths. Do not wrap commands
in shell substitutions or broad `bash -c` approvals. A repository allowlist
documents scope but does not change the environment's approval rules. Do not edit
protected `.codex` rules as a workaround. Group genuine new dependency, network or
provider approvals around concrete operations; local authorized edits need no
new user permission. The known WSL mount startup error is environmental evidence,
not a reason to change the product.

## 10. Gap-to-phase and outcome map

| Current gap | Implementation work | Required final qualification |
|---|---|---|
| Stale source-unavailable and categorical request language | P0 candidate overlay; P6 consistent rendering | Acquisition is distinct from applicability; immutable originals retained. |
| Responsibility/supervision/adequacy | P1–P3, P5 | Branch-specific meanings and missing warrants remain visible. |
| Paragraph 14 / footnote 5 and exception attachment | P2–P3, P6 | No invented priority; each duty retains its own trigger. |
| Actors, activities, dates and provider changes | P1, P2, P5–P7 | Scope and incomplete intervals prevent unsupported conclusions. |
| Evidence-to-classification bridge | P1, P4–P7 | A quote, event or record identifier alone cannot establish a legal classification. |
| Ownership/finality/incidents/remediation | P4–P5; expand in P8 | Token possession and an incident outcome do not independently settle legal title or breach. |
| SHOULD and legal consequences | P2, P3, P5–P6 | Duty modality and sanctions/liability use separate source-backed rules. |
| Unformalized readings, unseen English and amendments | P6–P8 | Unsupported branches counted; prospective evidence separate from development. |

Completion of a phase means its specified engineering or scoped formal work is
done. Completion of the master implementation means all required capabilities
operate, all obligations have honest dispositions, and future observation is
properly prepared. It does not mean every legal question has a unique answer.
Release eligibility remains false under this program.

## 11. Review and handoff

The [program review](../implementation/legal-interpretation-program/program-review.md)
records concrete flaws found and revisions made. The
[handoff memo](../implementation/legal-interpretation-program/claude-handoff.md)
asks Claude to inspect the whole program, source claims, existing interfaces and
phase contracts, returning severity-ranked findings and precise repairs. Its
manifest binds the reviewed files. A later edit requires refreshing that binding
before the review is represented as applying to the current program.
