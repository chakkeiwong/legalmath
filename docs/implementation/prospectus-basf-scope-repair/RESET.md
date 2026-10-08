# BASF scope repair reset

Worktree: `.worktrees/bond-gap-closure`, branch `feature/prospectus-evidence-master`,
baseline HEAD `4dfd340715059158d1b672aa120f37175ef75a93`. Preserve the existing
uncommitted integration work and all historical receipts. Do not run
`scripts.verify_prospectus_repairs`.

Final state: `run-003` passes 35 focused checks; adoption verification attempt-006
passes 148 tests, all seven phases current and reused on identical replay. A0 is
attempt-009 and A1–A6 are attempt-007. The installed constructor's complete product
equals A1. The 62 operations leave 19 brackets and 545 unresolved intervals;
all 1,578 body occurrences remain exact. LaTeX build and physical-page review
passed. See `RESULT.md`, `NEXT-PROGRAM.md` and `verification-001/result.json`.
Recovery catalogue: 13 large products and 253 snapshots; archive/snapshot and
identical-product recovery checks pass. Original products and before-catalogues
remain preserved. No commit, merge or push was performed in this continuation.
The following paragraphs preserve the implementation history.

The 62 reviewed operations are implemented in `basf_scope.py` and packaged
`basf_scope_review.json`; `basf.construct` consumes them. The original 83-entry
inventory, reviewed original images, detailed reasoning and data generator are
in `source-review-001`. The old unlisted notice selection is removed. The new
listed selection preserves the exchange-rule condition. Source/admission hashes,
page membership, geometry and visibility are guards, not legal adjudication.

`run-001` preserved 32 passing checks and two incorrect test expectations. Base
page 111 says `vom [Verzinsungsbeginn]`, not `ab dem`; page 120 has four empty
spare cells, not repeated named placeholders. Original images and raw inventory
confirm the correction. The implementation did not fail these two criteria;
the test oracle was wrong. The repaired assertions use the actual wording and
empty cells. No acceptance criterion was relaxed. Continuation audit: PASS for
rerunning the focused source checks, followed by installed verification.

`run-002` passes all 34 checks and executes 62 rules. The raw source and all
1,578 body occurrences are unchanged; remaining brackets are 19 and unresolved
intervals are 545. Post-run review identified a missing graph-level instrument
check: the admission and documents were bound, but another bundle could reuse
those sources under a different instrument ID. Added explicit equality and a
regression before the final run. This is a local integration guard, not a new
legal inference. The new run is necessary because the implementation changed.

Exact commands from this worktree:

```text
python3 -m scripts.prospectus_basf_scope_repair
python3 -m scripts.verify_prospectus_adoption
```

The new runner preserves immutable attempts, source/method bindings, failure
records and refreshed next-phase decisions. Ordinary local edits and CPU runs
need no new allow-list entry. The installed check also runs the BASF constructor
outside the checkout and compares its complete product with A1.
