# Design for completing the legal answer and evaluating tool contribution

10 October 2026, Hong Kong time. This is the reviewed design remainder of
`product-contribution` under [mission control](legal-interpretation-mission-control.md).
It is not a new execution program, grant, phase or reset of consumed effort.
The current request asks how to design the remedy and whether the gaps can be
closed. This package contains source/code inspection and design only.

The engineering failures have plausible, testable remedies. We can also finish
a finite evaluation of whether the selected tools help the product. Neither
outcome guarantees that the retained legal authorities select one interpretation,
that every tool helps, or that general English interpretation is solved. A useful
answer may give supported conditional conclusions and identify a genuine legal
ambiguity. That is different from leaving the question unanswered or declaring
the underlying legal obligation fulfilled.

## Starting evidence and the result we need

The [completed repair result](../implementation/legal-mission-control/results/context-boundary.md)
is the engineering baseline. Qualified source delivery and context-sensitive
cache reuse passed their local controls. An installed-backend investigation and
whole-dossier answer consumer connected on a synthetic fixture. Its answer was
deliberately legally empty. The separate full-source preparation reconstructed
four documents and 55 packet units; initial qualified inventory envelopes were
94,160 and 94,244 bytes. These results do not establish full-target capacity,
faithful reduction, a correct legal answer or tool benefit.

The historical stream used its own sources/question, with 492 pairs and 984
assessments. Its 1,927-record archive reconstructs, but a required review request
is 200,035 bytes against 200,000. A shared 211-byte reconciliation value has 41
occurrences, coupling their contexts and 54 dependency records. The correct
attribution is retained in
`artifacts/legal-mission-control/2026-10-10/context-boundary/capacity/failure-context-inputs.json`.
Do not use the earlier attribution from sorted JSON: sequential record IDs
referred to different rows. The historical stream is a regression case, not a
substitute for the full target.

Code inspection identifies two further risks, without executing another repair:

- `CompleteInvestigation.run` wraps a qualified provider in `ContextProvider`.
  The live branch of `scoped_investigation.investigate` requires an instance of
  `CodexProvider` with `GrantedAllowance`. The wrapper is not that class, so a
  valid underlying live provider would fail this guard. The offline fixture
  bypasses the branch. This is a code-derived blocker, not a reproduced live
  failure. `single_reader.run` has a similar guard; include it only if the chosen
  route reaches it.
- `dossier_answer.py` permits 64 reviews of up to 4,000 bytes each, then includes
  all reviews in interaction and synthesis requests capped at 200,000 bytes.
  The allowed review outputs alone can total 256,000 bytes. The current runtime
  overflow check stops safely, but the permitted maxima do not guarantee a
  completable run. Small scripted receipts did not qualify this aggregate bound.

The substantive baselines are the retained
[P10/evidence](../implementation/legal-mission-control/results/p10-standard.md),
[P14](../implementation/legal-mission-control/results/p14-attachment.md) and
[Gatecoin](../implementation/legal-mission-control/results/gatecoin-transfer.md)
results. Preserve the exact four questions in the original T0 questions file,
the 46 original obligations and all 35 original readings, including 32 presently
unformalized readings. There are no obligation closure decisions. Six of the
26 surveyed tools are selected and none is fully evaluated.

The deliverable is a complete answer to each original question, accompanied by
an inspectable argument from sources and stated facts, competing interpretations,
the strongest contrary, and the practical consequence of each unresolved premise.
An evaluation must then show what the tools changed in that answer. Coverage
receipts and solver agreement are supporting engineering evidence only.

## One source-linked argument from reading to answer

Use the existing source, candidate, criticism and answer interfaces. Add only the
missing relationships needed to explain an inference. Each material proposition
should identify:

1. Its original question, reading and obligation links. Preserve unmapped items
   explicitly; a new graph must not invent equivalence to an original obligation.
2. Its actor, action or duty, object, trigger, assessment interval, instrument
   version, jurisdiction and arrangement. Distinguish the source's statement
   from an interpretation, a supplied fact, an assumption and a computed result.
3. Exact supporting and contrary passages, with document/locator identity and
   the existing source qualifications. A quotation match proves location, not
   that the passage supports the proposed inference.
