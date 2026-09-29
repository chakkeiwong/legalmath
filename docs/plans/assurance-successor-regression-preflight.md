# Current implementation regression while the live study runs

Question: does the current engineering implementation pass the full existing and
new regression suite, including the pinned actual backends? The comparator is the
previous 1,029-test integration acceptance; the primary criterion is the entire
current suite with no failures, errors or skips and unchanged material source
hashes during execution. A failing test, changed implementation or missing XML
vetoes reuse of this result. Counts and elapsed time are descriptive only.

Run the fixed master action `.venv/bin/python
scripts/run_assurance_successor.py preflight` in the trusted environment. It
executes the whole suite, with CPU-only settings, in a separate artifact directory
and does not change phase state or consume model calls. This is independent of
the live interpretation requests. Tests use their isolated temporary fixtures;
the source programs and tool installations are read by the live study.

Before and after the run, record all material Python, Java, Lean and JSON source
files under `src`, `tests` and `scripts`, the commit, exact command, environment,
CPU status, timestamps, log/XML hashes and output paths. The run is not legal
accuracy evidence. The final S11 may reuse it only if the exact current material
hashes and retained files still match and the full suite passed without skips;
otherwise S11 executes the required suite again. No phase is marked complete by
this preflight alone.

Skeptical audit: an earlier subset pass cannot substitute for this suite. The
test process must not dispatch a live model; existing test fixtures explicitly
isolate provider calls. A result collected before later code changes becomes
stale. Shared source mutation is a hard veto. The official live task and reference
outcomes are not exposed to the initial interpretation contexts by this action.
The artifact is `artifacts/assurance-successor/2026-09-28/regression-preflight`.
