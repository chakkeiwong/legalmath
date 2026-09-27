# Catala main integration

28 September 2026. The complete Catala campaign and its final documentation are
merged into main as **`5417af674f1e4b2f25488dffc3b879e262226b74`**. The merge has
parents `67c9a12c` (previous main) and `cbfc0a03` (documented Catala branch), and
contains implementation checkpoint `d01635dd` and all its predecessors.

The [reviewed plan](../../plans/catala-main-integration.md) was followed. Main's
committed tree matched the common ancestor before the merge, so no committed
content conflicted. The merged tree exactly matches the tested Catala branch.
Fetching origin found main at `9160ce72`; `git merge --no-edit origin/main`
reported `Already up to date.` That remote commit is already in local main.

## Validation and preservation

The focused run passed **30 tests in 57.20 seconds**, with no failures, errors or
skips. It covers shared/native CLI routes, search formalization, existing Catala
host/release integration and isolated CLI startup. The tested source and test
tree identities match the committed merge. This complements the earlier campaign
evidence; it does not replace or relabel its full-suite checkpoints.

The documentation check verified 27 final source hashes, eight retained evidence
hashes and 18 documentation links. The
[run manifest](../../../artifacts/catala/main-integration-20260928/manifest.json),
[test log](../../../artifacts/catala/main-integration-20260928/focused.log),
[test XML](../../../artifacts/catala/main-integration-20260928/focused.xml) and
[preservation report](../../../artifacts/catala/main-integration-20260928/preservation-check.json)
retain the exact commands, environment, identities and outcomes.

Main had 56 tracked dirty files and 30,244 untracked files at the preservation
snapshot. Only `.gitignore` and `src/legalmath/cli.py` overlapped the incoming
tree. A path-limited stash saved exactly their nine added lines; they restored
without conflict after the merge. Independent three-way comparisons confirm
that the resulting files contain both committed Catala additions and the saved
local edits. The other 54 tracked files remained byte-identical, and no unrelated
edits entered the index or merge commit.

Of the untracked files, 30,243 remained unchanged. The unrelated untracked
`src/legalmath/interpretation/assurance/integration_execution.py` changed after
the snapshot. It is absent from both the merge and stash changes; its newer
contents were left untouched. This concurrent edit is recorded explicitly,
rather than claiming the entire working directory stayed static. Recovery
copies and the original patch are retained locally under
`/tmp/legalmath-catala-integration-20260928/`.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Accept local main integration | Exact tested-tree equality and 30 passing focused tests | No conflicts, failed checks or lost local edits | Finite existing test coverage | Publish main and synchronize the Catala branch | New language-quality or production-readiness evidence |
| Preserve ongoing main work separately | Tracked edits preserved; concurrent untracked edit untouched | No unrelated changes staged | Other sessions may continue editing their files | Leave that work in main's working directory | A clean main working directory or completion of other campaigns |

## Publication boundary

This result record is committed before publication. The authorized closing
commands are `git push origin main`, `git ls-remote origin refs/heads/main`,
then `git merge --ff-only main` in the Catala worktree. Completion requires
matching local main, confirmed remote main and `feature/catala-adapter` object
IDs, a clean Catala worktree, and containment of `d01635dd`. Git refs and the
supervising session's final verification record publication; this document does
not invent a future commit ID for its own commit.

No compiler installation, live provider call, new allowance, GPU work or backend
default change occurred. Unrelated dirty main work is intentionally preserved
and is not part of the published Catala campaign.
