# Original coupon anchor: bounded engineering validation complete

The reproduced local defect was a mismatch between the regular schedule and
the ACT/ACT ICMA reference validator. Starting from an explicitly supplied
30 August 2023 anchor, the schedule kept the original day through 29 February
2024 and returned to 30 August 2024; the old validator advanced from the
clamped February endpoint and rejected that second period. The new explicit
`fixed-coupon.v2` path uses the supplied anchor for both operations. It returns
the exact fractions `1/2` for the second regular period and `1` for the two
periods together. Historical `fixed-coupon.v1` retains its recorded rejection.

The selected `selected-coupon-terms.v3` path requires an operative, quoted
English date and pairs with `admitted-coupon-terms.v2` and the new calculation
profile. Both direct and selected service/P5 routes preserve the anchor,
source evidence, exact fraction and payments. The selected regular schedule
continues with 30 August 2024, 28 February 2025 and 30 August 2025. Missing,
changed, foreign, excluded, mismatched and premise-override controls reject.
Independently listed date cases cover 28th–31st anchors, leap years and EOM;
hand-enumerated short/long first/final fractions are `1/6`, `137/183`,
`91/366` and `137/182`. These are conditional arithmetic results, not a
decision about any real instrument's convention or entitlement.

Focused worktree checks passed 64 cases; the actual consumer passed. Installed
attempt 015 passed 11 cases in fresh, relocated and offline-restored stages,
with identical full question identities and anchor controls. Its retained
payload was 137,320,260 bytes under the 200-MB cap and metadata reserve.
The frozen collection contained 658 unique test identities. Current focused,
R0–R7 and remaining runs cover all 658 with no missing or unexpected cases,
failures, errors or skips; the remaining run passed 155. This is a partitioned
node union, not a single-process aggregate. R4 passed 386 cases in 2,902.244
seconds under its 4,500-second phase bound. R8 passed after the attribution
update. All nine phase receipts are current, valid engineering PASS.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Accept explicit anchored path as bounded engineering repair | Exact listed dates/fractions, both service routes, legacy compatibility and installed identities pass | No source, version, classification, coverage, method-drift or resource veto fired | Real source-backed coupon convention and entitlement events are absent | Commit this comparator; execute the reviewed worker-recovery plan, then return to real-source financial cases | General instrument support, actual payment, settlement, legal correctness, default promotion or package failure |

The claimed target here is the conditional ICMA fraction on the supplied
anchor lattice. The code computes that same quantity for the listed synthetic
dates; independent day counts and exact rational tests support the equality.
It does not compute an issuer's actual payable amount without reviewed terms,
holdings and events. No stochastic comparison or ranking is involved.
Engineering correctness, numerical validity and legal interpretation remain
separate. R1–R8 are substantively PARTIAL, `program_complete` is false and
independent legal acceptance is not established.

The pre-run comparator was commit `e814e99ad6db96e9530bdb318a3c630d36c85fdb`.
`execution-admission.json` binds it to the protected candidate. The actual
commands, CPU-only environment, method and source hashes, deterministic seed
status, limits, wall times and result paths are retained in
`validation-001/started.json`, `validation-001/*-started.json`,
`validation-001/*-result.json`, `validation-001/coverage.json`,
`validation-001/result.json`, `validation-001/manifest.json`,
`attempt-001/`, installed attempt 015 and the R0–R8 phase receipts. GPU devices
were intentionally hidden; the installed exercise used retained offline wheels
without network downloads, model API calls or new dependency versions. The
strongest alternative explanation is a shared date-rule error;
independently listed dates and overlap-day counts constrain it. A contrary
source-backed convention would limit this synthetic result rather than make
the historical endpoint mismatch disappear.
