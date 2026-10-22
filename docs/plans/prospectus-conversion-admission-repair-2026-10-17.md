# Repair the conversion parser exposed by admission tests

Entitlement005's first focused test stage failed:12 tests raised
ZeroDivisionError for `1/0`, while319 passed. The stage took
3.1215953528881073seconds. No consumer or sealing-success stage ran. Preserve
the failed test report, complete logs, frozen runner/methods and the original
admission; record005 as REJECT, never as a successful conversion trial.

Code tracing identifies a second exact-number parser,
`master_mechanisms.amount`. The earlier quantity repair changed
`semantics.exact`, which is used by fixed coupons. Conversion and write-down
profiles use this separate parser. Its regular expression permits `1/0` and
Fraction raises ZeroDivisionError, outside the public financial admission's
ValueError boundary. This is our incomplete cross-path validation repair, not
a fundamental package defect. Do not remove the failing controls.

Skeptical audit PASS for one changed repair: normalize only this parser's
zero-denominator exception to ValueError. Preserve all valid exact values,
positive-domain checks, optional fields, original source identities and
existing conditional outputs. Do not catch arbitrary exceptions at the answer
boundary or replace an invalid amount with zero. Add direct parser controls
and conversion holding/rate cases to guard the same failure beyond prices.

The original plan's primary criteria and consumer scope remain unchanged:
three source-verified original cases, independently calculated conversion
controls, malformed active/inactive refusal and the existing secondary
financial_cases report route. Current-source evidence does not establish
installed currentness or full direct primary-Q5 source interpretation.

Review one sixth cumulative entitlement admission for the changed parser.
Keep001–005, all old failures and the original300-second total new-work budget;
charge0.05694426316767931seconds preparation plus3.1215953528881073seconds failed
stage before proceeding. No seventh admission or second repair follows.

Two additional immutable program copies require increasing this repair's
cumulative new-storage ceiling explicitly from32MiB to48MiB, including the
old/new proposals, revisions225/226, failed005, new006, support and1MiB reserve.
This is accounting for retained evidence, not discarding it or resetting cost.
The60-second stage bound and zero network/install/native/OCR/model/GPU limits
remain. Retain a separately versioned runner so failed005 stays reproducible.

Promotion is vetoed by any changed valid complete result, accepted malformed
quantity, lost source binding or missing adverse control. Corrupt evidence or
resource exhaustion vetoes the affected run. Runtime/counts are explanatory.
Passing establishes this local input-validation repair only; it does not
establish actual conversion, ownership, legal meaning or whole-build completion.
