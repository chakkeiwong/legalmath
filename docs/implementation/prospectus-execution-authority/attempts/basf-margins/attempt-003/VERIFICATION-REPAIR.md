# One diagnosed verification repair

The original `repair-verify` failed after 15.872 seconds at candidate.py's
payment-list equality assertion. Preserve its started marker, failure, session,
runner and every candidate output. This consumes the one changed repair allowed
by revision46; a further failed verification ends this attempt.

The corrected and full-margin payment lists exactly equal the old payment list
minus the excluded reference-period definition. The omission case has one
additional, necessary difference: the reference from `basf-payment:partial_period`
to the omitted `basf-payment:day_count` changes `resolved:true` to `resolved:false`.
All its other fields, source spans and reading remain equal. The production
`basf_payment_terms.explain` returns the actual clause-graph reference edges;
preserving a resolved edge to an absent meaning would be wrong. The failure is
in the comparison expectation, not in the candidate or its consumer.

The smallest discriminating check compares that exact edge before and after the
omission, requires its previous resolved value to be true, requires the new value
to be false, and preserves every other expected payment field and row. It then
executes every remaining original comparison, including unknown day-count source
units, unchanged meaning nodes, Q4-Q6 equality, complete prior dependencies,
question differences explained solely by new unresolved margin IDs, and all 522
original inventory occurrences. No successful product stage is rerun.

Skeptical audit: proceed. The comparator and source interpretation do not change;
the repair narrows the expectation to the causal consequence of the deliberately
omitted node. It neither accepts arbitrary reference changes nor weakens the
ordinary candidate's exact equality. Verification methods and existing products
are frozen before the repaired command. The 120-second/80-MB limits, independence
requirements and original task budget remain. No legal or automatic-discovery
promotion follows from a passing checker.
