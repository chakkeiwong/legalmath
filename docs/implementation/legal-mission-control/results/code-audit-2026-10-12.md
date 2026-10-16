# Current product audit: partial repairs, incomplete integration

12 October 2026. The product is not fully integrated or legally qualified.
The principal causes are incomplete wiring of the latest repairs, conflicting
failure policies across layers, an incomplete whole-route capacity model, and
missing source-warranted inputs that would let the selected tools address the
substantive questions. These are different problems and need different evidence.

The previous statement that the local repair program had been executed was too
strong. Parts of its references, isolation and product-check branches were
implemented and tested. Its legal-target, actual applicability, scope/resource,
wrapper/approval and mission-closeout work was not completed. The largest
reported combined regression run was 52 passing tests; overlapping smaller runs
must not be added to that total. Those tests did not produce new legal answers
or establish native-engine contribution on newly warranted inputs.

This audit implements no product repair. It traces the current worktree, runs
nine new deterministic diagnostic cases and a separate capacity probe, and
retains their evidence. All nine assertions passed: several deliberately assert
that a gap is reproducible. The provider-disconnect test uses the real consumer
and budget guard with a scripted provider. It is not a live disconnect experiment.
No provider call was made. During the diagnostic, all monitored source files,
mission state, allowance files and retained answer/review responses were unchanged.

## Route traced and evidence boundaries

The normal route runs `CompleteInvestigation.run`, source inventory and candidate
generation, optional tool checkpoints, question assignment, scoped source
assessment, proofs and replay, then produces a dossier. The consumer
`dossier_answer.propose` verifies that dossier, groups its evidence, obtains
group reviews and an interaction review, and synthesizes an answer. Its terminal
success is explicitly `STRUCTURALLY_VALID_PROPOSAL`; legal correctness and
release eligibility remain false.

The version-5 trial used a different, focused route in
`scripts/legal_mission_answer_tools_recovery.py`. It supplied retained sources,
four readings and a reviewed argument graph directly to eight answer arms, then
reviewed eligible answers. That trial exercised actual adapters and real model
answers, but did not complete the normal investigation route. Its results cannot
qualify a different whole-product configuration.

The audit inspected these routes, the new helper modules, their callers, the
tool catalogue, current mission state and retained substantive dossiers. The
call-site scan covers `src`, `scripts` and `tests`; it does not rule out external
callers outside this repository. Historical runs and other optional semantic
branches were not all re-executed. Source hashes identify the dirty worktree;
the git commit alone does not identify this implementation.

## Confirmed engineering and integration gaps

### G1. The new backend and reference checks are not selected by a product runner

The new `IndependentProductToolBackend` has no instantiating caller outside
tests. Both `optional_tool_failures='continue-independent'` and
`continue_independent_reviews=True` are likewise selected only by tests. Existing
product runners continue to instantiate `ProductToolBackend`. The new
`prepare_answer_review` helper has only a test caller, and legal-locator
construction/validation has no product caller. The audit's caller inventory is
retained in `code-audit/call-sites.json`.

The old default backend also selects five tools; Logical English requires an
explicit selection. Several mission runners correctly select all six, so this
is a configuration distinction, not a claim that Logical English has never
been integrated. A successor must name its actual selected backend and tools,
then exercise the consumer through that same entry point.

Code: [product session selection](/home/chakwong/python/legalmath/src/legalmath/interpretation/assurance/complete_investigation.py:197),
[backend defaults](/home/chakwong/python/legalmath/scripts/legal_integration_tools.py:20),
[new backend](/home/chakwong/python/legalmath/scripts/legal_independent_tools.py:32).

### G2. The normal answer contract does not enforce legal paragraph citations

`AnswerClaim.support` contains source-unit quotations; `validate_answer` checks
those quotations, identities and accounts. A paragraph number appearing in prose
has no corresponding structured legal-locator validation. The real LegalRuleML
arm's P19/P20 error passed both answer validation and a fresh review. A literal
quotation therefore does not prevent a false paragraph attribution.

The old focused review also permits empty preservation quotations and searches
concatenated answer fields. The previous local regression tests establish those
weaknesses. The new field-span helper repairs those particular structural checks
only when a caller uses it. Historical failed outputs must remain failed; changing
the sealed validator would not supply a fresh accepted answer.

Code: [normal answer validation](/home/chakwong/python/legalmath/src/legalmath/interpretation/assurance/investigation_answer.py:281),
[focused review](/home/chakwong/python/legalmath/scripts/legal_mission_answer_tools_recovery.py:503).

