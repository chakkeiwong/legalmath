# Prospectus closure controller repair, 11 October 2026

## Research and engineering intent

The question is whether the closure controller schedules, fingerprints and
reuses phase evidence correctly after the merged branch changed shared project
metadata. The current comparator is the merged `closure_program.py`, its
`test_closure_program.py` tests and the retained R0–R8 receipts. The repair
targets the controller's evidence lifecycle; it does not promote any legal or
automatic-interpretation result.

The evidence contract is:

| Role | Contract |
|---|---|
| Primary criterion | A phase receipt is current only when the code, executed test/support files, relevant packaging metadata, environment and declared plan match, and every parent receipt identity matches. |
| Promotion veto | A test failure, invalid auxiliary evidence, digest drift during execution, missing output, unsupported retry or corrupted receipt blocks current phase promotion. |
| Continuation veto | A malformed plan/binding, missing executable input, lock contention, or an unchanged failed/interrupted attempt with the same method and parents stops that phase until a reviewed repair or changed input exists. |
| Explanatory diagnostics | Test totals, elapsed time, package counts and preflight executable locations explain a result; they do not establish correctness or legal acceptance. |
| Not concluded | This repair does not establish source authenticity, legal correctness, package superiority, automatic extraction quality, production confinement, portability or independent review. |
| Artifact | New focused tests, a versioned binding schema, refreshed status, per-phase receipts and an execution note under the closure directory. |

## Skeptical audit before execution

The old controller bound every phase to all successor tests and every
`prospectus_closure_*.py` helper. That made an unrelated test or helper change
invalidate phases it could not execute. It also hashed the complete
`pyproject.toml`; the merged addition of legal-interpretation package data
therefore made prospectus receipts stale even though the prospectus package
and command were unchanged. The repair keeps build/runtime fields and only the
prospectus package-data entries in the phase binding.

`status()` selected the newest valid receipt rather than the newest attempt.
That allowed an invalid or interrupted newer attempt to be silently hidden by
an older receipt. The repair treats the newest attempt as authoritative for
currentness while retaining older valid attempts as history. Finally,
`execute()` compared only the method hash when refusing an unchanged retry.
The same method with a changed parent receipt is a new evidence state and must
be runnable; the exact same method and parent state after a failed or
interrupted attempt remains blocked.

The changes preserve the existing evidence contract: failed attempts remain
valid diagnostic records, stale receipts are never silently promoted, and a
passing engineering check remains partial where `REMAINING` says so.

## Repair and execution sequence

1. Add phase-scoped test/support bindings and canonical prospectus packaging
   metadata; version the binding schema and make preflight expose it.
2. Make newest-attempt invalidity visible in status and refresh, including a
   repair reason rather than an apparent completion.
3. Compare method and parent identities in the retry guard; add regression
   tests for unrelated metadata, parent changes, invalid latest attempts and
   unchanged failed retries.
4. Run focused controller and attribution checks, then the closure dispatcher
   from R0 onward while the evidence contract remains satisfied. Do not rerun
   unchanged historical long tests; each new receipt records its command,
   method, parent identities, environment, outputs and residual gaps.
5. Refresh the next plan after each work package and record whether a result
   changed the controller, a candidate implementation, the harness or only the
   evidence boundary. Stop only on the stated continuation veto.

## Re-audit after the interrupted R4 run

The first narrowed binding (`closure-bindings.v2`) passed its 14 focused
controller checks and R0/020, R1/018, R2/018 and R3/016. R4/015 was stopped
after discovering that the first import scan omitted
`src/legalmath/prospectus/legal_review.py`. R4/016 was stopped at the next
audit: `basf_scope.py` loads `basf_scope_review.json` through
`importlib.resources`, but the binding hashes only Python files. Pytest also
loads `tests/conftest.py` automatically and reads `tool.pytest` configuration;
neither was bound. The import index represents package initializers as
`package.__init__`, so imports of a package need not bind that initializer.
These are controller-method failures, not adverse results for the legal engine.
Preserve both incomplete R4 attempts; do not promote either to a PASS receipt.

The earlier comparator is the merged branch at `e8beb52b1` plus its retained
pre-merge evidence, not the interrupted attempt. The primary criterion remains
method and parent identity with passing actual tests. Test counts, old valid
receipts, auxiliary package diagnostics and short focused checks are explanatory
or veto evidence, not substitutes for current phase results. The existing
4,500-second R4 bound is a reviewed resource ceiling, not a promotion metric.
An unchanged failed/interrupted method and parent state is a continuation veto;
a repaired binding version is a changed method, so one new attempt is justified.

The v3 repair will bind auto-loaded test configuration, package initializers,
packaged prospectus JSON and the direct/recursive project imports of actual
phase tests. It will exclude the global CLI import graph from phases that do
not exercise that CLI, while retaining the CLI in the runtime phase and through
its parent identity in final attribution. The packaging projection will retain
build, project, setuptools and pytest fields, excluding only the explicitly
unrelated `interpretation/` package-data patterns that caused the merge drift.
Malformed packaging and receipt records must produce a reviewable invalid
state, never an exception that masks status. Regression checks must mutate each
newly bound input and confirm an unrelated test/interpretation-resource edit
does not change the method. First run focused checks; then run R0–R8 in DAG
order, refreshing and inspecting each sealed receipt. No new full-phase run
starts until these controls pass. Stop on a real failed criterion or another
uncovered runtime input; revise the method before any repeated long run.

