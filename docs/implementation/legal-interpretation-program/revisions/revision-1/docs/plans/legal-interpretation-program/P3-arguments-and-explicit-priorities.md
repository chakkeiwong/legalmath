# P3: Evaluate competing arguments under declared semantics

Status: PLANNED_NOT_EXECUTED. The [master program](../legal-interpretation-master-program.md)
controls evidence, default assumptions, resource limits and source-fidelity claims.
Dependencies: P2.

## Question and inputs

Can structured arguments expose the disputed premises and priority choices without silently resolving legal uncertainty?

P2's source-linked readings and warrants; inspected ASPIC+ paper and correction; pinned PyArg source and licence. Review the actual finite theory conditions before invoking a formal result.

## Implementation

1. Implement semantics/arguments.py with premise attacks, conclusion rebuttals and rule undercuts, explicit contrary relations, defeasible versus strict rules, and typed priority premises. An unproved natural-language warrant must not become a strict axiom by default.

2. Construct a small independent reference evaluator from the declared finite attack relation. Validate grounded fixed-point behavior and tiny preferred-extension examples of at most eight abstract arguments, including empty, cyclic, self-attacking and mutually attacking theories. Eight is a convenience bound for exhaustive subset enumeration, not a supported maximum for all product inputs. Larger product theories require their own bounded evaluation; do not enumerate all subsets of 500 arguments.

3. Independently check argument construction as well as extension selection. On tiny structured theories, derive argument trees, contrary relations and each attack type directly from the stated rules; compare the resulting graph with the adapter. Checking only extensions on an already supplied graph would miss a faulty source-to-argument conversion. Test a pinned optional PyArg adapter against both reference stages. Supply ordering explicitly; inspect last-link versus alternative ordering effects without presenting one as governing law. Preserve conflicting or absent legal priorities.

4. Bound argument generation, recursion, time and nodes. Resource exhaustion yields incomplete evaluation with retained frontier; it cannot return a complete empty or unanimous extension.

5. Record which conclusions are in all, some or none of the computed extensions, separately from factual support and legal validity. State the explored domain and any uncomputed alternatives.

## Files and validation commands

Proposed semantics/arguments.py and semantics/pyarg_adapter.py; dependency/API/licence report and finite semantic reference cases.

The following test files are planned deliverables, not existing executed tests.
After implementing them, run these exact forms from the repository root:

```text
.venv/bin/python -m pytest tests/interpretation/semantics/test_arguments.py -q
.venv/bin/python -m pytest tests/interpretation/semantics/test_pyarg_adapter.py -q
```

Add the relevant existing regression paths discovered from actual touched imports.
Record those exact paths in the phase revision before executing; do not invent a
successful regression result or invoke a broad suite unrelated to the change.

## Discriminating challenges

PyArg default changes a result; a preference cycle appears; a missing premise is treated as false; a cut-off hides an attacking argument; a graph violates a rationality theorem's assumptions.

## Acceptance and failure decisions

Finite reference cases and selected adapter comparisons agree under identical explicit settings; mutations to premises and priorities yield recomputed results; incomplete work remains visible. No formal rationality theorem is claimed without its checked preconditions.

A library mismatch rejects that adapter configuration and triggers inspection or the reference-only optional path. Unsupported legal priority remains unresolved. A broken reference checker is a continuation veto for dependent reasoning claims.

## Result and next-phase refresh

P4 receives the actual semantic profile, supported attack types, unresolved priorities, API constraints and measured bounds. Explain any library substitution and invalidate affected results.

Save the executed plan version, input/output hashes, commands, results,
uncertainties, decision and refreshed successor plan under the immutable attempt
directory specified by the master. A planned test command is not run evidence.

Resource boundary: No model/GPU use. Keep the new profile separate from legacy search Settings, whose argument-node maximum is 16. The 64-alternative/500-node/30-second starting caps are convenience hypotheses inherited from existing contracts, tested for honest truncation and revised using measured finite probes.