### G3. The proposed locator helper does not verify its claimed original source

Confirmed with the actual retained staff-competence source unit. The genuine
HTML maps it to P19 and rejects P20. Supplying replacement HTML that places the
same text in a list starting at 20, while retaining the genuine original file's
path and SHA256, produces an index that accepts P20. `build_index` trusts the
caller-supplied `source_ref`; `validate_citation` checks internal hashes but never
verifies that the HTML came from that file or that the index is the approved one.

This is a missing provenance prerequisite in an unused helper, not an observed
attack on deployed answers. Closing it requires loading and checking the retained
original, binding units to that document, and binding the approved index and
extraction profile into the consumer request. A self-consistent hash cannot
substitute for the expected source identity.

A separate parser boundary is reproduced: a wholly emphasized substantive
paragraph is removed as a heading and becomes `UNLOCATED`. This is a synthetic
layout control, not a claim that the retained SFC page has that layout. The
previously generated index also lacks a source-file SHA256 and predates the
heading-parser edit. A current verified index and explicit support limits are
needed before use with further circulars or judgments.

Code: [index construction](/home/chakwong/python/legalmath/src/legalmath/interpretation/assurance/legal_locators.py:98),
[citation check](/home/chakwong/python/legalmath/src/legalmath/interpretation/assurance/legal_locators.py:125),
[heading heuristic](/home/chakwong/python/legalmath/src/legalmath/interpretation/assurance/legal_locators.py:74).
Evidence: `observations/source-identity.json`, `observations/emphasized-clause.json`.

### G4. The new review contract does not establish mandatory review coverage

Confirmed using the actual baseline review context, which carries seven
acceptance obligations and five cases. Replacing its requested review population
with one invented obligation tied to P10 allows `PASS_WITH_LIMITS`. The validator
correctly covers the requirements it receives, but the constructor does not
check those requirements against an authoritative question/obligation/case
register. This permits an incomplete caller to request an incomplete review.

The evidence catalogue also omits conditional alternatives, claim assumptions
and unresolved premises, reading explanations and tool accounts. These remain
visible in the supplied answer, but the reviewer cannot select their fields as
structured evidence. The new schema has no separate validated source-support
field even though its instructions request source support. Coverage, answer
location and source warrant therefore still need distinct checks.

Code: [requirements](/home/chakwong/python/legalmath/src/legalmath/interpretation/assurance/answer_evidence.py:59),
[catalogue](/home/chakwong/python/legalmath/src/legalmath/interpretation/assurance/answer_evidence.py:18),
[review validation](/home/chakwong/python/legalmath/src/legalmath/interpretation/assurance/answer_evidence.py:87).
Evidence: `observations/review-population.json`, `observations/uncitable-fields.json`.

### G5. The review entry point discards synthesis bindings without checking them

The diagnostic changes a valid synthetic proposal's stage binding, interaction
hash and review accounts. `validate_synthesis` rejects it, as expected, but
`prepare_answer_review` still constructs a review request because it strips those
fields before invoking the underlying answer validator. There is no current
production caller making this mistake; the prerequisite is simply unenforced
at the proposed entry point. Integration should accept a verified synthesis
receipt or perform the necessary validation before stripping fields.

Code: [review entry point](/home/chakwong/python/legalmath/src/legalmath/interpretation/assurance/dossier_answer.py:622).
Evidence: `observations/synthesis-binding.json`.

### G6. A provider failure still prevents independent downstream reviews

The two-group control gives the first reviewer an invalid response. With the
new continuation flag enabled, both groups are attempted, one valid review is
retained, and synthesis is correctly blocked. Changing only the first failure
to a provider exception results in one attempted group, no completed reviews
and `E_JOB_STATE`. The second independent group never runs.

`RouteBudgetProvider.check` requires every prior dispatch to be `RETURNED`.
The consumer calls that guard from `unchanged()` inside its exception handler,
before recording the failed group. The guard raises again, so `failed_reviews`
is empty, although the original failure remains in the durable budget ledger.
Thus the mission scheduler's independent task policy does not extend through
the actual guarded consumer. A resolved local failure, an uncertain in-flight
dispatch and a shared authority/integrity failure need different treatment;
failed calls must remain charged, and synthesis must still require all its inputs.

Code: [guard](/home/chakwong/python/legalmath/src/legalmath/interpretation/assurance/route_admission.py:128),
[review loop](/home/chakwong/python/legalmath/src/legalmath/interpretation/assurance/dossier_answer.py:583).
Evidence: `observations/invalid-content.json`, `observations/provider-exception.json`.

