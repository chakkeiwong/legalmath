# Inputs needed for the ACTUS comparison

This is a retained request specification; it has not been sent to anyone.

Supply an authorized copy of `org.actus:actus-core:1.1.0` compatible with official
service commit `7293157a7f272925dbce68b5a037d2e23c585c9e`, including its source,
build descriptor, official PAM tests, license and notices. Alternatively supply
an identified supported replacement release with its actual build, source,
tests and applicable terms so the version change can be reviewed. Record the
authorized access/provenance and permitted intended use. Keep any credentials
out of this repository. The retained README points to the ACTUS developer-access
request; sending that request requires the actual recipient/account and explicit
authorization. No license agreement or external request was made here.

The first trial remains a synthetic plain fixed-rate principal-at-maturity
contract. Its economic terms are lender outflow 1,000 GBP on 15 January 2025,
fixed annual interest 5%, principal repayment on 15 January 2026, one annual
coupon, 30E/360 day count, no business-day adjustment, no EOM adjustment, no
fees, scaling, optionality, FX, default or rate reset. Status precedes initial
exchange; exact ACTUS timestamp, calendar, role and enum encodings must be
checked against the supplied core and dictionary before execution. The simple
arithmetic reference is 50 GBP interest plus 1,000 GBP principal at maturity;
that total alone is not an acceptance criterion.

Audit PAM schedule, payoff, state-transition and equal-time ordering code and
its official tests before encoding the trial. Enumerate every scheduled event,
date, signed payoff and post-event principal/accrual state independently. Compare
the actual local core output with that enumeration; reject any dropped state,
implicit convention or unidentified engine. Then run adverse controls for a
missing required term, reversed chronology, wrong currency unit, and changed
event order. Only after the plain case passes should short/long stubs and
holiday cases be tried. The Shell ICMA long coupon is a separate convention;
it cannot silently substitute for this 30E/360 baseline.

The Python wrapper documentation's installation wording is not evidence of an
available numerical backend. Its inspected architecture explicitly delegates
event generation to a local or remote ACTUS service. A public demo without
identified code/version/state output cannot satisfy this pinned-core trial.
