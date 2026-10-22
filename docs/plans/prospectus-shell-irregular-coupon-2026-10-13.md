# Shell long first coupon and rounding basis

The admitted finance-conventions task will use retained Shell XS2228291279
Final Terms dated 8 September 2020 with its incorporated 13 August 2020
Information Memorandum. The final terms specify issue/interest commencement
10 September 2020, annual 10 December determination dates, first payment
10 December 2021, 1% interest, GBP1,000 calculation amount, a long first coupon
of GBP12.49 per calculation amount and Actual/Actual ICMA. Retained source
manifest hashes must match before any numerical interpretation. This family
becomes development-exposed; no historical holdout status is recycled.

The source-specific question is whether independently enumerated reference
periods and the appropriate rounding basis survive the actual financial product
and agree with QuantLib 1.38 on identical dates. Reference periods are
10 December 2019–10 December 2020 (366 days) and 10 December 2020–10 December
2021 (365 days). The first accrual overlaps them for 91 and 365 days. Thus the
source reading yields 91/366 + 365/365 = 457/366 years, and GBP1,000 at 1%
yields 2285/183 pounds before rounding and GBP12.49 after cent rounding.
Enumerate calendar dates independently of the local year_fraction routine.

Skeptical review found a material baseline trap: Condition 3(a)(ii), printed
p35, distinguishes global-note aggregate nominal rounding from definitive-note
calculation amounts/published broken amounts. Do not scale a rounded GBP12.49
per GBP1,000 to the actual GBP500m global issue. Retain separate conditional
form scenarios: global aggregate GBP500m rounded once, and a hypothetical
definitive GBP100,000 holding composed of 100 calculation amounts. The latter
form is conditional on the issue's limited exchange provisions; it is not the
actual issuance form. Source p35/p36 and final pp2–3 must be inspected together.

Primary numerical criterion: exact 457/366 locally and independent date counts,
QuantLib within 1e-12 years with explicitly supplied regular reference schedule,
and exact rational/cent amounts under each stated rounding basis. Primary
service criterion: Q5 remains CONDITIONAL, exact source evidence remains,
actual_event remains NOT_ESTABLISHED and full settlement remains unsupported.
Wrong source/anchor, missing reference, wrong reference date and wrong stub
must reject. Check the existing limitation that the published fixed_coupon_amount
field accepts regular coupons only; record that limitation without silently
calling the published broken amount a regular coupon.

Defaults audit: frequency one, December-10 lattice and ICMA come from the
retained final terms; no EOM date falls on that lattice. Rounding comes from
Condition 3(a)(ii), while definitive published broken amount is separately
specified. The event calendar, entitled recipient, absence of earlier
redemption/default/tax effects and intra-day event ordering remain explicit
hypotheses on their own synthetic source page. They cannot establish actual
payment. Native PDF extraction supplies source occurrences but does not certify
all terms; inspect rendered relevant pages. QuantLib is a comparator, not a
legal interpreter. Inspect its retained official ISMA schedule/overlap code;
do not allow its missing-reference fallback.

Skeptical audit PASS for this corrected bounded comparison. Inconsistent source
identity, accidental form mixing or missing comparator diagnostics veto the
run. Missing independent legal/convention review, actual entitlement/clearing
events and wider day-count scope veto promotion, not this conditional trial.
The Danske retained short coupon uses 30/360 and belongs to an explicitly
unsupported convention, not a reason to relabel it as ICMA.

CPU only; GPU intentionally hidden; 120 seconds per command with one-second
yields. Retain original identities, rendered pages, exact quotes, hypotheses,
method/environment/git manifest, comparator output, adverse cases and result
under finance-conventions/attempt-001, at most 30 MB. Record and refresh, then
continue the next ready task without a checkpoint handoff.