### G7. Adapter errors have an overbroad local-failure classification

The new backend catches every ordinary `Exception`. A diagnostic injected
`E_INTEGRITY` in one adapter; it became a FAILED receipt and the sibling ran.
That behavior may be right for a bad adapter output, but the backend does not
distinguish it from a shared source or resource failure. The parent session still
checks source/backend identity and durable evidence, so this does **not**
demonstrate that shared corruption bypasses those checks. The remaining gap is
an explicit error taxonomy and tests for its different scopes.

The new preferred-extension reference also needs actual native-engine evaluation
through the selected product path. The previous new-backend tests mocked the
engines. Older real-engine evidence remains useful for those older profiles.

Code: [adapter exception boundary](/home/chakwong/python/legalmath/scripts/legal_independent_tools.py:56),
[failed-receipt continuation](/home/chakwong/python/legalmath/src/legalmath/interpretation/assurance/independent_tools.py:7).
Evidence: `observations/adapter-error-classification.json`.

### G8. Prospective resource admission omits downstream structural limits

The separate probe calls the current admission function on a small declared
17-candidate workload with adequate declared stage allowances. It admits that
workload. The product, however, creates its replay only for 1–16 candidates,
and its `execution_complete` requires that replay. The answer contract accepts
up to 64 readings, so these boundaries are inconsistent.

There is another configuration-specific conflict. With machine qualification
enabled and 16 candidates, even supplied question assignments require at least
one question action, 16 proof actions, 16 qualification actions and one replay:
34 outer actions against 32. The default machine-qualification flag is false;
this second failure must not be attributed to every run. The probe checks
admission; the runtime bounds and action count are established by code inspection,
not a complete 17-candidate execution.

Existing limits also include 200 optional-tool actions, 4,096 scoped pairs,
64 dossier groups, bounded group/interaction responses, per-stage grants and
the absolute deadline. Complete claim and candidate populations remain unknown.
The 35 original readings span the mission; they must not be assumed to be the
population of every individual packet. An explicit justified partition and
reconciliation method could address this, but silently dropping readings cannot.

Code: [admission](/home/chakwong/python/legalmath/src/legalmath/interpretation/assurance/route_admission.py:91),
[outer journal](/home/chakwong/python/legalmath/src/legalmath/interpretation/assurance/complete_investigation.py:196),
[replay condition](/home/chakwong/python/legalmath/src/legalmath/interpretation/assurance/complete_investigation.py:320).
Evidence: `resource-probe.json`.

### G9. Evidence reduction has no demonstrated semantic adequacy

The dossier archive can reconstruct the original records exactly, and group
reviews retain record accounting. Interaction and synthesis nevertheless receive
reviews plus selected raw dependencies. Dependency selection uses explicit IDs,
recognized interaction keys and dependencies nominated by the reviewers. An
implicit exception or relationship omitted by a group review may never reach
synthesis as raw evidence. There is no demonstrated source-recovery path after
such an omission.

This is an unqualified behavior/risk, not a newly observed incorrect final
answer. It needs a legal example where necessary support or contrary material
crosses groups, plus a checked downstream result. Byte budgets, exact archive
reconstruction and complete ID accounting do not establish faithful reduction.

Code: [dependency identification](/home/chakwong/python/legalmath/src/legalmath/interpretation/assurance/dossier_answer.py:190),
[interaction request](/home/chakwong/python/legalmath/src/legalmath/interpretation/assurance/dossier_answer.py:455).

## Why the selected tools have not closed the substantive gaps

This table describes the retained original-question trial. It does not erase
earlier successful controlled tests of supported profiles.

| Tool | What was actually exercised | Missing discriminating evidence |
|---|---|---|
| BM25 | Exact-question retrieval reached actual answers; consideration was recorded | Relevance/coverage and a warranted downstream benefit; its fresh review was invalid. Full source was already supplied to the baseline |
| LegalRuleML | All four readings were unformalized; the adapter returned UNSUPPORTED without running its Boolean engine | A justified source-to-rule mapping in the supported Boolean profile, actual execution and downstream effect |
| Logical English | The same four null formalizations returned UNSUPPORTED without parser execution | A justified supported target and actual conditional reasoning; it is a restricted AST-to-controlled-language adapter, not a general English interpreter |
| PyArg | Native grounded/preferred computation on nine eligible nodes with no attacks | A legally justified conflict/undercut and an answer that changes for the justified computational reason; fresh review was invalid |
| Carneades | Native grounded/preferred computation on that same graph | The same warranted conflict requirement; its reviewer quoted text absent from the answer |
| clingo | Native stable-extension computation on that same graph; valid fresh review | The conditional baseline was also accepted. No corrected baseline error or conflict-resolution benefit was demonstrated |

