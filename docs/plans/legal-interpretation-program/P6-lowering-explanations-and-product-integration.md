# P6: Run the same meaning through explanation and execution

Status: PLANNED_NOT_EXECUTED. The [master program](../legal-interpretation-master-program.md)
controls evidence, default assumptions, resource limits and source-fidelity claims.
Revision 2 — 6 October 2026. Incorporates the [Claude review response](../../implementation/legal-interpretation-program/claude-review-response.md); implementation checks remain pending.

Dependencies: P3, P4, P5.

## Question and inputs

Does the actual product preserve the declared branches and qualifications when producing explanations and executable results?

P2–P5 structures and supported fragments; existing translation.model.from_reading, qualification_adapter.run/verify, complete investigator and existing target-specific checks.

## Implementation

1. Implement semantics/lower.py and render.py from the same immutable semantic records. Serialize the branch, assumptions, scope and evidence identity alongside the executable expression and explanation.

2. Map only supported constructs to existing RuleIR/Catala targets. Reject unrepresentable modalities, quantities, partial intervals or conflicting inputs with named reasons; never silently choose a Boolean or erase a branch. RuleIR has no scalar conflicting-support value: retain it in the versioned envelope and refuse unsupported lowering. Keep model provenance explicit. The legacy reviewer_interpretation basis and “Unreviewed interpretation” prefix mean a proposal, not human approval. Store declared_semantic_branch provenance in the new envelope with the explicit legacy mapping; the existing rule-bundle.schema.json enum does not accept that new value. Do not inject it into an old bundle. Test both schema validation and rendering without implying reviewer endorsement.

3. Implement semantics/integration.py as an optional route in the complete investigator. Preserve the old default/replay behavior and historical contracts. Store the semantic branch inventory in its own versioned manifest, never candidates.json. Legacy replay requires 1–16 candidates and a usable criticism proposal; verify more than 16 semantic branches against an otherwise replay-eligible legacy input, retaining the exact original candidates file and replay. Offline integration uses explicitly retained or synthetic provider responses, recorded as such; no live provider is invoked by this test.

4. Compute decision sets across every retained branch and declared semantic setting, keeping per-extension witnesses. Use the outcome contract below, including coexisting reasons; do not report unanimity from an empty or partial set. A completed grounded result with no accepted contested conclusion is valid. Conditional consequences still run for the represented branches without treating those branches as legally accepted.

5. Carry uncertainty into the operative field, detailed report and summary. Keep legal correctness and unrestricted future generalization NOT_ESTABLISHED unless an exactly scoped independent result supports something stronger.

6. Add a separate semantics/qualification_v2.py adapter/profile (planned legalmath.investigation-qualification.v2) around compatible machine qualification. Bind the canonical P1 branch hash, complete semantic record, assumptions/priorities, packet, query, assignment status, cases/evidence, method/evaluator and target identities. Store outputs under a branch-hash directory within an immutable attempt; verify exact equality of expected and retained branch inventories, including explicit unsupported outcomes. Preserve v1 files/profile for historical receipts. Changes to shared dependencies can still invalidate historical verification; report this rather than promising all old receipts will pass new code. Caller-selected directory uniqueness alone cannot supply semantic identity.

7. Execute compatible lowered models on actual selected runtime targets. A missing or unsupported target produces a qualified target result; never substitute a Python-only replay for claimed Java/Catala execution. Dependent development can continue, but at least one actual supported downstream target must execute before P6's execution capability is complete.

8. Extend investigation_observations.method with explicit semantics configuration: disabled is None; enabled includes profile, records version, evaluator/reference identity, ordering/preferences and limits. Version its boundary and reject unknown/mismatched settings. Extend check_stages to require and recheck the actual semantics-stage receipt, input/configuration hashes, stage times and exact per-branch qualification inventory. Independently recompute the decision set from retained semantic inputs and compare it with reported outcomes. A matching implementation hash alone is insufficient. Add the semantics start time to observe's existing admission-to-observation checks. Audit generated/volatile JSON under src/legalmath before a method freeze, since implementation_identity hashes those files too. Plan any change to identity coverage explicitly; never exclude files merely to avoid invalidation.

