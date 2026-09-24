# B0: reliable interpretation diagnostics and complete fidelity matrices

Date: 2026-09-24. Authorized scope: execute the next phase after A0–A7,
namely B0 in `docs/implementation/interpretation-round3/next-phase-plan.md`.
B1 remains the successor. No new live calls are required; retain the existing
78/100 allowance and all accepted and failed A7 evidence.

## Intent and evidence contract

The engineering question is whether the system detects known corrupt candidate
prose, gives actionable matrix-repair feedback, and either retains a complete
fidelity matrix or explicitly reports incomplete execution before exceeding its
resources. The comparator is commit `c810848` and A7 attempt 08, including its
90-row 23EC46 and 384-row 24EC16 investigations. The actual malformed Generation
response is in A7 attempt 05, 24EC16, call 002; the actual extra fidelity pair is
in attempt 07, 23EC46, call 008, corrected in call 009.

Primary acceptance criteria:

1. Flag self-repair chatter and placeholder-only explanatory fields in the
   retained response. Inspect candidate narrative and fact descriptions, with
   exact field paths and text offsets. Source quote fields, legitimate uncertainty,
   ordinary references to JSON, and non-English text are negative controls.
   A separate presentation record withholds flagged prose; raw readings remain
   available, and executable/source judgments are unchanged.
2. Missing, unexpected and repeated pairs have exact identities and occurrence
   counts in bounded repair feedback. The existing bounded output-repair loop
   uses it successfully and retains unsuccessful repairs separately.
3. Keep the model response contract (1,000 checks, 30 concerns) unchanged. Add
   an investigation aggregate contract. More than 1,000 checks and more than
   30 concerns must succeed when the declared investigation capacity permits;
   every row and concern, including duplicates, survives.
4. Preflight the whole claim/candidate matrix before dispatch, including cached
   and unsupported candidates. Then preflight pending batches against calls,
   concern and byte capacity. Reject impossible work explicitly. Retain completed
   batches on a subsequent failure, label the matrix incomplete, and never expose
   partial checks as a complete supported interpretation.
5. The full regression suite passes. Revalidate both accepted A7 matrices and
   the historical bad/corrected pair response from manifest-verified bytes.
   Record this as deterministic revalidation, not fresh or independent model work.

An integrity mismatch, loss of a row/concern, quiet truncation, presentation of
flagged prose as normal analysis, or a budget violation vetoes acceptance.
Corrupt/misidentified retained inputs invalidate the harness and stop dependent
work. A detector miss or false positive, failed boundary test, or regression
instead triggers implementation repair and another recorded attempt. Retain
failures and require an executed repair, refreshed plan and current-input review
before retrying. Permit at most three failed acceptance attempts; revising that
budget requires a documented plan amendment, not resetting the state.

Runtime, counts of findings, question counts and test counts are explanatory.
Passing this phase establishes engineering behavior on known failures and
controlled boundaries. It establishes neither English correctness, completeness
of the detector, a future error rate, nor savings on legal review. There is no
stochastic method ranking or population estimate in this phase.

## Assumptions and defaults

