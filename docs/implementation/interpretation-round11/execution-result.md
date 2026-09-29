# Round 11 execution result and reset memo

Date: 25 September 2026. All six planned phases are engineering-complete.
The final state is **PASS / UNCERTAINTY_RETAINED**, with
`legal_correctness_established=false` and `release_eligible=false`.

The [master](../../../scripts/run_assurance_master.py) installed and exercised
the additional tools, recorded failures and executed repairs, regenerated the
plan before each phase, rejected stale evidence, and wrote a final report after
M5 completed. This was an author engineering review and execution, not an
independent legal adjudication. The governing question, defaults, evidence
contract and final skeptical audit are in the
[execution plan](../../plans/assurance-round11-execution.md).

## Results and their scope

| Phase | Executed result | Meaning and limit |
|---|---|---|
| M0 | Canonical monograph 259 pages; technical companion 76 pages; process guide 7 pages. Reader-facing preservation, reference and citation checks pass; all 207 protected source-unit labels remain. The proposal PDF equals the canonical monograph. | The new section explains correlated failures, concrete SFC omission cases, tool contracts, disagreement handling and implementation stages. Preservation/build checks do not certify reader comprehension or legal meaning. |
| M1 | Isolated CPU toolchain installed and preflight passed. | Docling 2.130.0, Tesseract 4.1.1, pdfplumber 0.11.10, cvc5 1.4.0, clingo 5.8.2, Inspect 0.3.268 and PIT 1.20.3 were exercised. ResearchAssistant's Poppler adapter and existing Z3/Java engines were reused. The application environment was not changed. |
| M2 | Five extraction routes executed on 3 retained SFC PDFs covering 12 pages. The synthetic image-only exception and footnote were recovered. All 26 bounded investigation actions executed. | All twelve real pages have at least one extraction disagreement. These are retained as unresolved; their materiality has not been adjudicated. Two OCR configurations share an engine and are not independent votes. Docling table semantics were not enabled. |
| M3 | Four Boolean comparisons agreed between cvc5 and the existing Z3 route; distinguishing cvc5 witnesses were replayed in Python and generated Java. The integer threshold witness was 6. Clingo matched exhaustive Python evaluation on all 531 directed graphs with up to three arguments, including self-attacks and the empty graph. | Boolean-body comparisons assume aligned factual meanings. They do not cover complete RuleIR, conflict, all arithmetic or legal interpretation. Empty/truncated extension sets cannot create skeptical acceptance. |
| M4 | Inspect scored the synthetic control correctly and rejected five wrong/missing responses. PIT killed all eight emitted mutations in the Java pilot. | Inspect used a restricted public-only proposer interface and zero live model calls. PIT exercised an authored Boolean/threshold pilot; full generated-runtime mutation coverage remains next work. These are engineering challenges, not measured model accuracy. |
| M5 | **628 tests passed, zero failures/errors/skips**, in 470.21 seconds; two dependency deprecation warnings. Canonical document, citation and mathematics checks passed again. | Existing interpretation search, operations and generated-Java tests were included. Sixteen algebraic checks returned their expected results, including one expected inequality; the unchanged Lean declarations verified with pinned v4.29.1. This is not a whole-compiler or English-meaning proof. |

The completed [final report](../../../artifacts/interpretation/round11/final-report.json)
binds all six accepted manifests, the state hash and twelve unresolved issues.
The [state](../../../artifacts/interpretation/round11/state.json) retains every
attempt and repair. The within-M5 summary contains predecessor evidence because
it runs before M5 completes; the final report then adds M5 without a circular
hash. A final independent hash traversal confirmed those links and the test XML.

## Executed repairs

Six failed attempts remain in the history. M0 initially used an interpreter
without PyMuPDF. M1 encountered inherited application metadata during isolated
dependency checking and later found missing fixed PIT reporter dependencies.
M4 exposed Inspect's default write location and the missing PIT reporter jars.
M5's second attempt stalled in an existing Starlette TestClient startup inside
the sandbox and was interrupted. Each failed phase has an executed focused
regression and a refreshed plan before its accepted retry. The successful M5
retry passed the same API tests in the already approved trusted context; no test
was removed to obtain success.

The final audit separately corrected the legacy monograph checker's handling
of explicitly declared companion references. It also pinned the existing Lean
toolchain after a transient latest-release lookup timeout and added
post-completion report binding. The final focused controller regression passed
all 12 tests, including preservation of unresolved issues and rejection of
incomplete or stale finalization. `git diff --check` passed.

## Decision and continuation

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | What is not established |
|---|---|---|---|---|---|
| Accept the round's engineering integrations | All required phases, actual tool executions and full regression pass | No unresolved engineering failure in the accepted attempts | Evidence is scoped to these tools, fixtures and retained sources | Keep the pinned toolchain and immutable attempt evidence | General error-rate reduction or statistical independence |
| Retain semantic uncertainty | Every detected real-page disagreement remains reported after its two actions | Twelve source-disagreement vetoes still prevent semantic acceptance | Whether each difference changes a regulatory requirement | Classify exact differing source regions against the retained image and edition | Correct English interpretation or bank production readiness |
| Continue with the generated successor plan | The completed M0–M5 manifests and issues are bound to that plan | No current research-direction veto; individual discrepancies remain open | Full RuleIR semantics, host integration and external reference quality | Extend the independent encodings and generated-runtime checks, coordinate Catala integration, then evaluate a source-family holdout | That synthetic targets substitute for a legally validated evaluation corpus |

No stochastic comparison or model ranking was performed. Tool agreement,
mutation counts and successful execution are not calibrated probabilities of
legal correctness. The strongest alternative explanation for agreement remains
shared assumptions or omissions. A separating source fact or surviving material
runtime mutation would overturn acceptance of the corresponding claim while
leaving these tool integrations available for repair.

The [next-phase plan](../../../artifacts/interpretation/round11/next-phase-plan.json)
lists source-region adjudication, full RuleIR/four-state checks, generated-runtime
PIT, coordination with the Catala worktree, a held-out live study and scoped
KeY/calibration prerequisites. That successor work is planned, not completed in
this round.

## Reproduction

The approved trusted runtime vector is:

```text
/home/chakwong/python/legalmath/.venv/bin/python /home/chakwong/python/legalmath/scripts/run_assurance_master.py execute
```

Run manifests retain commit `9160ce72a17a255242299cc8ab33046f2501f42b`, the dirty
source hashes, exact child command vectors, environment, intentionally hidden
GPU devices, wall times, artifact hashes and CPU/toolchain locks. Source editions
are bound by their PDF hashes. Random seeds are not applicable to the declared
deterministic checks. No live provider calls were made. Installation and runtime
use the distinct exact vectors in the [allowlist](allowlist.json); local rules
and the operator guide describe their scope.

To resume, inspect `final-report.json` and the generated successor plan. Running
the master again first checks for changed material inputs and invalidates the
affected accepted phase and successors. Failed attempts must be repaired through
the documented operation; neither the attempt history nor its budget should be
reset. The Catala worktree and unrelated pre-existing changes were preserved.