4. The inference from its premises to its conclusion, including exceptions,
   defeaters, priorities and any evidential default. Mark each warrant as
   supported, disputed, assumed or missing, with its reason. A model's
   `SUPPORTED` label alone does not establish the warrant.
5. The conditional consequence of accepting each supported rival, and the
   particular authority or fact that could discriminate between them.

This representation must retain scope of negation, conjunction, quantifiers,
modals, reference to actors/objects, footnote attachment and temporal conditions
where they affect the answer. Unknown facts stay unknown. Absence of a fact is
not falsity unless an applicable evidential rule justifies that treatment.
Responsibility, duty activation, conduct, fulfillment and evidential sufficiency
remain distinct propositions. An unformalized interpretation remains available
to the answer and contrary review.

The 35 original readings are not the same population as the twelve candidates
in the later generated dataset or the current twelve-candidate generation
default. Preserve the original inventory as an acceptance cross-reference and
record what each fresh investigation covers or omits. If material readings are
missing, a completed candidate-generation stage is insufficient. Do not seed
only one trial arm with the omitted interpretations or report coverage of all
original readings from a smaller generated count.

Formalization is justified by agreement with the source-supported conditional
consequences, not by whether a parser accepts it. For every formalized reading,
use a minimal distinguishing example and its strongest rival. If the mapping
cannot preserve the difference, retain the natural-language reading and mark the
tool profile unsupported. Do not manufacture a unique meaning to make it runnable.

## Repair the evidence consumer without losing occurrence context

The candidate design separates three identities:

| Identity | Meaning | Required behavior |
|---|---|---|
| Content | Exact value under a versioned serialization and kind | Identical contents may share storage; retain the original archive and ordering template. |
| Occurrence | Content in a particular dossier path, role and ancestor context | Every occurrence receives its own review assignment; identical wording does not merge legal or procedural roles. |
| Dependency | A typed relation from this occurrence to a definition, premise, contrary, exception or other occurrence | Deliver the referenced content with the context needed for that relation; unresolved references remain explicit. |

Stable archive identities should bind content and structural paths instead of
depending on dictionary traversal order. Compact request-local aliases may
reduce transport overhead only through a validated, hash-bound mapping to those
identities. Preserve all original raw files and exact reconstruction; this is a
new representation of the candidate, not a rewrite of historical evidence.

Assign occurrence-specific homes, then calculate the definitions and context
needed for that home. A reconciliation occurrence in batch 0 does not acquire
the full context of 40 other batches merely because their scalar text is equal.
Conversely, a real relation to another batch must remain an explicit dependency.
Validate orphaned and ambiguous definitions, role changes and repeated content
in conflicting contexts. Definitions nested in a substantive row retain the
whole row. Do not split an indivisible legal argument merely to fit a request.

Use typed reference fields where the current schema identifies them. Unknown
forms must receive conservative context or an unsupported disposition; failure
to recognize a reference cannot silently remove it. Archive completeness is
checked separately from review delivery. A complete archive alone does not show
that the relevant material reached the reasoning step.

Mandatory interaction review must consider the full qualified sources, every
reading, explicit cross-group relations, incompatible warrants and unresolved
dependencies. Reviewer nomination of a cross-record ID is insufficient: a
reviewer can miss the exception. Include known typed relations automatically,
and adversarially test an exception placed outside its supporting rule's group.
Source-based substantive review must still assess relations absent from the
graph. Graph coverage does not prove completeness of legal reasoning.

Before dispatching any review, plan the aggregate interaction and synthesis
envelopes. For each, reserve serialized bytes for fixed source/question/context
fields, every permitted review output, the interaction output where applicable,
tool accounts and the raw dependency material that may be needed. The complete
reserved envelope must fit the existing 200,000-byte cap. Calculate actual
serialization overhead and compact mappings, not a sum of unencoded text lengths.
Also verify that the minimum occurrence accounts and substantive findings can
fit their output allowance. Do not solve input overflow by assigning an output
budget that cannot describe the required work.

Unknown requested dependencies need a declared bounded allowance. If their
required closure exceeds it, preserve the result and return `UNDER_CAPACITY`;
do not discard a contrary or present an unresolved interaction as cleared.
Reserve worst-case output space before the reviews, then check actual requests
again before every dispatch. Full-target pair/reading counts are generated
dynamically, so source admission and later dossier admission remain distinct.

