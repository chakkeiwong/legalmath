# Audit of multi-level tree verification

The completed P8 24EC50 run expanded three initial roots and created four
children. Its deepest node was at depth one. This establishes repeated branch
investigation, but it does not establish that the engine actually selects a
child for another refinement. The existing full-engine test also asserts only
that at least one child exists. The pure scheduler test checks unvisited roots
and backpropagation, without an end-to-end descent. Treating either as evidence
of multi-level execution would be a wrong baseline.

## Evidence contract before execution

Question: can both BFS and UCT finish initial-root exploration, expand a child,
and preserve a grandchild, its lineage, issued-call accounting and unresolved
frontier under the normal per-root bound? The baseline is the existing
child-creation assertion. The additional diagnostic is an actual engine run
with a deterministic synthetic provider returning distinct refinements.

The synthetic input is deliberate: it isolates traversal and accounting from
the live model's willingness to propose a distinct refinement. It must not be
reported as live interpretation evidence. Use three distinct initial roots,
four allowed investigation rounds, the existing three-call per-root bound, and
enough global slots to cover three initial calls, four refinements and the
three reconstructions possible before the selected root is exhausted.
Exact generated thresholds are fixture values, not source-derived legal labels.

Pass requires an actual depth-two node for each scheduler, correct immediate
parent and root identities, four recorded rounds, no hidden or excess call,
Java/Python conformance for compiled nodes, and an unresolved report that lists
the unexpanded grandchild. Reconstruction should remain bounded when a root's
third call is spent on refinement. No branch may be declared legally resolved.
Unexpected deduplication, a missing grandchild, broken lineage, a hidden retry,
an exceeded limit or lost frontier is a repair trigger and acceptance veto.

Node count, traversal order beyond the required breadth, reward and wall time
are explanatory only. No scheduler ranking, search completeness or English
interpretation accuracy follows. A deterministic passing case establishes the
tested behavior, not all possible trees. The live cases remain reported with
their observed maximum depth.

Wait for P8's immutable acceptance attempt to finish before changing any tested
input. Then append P9, record review of its exact inputs, execute the focused
check and full regression, and retain the resulting manifest and JUnit record.
This extension uses no further live calls. It does not reset any prior phase,
allowance or failure. If the focused check finds a defect, repair it and review
the changed implementation before accepting the full suite.

## Executed result

P9 attempt 01 passed both focused scheduler cases and all 282 tests. The
manifest, focused log and JUnit record are in
`artifacts/interpretation/round2/P9/attempt-01/`. Each scheduler generated a
depth-two node with checked parent/root lineage, ten counted fixture calls,
Java verification for all compiled nodes and an unresolved unexpanded
grandchild. No engine change was needed; this closed a missing verification
case. No additional live call was used.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | What is not established |
|---|---|---|---|---|---|
| Accept tested multi-level traversal | Both scheduler cases create a grandchild and preserve accounting/frontier; full suite passes | No fixture failure or Java mismatch | Other trees and source-driven quality | Preserve the regression and move to independent source review | Completeness, a preferred scheduler or legal correctness |

The weakest evidence is intentional: a synthetic provider guarantees distinct
refinements. Actual models need not generate them, as the bounded live trees
demonstrated. A live run that stops without deeper descent remains an incomplete
investigation, even though this test establishes that the scheduler can descend.
