# Isolated repair package — not deployed

The live worker remains on its existing bound source. The candidate is an optional exact-reference transport for context-disposition requests. No automatic patch application or model dispatch is installed by this directory.

- Plan: `docs/plans/legal-live-unblock-candidate-2026-10-25.md`.
- Result: `docs/implementation/legal-mission-control/results/live-unblock-candidate-2026-10-25.md`.
- Separate prerequisites: `docs/implementation/legal-mission-control/results/live-unblock-prerequisites-2026-10-25.md`.
- Code: `candidate/` contains the five changed/new files; `baseline/` retains originals; `candidate.patch` is an unapplied patch; `candidate-manifest.json` binds both versions.
- Verification: `tests-final-compatible.xml`, `replay-all-failed-context.json`, `capacity-measurements.json`, `source-attribution-controls.json`, `run-manifest.json`. Earlier failed/superseded diagnostics remain beside them.

## Commands actually executed

All commands below are local. The exact candidate source path is `/tmp/legalmath-unblock-v2/src`; no live provider is constructed by either diagnostic script.

```text
.venv/bin/python scripts/legal_mission_control.py admit
.venv/bin/python scripts/legal_mission_control.py refresh
.venv-context/bin/python scripts/legal_integration_master.py status
.venv-context/bin/python /tmp/legalmath-unblock-v2/replay_exact_context.py --sample
.venv-context/bin/python /tmp/legalmath-unblock-v2/replay_exact_context.py
.venv-context/bin/python /tmp/legalmath-unblock-v2/check_capacity_and_sources.py
.venv-context/bin/python /tmp/legalmath-unblock-v2/check_capacity_and_sources.py --source-only
git apply --check artifacts/legal-mission-control/2026-10-25/offline-unblock/candidate.patch
```

The focused tests ran from `/tmp/legalmath-unblock-v2` with the repository's `.venv-context/bin/python`, prepending the isolated `src` and root to `sys.path`, then calling `pytest.main` for these seven modules:

```text
tests/assurance/test_context_exact_references.py
tests/assurance/test_context_need_disposition.py
tests/assurance/test_context_pointer_warrant_targets.py
tests/assurance/test_corrected_context_disposition.py
tests/assurance/test_source_review_repair.py
tests/assurance/test_review_receipts.py
tests/assurance/test_review_assignment_contract.py
```

Final regression: 98 passed in 5.95 seconds. Final strict replay: 217 responses, 194 valid simulations and 23 rejected, 128.19 seconds. Capacity used the same 217 requests and the production local measurement path. All diagnostic scripts and code are preserved; recreate a separate tree from the hashed baseline and apply the patch there before reproducing. Do not add this directory to the live worker's import path.

Mission admission and refresh succeeded. The final master-status command is a read-only follow-up; its stdout/stderr are retained and `checkpoint-command-results.json` is written when it finishes. Earlier interrupted check/status attempts remain interruptions. No live permission, resource ceiling, attempt count or historical verdict is altered by a successful local check.

## Activation gate

Activation requires a verified safe worker checkpoint, current baseline hashes, reviewed same-master registration/bindings, an authorized finite live-control allocation and preservation of independent-question reserves. P14 attempt 7/7 and corpus attempt 6/6 remain exhausted. The candidate is ready for that controlled qualification, not a declaration of P14 acceptance.
