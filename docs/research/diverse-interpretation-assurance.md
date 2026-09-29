# Diverse interpretation assurance

Design recommendation, 25 September 2026. This document proposes the next product
increment; it does not claim that the increment is already implemented or that its
reliability has been measured. It supplements the
[current gap audit](../implementation/monograph-implementation-gap-audit-2026-09-25.md).

## The decision

Make complementary assurance methods mandatory for material source-to-control
claims. Each method should have a distinct opportunity to find an error, and each
remaining objection should have a visible resolution status. Agreement is one
observation. It cannot replace source coverage, applicability, factual definitions,
counterexamples or implementation checks.

The objective is to reduce undetected material errors, including errors shared
by every initial interpreter. A higher disagreement rate is not an improvement
by itself: an incompetent method can create many false alarms. Likewise, a system
that abstains on every question has not demonstrated useful accuracy. Required
metrics are unsafe acceptance, missed material conditions, correctly accepted
coverage, useful discrepancy detection and remaining reviewer effort.

The user's priority is accuracy over cost and latency. Accordingly, investigation
limits determine when to retain uncertainty and escalate a narrow question; they
must not lower the evidence needed for acceptance. Extra quota permits more
investigation, not a stronger correctness claim by itself.

## Why different methods can still agree wrongly

Knight and Leveson's multiversion experiment developed 27 programs separately and
compared their behavior over one million test inputs. Sections 4–6 report joint
failures exceeding the independence model. Sections 7–8 limit the conclusion to
the studied setting and explicitly do not conclude that diversity is useless.
The useful lesson is to measure dependent failures rather than infer independence
from separate development. Their specification and test-reference limitations
also matter when transferring the design to regulatory interpretation.

Littlewood, Popov and Strigini explain a mechanism in section 4.1, equations
4.1–4.4. In their model, programs are sampled independently and a particular input
has difficulty theta(x), the chance a sampled program fails on that input.
Conditional failures are independent at that fixed input. Across a distribution
of inputs X, however, both-failure probability is E[theta(X)^2], which equals
E[theta(X)]^2 + Var[theta(X)]. Variation in difficulty produces joint failure above
the product of marginal failure rates. This is the cited model's derivation, not
an estimated law of LegalMath errors. A distant exception or misleading common
definition is a plausible local example of a shared hard input.

Kim and colleagues (ICML 2025) measure agreement on the same incorrect answer
conditional on both models being wrong in multiple-choice tasks; they also study
residual correlation in resume assessments. Section 3 and appendices A and C
report substantial shared errors, including across provider boundaries. Their
benchmarks do not estimate Hong Kong regulatory accuracy. The transferred lesson
is that a provider label is a diversity hypothesis, not an independence result.

The three papers are retained in `docs/papers`; exact filenames, source locations,
hashes and inspected sections are in
[diverse-assurance-sources.json](../papers/diverse-assurance-sources.json). PDF text
was extracted with ResearchAssistant. The selected official Kim code was inspected
at commit `30a2c0aa88af3f428f1f7034538373d24c209176`, not executed. Its
`analyze_model_correlations` implementation confirms the conditional wrong-answer
agreement calculation. It returns zero for empty error denominators; our design
requires `NOT_ESTIMABLE` instead, so no observed failures cannot look like evidence
of uncorrelated errors. Its optional model-as-reference analysis must not become
our legal ground truth.

## Build diversity at each vulnerable transformation

| Question being checked | Complementary methods | Shared failure to challenge |
| --- | --- | --- |
| Did the packet preserve the source? | Text extraction; rendered-page/OCR and layout inventory; attachment/reference inventory | Every interpreter receives the same missing footnote or table |
| What duties and qualifications are stated? | Source-only actor/action/modality inventory; independently authored controlled rules; reader reconstructing expected cases directly from source | Shared summary, preselected rule or omitted distant qualification |
| What do the factual terms mean? | Competing actor/object/time schemas; explicit definition retrieval; independently constructed boundary examples | All formulas depend on the same wrong classification |
| Which interpretation survives objections? | Literal/scope analysis; authority and case arguments; counterexample-driven comparison; parallel official language where applicable | Fluent majority overrides a sourced minority objection |
| Does the formal representation preserve that reading? | Source-to-rule fidelity check; controlled-language roundtrip; separately authored formal model on a supported fragment | Faithfully translating the same initially wrong formula |
| Does the delivered implementation match the formal target? | Python/Java differential execution; Catala pilot after semantic alignment; symbolic witnesses; targeted proof and mutation checks | Shared test oracle, shared frontend or wrong output convention |
| Do bank facts and later changes preserve validity? | Reconciliation to independent records; historical replay; source/dependency change invalidation; shadow host execution | Correct program applied to stale evidence, wrong entity or obsolete authority |