This proposal uses one review layer, one mandatory interaction review and one
synthesis. It does not silently add recursive summaries or retries. If the
smallest faithful occurrence group or aggregate cannot fit, reject this candidate
for that target. A different architecture would require a specific method and
resource decision. The repair criterion is not merely saving the observed 35
bytes; it is preserving context while qualifying all stages of the declared
input/output envelope. Feasibility at the real target remains to be demonstrated.

## Preserve live authority through the qualified route

Retain the existing live authorization requirement. Use an explicit audited
provider composition or a narrow verifier for known qualification wrappers that
validates the actual underlying `CodexProvider` and its `GrantedAllowance`.
Do not authorize arbitrary objects because they expose `live`, `allowance` or
`provider` attributes. Verification must preserve the underlying service route,
authorization identity, per-arm and global spending, absolute deadline, context
binding and final encoded request size. The actual provider reserves each
dispatched call exactly once; wrapper validation must not charge a second call.

Validate the chosen composition before the core stage can spend calls. Inspect
the selected route for the similar single-reader guard; avoid widening a repair
to an unused mode. Offline controls should exercise valid qualified composition,
fake wrappers, a wrong/missing/expired grant, route substitution, mutated source
qualifications, oversize final input, reservation failure and cache reuse. Fake
live transports may record attempted dispatch without contacting a service.
The minimum reproducer must confirm the code-derived failure before repair.

A new live protocol also needs an explicitly reviewed grant adapter. Generic
`GrantedAllowance` expects an exhausted predecessor; the retained specialized
coverage ledger is expired with 49/200 calls, not exhausted. Do not falsify that
ledger, reuse its expired deadline constants, or assume its specialized provider
is suitable for a new experiment. Any new grant must preserve old spending while
recording its own reviewed scope. Local qualification and live authority are
separate decisions.

## Legal acceptance cases and the evidence that could close them

These acceptance cases come from the retained dossiers. They are review criteria,
not new holdings or an executor-authored answer supplied to only one trial arm.

| Question | Answer behavior that must be demonstrated | Remaining legal/factual evidence |
|---|---|---|
| P10 and evidence | Keep allocation, conduct and outcome readings separate. Explain why matching registrar and chain records can share a stipulated rights error. Analyze a discrepancy in a secondary copy using its role, timing and update standard. Keep P10 distinct from P11. | Applicable construction addressing whether a specified defect despite competent supervision/remediation defeats P10 itself, and over what period. Actual rights, constitutive terms, record roles and chronology for a real arrangement. |
| P14 | Distinguish request, confirmation, demonstration, object and standard; preserve A/B/C. Separate report existence, reasonable reliance, technical assurance about the deployed version, P10–13 compliance and SFC satisfaction. Analyze no-request and V1-audit/V2-deployment cases without inventing facts. | Applicable clarification/construction of footnote 5 and confidence attachment. The actual request and scope/version correspondence only when assessing a specific arrangement. |
| Gatecoin | Preserve event-specific prima facie treatment and rebuttal conditions. The same date with a different transaction category may change the inference. Relevant login/withdrawal evidence can defeat the automatic-entry inference. Preserve distinct parties and asset-capability versus actual trust. | Exact target rights, terms, parties, law and record role; dated later-treatment research for a current-authority claim; correction or authoritative treatment of the scenario-seven tension. |

A focused authority search should address those exact contrasts, retain search
date and scope, and inspect both supporting and contrary primary sources. New
source acquisition is not performed or authorized by this design. A search that
finds no clarification does not establish that none exists. Conditional source
analysis can proceed without private client facts; actual compliance cannot.

For each original obligation, record the answer before/after, source-supported
inference, strongest contrary, remaining dependency and reviewed disposition.
Keep a conditional product answer separate from legal resolution and actual
compliance. Do not count all 46 obligations closed because every row has a status.
Existing source results are reused, not counted again as new substantive advances.

## Evaluate the tools on their actual contribution