| Choice and provenance | Justification and status | Failure mode and earliest diagnostic |
| --- | --- | --- |
| Known-pattern prose detector, motivated by the retained malformed response | A deterministic diagnostic, not a language-quality classifier; reviewed limited scope | Mistaking legal discussion or source text for instructions; negative controls and exact field spans |
| Preserve raw prose; withhold the entire affected reading in the presentation view | Avoid changing proposed legal meaning through an automatic editorial rewrite; reviewed engineering policy | A consumer ignores the presentation view; explicit per-candidate status and top-level unresolved finding |
| Response limits remain 1,000 rows and 30 concerns | Existing wire contract and replay compatibility; baseline | Accidentally widening model responses; test both schemas independently |
| Aggregate ceiling 4,096 pairs | Finite engineering resource hypothesis, above the observed 384 and the former 1,000-row ceiling | Large investigations cannot fit; preflight before constructing rows or dispatching fidelity calls |
| Aggregate ceiling 1,080 concerns | 36 maximum journaled calls times 30 per response; engineering ceiling | Many individually valid batches exceed a smaller caller setting; preflight worst-case concerns and boundary tests |
| Aggregate byte ceiling 2 MiB, with a conservative pending-batch bound | Leaves room for duplicated diagnostics inside the existing 20 MiB report boundary; resource hypothesis | Rejecting a response that would have been short; explicitly report the conservative bound and allow smaller requested batches, never truncate |
| Reserve one action for final criticism when preflighting pending batches | Minimum viable completion, not a promise all output repairs fit; reviewed scheduling bound | A repair consumes spare calls or a deadline expires; preserve partial batches and report incompleteness |
| At most 64 pair identities in feedback, with exact totals and truncation indicator | Consistent with existing bounded schema errors; convenience/resource choice | Large mismatch needs more than one repair; record all raw outputs and never imply exhaustive displayed feedback |
| Retained development sources and scripted provider boundary cases | Precisely reproduce observed engineering failures without new spending | Overstating replay as independence; explicit evidence classes and an unchanged allowance hash |

## Skeptical audit before implementation

PASS WITH LIMITS. The predecessor backlog correctly identifies the aggregate
contract bug: concatenation currently reuses `Fidelity`, so schema-valid batches
can fail solely because their union exceeds a response limit. The plan is amended
to preserve partial validated results and check total capacity before dispatch;
merely increasing a Pydantic limit would leave resource exhaustion and evidence
loss unresolved. Narrative findings must use a separate PRESENTATION stage and
must not prune interpretations or supply evidence to an entailment judgment.

The old malformed and corrected responses are development fixtures, not held-out
evidence. Exact request replay is inappropriate after changing repair feedback;
the acceptance command will explicitly revalidate unchanged retained responses
instead. A new supervisor retains prior manifests and fixes commands and output
paths; it cannot dispatch a live provider. The environment is the existing
Python 3.11 `.venv` and retained JDK 17. No dependency or GPU change is needed.
The known API suite requires the approved/trusted execution context; a sandbox
failure would diagnose the execution environment before any product conclusion.

A misleading pass would detect only the verbatim bad phrase, accept all clean
syntax as sound English, or silently discard concerns to fit a schema. Adverse
variants, negative controls, independently asserted counts and retained-byte
hashes discriminate these failures. An unsuccessful diagnostic is an engineering
repair trigger, not a rejection of multi-interpretation assurance.

## Execution, review and refresh

Implement B0 in three steps: prose diagnostics/presentation; matrix validation
and capacity planning; integration and retained-source acceptance. Run focused
tests before the full acceptance command. Review final code and test oracles
against the criteria above and record a current-input author review. The review
is not an independent legal assessment.

Fixed runner: `.venv/bin/python scripts/run_interpretation_reliability_plan.py`.
Operations: `preflight`, `refresh B0`, `review B0 --note <project JSON>`,
`run B0`, and, after any failed attempt, `repair B0 --note <executed repair JSON>`.
The B0 command runs the full pytest suite with JUnit output, then
`scripts/interpretation_reliability_acceptance.py --out <attempt>/retained`.
CPU only; seeds are N/A for deterministic revalidation and scripted tests.
The runner records Git commit, input hashes, exact commands, Python environment,
wall time and output hashes under `artifacts/interpretation/round4/B0`.

The master plan is `docs/implementation/interpretation-round4/master-plan.json`.
Accepted history and live allowance are pinned by a B0 baseline manifest.
The supervisor refreshes a B1 plan after B0 passes, but B1 execution is disabled
until its implementation and current-input review exist. Record results and
remaining limits in `docs/implementation/interpretation-round4/execution-report.md`
and `reset-memo.md`; refresh the B1 tasks using observed B0 results.
