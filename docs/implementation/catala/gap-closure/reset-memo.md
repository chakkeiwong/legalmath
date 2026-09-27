# Catala gap-closure reset memo

Completed 27 September 2026 on `feature/catala-adapter`, from baseline `71633380`.
The main worktree's unrelated work is preserved. See [results](results.md), the
[reviewed plan](../../../plans/catala-gap-closure.md), and the bounded
[post-run repair](post-run-repair.md).

The additive `legalmath.catala.native.v2` profile has exact optional/payload
boundaries, explicit semantics, pinned standard-library imports, source-position
execution observations and a content-addressed package/authenticated host adapter.
The original compiler and v1 replay remain available. The trace derivative's
invariant limitation is explicit; recursive types and arbitrary imports remain
outside this profile. `NativeHost` string callers are trusted embedding inputs;
public callers must use `NativeAuth` with institution-supplied named identities.

Accepted artifacts under `artifacts/catala/gap-closure/`:

- `semantics/conformance.json` points to `executed-fca5bca0e053`: four shared
  controls, four intentional-difference controls and two native-feature controls.
- `study/` retains the original frozen four-task comparison, all 19 dispatches
  and 21 archived input files. The archived hashes match. Its current-source
  fingerprint is deliberately stale because the successor repair changed code;
  do not rerun it as though the frozen implementation were unchanged.
- `schema-repair-probe/` retains two additional calls, its own 22 archived code
  inputs and successful net-assets generation/criticism/four-case verification.
  Total own live calls: 21 of the authorized 24; shared end: 487; local ceiling:
  490; global maximum: 500. Check the shared ledger before any future live work.
- `source-review/` is the original packet; `source-review-successor/` adds exact
  footnotes and repairs the authorised-product qualifier. Both require independent
  legal adjudication, and their source families are exposed. The source family
  gate also checks identifiers and raw hashes in the task, so relabeling a row
  does not erase exposure.
- `reviewer-study/current.json` points to matched v5, `matched-d262bbeba01b`.
  Languages are balanced across task, defect and position. Thirty-two synthetic
  responses are excluded; zero human responses exist. Do not distribute owner
  keys/builds with the per-participant files.
- `validation.json` accounts for all 725 collected tests across passing focused
  and regression runs. Six packaging metadata files and four historical SQLite
  sidecars were absent from this worktree; only exact hash-matching copies from
  main were restored. `.venv` links to the existing shared environment. These
  local prerequisites are not changes to frozen baseline commitments.
- `invalidated-drafts.json` lists rejected/superseded attempts and their hashes.
  Their bytes remain locally in ignored `drafts/`; never promote their results.

Remaining work is evidence-dependent: inspect and adjudicate cross-referenced
legal authorities, assemble genuinely unexposed source families, review a
prospective repeated paired study with a suitable workflow budget, and collect
qualified human observations. The successful format probe does not demonstrate
a general converter advantage. Keep the native route optional; there is no
production release, default change or completed human/legal acceptance.
