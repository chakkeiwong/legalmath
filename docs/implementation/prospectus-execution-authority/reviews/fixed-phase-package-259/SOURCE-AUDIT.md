# Official QuantLib1.38 method inspection

The retained source is the upstream v1.38 tag. schedule.cpp94–135 requires the
explicit effective/first dates; the evaluation-date fallback at103 applies only
to a missing effective date with backward generation. Forward generation at
268–342 starts from the explicit first date and records irregular-first and
regular subsequent intervals. NullCalendar and Unadjusted keep accrual endpoints.

fixedratecoupon.cpp62–65 computes nominal times the compound factor minus one
on accrualStartDate_/accrualEndDate_. FixedRateLeg174–257 separately adjusts each
payment from the period end using paymentCalendar_ and paymentLag_; the binding
must accept explicit Simple compounding and zero lag. No interest is added on a
FOLLOWING payment delay. calendar.cpp84–104 advances through holidays; its
advance implementation with zero days delegates to adjust. BespokeCalendar45–58
creates a fresh implementation; explicit weekends and addHoliday avoid market
calendar substitution. The comparator checks adjusted dates remain in coverage.

The already retained quantlib-v1.38-thirty360.cpp45–46 maps BondBasis to ISMA_Impl;
72–82 implements the same two31-day endpoint adjustments as Base71(v). The
separate integer oracle encodes the source numerator, rather than importing the
engine or package. The calendar, principal, entitlement and rounding premises
are hypothetical. No package API inspected here establishes legal entitlement,
holder aggregation, event precedence, actual VP calendar or legal rounding.

The adapter's finite domain is annual non-EOM anchors on days1–28, a genuinely
short first interval, aligned end anchor, bounded rational inputs and covered
Sat/Sun calendar. This trial asserts only the original six source-bound coupons.
The first reset is a phase boundary. No bond/redemption/maturity object is used.
