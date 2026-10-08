# Fixed execution interface

Run from `/home/chakwong/python/legalmath`:

```text
.venv/bin/python scripts/run_legal_integration_repair.py assess-check
.venv/bin/python scripts/run_legal_integration_repair.py assess-execute
.venv/bin/python scripts/run_legal_integration_repair.py assess-status
.venv/bin/python scripts/run_legal_integration_repair.py assess-verify
```

The saved command prefix covers these fixed actions. `assess-execute` runs in
the trusted environment for the already authorized provider calls. It retains
the existing route and authorization, admits at most five new reservations,
and records one repair batch against the original shared ledger. No protected
global allow-list edit or new grant is needed. Local files remain ordinary
sandboxed edits.

`assess-check` preserves the predecessor and seals the current reviewed code,
inputs, plan, tool identity and provider route. It refuses to replace a changed
sealed review. `assess-execute` verifies these before each phase. It runs tests,
the complete controlled workflow and then a bounded live ladder. A phase with
a started marker and no result requires review of its retained evidence;
relaunching the command cannot silently redispatch it.

`assess-status` does not compete for the execution lock. Completed execution is
idempotent. `assess-verify` checks historical snapshots and receipts separately
from the current reviewed implementation, confirms append-only budgets and
revalidates scoped results. The predecessor's old live-source verifier is
expected to be stale after repairs. It must not be resealed to conceal the
changed method.

Exact original ceilings remain 96 provider reservations, 24 per product arm,
12 repair entries and the original 24-hour window. Starting consumption was
68 calls, 18 baseline, 13 combined and nine repair entries. This program adds
at most three baseline calls (including the service sentinel) and two combined
calls. Restart does not reset any ceiling or deadline.

The final legal-product denominator is 492 scoped pairs. The historical 420
count refers to broad fidelity's non-CONTEXT subset. Both counts are retained
in the new input inventory. Completion of a controlled fixture or selected
pair diagnostic is not full live completion or legal closure.