These are different claims. An OCR match cannot certify a legal interpretation,
and Catala/Java agreement cannot certify an English-to-rule translation. Each
claim needs evidence aimed at its own error mechanism. A second backend derived
from the first backend's exact intermediate representation tests a different
part of the chain from a separately authored source-based specification; both
can be useful, but their contributions must be labelled correctly.

The initial candidate policy is two materially distinct applicable checking
routes plus an adversarial omission/counterexample route for a material
interpretation. This is an engineering hypothesis to evaluate, not a theorem that
three methods suffice. Required routes depend on the source and question. A
scanned source requires a visual route; an event-order question requires a
temporal route. Unsupported or unavailable required checks remain unresolved.

The same gates apply to apparently unambiguous clauses. Restricting redundancy to
clauses an initial model labels ambiguous would let that model suppress the very
checks intended to catch its confident mistakes.

## Preserve independence where it can be preserved

Initial readers receive retained source editions and the selected business
question, but no preferred reading, peer answer or hidden expected result. Each
freezes its claim inventory, definitions, assumptions, source anchors, alternatives
and uncertain points before reconciliation. A scenarios-first reader derives
examples without seeing the proposed formula. Different factual schemas may be
proposed; they must not be silently forced into a common, possibly wrong schema.

Record every shared dependency: provider/model family, prompt, extracted text,
retrieval catalog, fact schema, intermediate representation, evaluation code and
reference cases. Use a dependency graph to show which comparisons can share a
cause. Do not convert this graph into a numerical probability of independence.

Cross-provider routing is useful candidate diversification, subject to authorized
access. Source-route, representation and checking-algorithm diversity can be
implemented with existing local resources before another provider is available.
No proposed score should reward an unreliable method merely for disagreeing.

## Resolve discrepancies using evidence

The controller should classify a discrepancy before choosing an action:

1. An extraction omission requests page/layout evidence and repairs the packet.
2. A missing or mismatched authority requests the specific edition or definition.
3. Different fact meanings open a separately versioned abstraction comparison.
4. Different formulas over aligned meanings request a concrete distinguishing case.
5. A legal argument requests supporting or defeating authority for its premises
   and priority, preserving the strongest located objection.
6. A formal-to-Java mismatch repairs the implementation and reruns dependent checks.

Every action records its target, source/input identities, permitted method,
budget, result and what new information it supplied. A new source or factual
abstraction invalidates downstream checks. A retry of identical reasoning is not
new evidence. Missing outputs, failed tools and unsupported fragments cannot count
as agreement.

Reconciliation can expose proposals to each other, but it cannot rewrite the
frozen initial record. A revision may retire a proposal only with its reason and
superseding evidence retained. The instruction is to find the source-supported
answer or explain the remaining alternatives, never to make the panel agree.

Stop an issue when required evidence resolves it, a declared resource limit is
reached, repeated actions produce no new information, or the available methods
cannot obtain the needed authority. In the latter three cases, report uncertainty
and the narrow residual question. Other independent issues can continue. More
calls are justified only when another permitted action could supply useful evidence.

## A concrete omission challenge

Consider a synthetic regulation: “A charge is prohibited when linked to a product
or product type, except for a genuine reduction of the subscription fee.” This
is a test fixture, not a quotation or interpretation of an SFC circular.

One reader encodes `linked_product AND NOT fee_reduction`; another encodes
`(linked_product OR linked_type) AND NOT fee_reduction`. A type-linked offer with
no particular product exposes the difference immediately. A source inventory
identifies the omitted words. The source, inventory and witness jointly justify
repairing the first candidate; a two-to-one vote would not be the justification.

A harder test gives both readers the first, wrong formula. The behavioral
comparison now agrees. The separate source-only inventory must still require
the type-linked route, and a scenario author who did not see either formula must
be able to supply a type-only case. A targeted mutation can additionally remove
the exception, reverse “or” to “and”, change the subject or shift the deadline.
These tests establish detection of specified planted faults; they do not prove
all natural omissions will be detected.

