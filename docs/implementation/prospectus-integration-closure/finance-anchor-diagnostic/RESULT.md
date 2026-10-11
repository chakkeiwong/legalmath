# A local month-end inconsistency is reproduced

The schedule generator accepts the existing fixture starting on 30 August
2023 and returns 29 February and 30 August 2024 for semiannual coupons with
EOM false. The reference-period validator rejects both the second coupon
period alone and the two contiguous periods together. The diagnostic took
0.004 seconds; the inspected methods remained unchanged.

The requested quantity is the ICMA fraction under that explicitly supplied
regular schedule. For a full reference period it is
`days(period)/(frequency * days(period)) = 1/2`; the two full periods sum to
one. The implementation returns no fraction. It independently advances six
months from 29 February and expects 29 August, losing the original 30th-day
anchor. This is wrong relative to the existing schedule-interface expectation.
It does not establish which schedule a real prospectus requires.

| Decision | Primary criterion | Veto diagnostic | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Confirm local interface inconsistency | Both existing schedule cases are rejected by the reference validator | Exact ValueError reproduced; checkout and method identities pass | Legal source of a real instrument's anchor and stub rules | Admit an R5 repair carrying the reviewed original anchor through schedule and reference-period construction | QuantLib, ACTUS or CDM failure; any actual payable amount |

The run manifest retains the command, baseline commit, imported source hashes,
CPU mode, exact dates, errors and elapsed time. `manifest.json` seals the run
files; this subsequent interpretation note is separate from that run snapshot.
No optional package or network call was used and no implementation changed.

The repair must use an explicit reviewed anchor, preserve its day through
temporary February clamping, and make regular schedules and short/long-stub
reference periods use the same rule. Simply enabling EOM would change the
target and can move 30 August to 31 August. Do not infer the anchor from a
single February endpoint or silently extend an old profile. Historical
requests and regular-only profile boundaries need dedicated controls.

Post-run review: a reader could interpret EOM false as repeated month addition,
but that alternative disagrees with the current regular-schedule test and
generator. A reviewed decision to change that declared convention would
change the target and must be explicit. This is a local integration repair
trigger; it is not evidence against day-count arithmetic or a third-party
package. The status/negative-pledge package remains next in the execution
order, and this R5 repair follows under its own admitted source/evidence plan.
