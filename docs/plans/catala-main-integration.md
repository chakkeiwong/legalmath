# Complete and integrate the Catala campaign

28 September 2026. User authorization: complete campaign documentation, commit
all Catala work, merge into main, fetch and merge origin/main, push main, then
merge main back into `feature/catala-adapter`.

## Pre-execution audit

Root Codex review: **PASS with the preservation procedure below**. Catala starts
clean at `d01635dd`; main is `67c9a12c`. The merge base is `5290bc53`. Main and
that base have the identical tree `073959b20088a4996767f0910b8a5f784a069d5b`,
so the one main-only commit adds no tree difference to reconcile. Git ancestry
alone would have overstated the committed integration risk.

Main has unrelated dirty assurance/monograph work, with no staged changes. Only
`.gitignore` and `src/legalmath/cli.py` overlap the Catala tree changes; no
untracked file overlaps. The dirty CLI adds an assurance command in separate
hunks from the committed Catala CLI additions. Staging main wholesale, testing
its unrelated dirty code as if it were the committed merge, or stashing all its
research files would give misleading evidence or disturb ongoing work.

The revised sequence snapshots main's dirty inventory and tracked content,
temporarily stashes only the two overlapping files, merges and commits the
Catala tree, then restores those two files. Preservation checks compare all
other dirty content and the three-way merge of the overlapping edits. Existing
untracked work remains in place. A concurrent edit requires a fresh comparison,
not overwriting the newer content.

## Execution and acceptance

1. Update both reset memos and write the final master-program summary. Verify
   document links and the retained final evidence hashes. Commit only these
   documents and this plan on the Catala branch; require a clean branch.
2. Run a focused integration check on that clean branch using the existing
   Python environment and pinned compiler/JDK. The command is:

   ```bash
   timeout 300 env PYTHONPATH=src:. /home/chakwong/python/legalmath/.venv/bin/python -m pytest -q tests/translation/test_cli.py tests/search/test_formal.py tests/catala/test_backend_integration.py tests/unit/test_bootstrap.py --junitxml=/tmp/legalmath-catala-integration-20260928/focused.xml
   ```

   Preserve the log and machine-readable result with the integration note.
   These tests check CLI routing, shared parsing and existing host integration.
   Earlier full-suite evidence remains tied to its recorded source checkpoint.
3. Snapshot main's dirty content and temporarily stash only overlapping paths.
   Run `git merge --no-ff --no-commit feature/catala-adapter` in the existing main
   worktree. Resolve any conflicts, require the staged tree to match the reviewed
   branch tree unless an explained repair is necessary, and commit the merge.
   Restore the saved local edits and verify preservation without committing them.
4. Run `git fetch origin`, compare ancestry, and run `git merge origin/main`.
   If the fetched changes introduce an actual tree difference, inspect it,
   resolve conflicts while preserving local work, and run checks appropriate to
   the affected code. Record the actual refs, merge outcome and validation in
   `docs/implementation/catala/integration-results.md` before pushing.
5. Push with `git push origin main` (never force). If remote advances, fetch,
   merge and validate the new changes before retrying. Confirm the remote main
   object ID matches local main with `git ls-remote`.
6. In the Catala worktree, run `git merge --ff-only main` when ancestry permits,
   or a normal merge if required. Require a clean Catala worktree, matching
   local main and confirmed remote main, and containment of `d01635dd`.

Acceptance is successful tests plus preserved unrelated work, complete Catala
ancestry in main, confirmed remote synchronization and a clean synchronized
Catala branch. Hash mismatches, failed required tests, unresolved conflicts or
unexplained concurrent changes block publication until repaired. A remote
advance is a synchronization repair trigger. Runtime and test counts are
explanatory, not evidence of language superiority or production acceptance.

This is repository integration, not a new conversion experiment. There are no
provider calls, random seeds, GPU work, new compiler installations or backend
default changes. Temporary preservation files live under
`/tmp/legalmath-catala-integration-20260928/`; the result note and focused-test
log/XML provide the durable integration record. Main may remain dirty with its
preserved unrelated work; only the Catala branch must finish clean.
