# Version-2 fresh-family run

After `freeze-v2.json`, acquire Danske Bank Series 4 DKK AT1 pricing supplement
and its 14 August 2026 base memorandum, plus Shell International Finance's
September 2020 GBP senior issue and its 13 August 2020 information memorandum.
Neither family was used to develop the classifier. Select programme editions
from explicit issue references and bind their date to its actual cover location.
Every source answer and open clause is published; no expected legal labels are
inputs. The same evidence contract and interpretation qualifications apply.

```
.venv/bin/python scripts/run_bond_loss_absorption_classification.py --inventory docs/prospectus/classification-holdout-v2/issue-inventory.json --output docs/implementation/bond-loss-absorption-classification/execution/holdout-v2 --checks
```

447 prospectus regression tests, including 305 classifier tests, passed after
the edition repair. Six real-source faults passed the delivery verifier. Execute
the fresh run with unchanged hashes; any new unresolved result is a published
limit, not grounds to tune secretly to the case or force an answer.

Archive reconciliation also found a retained Lloyds final filing in HTML on a
filing CDN. The earlier note that Lloyds was entirely unavailable was wrong:
issuer PDF acquisition failed, but the HTML mirror exists. Add that development
source separately with its mirror-authenticity qualification and text-unit
locator; it is not a fresh-family challenge.