The strongest remaining risk is dynamic imports or native dependencies outside
the declared binding. R6 retains a separate native-confinement and second-host
gap; this repair cannot claim complete dependency closure or legal acceptance.
This revised plan passes the skeptical baseline, criterion, environment,
artifact and stop-condition audit for a bounded controller repair.

## Final focused admission

The v3 focused check passed 23 tests through the checkout dispatcher. An early
relative-import regression failed because the level-one slice was empty; the
slice is corrected and the package-initializer/transitive/nested-script controls
now pass. A direct interpreter probe initially imported the installed older
package; it was discarded and rerun with explicit checkout `src` precedence.
All actual phase commands already enforce that precedence.

Trace review also found that the dispatcher returned exit zero when pytest
completed successfully but mandatory auxiliary evidence failed. It now returns
nonzero for that criterion failure and for `REPAIR_REQUIRED`. Refresh no longer
offers an unchanged interrupted attempt as a runnable next command. Actual
controller fixture executions cover changed parents, reuse of a passing
receipt, unchanged retry refusal and failed auxiliary evidence; the fake test
process in those unit checks does not count as a substantive phase run.

The exact focused command was
`python3 -m scripts.prospectus_delivery --program closure check tests/prospectus_successor/test_closure_program.py`.
It passed 23 tests in 2.30 seconds; `git diff --check` also passed. All R0–R8
bindings have no missing-input issues and all retained R6 auxiliary records
validate. Next run the focused controller/attribution pair with a retained XML
record, then R0–R8 using the fixed dispatcher. R4 retains its 4,500-second
ceiling. Keep bound code, tests, source packets and declared plans fixed from
phase admission to sealing; changes require explicit re-admission.

## R6 recovery fixture repair

R4/017 passed 386 checks in 3,157.075 seconds and R5/015 passed 65. R6/015
failed its actual-executor property check: the isolated repository had no
dispatcher, root plan or packaging metadata, so the repaired admission guard
correctly returned `HANDLER_OR_DEPENDENCY_MISSING` with `NOT_CHECKED` before
running the assessment. Fourteen other R6 checks passed. This is a fixture
compatibility defect caused by the new required-input rule, not evidence of
failed source recovery or a package limitation. Preserve the failed receipt.

Repair only the R6 recovery fixture by copying its actual required dispatcher,
plan and packaging inputs, and assert no binding issues before its first
execution. Add the minimized source/source example explicitly and show the
returned diagnostic in failures. First run that bounded example, then the
declared property check. The real clean-assessment comparator and mutation
actions remain unchanged. This test is scoped to R6; no earlier phase code or
input changes are justified. Passing the actual R6 phase after the changed
fixture admits R7 and R8. Review verdict: PASS; the fix supplies missing
execution context without weakening admission or the comparison criterion.

## Attribution review refresh

R6/016 passed all fifteen checks after the fixture repair; R7/015 passed
eleven. R8/016 correctly refused stale G20 evidence: its current-review record
still referenced pre-repair controller and controller-test hashes. Preserve
the entire prior attribution review, then revise G20's wording and those two
bindings after inspecting the actual repaired code and current phase results.
The old 685-identity coverage remains historical evidence at its recorded
method; it is not current whole-suite coverage. Add the focused v3 checks and
R0–R7 receipts as named evidence. Do not change any sealed phase receipt or
silently recompute every review hash. Retry only R8 under this reviewed input
change. This repairs a stale review record without weakening evidence checks.

## Final hybrid revalidation, 11 October 2026

The staged hybrid implementation was copied into the product and then traced
through `source_graph.py`, `extraction.py`, `ocr_worker.py`, the real three-report
consumer and the closure dispatcher. Native units remain unchanged; selected
pages retain original PDF numbers; retained pages are rerendered from the bound
PDF before acceptance. The focused product checks passed 9 tests and the
compatibility checks passed 56. The consumer passed for fresh 2008 OCR, retained
2009 OCR with rerender verification and native 2010, with 104,996 graph units;
a wrong source hash was rejected.

The stale G01, G10 and PyMuPDF/Tesseract/Poppler attribution hashes were
replaced with current code and product evidence. The prior attribution and gap
register remain under `controller-repair-2026-10-11/`. R7/016 passed 11 tests
and R8/019 passed 2 tests. After refresh, R0/022 through R8/019 are all current,
artifact-valid and engineering PASS; primary criteria remain PARTIAL and
external acceptance remains NOT_ESTABLISHED.

Skeptical audit: the comparator is the sealed pre-hybrid v3 method; the primary
criterion is actual product consumption with source/page/image identity and
native preservation; test totals, OCR word counts and runtime are explanatory;
wrong-source/page/model/image controls are vetoes. No unchanged retry remains
justified. The result does not establish whole-document coverage, authenticated
originals, native dependency confinement, second-host portability or legal
acceptance. The next changed work is the source, coverage, confinement and
independent-review program in `NEXT-PROGRAM.md`.
