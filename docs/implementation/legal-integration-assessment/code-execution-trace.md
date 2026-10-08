# Trace from product inputs to the assessment result

8 October 2026. This trace continues the preserved integration repair. It
corrects its mistaken description of the 420 broad-fidelity pairs as the full
scoped matrix. The actual retained product has 41 claims, six marked CONTEXT,
and 12 candidates. Broad fidelity excludes CONTEXT; scoped fidelity includes
it. Required coverage is therefore 492, of which 72 are context pairs.

| Boundary | Current implementation and execution evidence | Meaning and remaining limitation |
|---|---|---|
| Source and candidate intake | `CompleteInvestigation.run` reads the retained packet, claims and candidates; empty generation stops before question calls. | Sources remain fixed. The original combined generation failure is retained. |
| Broad fidelity | `Assurance._fidelity` selects non-CONTEXT claims; `semantics.fidelity_request` includes declared meaning, representation and reading hash separately. | Its 420-pair subset is a coverage diagnostic, not the full exact-question matrix. Declared prose cannot serve as executable evidence. |
| Repaired candidate feedback | `Assurance._fidelity` computes checks on the actual pending candidate subset before dispatch. | A newly repaired formula receives a fresh check. Exact identical subsets reuse their journal result. |
| Argument computation | `arguments.evaluate_criticism` determines eligible arguments and effective defeats; ProductToolBackend compares these with PyArg/Carneades and clingo. | Blocking, inherited defeats and unaccepted priorities affect the target graph. None establishes the legal premises. |
| Exact question | `CompleteInvestigation.question_request` retains proposed typed questions, separately from the broad selected slice. | All six retained unformalized candidates have REQUIREMENT_SATISFIED questions; none meets the live DUTY_TRIGGER selection prerequisite. |
| Scoped fidelity | `scoped_investigation.investigate` includes all 41 claims. It validates every batch against fixed originals and exact typed questions. | Full minimum at batch size 12 is 41 batches times two perspectives, or 82 calls per arm. The finite two-pair diagnostic cannot complete this matrix. |
| Reviewed limitations | `fidelity_v2.validate` admits UNAVAILABLE only without executable meaning and BLOCKED only with an assessed source/relevance obstacle, both without executable quotes and with followups. | UNASSESSED remains incomplete. Reviewed absence is neither executable correspondence nor legal closure. |
| Coverage | `assessment_coverage` separates reviewed pairs, actual executable comparisons, unavailable code, blocked premises, mixed correspondence and missing perspectives. | Counts use both latest validated perspectives. UNAVAILABLE/BLOCKED counts can overlap; they are not a partition or accuracy rate. |
| Tool attachment | `ToolSession` v2 binds source and reading hashes, prohibits backend identity overwrite, and keeps caller-held inputs isolated. | Atomic checks appear only when every checked reading is present and unchanged. Whole graphs are never trimmed into another graph. |
| Retrieval | `ToolSession.augment` uses exact scoped candidate questions and only the corresponding retrieval checks. | Retrieved locations assist navigation; they do not establish source sufficiency or question interpretation. |
| Wire transport | Executable/source reference adapters and readable tables preserve question and expression identities. | A response can copy a correct hash while reasoning about a different question. Independent semantic review remains necessary. |
| Cache and stop rules | Issued requests retain frozen context across restart. Unknown dispatches require review. The new diagnostic enables `stop_on_rejection`; default product repair behavior remains separately bounded. | No hidden retry, timeout increase or service substitution occurs in this program. |
| Dossier verification | Optional-tool report backend must match the dossier method and retained journal; historical v1 shape remains readable. | Historical verification preserves evidence identity. It does not reclassify old UNASSESSED responses or certify a remote model. |

The original transport evidence showed successful slots 63–66 and timeout slots
67–68. Plugin-catalog warnings occurred in both groups. They do not establish
the cause of the timeout. The finite diagnostic first checks the unchanged
route with one tiny structured response, then conditionally tests the same two
retained pairs in each arm. Actual results belong in `execution-result.md`.

The reviewed program is `docs/plans/legal-integration-assessment-program.md`.
The executable is `scripts/legal_integration_assessment.py`, dispatched through
the previously approved `scripts/run_legal_integration_repair.py` prefix.
`artifacts/legal-integration-assessment/2026-10-08/input-inventory.json` contains
every original obligation and reading, all 492 pair identities, and the stable
selection. The baseline directory preserves the source before these edits.
