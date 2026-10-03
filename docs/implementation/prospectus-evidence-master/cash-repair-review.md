# Final bounded repair: action-bound nominal repayment

E5 attempt-004 retains twelve applicable witnesses. Contextual inspection rejects
two LVMH cash witnesses: the materialised-coupon deduction in condition 7(f)
does not apply to this dematerialised issue, and a list of defined principal
amounts in condition 8 contains no nominal repayment equality. The inherited
expression `final redemption amount.{0,80}nominal amount` accepted both.

The causal patch replaces only that loose proximity alternative with an explicit
redemption action and a stated nominal-amount equality. Existing percentage,
par and exact amount/denomination paths remain independently tested. Two complete
reader counterexamples must first fail under the old implementation, and a
positive equality/action case must remain supported. Then execute focused,
controller, full regression, corpus and bank checks before freezing.

The remaining LVMH abstention comes from unresolved coupon-forfeiture and partial
cash-redemption wording. It is retained; this patch does not relabel uncertain
clauses to obtain a negative. BASF's missing operative terms remain an abstention.
SEB's explicit zero principal clause occurs as part of share conversion, with
share-delivery rights preserved. It does not establish zero economic recovery.

Skeptical audit: the defect is a source-witness mismatch even though the current
LVMH answer already abstains. It can cause an unsafe negative on another issue,
so repair is required. The revised baseline is the preserved four-case frozen
run plus the original 32 exposed cases. Passing tests is engineering evidence;
no source accuracy promotion follows. All four PDF cases become exposed, and
the final post-PDF repair cycle is consumed. No new source is called unseen.
