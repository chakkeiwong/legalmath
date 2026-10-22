# Commit and integrate legal and prospectus work, 22 October 2026

User instruction: commit the current branch and the prospectus branch, merge
the prospectus work into main, resolve conflicts, commit and push main.

This is a repository checkpoint and merge, not legal/product acceptance or a
new live execution allowance. Main starts at `3c3e462acabfde8c62285f4274f0f8c62b90a790`;
the prospectus worktree starts at `e8beb52b13399f18bbbff9aecea9636803729d5f`
on `feature/prospectus-evidence-master`, already an ancestor of main. Both
worktrees have substantial uncommitted changes.

## Dependency map and completion evidence

| Item | Success prerequisites | Independent work | Completion evidence / recovery |
| --- | --- | --- | --- |
| Inventory and audit | None | Inspect both worktrees | Scope lists, sizes, baseline refs and worker identity |
| Main checkpoint | Inventory | Prospectus checks and checkpoint | Commit containing current implementation, tests, plans, compact evidence and complete manuscript inputs |
| Prospectus checkpoint | Inventory | Main checks and checkpoint | Commit containing implementation, tests, plans and compact authority/result records |
| Isolate running legal checkout | Main checkpoint | Prospectus checkpoint | Same files and live worker on a new snapshot branch; main free for isolated worktree |
| Merge | Both checkpoints and isolation | Remaining read-only checks | Merge commit preserving both parents; resolve content conflicts explicitly |
| Validate and publish | Merge | No independent publish branch | Diff hygiene, scoped tests, no oversized new blobs, normal push to origin/main, remote hash equals merge HEAD |

Failures in one check do not block inventory or the other checkpoint. Investigate
environment failures once in the declared environment. Do not retry external
legal/model calls or change grants. Unexpected semantic conflicts, remote
divergence, missing source dependencies or invalid evidence block publication
until investigated; keep both commits and independent work. Never force-push,
discard changes, or overwrite sealed execution results. Stop this Git task when
both commits and the main merge are preserved and the remote hash is verified.

## Scope and skeptical review

Include changed tracked files, new source/tests/fixtures, plans and compact
decision records needed to understand the checkpoint. Main's manuscript changes
must include their new chapter and bibliography inputs. Keep large downloaded
and generated local caches, repeated historical snapshots and active dispatch
output outside this Git checkpoint; preserve them locally and record this
limitation. A repository commit is not a full backup of execution artifacts.

Review found a material flaw in an in-place merge: current legal bindings include
prospectus source hashes. Preserve the running checkout's bytes by moving its
branch at the checkpoint and merge in a separate worktree. This avoids changes
to the bound source without rebinding or weakening any checks. Do not replace
main's legal instructions with prospectus-only worktree instructions.

Review also found environment mismatches: the prospectus `.venv` symlinks to
main's environment and default imports resolve main's source. Tests must select
the prospectus source explicitly. Legal capacity tests require `.venv-context`.
The first full prospectus attempt was interrupted; its outcome cannot be
reported as a passing suite. The focused changed-area suite passed 366 tests;
legal regressions passed 240 tests in `.venv-context`. Full-suite collection
in `.venv-context` lacks Hypothesis; additional checks must use the prospectus
environment with correct source selection, or report the exact limitation.

Audit verdict: PASS for the revised checkpoint-and-isolated-merge plan. Exact
Git ancestry and file contents are the merge criteria. Unit tests are engineering
checks only; pending source applicability, review validity and legal acceptance
remain open. No model, numerical or scientific performance claim is made.

## Execution record

The main checkpoint selects 617 files (about 114 MB of file contents, including
already tracked files). The prospectus checkpoint selects 8,085 files (about
770 MB before Git compression), including all pending source, tests, fixtures,
plans, top-level authority records, history, dossiers and compact attempt results.
Repeated frozen worktrees, full product outputs, downloaded runtimes and live
provider payloads remain in their existing local locations. This is deliberately
not a self-contained restoration of the entire execution evidence archive.

Validation outcomes before merge:

