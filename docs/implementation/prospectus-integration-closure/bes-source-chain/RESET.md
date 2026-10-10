# Reset memo: BES source-chain completion

The current prospectus worktree is `feature/prospectus-evidence-master` at the
method commit recorded in `real-scan/validation-001/started.json`. The active
real-scan regression is complete: 685 unique tests, exact coverage, unchanged
method, current R0–R8 receipts and final-attribution equality.

The BES source-chain package is complete through its local bounded consumer.
All eight retained PDFs were hash-checked, all 31 newly rendered base/supplement
pages were visually inspected, and the actual service consumed the eight source
documents. Read `SOURCE-REVIEW.md`, `consumer/attempt-007/result.json` and
`RESULT.md` before continuing.

The 2010 base conditions establish the Bank/BES Finance distinction, the
head-office Interbolsa issuer, Final Terms and agency-agreement precedence,
senior-status exception for legal priority, and Condition 22's Portuguese-law
branch with an express other-competent-courts qualification. The fifth
supplement's requested EUR1.25bn, three-year state-guaranteed financing is a
separate transaction and was not assigned to Series 23. The sixth supplement's
rating statement concerns the Portuguese sovereign. These distinctions are
source facts, not independent legal conclusions.

The service result is `ASSISTED`; Q1/Q2 are UNKNOWN, Q3 PARTIAL, Q4 UNKNOWN,
Q5 UNSUPPORTED and Q6 UNKNOWN. Fourteen onward dependencies remain unresolved:
11 applicable incorporated financial sources and three agency agreements.
The mixed 2013 dossier dependencies were excluded from this 2010 chain.

Failed attempts 001–006 are retained. They exposed local annotation-shape,
dependency-filter, adverse-layer, evidence-size, timeout and indexing issues;
attempt 007 passed after bounded repairs. Do not interpret these as failures of
PyMuPDF, Tesseract, Poppler or the service. No package ranking or legal
acceptance follows. The two oversized failed reports are preserved as verified
gzip streams with original-byte hashes in their `compression.json` records.
