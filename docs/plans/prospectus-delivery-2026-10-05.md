# Prospectus campaign delivery — 5 October 2026

User authorization: finalize campaign documentation, commit all work on
feature/prospectus-evidence-master, merge into main, fetch and merge origin/main,
push main, then bring the feature branch up to the same main commit.

## Skeptical audit and execution contract

Baseline: feature 5bff0065dcc73268aab78cba3e9522b7455825ac; local main and
origin/main initially 00c1b4bb8b63464050f0265de4cdf1e253d43d30.
The feature branch is in .worktrees/bond-gap-closure; main is already checked
out in the repository root with unrelated assurance edits. Git worktrees share
refs. Perform each merge in its existing checkout rather than trying to check
out main twice.

Audit verdict: PASS for delivery with these controls:

- Preserve all numbered receipts, historical method/source hashes and frozen
  results. Update the active BASF reset memo and add a new final delivery summary;
  do not rewrite prior result claims about their original uncommitted state.
- "Campaign complete" means the bounded OCR, extraction and BASF-selection
  engineering execution is verified. It does not mean full contract construction,
  independent legal validation, programme closure or production readiness.
- Snapshot identities of main's dirty files and its index before merging. Check
  the merge path set against those files. Do not commit, stash, discard or overwrite
  unrelated work. If overlap occurs, perform conflict resolution in an isolated
  checkout and preserve local bytes before updating the shared main checkout.
- Include source data, code, tests, review records, PDFs and receipt-bound outputs.
  Global ignore rules hide some logs/LaTeX files needed by the receipts; explicitly
  stage required evidence. Exclude only unbound runtime locks/caches.
- Inspect the staged index for task scope, missing bound files, malformed files
  and oversized blobs. Check the current campaign status before commit.
- Use normal merge commits and fast-forward pushes; never force push or rewrite
  remote history. Fetch remote changes before publication; review and resolve any
  overlap. Revalidate after integration before pushing.
- On the integrated branch run the focused 186-test suite and verify campaign
  receipt/source history, using local CPU Python with GPU intentionally hidden.
  Use a clean checkout if required to demonstrate committed evidence is complete.
- Finish with main, origin/main, feature and origin/feature at the same commit,
  with a clean feature worktree. Main's pre-existing local edits may remain dirty;
  verify and report their preservation separately.

Primary delivery criterion: all authorized campaign files committed, merges
contain both main histories, both remote refs confirm the resulting commit,
and the feature worktree has no staged, unstaged or untracked changes.
Hard vetoes: source/history corruption, missing committed evidence, failed
relevant tests, unresolved merge conflicts, or loss of unrelated local work.
Counts and timings are explanatory. Existing scientific/legal conclusions do
not change merely because Git delivery succeeds.

## Sequence

1. Inventory campaign evidence and main's unrelated work; record hashes in /tmp.
2. Update the active reset memo, write the master-program final summary, and check
   scope, required evidence and current completion state.
3. Commit the complete campaign on the feature branch and verify its clean index.
4. Merge feature into the existing main checkout, retaining unrelated local work.
5. Fetch origin, merge origin/main and any feature-branch remote advances if
   present; resolve conflicts and run integration checks.
6. Record integration evidence and commit delivery notes on main.
7. Merge main back into feature, push synchronized refs, and confirm remote SHA
   equality and feature cleanliness.

Runtime evidence lives under /tmp/prospectus-delivery-20261005.
The committed final summary lives at
docs/implementation/prospectus-delivery-2026-10-05/FINAL-SUMMARY.md.
No paid-model, public-source retrieval or GPU work is needed. Git transport is
separate from the prospectus source-retrieval budget (188/212).
