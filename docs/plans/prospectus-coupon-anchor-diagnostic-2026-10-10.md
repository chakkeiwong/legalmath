# Coupon schedule/reference-period consistency: bounded diagnostic

This is a debugging-only check of the open R5 month-end gap, performed while
the already admitted R4 validation runs. It changes no bound source, tests,
packet or execution plan. It does not admit a finance implementation change,
benchmark, default change or package comparison. The status/negative-pledge
package remains the next substantive implementation.

Question: do `contract_terms.regular_schedule` and
`fixed_coupon.year_fraction` agree on a six-month schedule anchored on
30 August when February temporarily clamps the day? The existing regular
schedule test explicitly requires dates 29 February and 30 August 2024
from a 30 August 2023 start with frequency 2 and EOM false. Inspection finds
that `year_fraction` instead advances independently from each supplied
reference-period start, which may lose the original day anchor after February.

The exact comparator is the existing regular-schedule fixture, not QuantLib
or a newly chosen financial convention. Call `regular_schedule` on that
fixture, then pass its contiguous periods to `year_fraction`. The expected
conditional arithmetic is one half for the second full reference period and
one for both periods together. A ValueError establishes disagreement between
these two local interfaces under this declared convention. It does not decide
which convention applies to any real instrument.

| Role | Evidence |
|---|---|
| Engineering pass | Existing schedule dates accepted as regular ICMA reference periods and exact fractions 1/2 and 1 |
| Promotion veto | Interface rejection or different fraction under identical declared date/frequency/EOM inputs |
| Continuation veto | Wrong checkout import, missing input or changed method during diagnostic |
| Repair trigger | Local inconsistency; next R5 design must preserve original anchor across quasi-coupon dates and cover regular and stub composition |
| Explanatory | Error text and two returned schedules; no stochastic ranking or package conclusion |

Defaults: the date choices and EOM false come from the retained test, making
them a regression baseline. The expected fractions follow directly from
`days(period)/(2*days(period))`, once these dates are admitted as the intended
regular periods. This is not evidence that the dates follow any prospectus.
Use the checkout source, CPU only, no network or optional packages, with a
30-second bound. Retain actual command, hashes and result in
`docs/implementation/prospectus-integration-closure/finance-anchor-diagnostic/`.

Skeptical audit: PASS for this small consistency diagnostic. It uses the
existing stronger month-end fixture and reports both interfaces. A successful
command can still reveal a rejected candidate; command exit status is not
the criterion. A rejection concerns local anchor handling and cannot be
attributed to QuantLib, ACTUS or CDM, which are not invoked.