The first experiment remains one complete P10/evidence case with two independent
product investigations: optional backend absent versus explicitly injected.
Use identical full sources, qualifications, exact questions, model/service route,
method, prompts, source access and nominal effort policy. Generate inventories,
readings and criticism independently in each arm. No historical excerpt packet,
handwritten complete answer or synthetic dossier substitutes for this test.
Freeze evaluator criteria and distinguishing cases before seeing either answer.

Retain arm order and actual effort. A different runtime or call count may be a
downstream treatment consequence; record it rather than hiding it. If an arm
cannot complete within the admitted envelope, no complete-answer comparison is
available. A single completed pair supports a descriptive case analysis, not a
causal ranking or general superiority claim. Evaluation of a specific changed
inference needs its source-to-warrant reasoning, not just different prose.

| Selected tool | Proposed contribution and discriminating test |
|---|---|
| BM25 | Locate useful and contrary passages within the same full packet. Inspect the known missed qualifications and whether the answer uses them despite retrieval omissions. Keep full source access in both arms. |
| LegalRuleML | Preserve a supported rule representation. Trace semantic loss, invalid-but-well-formed shortcuts and unformalized readings through to the answer; round-trip validity alone is not benefit. |
| PyArg | Compute the declared argument semantics on reviewed premises and defeats. Test false warrants, missing undercuts and an added decisive contrary, then inspect downstream use. |
| Carneades | Evaluate its actual configured argument profile separately. Agreement with another engine is a computation check; record whether it changes, duplicates or harms the legal answer. |
| clingo | Check the encoded stable-extension consequences. Preserve the distinction from grounded/preferred semantics; no stable extension must not be treated as legal falsity. |
| Logical English | First specify a supported conditional and its rival, then qualify the source-linked controlled-language mapping and product adapter. Test negation, scope, unknown facts and unsupported readings. Parser examples are insufficient. |

The current argument adapter's at-most-twelve-eligible-arguments profile is a
target limitation, not permission to prune a larger material graph. Unsupported
graphs stay visible in the answer. Test an unsupported profile as such. Logical
English is not yet adapted; exclude it explicitly from any earlier bundle claim.
If independently selectable engine feedback is absent, that narrow adapter
capability must be qualified before an individual-tool comparison is claimed.

After a valid first pair, use individual applicable tools and the combined
configuration on the original questions. Controlled ablations on a fixed retained
dossier can help attribute a change, but cannot replace the independent-generation
product trial. Preserve raw tool input/result, downstream delivered request,
answer passage, source review and negative/unsupported outcome for each tool.
Classify contribution as supported in this case, no observable contribution,
harmful, unsupported profile or inconclusive; none should be forced to be helpful.

Keep all 26 existing dispositions. Conceptual HYPO/CATO/AGATHA ideas, deferred
systems, target-unsuitable tools and supporting infrastructure are not relabeled
as integrated. General accuracy claims require independent heldout cases and a
separately funded replication/uncertainty protocol. Do not select a deployment
default from one stochastic pair or from the same cases used to repair prompts.

## Finite sequence and resource design

This is one dependency sequence within the existing mission, with a recorded
return after each admitted package. It grants no execution itself.

Current offline inspection supports a design specification, not a numerical
promise that all subsequent steps fit a particular allowance. The next
engineering admission must name a wall-time deadline, one candidate/attempt,
zero live calls and installations, exact local commands, and an immutable result
path. Its reviewed mission revision must retain the three prior detours. The
later live amount remains unset until its actual stage/cost envelope is reviewed;
the symbolic accounting below must not be converted into an invented budget.

