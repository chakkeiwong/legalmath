# Current prospectus package integration audit

Baseline: `03883b5f7d914a2678ac4f472e688c9fc1c60006`, clean
`feature/prospectus-evidence-master` worktree. This investigation answers the
user's request to understand the remaining package integration gaps. It does not
implement repairs or rerun the historical repair program.

## Question and evidence contract

For every package or tool proposed in the prospectus survey, which supported
inputs can reach a real service consumer, what transformations preserve their
meaning, and what evidence supports that path? Distinguish our missing or faulty
integration, configuration/usage limitations, unavailable source or human inputs,
unexecuted capability, and a demonstrated limitation of a pinned package.

The comparator is the actual service and installed CLI at this commit, together
with the latest retained trial receipts. Old plans and completion statements are
claims to check, not the baseline. A functioning integration requires a traceable
producer, validated boundary, consumer and relevant exercised behavior. A trial
may correctly validate a narrower adapter without meeting this criterion.

Primary audit criterion: each surveyed tool has a code/evidence disposition and
every reported defect has a concrete trigger and inspected implementation or
minimal reproduction. Wrong source identity, ignored input, unvalidated output,
unsupported default and disagreement with the declared target are defect
evidence. Test counts, installation, successful HTTP calls and benchmark scores
are explanatory only. None establishes full legal correctness, general parser
accuracy, production readiness or a fundamental package defect.

Continuation vetoes: changed baseline, corrupted comparators, unexpected external
write, protected-path write, or a diagnostic requiring an unreviewed long run.
Missing coverage triggers a targeted investigation; failed candidates do not
stop unrelated audit paths. Do not run `scripts.verify_prospectus_repairs` or
refresh sealed historical outputs.

## Investigation sequence

1. Inventory survey candidates, dependencies, service entrypoints and setup.
2. Trace package producer → adapter → persisted representation → service consumer,
   including constructor, interpretation, annotation, finance and recovery paths.
3. Compare actual test assertions and current receipts with each claimed use.
4. Use small CPU-only temporary probes only where reading leaves an actionable
   question. Preserve their code, commands and results in the audit directory.
5. Record severity, trigger, root-cause class, scope, evidence and the smallest
   discriminating repair/check for each gap. Update the current reset pointer.

Commands: bounded `rg`, `sed`, `nl`, Git reads and, if needed, the existing
application Python for isolated diagnostics with `CUDA_VISIBLE_DEVICES=-1` set
before imports. No network, package installation, live authoring, new benchmarks,
Git mutations or source-code changes are planned. Results belong under
`docs/implementation/prospectus-package-integration-audit/`; temporary inputs
belong under `/tmp`.

## Assumptions and skeptical review

The latest 153 passing tests are a regression baseline, not proof of integration
coverage. The two Docling pages and synthetic annotations are exposed development
inputs. Optional comparator tools need not be runtime dependencies; the audit
must judge the promised role rather than demand every tool be called per request.
ResearchAssistant availability does not imply service integration. Hand-reviewed
legal premises cannot be attributed to an automatic package. Retained package
versions and models constrain every package-behavior conclusion.

Audit verdict before investigation: PASS for this bounded read-only code audit.
Wrong baselines, stale completion labels, proxy promotion, unmatched environments
and hidden source defaults are explicit targets. The earliest check is the call
graph and actual assertions, before any diagnostic. No population ranking or new
package rejection will be inferred. A complete package-level verdict requires a
supported configuration and a minimal reproduction; absent that, record the
narrower local gap or 'not checked'.

## Targeted diagnostic review

Code inspection nominates seven small checks, all on synthetic temporary inputs:
duplicate/reordered/out-of-range retained OCR pages; an excluded alternative used
as a named clause constraint; solver diagnostics retained by the service; a
thirteen-fact law/constructor expression despite selecting Z3 for the request;
references into AST-rendered text; evaluation of an unbound source quotation;
and a native subprocess reading a file
outside the recorded input list. Each compares a valid control with one changed
boundary. The native-read check tests the already declared limitation, not a
claim that this component is an OS sandbox. The excluded-constraint check tests
missing applicability admission, not Z3's Boolean arithmetic. The scoring check
cannot establish fake human identity; it tests only mechanical source binding.

PASS before execution: no model, server, external retrieval or historical output
is needed. Use `.venv/bin/python` with CPU devices hidden, a 60-second process
bound and a new diagnostic directory. Record every result, including negative
findings. These checks classify engineering boundaries; they are not a research
benchmark or acceptance evaluation.

Follow-up after the seven probes: compare standalone replay with fresh intake
after changing only the OCR derivative, and compare a missing Poppler executable
with a normal text-source control. Both are small source-boundary diagnostics;
they require no real OCR, new PDF parser run or altered runtime. A mocked missing
binary is an error-path check, not evidence that Poppler is absent on this host.
An archived P1 product may be replayable by design; distinguish frozen replay
from a result described as current instead of calling every old snapshot corrupt.

The reader protocol's standalone `.xmi` example also needs a discriminating
check: the codec has no type-system argument but the decoder requires one unless
it arrives inside a ZIP export. Compare a freshly encoded synthetic CAS as plain
XMI versus the same bytes with their type system in ZIP, using only the installed
Cassis sidecar. No server, browser or human annotation is involved. This is an
API/usage smoke check with a 30-second subprocess bound.

## Completion

The [report](../implementation/prospectus-package-integration-audit/REPORT.md)
records twenty findings and coverage gaps, with separately classified package
prerequisites. All targeted probes completed and their results were retained;
observed boundary failures did not invalidate unrelated audit paths. Final checks
verified all 76 indexed file hashes, 67 local Markdown links, the four JSON
records and four Python scripts, recorded probe hashes and whitespace. Source
HEAD remained the stated baseline. No production repair or broader regression
rerun was performed.
