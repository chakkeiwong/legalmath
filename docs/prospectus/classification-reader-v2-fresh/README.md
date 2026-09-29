# Sources acquired after the reader repair freeze

Two originals, totalling 184 pages, are retained with their extracted text,
URLs and hashes in [manifest.json](manifest.json). The code was frozen before
searching for these issuer families. These are dated documents first exposed
to this implementation after the freeze, not publications from an unknown
future date and not a random accuracy sample.

The Santander circular covers the July 2025 euro AT1 issue, XS3100756637.
Its contractual name is Preferred Securities; the status provisions describe
unsecured subordinated payment obligations, distinct from the US preferred
stock depositary shares excluded from the bond report. That scope reading
remains qualified. All pages are examined without an expected answer field.

The Unilever final terms cover the 2.750% issue due 22 May 2030, XS3081333547.
They expressly require the Information Memorandum dated 16 May 2025. Both
issuer-published memorandum URLs returned HTTP 403. This is recorded as a
missing operative dependency and blocks a binary classification. The missing
original cannot be replaced by search snippets or a different year's edition.

AstraZeneca was the initial corporate candidate. Both public PDF requests
returned HTTP 403, including a browser-user-agent retry for the base. No
classification was attempted from those responses. The acquisition headers
are preserved; the failed candidates have not been silently counted as
successful source acquisition.

[Issue inventory](issue-inventory.json) records the source boundaries.
[The frozen run](../../implementation/bond-reader-repair/fresh-final/classification.md)
records every answer and abstention. An abstention is a coverage result, not
evidence that a bond contains the requested feature.
