# Next work after the source-driven search increment

The current implementation passes its engineering regression: P12 attempt 01
passed **310 tests**, including 78 search tests, and replayed all 45 recorded P8
pairs. P10–P12 added exact fact aliases, conditional correspondence analysis and
separate reviewer decisions. All 33 incompatible pairs remain explicit and
have complete review packets. P5 attempt 05 and P8 attempt 01 passed the earlier
one-round and multi-round live engineering criteria on both retained circulars.
Independent English-interpretation accuracy remains a separate question. The
[execution report](execution-report.md) records the evidence and failures that
determine this order.

## 1. Record the completed live acceptance

**Question.** Did the repaired current engine execute the bounded procedure
on 24EC50's submission-channel control and 23EC46's gift-promotion control,
while retaining every unsupported reading and blocking release?

**Authority and retained evidence.** The user authorized up to 100 total live
invocations, including earlier failures, with “you have 100 tests. continue”.
The plan and shared ledger both record that ceiling. The authorization receipt
preserves the first twelve reservations; P5 attempt 05 used eleven further
calls and passed. The extension does not require spending all 100. Retain all
previous failed attempts and the earlier successful one-round investigation.

P8 used three rounds and at most twelve calls per source, with at least two
actual rounds required. It consumed nine calls per source, for 41 of the 100
authorized invocations in total. The fixed runner, live output and skeptical
review are recorded in `operator-guide.md`, `p8-review.json` and
`artifacts/interpretation/round2/P8/attempt-01/`. The pilot read only retained
public source, without supplied candidate answers. A passed phase cannot be
rerun in place; future substantive repairs require a new phase and evidence.

**Pass criteria.** For each source: at least two actual investigation rounds,
all three initial roles return validated
generation, at least two commitments are retained, at least one accepted child
is created, and at least one isolated reconstruction is recorded. Any malformed
response is retained and either receives a validated bounded repair or causes
failure. All compiled candidates receive Java/Python probes. The terminal report
must remain blocked for unreviewed legal meaning. Inspect the statements,
citations, fact definitions and counterexamples after the run; test success is
an engineering result only.

**Vetoes and repairs.** Do not count an unavailable provider, a malformed final
response, lost dissent, unreported frontier, excessive calls or a failed Java
comparison as a successful run. Diagnose the actual failure, make the smallest
discriminating repair, add its regression, and refresh/review the phase.
The six-attempt engineering bound and separate live-call allowance remain in
force. Exhausted allowance is a continuation veto for live work, not authority
to reset the ledger or replace the criterion with fixture playback.

Both sources passed these engineering criteria. Their reports remain
`BLOCKED_UNRESOLVED`, and their maximum live-tree depth was one. P9 then
verified depth-two descent in a deterministic local fixture for both schedulers
and reran the full suite. These outcomes show that the implementation executes
the bounded search and preserves uncertainty; they do not show that it found
every legally plausible reading or that any generated reading is correct.

The 100-call ceiling has 59 unused slots. Do not spend them without a new
source-driven question and a reviewed evidence contract. A failed candidate or
bad model response does not by itself reject the multiple-interpretation
approach; it identifies a repair or a source-review question.

## 2. Build an independent interpretation reference

Before generation on a new held-out circular, assign at least two independent
source readers and a distinct adjudicator through the implemented annotation
API. Supply the whole retained source, footnotes and available referenced
authorities. Record unavailable material. The readers identify duties, scopes,
exceptions, dates, material alternatives and unresolved questions without
seeing system candidates. The adjudicator records the admissible set and its
uncertainty. Do not force a single answer where the evidence permits several.

Use the seven earlier development circulars for debugging only. Select held-out
sources across different mechanisms: time transitions, scope/definition
boundaries, exceptions, continuing duties, discretion, cross-document
dependencies and amendments. The sample size and acceptable unsafe-clean rate
must come from an explicit review/evaluation protocol; no numeric accuracy
threshold is approved by this plan.

The software checks distinct local identities, source binding and completeness
of adjudication. The organization must establish actual reviewer qualifications,
independence and authority. A second model cannot supply that evidence.

## 3. Compare procedures without rewarding abstention

Predeclare equal source access and invocation budgets. Compare a single-reading
baseline, three-role generation without search, BFS investigation and UCT
investigation. These are candidate procedures; UCT is not presumed superior.
Preserve all runs and provider versions. Evaluate against frozen adjudication
using `evaluation.compare_frozen`.

