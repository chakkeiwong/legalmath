# Repaired continuation deployed and running

Installed October 26, 2026. The verified registration raises service recovery
from 288 to 788 cumulative replacements and reopens P14/Gatecoin once each,
preserving all prior attempts. Global ceiling remains 8,100; deadline remains
October 27 at 05:15:09 UTC. Protected question reserves are unchanged.

- `registration.json`: committed, recoverable deployment transaction.
- `tests-staged.xml`: 167 passed in the actual product virtualenv.
- `staged-verification.json`: final validation plus exact delta from full history validation.
- `before-diagnostic-staged-verification.json`: full recursive history validation PASS.
- `installed-verification.json`: installed source hashes and provider authority PASS.
- `mission-refresh-receipt.json`: required mission refresh succeeded; work remains.
- `preview-p14.json`, `preview-gatecoin.json`: actual product startup reaches its first new request with transport prohibited.
- `real-checkpoint-replay.json`: real retained successes/failures reused or retried correctly.
- `armed.json`, `worker.json`: exact worker identity; verify before restarting.
- `service-resumption/6471/scheduled.json`: authenticated next exact request.
- `problems-and-audit.md`: remaining engineering and legal evidence gaps.

Worker command: `.venv-context/bin/python scripts/legal_repaired_retry_continuation.py arm`.
The user-approved exact command prefix is now saved. Do not launch another worker
while the recorded process remains alive. The initial worker encountered a local
capacity-setting bug before making a provider call: its 100,000-byte default was
smaller than the authenticated 156,917-byte request and its approved 250,000-byte
profile. Its failure and completed cleanup remain in the original files.

The bounded correction is installed under `probe-capacity-fix/`: 189 tests pass,
the exact retained request reaches a virtual reservation without transport, and
installed checks preserve all budgets, the original stage and replacement 289.
The replacement worker is PID 209084, start 36285367, launched at 06:05:54 UTC.
Use `probe-capacity-fix/armed.json`, its worker log and receipts for current status.
At 06:07 UTC call 6472 ended in an authenticated service timeout with no output.
The worker scheduled its next five-minute retry for 06:12:02 UTC. It has spent
6,472 calls and reserved 290 of 788 replacements; 1,628 global calls remain.
These are point-in-time counts. Read the current ledgers for subsequent changes.

Integration is incomplete. Source-backed adverse/unresolved decisions remain
visible; the new allowance does not convert failures into legal acceptance.

Run manifest: git HEAD a093e062a26d6f3ad28110b06cbbbb3c6a639b28; actual source
identities are recorded in the registered revision because the worktree is dirty.
Environment .venv-context, CPU-only (CUDA_VISIBLE_DEVICES=-1). Data identity and
all prior transport receipts remain in checkpoint references. Seeds N/A for
deterministic local checks; provider stochastic outputs remain unranked.