Finally, “genuine reduction” may itself be disputed. Define that term through
source-backed competing classifications rather than making it an unquestioned
Boolean input. If authority cannot settle the distinction, the correct result
is a scoped unresolved classification with its operational consequence shown.

## Acceptance must require a reason for confidence

For each proposed control, retain an assurance record containing:

- The exact claim, business perimeter, source editions and incorporated materials.
- Independent initial proposals, assumed definitions and shared dependencies.
- Required checks, their support/contradiction/unresolved outcomes and evidence.
- Material objections, distinguishing cases, repair attempts and resolution reasons.
- Formal/computation checks with supported domains and exact implementation hashes.
- Accepted assumptions, remaining uncertainty and the event that requires reopening.

This is a structured argument backed by evidence, not a generated confidence
percentage. It should make a false claim of completion easy to detect. The
aggregation/controller itself needs simple invariant checks and adversarial tests;
it must not be another unconstrained model that summarizes away objections.

An unresolved material discrepancy blocks automated approval of the affected
control. A lone unsupported objection is investigated and may be closed with a
recorded reason; it is not an eternal veto or an opportunity for quoted source
instructions to control the system. Every required check must execute within its
supported scope. Agreement alone never establishes completion.

The fallback for an affected bank operation must be explicitly authorized. Holding
a transaction, applying an existing approved control or requesting a narrow review
are possible policies; automatically choosing the most restrictive rule can itself
be wrong for a positive duty or time-sensitive obligation. Logical equivalence
across the supported readings may justify a shared consequence under a defined
policy, but does not resolve the readings' source ambiguity or missing-law risk.

## How to establish whether the redundancy helps

Predeclare the comparison before live experiments: one reader; multiple fresh
contexts using the same method; diversified methods; diversified methods plus
evidence-driven repair. Record actual resource use, give each arm its declared
cap, and avoid crediting diversity for simply receiving a much larger budget.
Accuracy remains primary; cost and latency are secondary measured outcomes.

Use source-family splits with references frozen before seeing outputs. Keep
official examples, internally adjudicated interpretations, unresolved disputes
and synthetic mutations distinct. A source's ambiguity can require a set of
acceptable readings; do not manufacture a unique reference for convenience.

For methods checking the same claim, measure individual material errors, joint
errors, same-wrong-answer agreement where meaningful, and the fraction of one
method's errors caught by another. For a proposed acceptance policy, measure
unsafe accepted cases among accepted cases, accepted coverage and reviewer effort.
Use confidence intervals that respect shared source families and report the
denominators. Zero observed failures or zero accepted cases must not generate a
claim of independence or a zero-risk estimate. Different types of check may need
failure-detection measures rather than a forced common output label.

The minimum challenge set includes a shared omitted exception, an incorrect
unanimous factual schema, a scanned qualification, an inapplicable authentic
citation, a wrong official-language alignment, a stale source edition, a reversed
output meaning and a compiler mutation. Freeze some challenge families until
evaluation; a detector tuned on every challenge is development evidence only.

No numeric legal-risk tolerance is invented here. The institution must define
materiality and acceptable risk for the intended scope. Until the requisite
evidence exists, demonstrations support draft investigation and shadow operation.
The goal is to focus internal or specialist review on reusable definitions and
residual disputes, not commission an external opinion for each clause.

## Implementation sequence and decision

First add a shared method-result/evidence contract, dependency declarations and
required-check policy. Then connect existing inventories, source criticism,
argumentation, search, questions, comparisons and bounded repair to one persistent
investigation. Add competing factual schemas and visual coverage. Integrate the
other agent's Catala route within its declared fragment without treating shared
input preparation as independent evidence. Expose the claim-level assurance
record and run the planted-fault suite before a held-out live study.

The pre-implementation audit must check the exact baseline, labels, applicable
fragments, missing-output behavior, independence assumptions, stop conditions and
whether the recorded evidence can answer the error-detection question. A failed
challenge triggers a focused repair and fresh evidence; it does not justify
lowering the acceptance criterion. This document does not replace that executable
phase plan, its review or the later live-run evidence contract.

Decision: proceed toward mandatory diverse assurance, with measured complementary
failure detection and explicit residual uncertainty. No automatic-clearance policy,
production deployment or new paid provider use is authorized or performed by this
research note. No claim of absolute correctness or statistically established
independence is made.