Three blocked arguments remained visible as legal alternatives. Removing the
eleven unjustified attacks was a valid correction; inventing replacements merely
to exercise an engine would reverse that progress. The finite Boolean adapters
and graph solvers compute consequences of supplied premises. They do not discover
the applicable fulfillment standard, justify a legal analogy, resolve an ambiguous
footnote or establish the truth of an assessed premise.

The trial's baseline received the same full source, obligations, cases, readings
and reviewed graph. This is a fair comparison of incremental tool feedback, but
offers little discrimination where that common material already supplies the
conditional answer and the graph contains no conflicts. One answer per arm gives
no statistically supported ranking. The evidence does not show that these
packages are useless; it shows that their substantive benefit remains unevaluated.

Code: [formal profile](/home/chakwong/python/legalmath/scripts/legal_integration_tools.py:79),
[Logical English translation](/home/chakwong/python/legalmath/scripts/legal_mission_logical_english.py:64),
[unknown-input treatment](/home/chakwong/python/legalmath/scripts/legal_mission_logical_english.py:125),
[argument evaluation](/home/chakwong/python/legalmath/src/legalmath/interpretation/assurance/arguments.py:157).
Retained result: [answer-tools-repair.md](answer-tools-repair.md).

The wider catalogue is also not fully integrated. HYPO/CATO/AGATHA remain
conceptual case-reasoning sources. SARA-IE lacks the recorded reuse and target
training prerequisites; CLERC lacks corpus/deployment qualification; MAPIE lacks
an independent labelled calibration set. Tweety, s(CASP), KeY and LangGraph are
deferred because no distinct blocking computation currently justifies their
integration. Eyecite's target-jurisdiction suitability remains unresolved.
Docling/OCR, Inspect/PIT, Java/Catala/Lean and Z3/cvc5 have supporting roles;
those roles are not evidence of legal-answer benefit for all four questions.
These are the retained dispositions in `tools.json`, not new evaluations of all
upstream projects in this audit.

## Open legal and product questions

| Original question | Supported analysis already retained | What remains open |
|---|---|---|
| P10 responsibility and fulfillment | Allocation of responsibility, supervisory conduct and operational/records outcomes are distinct; outsourcing does not discharge responsibility | Applicable fulfillment standard, assessment period and effect of a defect/cure; conditional applicability and source-to-rule warrant |
| Evidence of supervision/proper records | An event or a matching reconciliation does not by itself establish adequate supervision or records reflecting the relevant rights | Rights, record roles, coverage, chronology, evidence quality and the governing standard; P11 must not be assumed to apply to an unspecified defect |
| P14 and footnote 5 | Request-conditioned versus standing demonstration and technical-only versus broader confidence are separate axes; P15/P16 requests remain distinct | Complete answer and contrary review on the original P14 question, with warranted treatment of both axes and fulfillment/SFC satisfaction |
| Gatecoin | Property versus actual trust, distinct parties, scenario-specific consent evidence and the reasons/Annexure distinctions are retained | Source-supported target transfer, scenario-seven reasons/order tension, and dated later-treatment research; no automatic transplant of case directions to a Product Provider |

The precise arguments and remaining evidence requests are in
[P10](p10-standard.md), [P14](p14-attachment.md) and [Gatecoin](gatecoin-transfer.md).
They support continued conditional source analysis without private client facts.
Missing facts constrain an arrangement-specific conclusion; they do not block
all source work. No code change can legitimately invent the missing authority.

The focused seven-obligation/five-case trial does not close the mission's
four questions, 46 original obligations or 35 original readings. Neither source
span preservation nor a proposal listing every candidate establishes complete
population discovery or correct English interpretation.

## Execution and approval state

Mission check/status/admit passed at audit entry and admitted offline diagnosis.
Version 5 is terminal with no ready/running task and an expired live deadline:
12 October 2026 04:28:01 UTC. The charged ledger remains 41/400. The new
whole-route guard explicitly refuses live use pending method qualification;
that refusal is an intentional boundary, not a service outage.

The register still counts 14 detours. The subsequent local repair plan declares
an additional consolidated attempt, and code was written, but that attempt was
not registered or closed out. Therefore 14 is the registered lower bound, not
evidence that the later attempt is unspent. Before further repair execution,
reconcile that consumed local package in a reviewed revision. This diagnosis
does not register a repair, reset any count or extend the expired grant.

