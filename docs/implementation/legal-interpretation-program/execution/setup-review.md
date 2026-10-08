# Execution setup review and result

6 October 2026 (Asia/Hong_Kong). Scope: the local operations and approval
mechanism for the legal interpretation master, not product implementation.

## Observed result

The dedicated rule was installed at
`/home/chakwong/.codex/rules/legalmath-legal-interpretation-program.rules`.
Its SHA-256 is
`d455efc4d75d84c5bd71b6c214acc58f5fb06be8504ba93d0e5de8e7bb3fb814`.
The exact launcher is:

```text
.venv/bin/python scripts/legal_interpretation_ops.py
```

A single grouped installation approval covered the finished local runner and
its rule installation. The environment additionally saved that exact
interpreter/script prefix for this session. The dedicated file lists the
ordinary actions separately and deliberately omits the installer. The saved
session prefix can also reach the installer, which remains limited to that
one named rule file and refuses different pre-existing content.

After installation, four actual calls using the same prefix, repository cwd,
`login: false` and trusted execution completed without further approval:
status, handoff verification, test-log reading and the P0 missing-test check.
The last correctly returned exit code 2 with NOT_IMPLEMENTED; it ran no product
tests and did not change phase completion.

The final tool self-test run passed **30 tests in 1.56 seconds**, with the wrapper
reporting **1.926 seconds** including launch/receipt overhead. These are
descriptive timings only. The actual result and output log are under
`artifacts/legal-interpretation-program/operations/20261005T174519Z-1499c9f8b7/`.
The rule checker passed 24 positive command examples and seven negative examples.
All 693 existing review-package hashes matched after setup.

## Skeptical findings and repairs

| Finding | Resolution and evidence |
|---|---|
| Old rules target a provider campaign or another interpretation runner. | Added a distinct fixed local launcher; negative policy examples include the old ops-run command. |
| Merely writing a policy under docs does not install it. | Installed the exact reviewed bytes in the active user rules directory and checked that installed file with the native CLI. |
| Shell-wrapped commands and changing interpreter/path spellings miss literal matching. | One documented relative spelling and cwd; tool calls use login:false, with no shell assignments, substitutions, pipes, redirections or timeout prefixes. |
| Large JSON edit payloads embed shell syntax in the command. | Added edit with one literal stdin JSON line. It delegates to the existing guarded editor, disables terminal echo/canonical line limits, and accepts no extra CLI arguments. The subprocess test retains literal shell characters and more than 12,000 characters. |
| Installing before checking the code could authorize a defective runner. | Installation requires a PASS self-test receipt bound to both runner and test-source hashes, plus native rule checks. |
| A missing future phase test might look like a successful empty suite. | Fixed phase mappings require every named test file and compare against the phase manifest. Missing files return NOT_IMPLEMENTED, as observed for P0. |
| A crash, timeout or failed executable could disappear from the history. | Unique attempt directory, atomically replaced/fsynced result records, captured output, explicit failed-launch/timeout/interrupted outcomes and bounded process-group termination. These paths have actual subprocess tests. |
| Successful tools might be confused with semantic phase completion. | Receipts carry phase_completion:false. No command changes the phase status or implements the P0–P8 repairs. |
| Borrowing an expired provider allowance could authorize fresh calls. | The launcher has no provider, Claude, download or install command. The local test environment hides GPU and removes common model credentials. This is not an OS network isolation claim. |
| A broad persistent command prefix could accept arbitrary suffixes. | The native policy matches prefixes; the CLI separately rejects unsupported actions, extra arguments, arbitrary test paths and shell pass-through. Both layers are required. |
| Inspection or editing could escape through paths or symlinks. | Repository/protected-path checks for inspection; existing guarded editor for writes. Protected metadata, parent traversal and symlink escape tests pass. |

## Operating choices and limits

Tests and document builds use existing environments. Test groups are fixed and
selected by name; no dependency or toolchain was installed. Subprocess limits
are convenience bounds: 120 seconds for tool tests, 300 for phase/regression
tests and document builds. A timeout means the attempt is incomplete, not that
the underlying method is invalid. Revise the recorded plan before extending a
limit for justified longer work.

The WSL host still cannot start its ordinary sandbox because of the
`/mnt/wslg/distro` mount. Trusted execution of the approved command is the
observed working route; the setup did not change global sandbox settings or
host mounts. Installation and the observed four calls do not guarantee that
another client session or a future managed policy will suppress every prompt.

The official Codex documentation endpoints returned HTTP 403. Syntax and match
behavior were therefore established using the locally installed
`codex execpolicy check`, not an uninspected web page. No claim is made about
undocumented hot-reload behavior. The observed session accepted the saved exact
prefix; future sessions can check the dedicated rule and reload if needed.

The frozen literature/program handoff remains intact. These new setup files are
a separate operational increment; they do not silently replace its review
version. Claude review and P0–P8 remain pending. When product execution resumes,
use the master and phase plan to implement the substantive repair, run its
mapped tests, inspect the receipts and rewrite/review the successor phase plan.
A tool-test receipt cannot stand in for that result.

## Decision

Proceed with local implementation using the exact commands in [the operator
guide](README.md). The approval mechanism and local tools passed their stated
checks. Source-to-rule fidelity, case-law applicability and the product phases
retain their earlier unresolved status. New external acquisition, dependency
installation or live model work requires concrete scope; this setup creates
no fresh numerical allowance.
