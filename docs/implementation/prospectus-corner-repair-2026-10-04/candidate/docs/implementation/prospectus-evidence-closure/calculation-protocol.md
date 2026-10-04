# Source-specific conditional calculation extension

Pre-implementation source review, 2026-10-04. Comparator: existing separate
Deutsche exact arithmetic and UBS-only bank adapter at 2d6b737b.

Question: can the actual bank investigation carry distinct, source-bound
Deutsche, BBVA and SEB conditional event/entitlement profiles without treating
missing notice, a holder election or principal zero as a different legal fact?
Pass requires exact issue/edition dispatch, hand-calculated boundary tests and
bank integration preserving every duty and permission false. Vetoes are wrong
source bindings, unsupported defaults, incorrect branch/election treatment,
unit mismatch, omitted rounding or missing required calendar/input evidence.
Tests and synthetic examples concern engineering; actual loss, complete event
implementation and whole-law applicability are not established.

Deutsche, retained German/English prospectus pp.52–55 and 62, section 5(4):
trigger is strictly below 5.125%; required loss is externally determined. The
pro-rata reduction is min(required loss, eligible total) times own prevailing
principal divided by eligible total. Ineffective other instruments are excluded.
Section 5(4)(b) gives H = J*S/T1, limits distributions and restoration, and
retains issuer discretion. Page 55 requires write-up notice no later than ten
calendar days before the payment date. Section 11 on p.62 deems Federal Gazette
notice given on publication plus three calendar days; the permitted supplementary
clearing-system route uses plus five. Missing notice does not invalidate a
write-down (p.53). A complete one-month legal deadline calculation needs the
applicable time-counting law and any shortened authority period: accept an
explicit reviewed deadline and report the outer-limit check separately from
the unresolved requirement to act without undue delay. Do not invent a principal
rounding quantum: the inspected rounding provision concerns interest. Exact
principal fractions are conditional calculations pending any operative rounding
or implementation determination. Do not turn a write-down into a cash payment.

BBVA pp.96,104,108,116–118,127,129–131: 6.1 trigger conversion is mandatory;
6.2 capital-reduction conversion permits a valid timely opt-out; that opt-out
does not prevent later 6.1 conversion. Condition 7.7 can override the 6.2 path
when its redemption conditions are met. Conversion price is the maximum of the
reviewed floor and nominal value, plus reference market price if listed. The
reference market price is the mean of five eligible closing prices rounded to
nearest cent, halves upwards. Floor adjustments, retroactive adjustments,
current listing and currency are separate required inputs, not silently fixed
at issue-date values. Divide liquidation preference by price; aggregate for
the same registration name under 6.11 then round down whole shares; no cash for
fractions. Delivery to the depository discharges the stated bank obligation,
which is distinct from onward delivery to the holder. Business-day deadlines
require a complete supplied calendar, not a weekday heuristic.

SEB pp.39–44,59–60,65: either bank/group ratio strictly below 5.125% triggers
automatic conversion. Principal then becomes zero but share rights survive.
The conversion price in USD is max(adjusted floor, quota value converted to USD,
current market price converted to USD if listed). The current market price is
the relevant five-dealing-day VWAP average with the documented dividend and
availability rules; supply an independently determined current market price
until its full history and adjustment inputs are present. Aggregate applicable
same-name delivery principal then floor the share count (5A.10). Offer proceeds
and unsold shares remain distinct from principal: neither is forced to zero.
Registration, delivery notices, offer expenses, taxes and the 40-business-day
offer/five-business-day settlement limits need actual evidence. A supplied
adjusted price is a conditional input, not an implemented corporate-action engine.

Assumptions: exact rational arithmetic is inherited and checked against simple
hand values; thresholds/rounding and branch precedence come from the cited
clauses; assessment dates are explicitly hypothetical. Missing inputs produce
requirements, not zero. The calendar is a fully specified input whose coverage
is tested. Source-specific additions are optional and cannot change a feature
answer or clear a bank duty. No formula transfers between profiles.

Skeptical audit passes for these bounded conditional profiles and their adapter.
Full corporate-action price derivation, actual settlement, authority, complete
contract admission and other issuer profiles remain explicit work, not silently
certified by this extension. Preserve source hashes, scenario provenance and
every downstream receipt. Human legal acceptance remains absent.
