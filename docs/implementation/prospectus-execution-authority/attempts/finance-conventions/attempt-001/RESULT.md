# Shell XS2228291279 long first coupon

The local exact calculation, separate calendar-date enumeration and QuantLib
1.38 agree on 457/366 years for 10 September 2020–10 December 2021. The two
reference periods contain 366 and 365 days; the accrual overlaps them for 91 and
365 days. At 1% on GBP1,000, 2285/183 pounds rounds to GBP12.49, matching the
published initial broken amount. QuantLib received those same explicit
reference dates and used no missing-reference fallback.

Under the recorded global-note interpretation of Condition 3(a)(ii), a
hypothetical unchanged GBP500m aggregate produces GBP6,243,169.40 after one
rounding. Under the separate hypothetical definitive-note form, a GBP100,000
note with 100 calculation amounts produces GBP1,249.00. Applying GBP12.49 per
GBP1,000 to the global aggregate instead would produce GBP6,245,000, a difference
of GBP1,830.60. That shortcut mixes the form-specific calculation bases.

The original PDFs and retained text hashes match the acquisition manifest.
Final Terms pp2–3 and Information Memorandum pp35–36 were inspected as rendered
pages; their exact native source occurrences and full relevant contexts are
retained. Condition 5(c)'s following Payment Day rule was read separately.
Calendar opening, outstanding balance, definitive exchange, entitlement,
presentation, absence of earlier events/tax and event ordering remain explicit
hypotheses. These source interpretations still require independent review.
The family is development-exposed and cannot count as new unseen evaluation.

Both actual financial-product answers remain CONDITIONAL with
actual_event=NOT_ESTABLISHED and full_settlement_supported=false. Six adverse
or unsupported inputs return Q5 UNSUPPORTED with the expected specific reason:
missing/invalid references, wrong stub, changed English-date anchor, changed
source edition and published irregular coupon supplied through the regular-only
fixed_coupon_amount field. The last case reproduces a genuine interface limit:
the amount agrees with recomputation here, but cannot yet be consumed as a
published broken amount. The selected-contract route also remains regular-only.

The first local harness incorrectly expected invalid premises to raise through
the service. The service correctly returned its typed UNSUPPORTED answer.
One bounded harness repair checked that status and exact reason; retained
positive results were verified and not rerun. The failed command did not write
its final wall timer; that duration is unavailable. The original and repair
scripts and partial failure remain retained. No production financial code was
changed in this attempt.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Unsupported conclusion |
| --- | --- | --- | --- | --- | --- |
| Retain conditional irregular comparison | Exact fraction, published amount cross-check and QuantLib agreement pass | Invalid inputs remain typed; no numerical discrepancy | Independent source/form review | Preserve form-specific evidence in entitlement work | Actual payment or legal entitlement |
| Keep integration partial | Published broken input and selected irregular route unsupported | Interface/scope promotion veto | Broader stub and payment-form behavior | Reviewed refinement to add typed broken-coupon/form support and source-bound selected irregular schedules | Full settlement or package unsuitability |

The strongest alternative explanation is that the simple December anniversary
avoids harder calendar and stub cases; a numerical agreement does not validate
the form interpretation. Independent legal review could change the selected
calculation basis. The kernel's PER_LEGAL_HOLDER setting represents the global
aggregate only because this scenario explicitly supplies one global coupon
recipient; it is not a general note-form selector. No QuantLib defect was found.
The retained Danske short coupon uses 30/360 and remains a distinct unsupported
convention requiring its own source review, not relabeling as ICMA.
