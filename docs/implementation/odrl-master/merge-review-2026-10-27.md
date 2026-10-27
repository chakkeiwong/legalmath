# Review of the merged reuse baseline

The user authorized committing this work and merging main back into the working
branch. That merge changes five of the ODRL planning baseline's 28 bound files.
The post-merge suite correctly rejects the stale bindings: 445 tests passed and
one planning-integrity test failed. This is a baseline reconciliation, not ODRL
implementation authority or a claim that the feature works.

The premerge program and exact five source versions are retained under
`history/premerge-2026-10-27/`, with their original hashes. The current program
binds both those archives and the merged files. All 22 task identities, their
dependencies, zero attempts, authority gates and acceptance obligations remain
unchanged. The old review and verification remain historical evidence.

| Changed file | Inspected change | Consequence for the planned reuse |
| --- | --- | --- |
| pyproject.toml | Packages comparative specifications and compressed successor JSON inputs | Includes existing prospectus inputs; introduces no new ODRL dependency or authority |
| semantics.py | Converts a zero rational denominator into an explicit ValueError | Preserves exact rational policy; invalid input remains rejected |
| source_graph.py | Adds sealed extraction receipts, explicit hybrid native/OCR evidence, geometry qualification and stricter timestamp checks | Do not infer whole-document coverage from selected pages; T03/E04/F06 must retain these qualification premises |
| reference_closure.py | Sorts outgoing edges and roots deterministically | Preserves conservative cycle evidence with reproducible traversal |
| clause_graph.py | Validates five additional prospectus effect families through their own modules | No ODRL semantic mapping is inferred; unsupported target effects remain outside the reviewed ODRL profile |

Skeptical review: PASS for updating a planning baseline. The wrong-baseline
failure is reproduced and exact predecessors are retained. No passing test is
treated as an ODRL, scientific or legal promotion criterion. The independent
case-writing and qualification tasks remain required before any reuse is
promoted. No new model calls, feature dispatch, task status or budget is added.
Verification is the same adverse planning suite and merged changed-area suite;
the result is retained separately after execution.
