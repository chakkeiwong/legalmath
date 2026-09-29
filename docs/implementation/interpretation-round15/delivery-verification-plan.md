# Round-15 delivery verification

This continuation verifies the completed implementation against the repository's
existing regression suite and incorporates the observed result in the unified
monograph. It does not expand the live allowance or reinterpret a failed phase
as a pass. The round-15 execution plan and its bound code remain unchanged while
the master runs.

The baseline is the round-14 record of 765 passing tests and the 270-page main
monograph. The new focused preflight passed 54 tests. The full regression command
is `.venv/bin/python -m pytest tests -q
--junitxml=artifacts/interpretation/round15/full-regression.xml`, with
`CUDA_VISIBLE_DEVICES=-1`, `HF_HUB_OFFLINE=1` and the installed project/tool
environments. The test inventory uses mocks or temporary allowances for model
work; it is not a new live interpretation experiment. The command, times, commit,
code identity and exit status will be retained in `full-regression-manifest.json`
alongside its complete log. Stop after 30 minutes and preserve an incomplete
result rather than report a pass. A failing assertion triggers a scoped repair
and the checks justified by that repair. Test count is an engineering diagnostic,
not an estimate of legal accuracy.

Before editing the monograph, wait for the master to finish and preserve its
current TeX sources and PDF. Add a connected explanation of the restored-context
failure, exact rational representation, and observed round-15 findings. Preserve
all existing chapter text. Rebuild with the established document environment,
run both document checkers, inspect the new rendered pages and confirm that the
proposal alias is byte-identical. Page count is a loss diagnostic, not a quality
criterion. Human readability acceptance remains pending.

The delivery record will distinguish immutable execution inputs from the later
documentation revision. It must verify phase/model receipts and their referenced
files, all 232 restored rows, the unchanged allowance prefix, the 500-call ceiling,
and the remaining dependency queue. A successful delivery cannot promote a
model judgment into legal proof or a backend comparison into source equivalence.

Skeptical review: the chief misleading success would be a fully green suite while
the source interpretation remains incomplete. The explicit phase counts and
pending queues veto that conclusion. Concurrent regression execution is confined
to temporary test data and immutable code; it does not mutate master evidence or
consume model reservations. Any resource contention or source change must be
reported before attributing a failure to the implementation.

## Targeted child witnesses

Reviewing the actual parent comments shows that P2's generic Boolean probes
cannot establish historical coverage or performance of a duty. A supplementary
local run therefore freezes nine cases for the three unchanged encoded children:
one positive input, one historical version refusal, and one changed condition
per child. It also records pairs of event histories that project to the same
child inputs while differing in contact timing or performance. These pairs are
information-loss witnesses under the stated projection, not adjudicated legal
answers. No source-derived commencement date or performance deadline is invented.

Run `.venv/bin/python scripts/assurance_round15_witnesses.py` after its own small
Python check. The command compiles the unchanged children and applies Java,
Python, cvc5 and supported Catala to the actual cases, writing
`artifacts/interpretation/round15/child-witnesses`. Expected ERROR results are a
promotion veto for historical use, not a test-harness failure. A backend
disagreement invalidates that comparison. The run uses no model calls and does
not change the active master or its inputs. The skeptical audit accepts this
addition because it tests the identified parent conditions directly rather than
treating a larger generic probe count as closure.

## Environment repair

The sandboxed full run reached 558 completed tests and stalled at
`test_api_evaluation_identity_and_restart` until its 30-minute limit. That exact
test passed in the trusted environment in 0.93 seconds. Preserve the timeout
under `sandbox-regression`; it is incomplete environment evidence. Run the full
suite with `python3 -m scripts.run_round15_regression` in the trusted environment.
The standard-library supervisor invokes the same project Python, adds a
60-second thread-dump diagnostic, enforces the same CPU-only and 30-minute
limits, and retains command/code identities and logs. This repair changes no
product code or expected outcome. A trusted failure remains a real test failure
to investigate; the isolated pass does not establish that the full suite passes.

## Summary binding repair

The delivery check found P0–P5 summary manifests carrying six predecessor hashes
instead of their phase-specific prefixes. The immutable journal and stored phase
results retain the correct prefixes 0–5: the in-memory summary shared the mutable
dependency list. Preserve the original summaries and executing code in
`pre-summary-repair`. Copy the list in `phase_binding`, and extend the resume test
to compare every summary against its stored journal result. Reconstruct only the
derived summaries with `scripts/repair_round15_summary.py`; verify that all result
content is identical and the journal hash is unchanged. Do not rerun model work
or change its evidence. Bind the executing and repaired code hashes separately
and repeat the full suite on the repaired code before final acceptance.

## Timed diagnostic crash

The first full rerun of the repaired code exited with signal 11 after beginning
the 60-second stack-dump diagnostic in the long Catala operator-status test.
No failed assertion or complete crash traceback was produced. The isolated
test then passed in 79.24 seconds with `faulthandler_timeout=0`. This nominates
the asynchronous dump as a possible cause, but does not establish it. Preserve
the failed run under `diagnostic-crash-regression` and repeat the full trusted
suite with pytest's default disabled timed-dump behavior, keeping the independent
30-minute process deadline. No product code or expected result changes. If the
crash recurs, stop and investigate the runtime; do not label the suite passed.
