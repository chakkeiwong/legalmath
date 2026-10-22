# CLI invocation repair before formal freeze

Development diagnostic004 passed64 checks and failed the actual command test.
The new runner and test incorrectly invoked `python -m legalmath`; this package
has no `legalmath/__main__.py`. The project entry point is `legalmath.cli:main`
(pyproject.toml), and sealed095 uses `python -m legalmath.cli`.

Change only those two unsealed invocation prefixes to the existing CLI module.
Retain diagnostic004 and its command log unchanged. Test failures now include
captured stderr. No production behavior or frozen source expectation changes.
The isolated installed check already calls legalmath.cli.main and needs no repair.

Skeptical audit: PASS. This corrects an execution-harness error against the exact
existing entry point. Passing the changed test still requires discovery and
reconciliation files to equal the API reports, not merely a zero exit. Formal
freeze has not happened, and there is no unchanged formal retry or new allowance.
