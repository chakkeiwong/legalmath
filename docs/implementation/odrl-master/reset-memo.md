# Policy-to-ODRL program handover

## Merged baseline checkpoint — 27 October 2026

The authorized main integration changed five of the original 28 baseline files.
The first merged suite correctly failed one stale-binding check. The exact
premerge programme and five source versions remain under
`history/premerge-2026-10-27/`; [the merge review](merge-review-2026-10-27.md)
explains each change. Current `program.json` binds the merged sources and their
retained predecessors. All 22 tasks, zero attempts, planning-only authority and
acceptance obligations remain unchanged. The repeated merged suite passed
446 tests, including the ODRL planning checks. See
`../legal-mission-control/checkpoint-2026-10-27/postmerge-verification.json`.
The older verification and handover below remain historical; this reconciliation
does not implement or execute the ODRL programme.

## Original planning handover

22 October 2026. The user requested a master program to implement the ODRL
proposal and a thorough review. That planning task is complete. The ODRL feature
has not been implemented or executed by this task.

Start with [the master plan](../../plans/odrl-implementation-master-2026-10-22.md),
[program.json](program.json), [contracts.md](contracts.md) and
[review.md](review.md). The program has 22 tasks, 11 requirements, 20 case
families and 17 mutation obligations. All feature tasks have `NOT_STARTED`
status and zero attempts. The completed proposal remains available as
[the focused PDF](../../proposal/policy-to-odrl.pdf).

The first implementation task after an execution instruction is S00. Verify
the reviewed files and baseline bindings, record the actual instruction and
resource boundaries, inspect conflicting writers, and retain execution state
under `artifacts/odrl-master/`. The program is a specification with a read-only
checker, not an installed dispatcher. No live generation grant, model settings,
call budget, dependency installation or subagent authorization is implicit.

Important retained decisions:

- Reuse the prospectus/source and translation machinery already on main. Its
  conditional SPI fixtures need source and domain review; no branch merge is
  required for the inspected code.
- Use reviewed norms with deterministic ODRL export and exact computations.
  Catala provides selected conditional comparisons; separate source-based cases
  challenge shared errors.
- Known absence of a non-associate joint-allocation agreement invokes the
  source's equal-share rule. It differs from unknown agreement/holder evidence.
  Support signed net assets rather than blindly reusing the nonnegative helper.
- Prior consent includes the paragraph 13.1 written information and explanations.
  Monetary eligibility does not establish monitoring, record, warning or review
  duties. Preserve percentage-of-AUM and other unresolved calculations explicitly.
- F06 waits for P05, X07 waits for T03. D12 changes shared code, so Q13 must
  requalify the combined eligibility and duty versions before release.
- V08 or one qualified R08 is sufficient; never require both to pass. Recovery
  requires `SUPPORTED_FRAGMENT_INCOMPATIBILITY`, one attempt, unchanged scope
  and the same independently specified cases. Retain the original failure.
- Optional C09C requires an explicit terminal disposition. K17/A18 can complete
  without live G16, but full-program completion includes the assessed generation
  study. An assessed rejected candidate is not an experiment execution failure.

The previous legal-mission checks passed in this session and admitted only the
existing four-question campaign. Its active worker, mission register, sources,
grants and attempts were not modified by this task. The worktree is extensively
dirty from that campaign and earlier document work; preserve it. Do not dispatch,
stop or duplicate that worker because this program exists.

The inspected main commit is `3c3e462acabfde8c62285f4274f0f8c62b90a790`;
prospectus is `e8beb52b13399f18bbbff9aecea9636803729d5f`. The program binds 28
baseline files. [verification.json](verification.json) records final hashes and
actual check results. A stale binding requires a diagnosed program revision,
not silently replacing the old hash. The initial local `write-program.py`
drafting helper predates review corrections: **do not rerun it** to regenerate
the reviewed file.

Recheck only the relevant package:

```text
.venv/bin/python scripts/check_odrl_master_program.py
.venv/bin/python -m pytest tests/tooling/test_odrl_master_program.py -q
```

Planning-test success is not ODRL or legal validation. No third-party engine,
Catala comparison or stochastic experiment was run here. Preparation P1–P5 is
complete, with no remaining authorized planning work. Future execution starts
from the original task IDs, explicit current authority and cumulative attempt
records; it does not inherit another campaign's allowance.
