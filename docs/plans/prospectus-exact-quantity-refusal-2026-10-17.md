# Exact quantities must fail through the declared refusal interface

Continue the original finance-conventions task after the current comparative
package is recorded. The immediate preparation is a small debugging probe, not
a new source, package trial or acceptance claim. Actual holdings, private files
and external opinions are unnecessary for this implementation question.

Trace finding: fixed_coupon.calculate calls semantics.exact on the annual rate,
principal and calculation amount. exact delegates to Fraction after rejecting
floats/booleans. Fraction('1/0') raises ZeroDivisionError. The public direct
financial consumer catches KeyError, ValueError and TypeError, so this malformed
quantity may crash instead of returning UNSUPPORTED. The earlier rounding repair
normalized this failure only inside rounded, leaving other quantities exposed.
Selected v4 numeric term admission also calls exact inside an exception boundary
that omits ZeroDivisionError. This is a hypothesis until reproduced.

## Contract and skeptical audit

The baseline is the current source, with no edits to semantics or coupon code.
Use the existing coupon fixture and six matched probes: a zero denominator in
rate, holding principal or calculation amount, each with entitled and excluded
holders. Retain the exact inputs and observed exception/status in a new local
preparation directory. This debugging probe must stay under15seconds and1MiB;
use CPU only and no network/native/model/install activity.

If reproduced, the target is a consistent invalid-exact-quantity refusal without
changing any accepted rational, day count, rounding, entitlement or event rule.
Prefer the shared exact-quantity boundary if the caller audit shows that exception
normalization is compatible. Do not catch arbitrary failures in the whole engine
or silently replace invalid quantities with zero. Preserve valid whole consumer
answers and original source/premise distinctions, and test malformed inputs even
when all holders are excluded. Validate selected term admission as well as the
direct Q5 interface. The source-specific payment limitations remain unchanged.

Primary criterion: invalid rational quantities receive the declared ValueError
or Q5 UNSUPPORTED response at each relevant boundary; complete valid direct and
selected answers are unchanged. Vetoes: changed valid rational values, hidden
crashes, invented zero, changed source interpretation, broad exception swallowing
or lost valid answer fields. An invalid baseline, changed frozen methods or
exceeded bounds veto the affected run. Test totals are explanatory only.

The reused fixture is a debugging example, not a new prospectus cohort. A parser
defect says nothing about fundamental package suitability or legal correctness.
The exact accepted representation set is an inherited contract; inspect its
callers and existing refusal tests before changing it. A failure in the candidate
triggers a reviewed changed repair; it does not invalidate exact arithmetic.

Audit verdict: the minimal baseline probe is justified and has a specific
discriminating outcome. Production edits and substantive execution wait for the
current source06 acceptance, the probe result, completed caller audit and a
reviewed finance task refinement with original cost/admission history preserved.
No unchanged retry or new live-call allowance is granted by this preparation.

## Probe result and implementation review

The six public-consumer probes all raised ZeroDivisionError, in0.011343541089445353
seconds. Their complete scenarios and graph are retained in continuation-reviews/
exact-quantity-preparation/baseline.json. This is a local input-validation defect,
not evidence against exact fractions or any external package.

The caller audit found fixed_coupon, coupon_amounts, selected contract-term
admission and the separate eligibility calculation, plus semantics' own
transition. Normalize only Fraction's ZeroDivisionError at the shared exact
parser to ValueError with an explicit zero-denominator reason. Leave other
exception types, accepted representations and all numerical operations alone.
This is smaller and more complete than adding catches to individual coupon
fields. Every successful call still returns exactly Fraction(value); only the
invalid zero-denominator branch changes. Current direct Q5 already translates
ValueError to UNSUPPORTED; selected admission already declares ValueError as
its refusal interface. Existing eligibility/semantic and coupon suites check
the other callers. No numerical default changes.

After source06 acceptance, retain the pre-edit parser bytes. Preparation may
then implement and test this precise change. The next revision preserves the
three finance admissions and proposes a fourth, with a named finite criterion
and separate remaining-original-finance criterion. New cost is bounded to
90seconds preparation (including the probe),180seconds candidate and180seconds
acceptance,40MiB inclusive new retention and262144-byte failure reserve. Retain
and report historical recorded costs separately; earlier unrecorded shell times
remain unknown rather than inventing a cumulative total. Carry forward all
existing finance/support storage before adding this allowance. No new package,
network, source extraction, installation or model call.

Primary full-answer comparisons use original source-bound Danske direct and
selected consumers plus retained Shell v3 global/definitive records. Recompute
P5 and final answers from the actual saved parents; verify exact complete-record
identity for valid cases. Exercise the six malformed direct cases, malformed
selected premises and v4 amount admission. Use compact input/output deltas and
hashes for large retained answers. Do not regenerate source graphs or claim a
second package comparison. Freeze methods and inputs before the fourth
admission, then record actual acceptance, refresh and continue.

## Final preparation audit

The runner review confirms that historical comparisons use complete sealed
consumer records, with each baseline checked against its original output
manifest. The v2 cases retain their original explicitly hypothetical per-holder
scope; they are not historical full-answer replays. The required matrix is
fourteen unchanged valid records and twenty-two specific refusals. A missing
case cannot pass by reducing the observed total. The focused test report and
all successor production modules are frozen alongside the reviewed parser,
source inputs and methods. Original finance and entitlement attempt storage
and manifest identities are reported separately from the new allowance.
Unrecorded historical time remains unknown. No unit-test count or successful
command is promoted to broader finance or legal correctness.

Audit verdict: PASS for this finite engineering repair. The original crashes,
exact exception normalization and caller review provide a discriminating
comparison; full-answer preservation, specific refusals, source identities and
the resource bounds can veto acceptance. A passing result triggers current
method and installed-package validation, followed by the remaining source and
financial work under the same master authority.