| Step | Concrete work and deliverable | Exit / return condition |
|---|---|---|
| 1. Fix the substantive acceptance specification | Reuse the three dossiers and original questions; freeze the argument requirements, distinguishing cases and source/contrary rubric above. | Every proposed test addresses an original inference; missing authority has a conditional branch rather than a fabricated standard. This design supplies the specification for review. |
| 2. Qualify one consolidated engineering candidate | Reproduce the wrapper failure offline; implement occurrence-specific packing, aggregate budget admission and audited provider composition in the existing path. Retain one exact full-path local qualification and historical regression, plus adversarial failures. | Require exact evidence reconstruction, preserved occurrences/relations, authorization controls and feasible aggregate envelopes. One admitted attempt with an explicit time/repair limit; success or failure returns to `product-contribution`. This requires a reviewed revision because prior attempts are consumed. |
| 3. Freeze a costed two-arm pilot | Bind actual source preparation, route/settings, review limits, grant adapter, stage reservations, monetary ceiling and exact narrow command in a manifest. | No live admission until resources and local prerequisites are concrete. One grouped resource/command decision when ready. |
| 4. Run and assess one P10/evidence pair | Produce full answers and trace tool feedback to supported/unsupported inferences; retain rejected outputs and actual spend. | Inspect the substantive result before expansion. Candidate legal failure triggers the predefined source/argument review; it does not automatically authorize another engineering repair. |
| 5. Complete the finite question/tool evaluation | Under a separately costed remaining envelope, assess P14/Gatecoin and individual applicable tools, including the Logical English mapping. Record original-obligation dispositions and remaining law/facts. | Stop at explicit dispositions and reviewed answers. Benefit is not guaranteed, and unresolved law is not hidden by task completion. No appended phase or reset of the cumulative bound. |

The old 176-call illustration is stale for the current consumer. A correct
symbolic ceiling for a two-arm protocol is

`sum_over_arms(core + question_assignment + scoped + challenge + review_groups + 2) + assessment_calls`.

The final two calls per arm are mandatory interaction and synthesis. Challenge
and assessment calls are zero only if explicitly excluded from the frozen method,
with the resulting claim limit stated. Include charged failed calls and declared
repair attempts; no automatic retry. Use actual configured ceilings, not this
expression as a grant amount. With two scoped perspectives and batch size 12,
492 historical pairs require at least `2 * ceil(492 / 12) = 82` initial scoped
calls, already above CompleteInvestigation's default 48. This is an explanatory
historical scale check, not a prediction of the full target's pair count.

Before generation, reserve bounded maxima for both arms and all remaining
stages, including answer/review and any assessment calls. After claims/readings
are generated, check the actual pair matrix and byte plan before the next stage.
Protect the second arm and answer budget from first-arm overruns. If the target
cannot fit, retain that under-budgeted result without dropping readings or pairs.
Source-only feasibility cannot justify the live pilot's downstream budget.

The service's monetary and token capacity remains unqualified. Inspect the actual
nonsecret route/settings and applicable pricing before a proposal; do not invent
a dollar ceiling from generic pricing. The manifest must include commit plus
hashes of dirty executed sources, command, environment, CPU/GPU choice, source
versions, provider/model settings, seed if supported, wall-time deadline,
per-stage/global limits, artifact paths, plan and result paths. Hardware is CPU
only unless a later explicit plan requires otherwise.

Use exact simple repository-root commands and a narrow reviewed wrapper when
an executable pilot exists. The wrapper must admit only the frozen invocation,
preserve spending across resume and refuse expired/exhausted resources. Do not
describe a proposed command or an application allowlist as already installed
host permission. This package changes no allowlist and launches no provider.

## Evidence contract and skeptical review

Main question: can the real product answer the original legal questions with
supported inferences and conditional alternatives, and which tools contribute?
The mechanism under test is contextual evidence delivery plus explicit warrant
review and optional computational feedback. The engineering comparator is the
current frozen failure and installed synthetic connection; the product comparator
is the same full investigation without the optional backend. These comparators
must not be exchanged.

| Diagnostic role | Predeclared criterion and response |
|---|---|
| Primary engineering pass | Correct reconstruction and occurrence/dependency delivery, valid authorization composition, and bounded complete dispatch envelopes on the admitted profiles. A pass permits a feasibility pilot, not legal promotion. |
| Primary product acceptance | Complete source-supported answers meeting the question-specific criteria, preserving contrary readings and uncertainty. A correct conditional answer can pass while the legal obligation remains unresolved. |
| Tool-contribution criterion | Trace a source-reviewed answer effect to actual product tool use under a valid matched protocol. No effect or harm is a reportable result; one pair cannot establish statistical superiority. |
| Promotion veto | Unsupported warrant, changed legal target, lost decisive contrary, unknown-as-false, false tool/legal equivalence, or insufficient evidence of downstream consideration. Reject the affected claim; continue already planned independent substantive work. |
| Continuation veto | Invalid/corrupted inputs, mismatched comparison, unavailable required route, unauthorized dispatch, exhausted resources, or a declared capacity failure. Stop that affected execution and retain its result. This does not reject the entire legal research direction. |
| Repair trigger | A reproduced blocker of an admitted substantive task. Only the expressly bounded admitted repair is available; failure does not create another attempt. |
| Explanatory only | Test totals, record counts, request bytes, runtime, solver agreement and one-pair descriptive differences. They cannot establish legal correctness or a preferred default. |

