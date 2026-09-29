# First bounded parser repair

Initial controlled tests: 286 passed, two failed; `initial-tests.xml` is retained.
The creditor-amendment recognizer incorrectly treated an issuer's conversion
without holder consent as an amendment requiring creditor approval. Restricting
that recognizer to amendment/voting language repairs the subject and consent
distinction. A resolution-authority reference without the word bail-in was not
retrieved; adding that phrase makes the benchmark-administrator exclusion
observable. Neither repair depends on an issuer, country or desired bond answer.

Command: `.venv/bin/python -m pytest tests/prospectus/test_loss_absorption.py -q
--junitxml=docs/implementation/bond-loss-absorption-classification/execution/repair-001-tests.xml`.
Result: 288 passed. These are controlled construction and integrity tests; they
do not establish unrestricted English interpretation accuracy.
