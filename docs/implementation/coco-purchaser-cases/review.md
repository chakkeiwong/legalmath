# Skeptical review and repairs

The plan in `docs/plans/coco-purchaser-cases.md` was reviewed before
implementation. Its selected decision is the original offering's purchaser
condition. The baseline bank investigation cannot supply this condition from
an issuer's name, the word CoCo, a generic risk label or caller-supplied approval.

The initial interpretation that a write-down CoCo should be rejected while a
conversion CoCo is approved was rejected. The inspected Hong Kong survey does
not support that universal rule. Two UK contingent convertible issues with the
same initial coupon and denomination give a more discriminating purchaser test:
public US distribution versus the specified QIB/offshore distribution.

The source review distinguished SEC registration from registered ownership
form, issuer offering eligibility from regulatory endorsement, and original
distribution from future resale. It inspected Barclays' affirmative public
offering provision on printed S-99 and Standard Chartered's US restriction on
printed 140 in rendered pages. The files are retained under `rendered-sources/`.
The prospectuses' other restrictions are not silently set to satisfied.

Two fixture repairs were necessary:

1. The first expired-input diagnostic accidentally had equal validity start
   and end times. The frontend correctly rejected the malformed interval.
   The repaired case starts the previous day and expires at the evaluation
   instant, testing the intended half-open validity boundary.
2. Attempt 001 reached 139 cases in each target, then rejected a conflict
   fixture whose fact evidence IDs disagreed with its snapshot evidence map.
   This was a fixture integrity failure, not a compiler or legal-rule failure.
   Both evidence locations now describe the same disagreement. The adapter
   validates the whole observation before reporting conflict, and a separate
   regression preserves rejection of the original malformed input.

Attempt 001 and its failure receipts remain preserved. The revised input set
must pass all affected phases before promotion. No unknown legal premise was
changed to true in either repair.

The strongest alternative explanation for a green formal result is that both
compilers faithfully implement an incomplete or wrong legal interpretation.
The independent equation and mutation checks address formal implementation;
they do not eliminate that explanation. Source meaning, registration
effectiveness, complete original/current law and private-bank approval remain
unproved. The final document and result must say so. Human judgments are not
used as quality evidence.