The primary criteria must jointly address unsupported clean decisions and
useful coverage. Report omitted duties, retained material alternatives, incorrect
pruning, abstention, unresolved source units, reference incompleteness and
reviewer effort. Group uncertainty calculations by circular, because multiple
questions from one circular share source and model errors. With few independent
circulars, treat observed differences as descriptive. Neither high agreement
nor fewer unsafe decisions achieved by blocking everything establishes useful
legal interpretation.

The resulting plan must specify sample size, repeated-run policy, model
diversity, uncertainty estimation, promotion criteria, vetoes and resource
budget before it runs. The current implementation supplies bookkeeping; it
does not supply an approved statistical study or calibrated legal probability.

## 4. Review correspondences and define the next representation increment

The fact-correspondence increment is complete for its restricted scope. Its
[result](fact-alignment-result.md) and [operator guide](operator-guide.md)
describe the executable workflow. P12 retained 18 of 21 24EC50 pairs and 15 of
24 23EC46 pairs as incomparable. None differed only by exact metadata renaming.
The [24EC50 review index](../../../artifacts/interpretation/round2/P12/attempt-01/replay/24EC50/review-packets/index.md)
and [23EC46 review index](../../../artifacts/interpretation/round2/P12/attempt-01/replay/23EC46/review-packets/index.md)
are ready for qualified reviewers. A proposal must state all changed input
assumptions and what the output means. Acceptance permits conditional analysis;
it cannot certify legal meaning or resolve the original investigation.

The hypothetical 24EC50 example found no difference in 36 probes after equating
submission events, timing conventions and routes. It remains conditional.
Review must address dispatch versus receipt, product classification, available
earlier guidance and the bank's actual data bindings. Reviewers may reject or
leave a mapping unresolved. These candidate-exposed packets must remain
separate from the source-first reference study in section 2.

Two concrete representation gaps remain available for the next engineering
phase, which must receive its own audit before execution:

| Task | Required implementation | Discriminating acceptance |
|---|---|---|
| Explicit output convention | Bind a named selected control and meaning of each result value/status into candidate commitments and review | Equal Boolean values with compliance-versus-restriction meanings must not be silently treated as legally equivalent; retain original histories and unsupported legacy conventions |
| Derived fact correspondence | Define a restricted typed expression mapping, including the shared observation source and three-valued semantics; store all decomposition assumptions | Compare a combined `gift_offered` with separate offer and gift facts; test UNKNOWN, conflict, scope and hidden-exception cases; replay original Java with derived snapshots; retain conditional status |

Do not implement many-to-one correspondence merely by dropping facts. First
state the target relation, direction of derivation, admissible input domain,
and what an unknown derived fact means. No next-phase execution or acceptance
is claimed here. The unchanged P8 histories and P12 packets are its concrete
starting cases. A failed representation hypothesis motivates a revised
candidate unless it invalidates the source, semantics or harness.

Other extensions depend on observed failures and the held-out source needs:
quantified duties, temporal/event composition, reviewed source acquisition,
structured legal attacks and priorities, and human decisions linked to a
successor investigation. The current restricted RuleIR and behavioral attack
graph are explicit boundaries. Before extending them, write the target
semantics, negative examples, Python/Java obligations and review requirements.
Do not describe a new scheduling heuristic as a proof of legal fidelity.

## Decision boundary

| Work | Can proceed with current authority? | What would justify the next step? |
|---|---|---|
| Local code review, documentation and regression repairs | Yes | An observed defect and a discriminating check |
| Conditional correspondence review | API and 33 packets ready; actual qualified reviewers missing | Record substantive decisions and assumptions; all analyses remain conditional |
| Output convention or derived-fact extension | Local design and implementation authorized; no acceptance claimed | Target semantics, negative examples, original-Java replay obligations and a reviewed new phase |
| New source-driven live run or repair | Yes, within the remaining 59-call ceiling and a new reviewed phase | A concrete source question, bounded budget and skeptical evidence contract |
| Human reference annotation | Software is implemented; actual reviewers are missing | Qualified independent people and an authorized adjudication process |
| Comparative legal-accuracy study | No study has been accepted yet | Frozen held-out references and a reviewed evidence contract |
| Java production release | No generated candidate is eligible | Exact-candidate meaning, engineering, applicability and institutional approvals |

The next result must state whether a failure invalidates the source, harness,
encoding, Java implementation or current model proposal. Continue a planned
repair when it addresses that failure. Stop dependent execution only for its
declared continuation veto, and retain every unresolved issue in the report.
