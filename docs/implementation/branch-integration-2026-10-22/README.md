# Branch integration evidence, 22 October 2026

User request: commit the current and prospectus branches, merge prospectus into
main, resolve conflicts, commit and push main.

The legal checkpoint is `a093e062a26d6f3ad28110b06cbbbb3c6a639b28`; the
prospectus checkpoint is `76d2dfa8c0cd2bc25b213e49656bca4261c4652a`.
The merge preserves both instruction blocks in the sole conflicting file,
`AGENTS.md`. The automatic package-data merge was inspected.

`validation.py` is the exact diagnostic helper run from
`/tmp/legalmath-main-integration-20261022` using the root `.venv-context`
interpreter. It is retained as a run record, not installed product code.
`tests-manifest.json` preserves the commands, test selection, source path,
environment and elapsed time. `tests.xml` records 453 passes. The three tests
named by the selection expression require retained production evidence and were
deliberately deselected. `static.json` records syntax, conflict-marker,
package-data and outgoing Git object size checks.

The broader premerge prospectus run recorded 2,378 passes and five failures:
registration-only validation of accumulated method changes; frozen/current
installed-method identity; a stale exact-source dispatch expectation; and two
tests requiring a missing annual-statement fixture. Those failures remain open.
See `docs/plans/branch-integration-2026-10-22.md` for full scope and review.

The original legal checkout remains at its checkpoint on
`checkpoint/legal-integration-2026-10-22` so its active worker's bound bytes are
preserved. Later edits and bulky local archives remain outside this checkpoint.
This commit is not a full execution archive or legal/product acceptance.
