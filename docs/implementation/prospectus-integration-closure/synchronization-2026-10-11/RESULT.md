# Prospectus branch and main synchronization, 11 October 2026

This note records the requested Git handoff and the resulting validation
boundary. The local audit began with feature `104ef1406`, main `cde11a610`
and common ancestor `03883b5f7`; main had two commits and the feature ten
commits after that ancestor. The feature worktree was clean. Main had nineteen
modified tracked files, an empty index and 54,661 untracked files, all outside
the incoming feature paths. A local preservation snapshot is stored outside
Git at `/tmp/prospectus-finalization-20261011/main-before.json`.

The documentation commit `e6b8be604` added the master summary, amended the
reset memo and corrected evidence links. The non-autostashing merge into main
found one committed-history conflict in `.gitignore`; the resolution kept both
main's legal-tool lock patterns and the feature's prospectus restoration rules.
No pre-existing dirty or untracked main file was staged. The merge commit is
`927ee73a1b1456eee9c12183b26197a05c321441`.

The merged main passed 69 focused controller, attribution and coupon-anchor
checks in 0.58 seconds using the project's CPU-only dispatcher. Fetching
origin found `origin/main` at the common ancestor; its merge into local main
was already up to date. Main was pushed to origin. The clean feature branch
fast-forwarded to the same merge commit and was also pushed to origin.

The first preservation check observed seven concurrently changed, unrelated
untracked legal-mission files. No task command edited or staged them. A later
check found all nineteen originally dirty tracked paths still dirty, all
54,661 originally untracked paths still untracked, an empty main index and
eleven additional untracked paths. These files were preserved; main is not
claimed clean. The prospectus worktree was clean immediately after the merge.

Main's `pyproject.toml` change adds legal-interpretation package data, but that
file is an input to all nine prospectus phase method fingerprints. Read-only
post-merge status found all nine old receipts artifact-valid and stale. The
actual controller refresh updates `../next-phase.json` and nominates R0. The
69 focused checks establish bounded merge compatibility only. The lengthy
R0–R8 program was not rerun as part of Git delivery, so no current merged-method
phase validation or new legal acceptance is claimed. R1–R8 remain PARTIAL and
`program_complete` remains false.

This follow-up note and the refreshed status are committed after the first
synchronization; both branches are then advanced and pushed again. Verify the
final refs, rather than assuming the earlier `927ee73a1` remains their tip.
