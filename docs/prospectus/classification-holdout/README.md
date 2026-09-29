# First source-family challenge: preserved and repaired

Five original PDFs, 477 pages, are preserved in [manifest.json](manifest.json):
Compass's 3.500% 2035 final terms, its 2025 base and December supplement, an
incorrect 2026 base, and ING's September 2025 AT1 supplement/base bundle.
They were acquired after the first classifier freeze.

The original frozen classifier returned negative for Compass and positive for
ING. A subsequent fault challenge found that substituting the 2026 base could
pass the old whole-document date check because it mentioned the 2025 edition.
That version's integrity claim was rejected. Edition matching now checks the
identified page, and the real wrong-edition substitution is rejected.

These sources are now development material. They are **not** counted as fresh
transfer evidence for the repaired version. The initial
[inventory](issue-inventory.v1.json), corrected [inventory](issue-inventory.json),
originals, failed challenge record and subsequent runs remain available.
The correct Compass documents specify principal repayment; ING's selected AT1
provides for compulsory ordinary-share conversion.

[Combined results](../../implementation/bond-loss-absorption-classification/results.md)
retain their qualified outcomes and generated reasons.