- Legal repair/capacity tests: 240 passed in 22.92 seconds, `.venv-context`.
- Prospectus changed-area tests: 366 passed in 55.03 seconds, `.venv-context`
  with prospectus `src` first on the import path.
- Corrected broader prospectus run: `.venv` with both parent and child source
  paths fixed, CPU hidden, five-failure stop: 2,378 passed and five failed in
  235.18 seconds. Hypothesis is present in `.venv`, absent in `.venv-context`.
  Failures: a registration-only check rejects accumulated validator changes;
  a retained OCR test rejects current methods differing from its frozen methods;
  an older dispatch test expects a previous exact source; two annual-group tests
  require the not-yet-present `bes_annual2010_statement_cells_v7.json.gz`.
  These failures predate this merge. They are recorded, not suppressed, and the
  requested Git checkpoint does not certify either product complete.
- Initial tracked diffs pass whitespace checks. Added source-bound publications
  and fixtures retain original whitespace; several frozen source/test files have
  harmless trailing whitespace or a final blank line. Do not change their bytes
  merely to clear a cosmetic diagnostic and break existing evidence hashes.

Both worktrees are being edited concurrently. The staged snapshot defines the
checkpoint boundary. Later working changes remain in place and are not discarded.
The legal worker and its hashes must remain in the original checkout. The
separate main integration checkout can be validated without mutable run output.

## Merge validation audit

Checkpoints: main `a093e062a26d6f3ad28110b06cbbbb3c6a639b28`, prospectus
`76d2dfa8c0cd2bc25b213e49656bca4261c4652a`. Main is checked out for the merge
at `/tmp/legalmath-main-integration-20261022`; the running legal checkout stays
on `checkpoint/legal-integration-2026-10-22` at the main checkpoint.

The sole content conflict is `AGENTS.md`. Resolution retains both instruction
blocks under their separate legal/prospectus headings and the shared continuation
policy. The automatic `pyproject.toml` merge retains main's dependencies and adds
the prospectus JSON and compressed JSON package-data patterns.

The merged-checkout check uses the root `.venv-context` interpreter with both
`PYTHONPATH` and parent imports pointing explicitly to this checkout. It runs the
common capacity, acquisition, review, timeout, budget and registration controls,
plus prospectus mechanisms, consumers, coupon, finance, program, synthetic scan
and repair controls. The real BASF/BES archive checks and the authenticated
production timeout/receipt checks are not repeated against a partial archive.
Their premerge evidence remains distinct. CPU devices are intentionally hidden;
no provider calls or product authority transitions are part of this Git task.

Exact validation entry points (temporary diagnostic helper):

```text
/home/chakwong/python/legalmath/.venv-context/bin/python /tmp/legalmath-merged-validation.py static
/home/chakwong/python/legalmath/.venv-context/bin/python /tmp/legalmath-merged-validation.py tests
```

Audit verdict: PASS for these engineering merge checks. Compare committed parent
snapshots, not concurrently changing worktrees. A source import from either old
checkout, a new semantic conflict or an oversized outgoing Git blob vetoes
publication until investigated. Local archived evidence is not recreated or
substituted. The pre-existing broader-suite failures remain open and do not
become passing acceptance evidence merely because the merge checks pass.

## Merge check results

The merged-source suite passed **453 tests in 15.48 seconds**, with the three
explicitly identified archive-dependent tests deselected. Both legal and
prospectus modules resolved to the integration checkout. No live calls were
made. Static checks parsed 1,395 changed Python files, found no merge-conflict
markers in checked source, verified both added package-data patterns, and found
no outgoing blob at or above GitHub's 100 MiB file limit among 9,279 outgoing
blobs. The largest was 40,896,279 bytes. The resolved instructions and package
configuration pass `git diff --cached --check`.

Results and the exact diagnostic helper are retained in
`docs/implementation/branch-integration-2026-10-22/`. These checks support the
requested merge and publication of the checkpoint. They do not clear the five
premerge broader-suite failures or certify either product complete. Both source
checkpoints are retained as merge parents; subsequent concurrent edits and local
archives remain untouched in the original worktrees.
