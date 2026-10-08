# Execution review, 6 October 2026

The protected proposal remains a pre-implementation snapshot. Live status is
state.json and next-phase.json in this directory. A runnable phase artifact is
not phase acceptance; downstream engineering may consume partial artifacts
only while preserving their unknowns. No phase has legal release acceptance.

The implementation found and repaired four concrete failures:
- pdftotext emitted XML-illegal control characters. The intake preserves the raw
  output hash and records each omitted XML code point and offset.
- A trailing sentence separator produced a spurious unknown clause. Empty
  operative pages remain unknown after the whitespace repair.
- Repeated PDF sentence fragments collided under text-only identifiers. Node
  occurrence indices now distinguish repetitions.
- The default Python lacked application dependencies, while the shared editable
  virtual environment imported the main checkout. The fixed phase wrapper selects
  the existing application interpreter and pins checkout code; P6 additionally
  installs the local package into /tmp with --no-index and verifies the installed
  service bytes before running the CLI. No dependency was downloaded.

Skeptical review: the grammar is a deliberately bounded development baseline.
Most unfamiliar fixtures abstain. Passing them demonstrates safe non-answers,
not general context interpretation. Q1/Q2 require explicit unit disposition,
complete declared scope and character coverage; missing clauses, dates or
dependencies prevent an accepted result. Typed clause inputs remain supplied
interpretations. The legacy v2 comparison and full automatic extractor are
unfinished. Bank inventory preservation does not establish applicability.

The BASF construction is partial. Page 112 visibly lacks a closing square
bracket at the end of the long-coupon alternative. No missing character may be
invented to assert complete composition. A structural deletion of that
unselected alternative needs an explicit source-backed operation and review.
The 26 German pages retain all body and marginal units in the source map.

The earlier manuscript version was inspected on physical pages 89–96.
After the final execution update, the rebuilt section and transitions were read
on physical pages 89–94, and the companion reproduction opening on pages 12–13;
no clipping was found. See document-review/FINAL-REVIEW.md for the final scope. The seven new citation judgments are author/executor
judgments based on the retained technical literature reading, not independent
legal or human readability acceptance. Equations, citations and historical
cases from the earlier source were preserved.

Next engineering work must improve actual source construction and typed
interpretation. Missing independent labels veto legal release, not continued
engineering. No population accuracy, automatic production readiness or actual
loss event follows from these development results.

## Verified final execution checkpoint

The continuation verified every current method, dependency and output hash.
The command `python3 -m scripts.prospectus_delivery run` then reused all nine
unchanged receipts. That is successful resumption, not nine newly accepted
phases. The exact run record is [finalization/resume.json](finalization/resume.json).

| Phase | Retained receipt | Engineering and evidence result |
| --- | --- | --- |
| P0 | [attempt-007](phases/P0/attempt-007/receipt.json) | Partial; reviewers, unexposed cohort and review-count reconciliation absent |
| P1 | [attempt-007](phases/P1/attempt-007/receipt.json) | Partial; source geometry captured, German order and dates need review |
| P2 | [attempt-005](phases/P2/attempt-005/receipt.json) | Partial; BASF construction and other agreement sets unfinished |
| P3 | [attempt-005](phases/P3/attempt-005/receipt.json) | Partial; bounded English interpretation, German semantics unresolved |
| P4 | [attempt-005](phases/P4/attempt-005/receipt.json) | Partial; dated authorities and actual applicability facts missing |
| P5 | [attempt-005](phases/P5/attempt-005/receipt.json) | Partial; complete financial conventions and independent calculations missing |
| P6 | [attempt-003](phases/P6/attempt-003/receipt.json) | Partial; installed CLI and bank inventory checks passed, real-contract acceptance absent |
| P7 | [attempt-002](phases/P7/attempt-002/receipt.json) | Guard executed; independent paired evaluation not executed |
| P8 | [attempt-002](phases/P8/attempt-002/receipt.json) | Guard executed; release blocked |

The full successor test suite passed again: **50 tests, zero failures, errors or
skips**, in 0.24 seconds of pytest time. The application interpreter, pinned
checkout path, CPU-only environment, command and JUnit output are saved in
[finalization/test-command.json](finalization/test-command.json) and
[finalization/tests.xml](finalization/tests.xml). The verification run manifest
is [finalization/manifest.json](finalization/manifest.json).

Inspection of P6 [integrated-report.json](phases/P6/attempt-003/integrated-report.json),
[bank-obligations.json](phases/P6/attempt-003/bank-obligations.json), and
[installed-package.json](phases/P6/attempt-003/installed-package.json) confirms:
Q1/Q2/Q4 UNKNOWN, Q3 PARTIAL, Q5 UNSUPPORTED, Q6 CONDITIONAL; all 14 bank
obligations retained; installed service hash matches current code;
`source_path_injection=false`; no independent legal acceptance and no
transaction permission. These are bounded integration findings, not semantic
success on BASF.

BASF intake: four documents, 519 pages, 43,626 text units and 489 detected
references. Assembly: ten operations, 163 unresolved bracket branches and one
unmatched opening at raw offset 14862;
`full_german_contract_constructed=false`.
The compact inspected results are in
[finalization/verification.json](finalization/verification.json).

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain engineering checkpoint | Current receipts, installed service and 50 tests pass | No verification veto | Complete contract and semantic coverage absent | Complete source-backed construction and interpretation | General correctness or completed engine |
| Keep legal release blocked | Independent finite-cohort criterion not evaluated | Missing labels, scope and independent sign-offs | Real legal meaning and source applicability | Obtain independent readings after source construction | Accuracy, legal clearance or production readiness |
| Continue repair program | Failures identify incomplete source/meaning interfaces | No research-direction continuation veto | Whether reviewed complete inputs allow useful answers | Diagnose reviewed inputs before automatic extraction comparison | Rejection of source-to-answer design |

The result invalidates a claim of completed delivery. It does not invalidate
the source-to-answer approach or justify abandoning the planned repairs.
The strongest alternative explanation for the passing tests is that they mainly
exercise abstention and development grammar. A correct independently reviewed
positive/negative evaluation on complete real contracts is still required.
The weakest evidence is source construction and automatic German interpretation.

The first attempted finalization invocation used `python3 -m runpy` with a file
path, which runpy interprets as a module name. It failed before any verification
work. The corrected checked-in command is
`python3 -m scripts.verify_prospectus_delivery`. The failure changed no phase
receipt or result.

The final tracked-file `git diff --check` passed. A separate no-index check
of 23 added implementation/documentation files found three existing trailing
blank lines at EOF: basf.py:151, jobs.py:236 and test_successor.py:237. All other
checked additions had no whitespace diagnostics. These formatting-only lines
were retained to preserve the verified source-byte bindings; no global
whitespace-clean claim is made. The no-index exit status 1 on the other files
indicates that each file differs from /dev/null, not a whitespace defect.
