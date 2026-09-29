# Executing and extending the program

From the repository root, use:

```sh
.venv/bin/python scripts/run_instrument_evidence_closure.py --phase all
```

`--phase E0` through `--phase E4` select one phase. Reuse requires unchanged
inputs, verified predecessor outputs and a passing prior attempt. A failed
attempt needs `--repair-note` naming its diagnosed cause and executed repair.
Four attempts is the bound; do not edit old manifests or reset attempt counts.
The protected dirty baseline is `baseline.zip`. Per-phase input manifests bind
code, sources and tools; E4 additionally binds manuscript and citation reviews.

The accepted E0–E4 execution is already complete. E0, E1 and E2 have used their
four attempts. Concurrent edits changed one shared source helper and a chapter
after E4; the helper passed the bounded supplemental check documented in
`continuation-review.md`. The master must not silently reuse the old acceptance
for changed inputs. Use `accepted-snapshot.json`, `accepted-method-snapshot.zip`
and `accepted-documents/` for the actual tested state; continuation with new
inputs requires a reviewed new scope, not reset counters. The snapshot records
external tool hashes but does not include the installed environment or all
historical fixture directories.

The APIs are deliberately conditional:

- `instrument_evidence.resolve` retrieves a record's actual content and checks
  scope, kind, effective and knowledge dates, freshness and declared coverage.
  Supplier truth and legal validity remain unproved.
- `instrument_evidence.attach_private` adapts eligible records to the existing
  bank request. A record binds instrument, client, booking entity, establishment,
  service, action and route hash. Conflicting inputs survive; derived answers
  and quality labels cannot be asserted as private facts.
- `instrument_evidence.requirements` creates a missing-evidence queue from the
  actual fourteen-obligation investigation. It does not claim complete legal
  discovery beyond that inventory.
- `CoveredCalendar` requires an explicit open/closed value for every covered
  date and an exact market and purpose. An official holiday table alone cannot
  fill unlisted days. `successor_separate` takes one calendar per exchange.
- `instrument_investigation.investigate` accepts an optional
  `extensions_sha256` record with `private_records`, `alternative_notice`,
  `price_determination` and `holder_delivery` content references. It assembles
  these branches with the existing schedule and entitlement, preserves the
  reconstructed price, and rejects attempts to bypass missing or inconsistent
  event/creation evidence. Separate successor-share valuation is conditional
  arithmetic; executing conversion into a replacement security still requires
  its actual amended terms. The real-document reports have no actual events.
- `preferred_ss` binds the retained supplement and controlling certificate
  extraction. Regular dividends require an explicit allocation convention;
  stubs stay qualified. Redemption checks selected conditions but does not
  infer payment or supply the current-period dividend/record-holder calculation.
- `transaction.prospective.observe_sources` checks dated content references and
  distinguishes private facts, preexisting sources and post-freeze publication
  assertions. It does not attest timestamps or measure legal accuracy.

The refreshed next-phase file records remaining source and private-data work.
New authentic material should enter the content-addressed store with its exact
scope and dates, followed by reassessment of dependent receipts. No arbitrary
fresh-until date or complete-history assertion may be inferred from a fetch.

## Prepared model comparison

Preparation is offline and may be inspected without dispatch:

```sh
.venv/bin/python scripts/run_instrument_transport_study.py --prepare
```

The fixed study covers both full PDFs, partitions them at a declared byte bound,
and supplies identical source text/questions to literal and readable-table arms.
The expected 32 calls have no retry reserve. Calls stop on invalid source
accounting, invalid response references or service failure; a failed response
cannot be silently skipped on resume. Model proposals and disagreements are
diagnostics, not legal truth or a statistical ranking of representations.

After an explicit new allowance is recorded in a distinct grant anchored to the
exhausted predecessor, the exact command is:

```sh
.venv/bin/python scripts/run_instrument_transport_study.py --grant docs/implementation/instrument-evidence-closure/transport-study/grant.json
```

No such grant has been created by this offline program. User approval is pending.
The existing network/CLI authorization does not replenish a model-call ledger.
