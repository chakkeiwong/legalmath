# Isolating the final assessment

The first final-assessment preflight used the wrong serialization when checking
the live journal. The native `journal_receipt` verifier checked the retained
journal successfully; assessment attempt 2 used that verifier. Both receipts
remain available.

Attempt 2 built and checked the monograph, then started a full regression in the
shared worktree. The progress log showed two failures. The two corresponding
dossier tests passed when run alone: 2 passed and 37 deselected in 25.63 seconds.
Before the full run completed, eleven material input paths had changed under
the separate bank-compliance development. They included transaction source,
transaction tests and the bank-compliance manuscript chapter. None belonged to
the 424-file reviewed assurance snapshot.

The suite then stalled at the API-test boundary in the sandbox, an environment
limitation already documented in START-HERE. Two SIGINT requests did not complete
cleanup. The owned pytest process was terminated, and its wrapper recorded
return code -15 after 902.911 seconds. Its partial log, manifest and commands
remain preserved. No complete JUnit result or failure traceback was produced;
therefore neither the full passing count nor the exact cause of each failing
assertion can be inferred from this run. Source changes invalidate a stable-tree
claim independently of those assertions.

The repair copied the source, tests, scripts, manuscript and retained evidence to
`/tmp/legalmath-continuation-final-20260929`. It preserved the toolchain's relative
paths and archived 862 material input files with their hashes. All 424 reviewed
assurance inputs remained unchanged. Each final material file was copied from a
stable read. The manifest does not pretend that concurrent development had an
atomic repository-wide checkpoint during the data copy.

The isolated assessment uses the existing Python environment with explicit
`PYTHONPATH` pointing to the snapshot. It checks the actual imported package
location before running. Trusted-host execution resolves the known API-test
environment limitation: that preflight passed in 0.91 seconds, and the complete
39-test dossier module passed in 39.88 seconds. Attempt 3 finished with 1,518
passing tests, one failure, no errors and no skips. The failure was the old
absolute appendix path in
`test_retained_authentication_appendix_is_an_explicit_root_for_both_arms`.

The focused repair reuses the already frozen appendix record when the old
producer receipt names a different checkout. It requires the same original task,
incorporated URL, PDF media type and byte hash, then applies the existing local
path and source-byte checks. It does not rewrite the producer receipt. The first
new positive test incorrectly compared loaded source dictionaries with reference
dictionaries; that test assertion was corrected to compare exact source bytes.
Its failed JUnit file is retained. The repaired checks, including symlink escape,
media-type mutation and all earlier source-freeze cases, passed 15/15.

`isolation-repair/manifest.json` binds the original frozen inputs, the failed
assessment, that focused result, the two changed code/test files and the updated
repair plan. All other snapshot inputs are unchanged. Attempt 4 executes the
same complete regression and document checks against this repaired snapshot.
It passed 1,529 tests with zero failures, errors or skips and unchanged snapshot
inputs. Its final result is recorded in
`final-assessment/attempt-04/manifest.json`. The separate finalizer checked every
retained phase output and the tested-input archive; later concurrent work is
listed separately rather than attributed to the passing result.

This repair changes the verification environment, not the source checks or the
acceptance threshold. It supplies evidence for the archived snapshot. It cannot
certify unrelated files edited afterward, convert a failed C6 receipt into a
pass, or enlarge the exhausted allowance. The report lists the snapshot's
differences from the live worktree separately.
