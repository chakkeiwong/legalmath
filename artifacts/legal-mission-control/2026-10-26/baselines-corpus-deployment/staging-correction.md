# Bounded staging correction

The first full validation passed master construction and state classification,
then failed mission reference checking: Missing evidence:
check_corpus_and_residuals.py. No source or registration transaction had run.

The staged filesystem overrode read_text/read_bytes but omitted is_file/exists.
New-file bytes were available to hash checks while mission validation correctly
reported them absent. The correction maps existence checks to the same exact
staged paths. It does not skip any evidence, hash or mission validation. An early
complete mission-reference pass now precedes the expensive historical validation.
All 145 passing candidate tests and immutable staged identities remain unchanged.
This is the one bounded deployment-harness correction; no legal verdict, task
attempt or provider allowance changes.
