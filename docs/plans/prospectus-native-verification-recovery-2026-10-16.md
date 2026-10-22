# Record failed native verification without losing evidence

Native-binding attempts011/012 wrote `started.json` and then exited without
`result.json` or `outputs.json`. The authority consequently rejected missing
outputs instead of retaining the actual validator failure. The current wrapper
calls the validator outside any failure finalizer. This is our execution-code
defect. The historical native driver also targets sealed attempt008, and its
validator requires current downstream modules to equal historical snapshots.
Those issues remain distinct from failure recording.

## Evidence contract and audit

Question: can one current admitted verification retain a truthful, complete
failure record, while preserving success behavior and refusing duplicate or
unadmitted writes? The baseline is the exact current
`scripts/prospectus_verify_task.py`, frozen before editing. The original
native-binding validator and its acceptance requirements remain unchanged.
Its real current rejection is expected; it is not a veto on this wrapper
repair. Acceptance of stale native evidence is a veto.

Primary repair criteria: injected validator error, timeout/interruption and
post-validator binding changes produce nonzero status, error evidence, a
truthful FAIL result and a hash-valid manifest. A successful fixture produces
PASS pending authority validation. A repeated or stale invocation refuses
before altering retained evidence. Then execute the real validator once;
retain its actual failure and verify the authority records REJECT with a valid
output manifest rather than another missing-output rejection. This deliberately
does not complete native-binding or change native acceptance rules.

Explanatory diagnostics are tests, timing, file counts and the retained native
receipt inventory. They establish no new extraction, package suitability,
independent interpretation or host-security claim. A hard kill, power failure
or unwritable filesystem cannot be guaranteed to finalize; cooperative SIGTERM
and Python exceptions can. Do not claim more.

Skeptical audit: PASS for this narrow repair. The error is reproduced by code
trace and two unchanged failed admissions, not inferred from missing packages.
Using the old validator as a positive comparator would be wrong because its
method inventory is stale. Preserve that refusal as the expected real negative
case. Freeze production methods and sources; edit only the wrapper and its new
focused tests. Keep snapshots and old attempts immutable. The exact route
inventory distinguishes recorded subprocess reservations, receipt-bearing
calls and uncounted descendants. It must not label retained replay as fresh
execution or turn lower bounds into exact totals.

## Bounded execution

One reviewed admission extension, native-binding12 to13, covers only this
local repair. Retain all twelve admissions; no fourteenth is implied. No new
native/OCR/model/network/GPU/installation/permission action is authorized.
First retain five-route receipt/source/manifest identities and the process
ledger lineage using local file reads. Record ten changed successor modules
and two additions after the statement integrations, with their exact hashes.

Add focused tests for failure finalization, positive behavior, duplicate/stale
refusal, cooperative cancellation and changed bindings. Run in-process pytest
with GPU visibility disabled and subprocess creation forbidden. Maximum two
120-second test starts, with only one bounded repair. Run the actual wrapper
once, maximum120 seconds. Hash-only finalization is at most60 seconds. New
attempt evidence is limited to8MiB; preparation inventory to2MiB. Use exclusive
writes, one-second yields and poll existing jobs. Preserve failed tests if any.

Before the real invocation, retain the tests, diff, method snapshots and repair
note so the wrapper can include them in its final manifest. Afterward inspect
all manifest hashes, actual error reason and history event; refresh. Update
the continuation map with the Q1 event944 result and this outcome. Return to
the substantive native source question through a separately reviewed current
driver/validator design, without rerunning sealed attempts or granting calls.

The future five-route campaign needs ten source calls (two per route), with
the first fresh source route serving as its canary, plus a separately bounded
boundary probe. A candidate repair reservation cannot be inferred from an
old unused slot. Exact future counts remain a proposal until current driver,
source comparator, failure finalizer, runtime bindings and cumulative budget
are reviewed together. This local repair does not execute that campaign.
