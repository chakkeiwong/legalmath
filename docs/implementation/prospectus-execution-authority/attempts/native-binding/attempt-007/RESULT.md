# Preparation refused: product digest mistaken for file digest

No native process launched. Preparation verified all historical006 output
identities and current product methods, then compared the compressed file hash
with its internal P1 product digest. These are different defined quantities.
The protected gzip bytes still match admission:
d6c43e6e24b310f1a26c6067ac79ec8431aa45df60213b16ab38ad6f310bf33f.
The verified internal P1 digest is
8ec9f35d664c5ef491093ce333c39f6c1ec7a4bf1ad5d1f3af8243e01360a69a.

This is our validator implementation error, not corrupted source evidence or
a package limitation. The failed preparation, frozen methods, failed prefreeze
fixture check and empty12-start ledger are retained unchanged. A reviewed
changed repair must check both identities separately and bind the next attempt.
The source matrix has not run, so no preservation or acceptance is concluded.

| Decision | Primary criterion | Veto status | Uncertainty | Next action | Limit |
| --- | --- | --- | --- | --- | --- |
| Reject preparation | Matrix not executed | Wrong digest comparison | Other paths unevaluated | One changed identity repair under same12-start campaign | No native/package verdict |