The promised `scripts/legal_mission_integration_repair.py` wrapper does not
exist. No corresponding new integration rule file was found in the host rules
listing; the existing answer-tools rules concern the older fixed runners. The
prospectus rule file is unrelated. Thus the earlier approval-setup branch cannot
be described as completed. This audit required no protected-path changes or
additional approvals.

The shared reset memo still led with an October-11 result and 13 calls before
this audit. That stale restart guidance and the gap between plan, code and
mission state are concrete contributors to repeated rediscovery. This audit
retains a diagnosis entry and refreshed restart guidance; it does not relabel
the incomplete prior program as successful.

## Closure dependencies and review of this diagnosis

The next implementation program should contain these independent obligations,
with success conditions on the actual selected product path:

| Work | Can proceed independently of | Evidence needed before dependent acceptance |
|---|---|---|
| Source/review interface: G1–G5 | Tool-benefit ranking, P14/Gatecoin conclusions | Trusted originals and locators; authoritative requirements; complete permitted fields; verified synthesis binding; actual consumer review |
| Failure policy: G1, G6–G7 | Paragraph parsing and legal-standard selection | Content failure and provider exception both preserve independent work; shared failures block dependants; durable charging and failed evidence remain |
| Capacity and reduction: G8–G9 | A positive tool contribution | Complete or justified population bounds, every downstream cap, source-recovery controls and actual response adequacy |
| Conditional legal source work | Unrelated failed adapters and private facts | Warranted propositions, contrary readings and source-specific counterexamples for each original question |
| Tool applicability | Unrelated tool failures | The relevant legal input and selected adapter work; supported cases, unknown-input/failure controls and real outputs |
| Matched answer evaluation | Unrelated source questions outside its declared scope | Its interface, legal targets, tool receipts, resource admission and fresh answer/review; new live authority where required |

The source work must not be parked behind all engineering work. Equally, a live
answer comparison must not be launched before its own prerequisites are valid.
Assessment depends on completion of branches, including retained failures;
acceptance depends on the successful evidence required for that particular claim.

| Decision | Primary evidence | Veto/uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|
| Reject full-integration/completed-program claim | Caller trace, unfinished branches and retained trial | No complete normal-route legal answer comparison | Reconcile actual completion state and repair the named interfaces | That nothing has improved |
| Retain the source-identity and continuation defects | Deterministic positive/negative controls | Scripted provider; unused locator helper | Repair and exercise the same real boundaries in a successor | A live outage or deployed citation exploit occurred |
| Retain missing capacity constraints | Actual admission output and inspected runtime limits | No full 17-reading run; populations remain incomplete | Include replay and action budgets in prospective admission | That all configurations fail at 16 readings |
| Keep substantive and tool-benefit questions open | Null formalizations, trivial graph, retained legal dossiers | Missing warrants, full scope and reliable matched review | Continue independent source work and meaningful target evaluation | Tool uselessness, a ranking, compliance or legal closure |

Post-run skeptical review: several validators intentionally promise only
structure, and an outer trusted caller could supply missing prerequisites.
This audit therefore labels those as integration gaps rather than claiming
the validators prove legal truth incorrectly. The strongest new counterexample
is the guarded two-group failure comparison. The weakest extrapolations would
be from synthetic parser layouts to unseen judgments, or from the narrow tool
trial to every possible legal task; neither conclusion is made. A verified
production caller enforcing these prerequisites, or a full matched evaluation
on warranted targets, would change the corresponding findings.

## Reproducibility

Plan: `docs/plans/legal-mission-code-audit-2026-10-12.md`.
Evidence directory: `artifacts/legal-mission-control/2026-10-12/code-audit/`.
Exact diagnostic command:

```text
.venv/bin/python artifacts/legal-mission-control/2026-10-12/code-audit/run_audit.py
.venv/bin/python artifacts/legal-mission-control/2026-10-12/code-audit/resource-probe.py
```

The first command retained nine passing diagnostic assertions, JUnit, stdout,
stderr, call sites, source hashes, the synthetic product dossier and per-finding
observations. It took 13.317 seconds including capture. The separate resource
probe retained its inputs and outputs. Both commands are one-shot diagnostics;
do not rerun them merely to reproduce a completion count. Manifests record
commit `21e810b32759c890f833e3655bcfaf68c80a5dac`, dirty-source hashes,
the `.venv` Python, commands, UTC times and output locations. GPU devices were
intentionally hidden; seeds are not applicable to these deterministic scripted
checks. No native optional engine was newly evaluated by these diagnostics.
