# Development readings fixed before the consumer

The executing agent inspected both retained 120 dpi page images. This is an
exposed development reading, not an independent reader's acceptance. Original
source hashes, image hashes and page dimensions are in `page-selection.json`.

Portuguese BES 2009 PDF page 136 (printed 135) is a real financing table. Its
heading says `31.12.2009` and its unit label says `milhares de euros`. The
instrument currency column is distinct from the reporting unit for balance
values. Freeze three complete rows: the first EUR 2002 zero-coupon row with
balance 51 159, maturity 2027 and effective rate 5,90%; the USD 2003 step-up row
with balance 53 436, maturity 2010 and **first-coupon** qualifier 3,50%; and the
EUR 2003 fixed-note row with balance 24 754, maturity 2013 and a single coupon
paid in advance. These are accounting disclosures; they do not establish the
full contractual cash-flow schedule or identify a client's holding. The two
zero-coupon rows have similar names but different values and effective rates,
so testing only the instrument name would be an inadequate comparator.

Portuguese BES 2008 PDF page 24 has an organization diagram and charts beside
body text. `Negócio Doméstico` and `Negócio Internacional` are rotated Latin
labels. Their words read along a rotated horizontal baseline; this page is not
evidence of true vertical writing. The whole-page PDF rotation is zero.

The exact strings and point rectangles in `development-readings.json` were
fixed from the image and the separately retained PyMuPDF text/geometry before
running the Poppler-based P1 product. Rectangles are explicitly supplied
regions. Successful projection tests source accounting under those supplied
regions; it cannot establish automatic table detection or row/header semantics.

Consumer evidence contract: construct real P1 products from the two complete
original PDFs, preserve them, and send the frozen regions to the existing
`project_layout` consumer. For each region retain the actual text, source
offsets, failures and source identity. A mismatch is a candidate failure and
must remain visible. Adverse controls remove the first-coupon qualifier, alter
the rate, move the box to the adjacent row, substitute another edition, assign
one unknown box and duplicate region ownership. These must refuse projection.
No product code changes or parser retuning are authorized by a failed case.
Continue source preparation if a family remains absent.

Command: `timeout 120 .venv/bin/python docs/implementation/prospectus-execution-authority/attempts/native-layout-cases/attempt-001/consume_sources.py`.
The script pins worktree imports, records method/source hashes, hides GPUs and
retains full P1 products. Pass requires exact frozen nonspace characters with
complete source-bound accounting; test counts are explanatory. Source corruption
or broken P1 identity invalidates the run. No financial or legal conclusion
follows from successful projection. Audit verdict: proceed on this finite,
supplied-region contract; no unexamined scientific default is being promoted.