Material assumptions/defaults reviewed:

| Choice and status | Provenance / justification | Failure mode and earliest diagnostic |
|---|---|---|
| Retained full sources and qualifications; baseline | Existing mission source preparation preserves the target. | Incorrect edition/authority or lost reconstruction caveat; check source identity and qualification before generation, retain applicability limits. |
| Occurrence-specific grouping; hypothesis | Exact retained failure shows duplicate content coupling unrelated contexts. | Omitted cross-context exception; conflicting-role duplicate and separated-exception controls, then source-grounded review. |
| One reduction layer and 200,000 bytes; inherited constraint | Current method and provider cap, not a proven target capacity. | Required material cannot fit; predispatch aggregate/minimum-output screen, explicit under-capacity result. |
| Known-wrapper grant verification; hypothesis | Existing live guard rejects qualified composition by class identity. | Fake authority or duplicate charge; offline adversarial wrapper/reservation controls before spending. |
| Existing scoped/candidate/argument limits; inherited baselines | Current code, not target-specific adequacy evidence. | Silent truncation or under-budgeted target; actual generated pair/graph admission, including the twelve-argument adapter limit. |
| Same-source backend-off/on pair; diagnostic design | Minimal complete product comparison already selected by the mission. | Different inputs, failed arm, model randomness or unequal effort mistaken for benefit; freeze method, retain arm order/spend, limit conclusions to inspected case evidence. |
| Source-reviewed conditional acceptance; reviewed design choice | Legal ambiguity and missing client facts are real constraints. | Evasion disguised as uncertainty; require substantive branch consequences, strongest contrary and exact discriminating evidence. |

Skeptical verdict: **the design is suitable for a bounded implementation proposal;
live execution is not ready**. The review rejected four tempting shortcuts:
saving only 35 bytes, using the synthetic success as full-target qualification,
reusing the 176-call estimate, and weakening the live grant guard. It also
rejected a larger tool matrix before the first complete substantive answer.
Wrong baselines, proxy promotion, hidden output limits, grant/environment mismatch,
unfair source access, missing stops and artifacts that answer only a plumbing
question are addressed explicitly above.

The main remaining design uncertainty is whether occurrence-specific grouping
and finite aggregate output allowances can preserve enough raw context at the
actual target scale. The next smallest discriminating engineering result is the
bounded local qualification, not a larger live allowance. The strongest
alternative explanation for disappointing tools is an unsupported source-to-rule
mapping; more invocations cannot supply that warrant. Source review and final
answer assessment are therefore acceptance requirements, not later polish.

This review is the executor's code/source audit, not independent legal
adjudication or a second model's review. A source-grounded independent legal
review is needed before a production-readiness claim. No stochastic comparison
ran in this package and no ranking is supported.

| Decision | Primary criterion status | Veto status | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Retain this design | Specific defects, legal criteria and finite comparisons are identified | No design-only continuation veto | Candidate feasibility and actual legal/tool behavior | Review a bounded engineering revision and concrete pilot resource requirements within the existing mission | Another repair or live run is approved |
| Keep mission open | No new complete answer or tool evaluation | Substantive promotion evidence missing | Authority, interpretation and downstream contribution | Preserve all original questions/obligations/readings and record this package as `no_advance` | General English accuracy, legal compliance, tool benefit or completed integration |

Three engineering detours remain counted; the ordinary maximum remains one.
The latest 120-minute offline attempt is consumed and its window expired at
02:38:48 HKT on 10 October. No fourth attempt, live calls, external acquisition,
installation, GPU work, commit or push is authorized by this design. Historical
grants, deadlines and results remain intact. Local design/document work and
mission refresh require no additional permission.
