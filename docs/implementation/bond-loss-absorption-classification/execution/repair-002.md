# Corpus-driven semantic repair

The preserved `development-001` report is rejected. It misclassified cash
redemption and partial repayment as principal write-down, interpreted unrelated
conversion-price definitions as mandatory conversion, and treated temporary or
conditional negation as an absolute denial. This is an implementation failure,
not evidence that corporate senior debt has CoCo triggers.

Repair: bind conversion to a debt-to-share relation; distinguish principal paid
in partial redemption and cancellation after repayment; require an absolute
debt-specific negative proposition; distinguish coupon cancellation from
principal reduction; recognize spacing around hyphens; resolve each-holder
amendment consent; preserve section boundaries when joining pages. Added
controlled tests for the causal constructions, issuer/country invariance and
section-boundary concealment. No expected outcome is stored against an issuer.

The Standard Chartered source contains explicit “subject to completion” text
on PDF page 1. Its rejection is preserved; a completed coupon or dated filename
does not establish that it is a final document. The next report must retain an
unresolved row unless the final-source question is independently resolved.

Commands before the next diagnostic:

```
.venv/bin/python -m pytest tests/prospectus/test_loss_absorption.py -q --junitxml=docs/implementation/bond-loss-absorption-classification/execution/repair-002-expanded-tests.xml
.venv/bin/python scripts/run_bond_loss_absorption_classification.py --inventory docs/prospectus/classification-additions/issue-inventory.json --output docs/implementation/bond-loss-absorption-classification/execution/development-002
```

The next diagnostic inspects emitted witnesses as well as answers. An answer
that happens to be right with a wrong supporting clause is not accepted.
