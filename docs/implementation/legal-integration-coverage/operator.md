# Retained coverage continuation

Governing plan: `docs/plans/legal-integration-coverage-program.md` and the
append-only repair reviews in this directory. Current reviewed source is
selected from the highest numbered `review-v*.json` under
`artifacts/legal-integration-coverage/2026-10-08/`.

The exact approved command prefix is:

```text
.venv/bin/python scripts/run_legal_integration_coverage.py
```

Append one fixed action: `check`, `test`, `pilot`, `execute`, `repair`,
`diagnose`, `status`, or `verify`. There are no path, model, limit or arbitrary
command parameters. Run local checks in the sandbox. Live actions need trusted
execution because the nested provider needs its state database and network.
The prefix approval was saved during this continuation; no policy-file edit is
needed. Do not change the spelling or invoke a shell wrapper unnecessarily.

`execute` verifies the current review and matching test receipt, reuses complete
batches, and stops at the first incomplete batch. `repair` admits only the
specific failure and attempt numbers reviewed in the source; it is not a
generic retry command. `diagnose` reuses its completed five-call ladder and
does not spend those calls again. Unknown interrupted attempts remain blocked.

The original ledger allocation was combined 82, baseline 4, repair 14, with
100 calls total. Revision v12 preserved the original authorization and its
51-call prefix and explicitly redistributed unused allocations to combined
81, baseline 3, repair 16. The total and absolute expiry did not change.
Repair calls are included in the total. The user authorized up to 20 repairs;
`repairs.json` records implementation and live recovery batches separately from
provider consumption. Failed calls remain consumed. All live work uses the
original absolute expiry 1791519402.34676. The v9 capacity review sets a
300-second cap for new large batches; historical attempts and the completed
small diagnostic retain their 180-second cap.

The current run is stopped at 54 calls and 20/20 repair entries after batch
17 attempt 2's second perspective selected another candidate's executable
meaning. `execute` reuses retained evidence and returns REPAIR_REVIEW_REQUIRED
without a new dispatch; this was checked. `repair` has no reviewed remedy for
this new failure, and its repair counter is exhausted. Do not reset either
ledger. Local verification and reporting remain available. Recovery requires
a fresh explicit repair authorization and a reviewed allowance: at least 47
calls would remain necessary if the existing validated first perspective can
be safely reused, while only 46 currently remain.

Read `next-phase-plan.json`, `allowance.json`, and the latest batch receipt for
recovery. Original attempts and superseding attempts remain separate. Never
delete a start marker, alter a failed receipt, rewrite old ledgers, or reduce
the 492-pair denominator to permit a resume. A completed diagnostic or batch
does not establish legal accuracy. Current result and remaining work are
recorded separately from this operating guide.
