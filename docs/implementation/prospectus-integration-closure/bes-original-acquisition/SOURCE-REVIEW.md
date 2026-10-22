# Retained BES original candidates, 11 October 2026

Three complete English annual-report PDFs were retrieved from the issuer's
retained archive. Portuguese editions are retained for comparison. The public
archive route and exact bytes are evidenced; independent authentication is not
established. None of the fourteen onward dependencies has been promoted in the
consumer. Eleven still lack a matching original candidate in this acquisition.

| Candidate | Dependency | PDF pages | SHA-256 |
|---|---|---:|---|
| BES 2008 English annual report | BES-DEP-07 | 286 | `6ea068cae9bd7bf72e97cfa473b60b7f90e32aaa0838fb78922c222a681feb3b` |
| BES 2009 English annual report | BES-DEP-06 | 229 | `5a8e79459e2109bd43173320af39aa4bc4ee08392746772f3bf7e4ffac8027c8` |
| BES 2010 English annual report | BES-DEP-09 | 256 | `f6c1196ffcbaed34dc4068b4fbc095b4494e421e224977bfa54b215134e32f25` |

Counts come from the parsed original PDF, including blank/image-only pages.
The earlier inspection script's count of nonempty text pages is not a PDF
page count. Reporting year end and PDF creation metadata are not publication
dates or historical knowledge dates. Those dates remain unestablished.

The introducer is the retained 2011 programme prospectus, PDF pages 37–38.
The 2008 English report uses identical printed/PDF numbering. Its statements
and notes at printed 69–75, 163, 165–171 and 241 match the cited sections.
The 2009 report has one front page: PDF page equals printed page plus one.
Printed statements 66–79 and notes through 170 match their cited types.
The 2010 report uses identical numbering at the cited income statement 92,
balance sheet 94, cash flow 96 and notes 97–187.

Six audit pages require hybrid OCR: 2008 PDF 245–248 and 2009 PDF 174–175.
Rendered images show full audit bodies and dates, while native extraction
returns headers/footers. The 2008 pair 245–246 is consolidated; 247–248 is
individual, with the Bank of Portugal Adjusted Accounting Standards and stated
IFRS exceptions. Both opinions are dated 25 February 2009. The 2009 consolidated
opinion is dated 4 March 2010. Their English-translation qualifications must
survive intake. The 2010 audit opinion is on PDF 190, dated 4 March 2011.
PDF 191 is an Audit Committee report dated 7 March 2011, not a second page of
the auditor's opinion. Retain that source-type distinction even though the
introducer groups pages 190–191 under its auditor reference.

## Acquisition/search disposition

Issuer Portuguese/English indexes, original response headers, failed and
resumed transfers, extraction logs, images and retrieval receipts are retained
under `attempt-001`. Initial DNS failures were sandbox failures. Trusted
partial transfers reflected the observed server rate; completed resumed files
matched their declared lengths and ETags and parsed successfully.

The Google response was a JavaScript challenge. Three Bing RSS responses
returned unrelated material; they are unusable search results. The inspected
issuer release index exposed recent entries, not the required historical
releases. These results do not establish that the other originals are absent
from the internet. The agency agreements and BES Finance statements remain
unresolved; a Bank annual report cannot substitute for the separate issuer.

## Decision

| Decision | Primary criterion | Veto/uncertainty | Next justified action | Limit |
|---|---|---|---|---|
| Retain three original candidates | Exact bytes, issuer route, period and cited sections checked | Complete audit intake and historical dates remain open | Run reviewed original-page hybrid OCR, then consumer identity controls | No authentication or source-complete consumer claim |
| Repair local mixed-page intake | Six missing audit bodies reproduced against rendered pages | Native headers conceal image text; whole-document scan cap is twenty pages | Execute `prospectus-hybrid-page-intake-2026-10-11.md` | This is a local selection/usage defect, not proof that the OCR package is unsuitable |