## Outcome contract and required checks

A versioned outcome contains query identity/type, branch and extension identities,
a value (true, false, unknown, conflict, out-of-scope), completion status,
target-lowering/execution status, and an ordered canonical set of reasons with
their premise/witness references. Unknown-fact, unknown-applicability,
unknown-interpretation, conflicting-evidence, conflicting-extensions,
unsupported-lowering and unfinished may coexist. Input conflicts and extension
disagreement remain different reasons.

For completed extensions, opposite determinate answers to the same query yield
conflict with conflicting-extensions; true plus unknown stays qualified/unknown
and retains both witnesses. An uncomputed required extension or unvisited frontier
means unfinished; a completed empty grounded extension is not missing work.
A trigger query renders settled-triggered/settled-not-triggered only for its
completed conditional true/false computation under stated applicability and
assumptions. Out-of-scope, unsupported lowering and target availability are
separate from “not triggered”. An unsupported target may leave a reference
query value available, but cannot become a successful compiled-target result.
Unresolved legal meaning and supplied evaluative judgments always remain visible.

Uniformity is computed over an explicit projection (query value, relevant scope,
assumptions, completion and reason inventory), with source/branch identities
retained alongside it. A trigger-only comparison must not erase object/standard
differences or claim uniform legal meaning. No empty inventory, unvisited
extension or unsupported qualification can be labelled complete unanimous success.

Add these discriminating checks to the three declared test files:

- test_lowering.py: legacy schema accepts the mapped basis; envelope provenance
  remains a proposed semantic branch; conflicting support refuses Boolean
  coercion; original v1 inputs are not rewritten.
- test_rendering.py: every value/reason and coexisting-reason case reaches the
  operative field, summary and detailed report consistently; extension
  disagreement is not collapsed; a valid empty grounded report is preserved.
- test_integration.py: two branches with one legacy Reading but different
  settings/priority assumptions receive distinct identities and receipts;
  missing, duplicate or swapped branch receipts are rejected. More than 16
  branches preserve an eligible legacy candidates.json and replay. Missing
  semantics stage is rejected, changed settings invalidate the binding, and
  timing/input/configuration evidence is rechecked. P8 extends these cases
  through freeze/observe, not only helper calls.

## Files and validation commands

Proposed semantics/lower.py, render.py, integration.py and qualification_v2.py; narrowly scoped optional-route changes to complete_investigation.py and method/stage checks in investigation_observations.py. No new autonomous provider scheduler.

The following test files are planned deliverables, not existing executed tests.
After implementing them, run these exact forms from the repository root:

```text
.venv/bin/python scripts/legal_interpretation_ops.py phase-tests P6
```

Add the relevant existing regression paths discovered from actual touched imports.
Record those exact paths in the phase revision before executing; do not invent a
successful regression result or invoke a broad suite unrelated to the change.

## Discriminating challenges

Summary drops footnote uncertainty; branch fails lowering and disappears; all branches out of scope; explanation condition differs from code; shared source error passes two compilers; claimed stage was never called.

## Acceptance and failure decisions

The actual complete-investigator route preserves all declared branch outcomes, source/evidence identity and qualifications. Supported compiled executions match the independent declared-semantics reference. Branch identities remain distinct even after identical legacy lowering, and stage verification rejects absent or mismatched semantics evidence. Unsupported targets/branches remain in the denominator.

A lowering counterexample blocks that target and triggers repair. A complete investigator bypassing the new route is an implementation failure. Agreement between targets never closes the source-fidelity gap.

## Result and next-phase refresh

P7 receives actual integrated outputs, the exact supported domain, rejected constructs, runtime identities, counterexamples and the formal propositions worth proving. Remove proof ambitions that the implementation does not express.

Save the executed plan version, input/output hashes, commands, results,
uncertainties, decision and refreshed successor plan under the immutable attempt
directory specified by the master. A planned test command is not run evidence.

Resource boundary: Local CPU/runtime checks; deliberately hide GPU before any optional ML import. Provider dispatch remains separate and requires valid explicit allowance.
