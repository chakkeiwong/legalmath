# Portuguese source availability corrected

All three original issuer-linked Portuguese PDFs were already retained from
11 October. Their receipt-listed files match the recorded hashes (seven files
per year). Each PDF opens without a repair being required. The earlier 2010
bytes are identical to the subsequently acquired 2010 copy. No additional
download was necessary for this reconciliation.

| Year | Retained original | Bytes | PDF pages | SHA-256 |
| --- | --- | ---: | ---: | --- |
| 2008 | `../attempt-001/bes-2008-pt-resumed/response.bin` | 3,903,190 | 284 | `e7284e7f098ab405b24d461e493e0f0a043ed57f10eca5ac18f31a4bbdee588a` |
| 2009 | `../attempt-001/bes-2009-pt-resumed/response.bin` | 4,460,884 | 228 | `9c3172f2cbb7f566be41985bee38d0d1393ab87fcf897a53d0cbc233ecf37c19` |
| 2010 | `../attempt-001/bes-2010-pt-resumed/response.bin` | 8,125,384 | 256 | `981fa3f96ed65da0d42f3de9c35797f1dfbd676c6f6c11fbcf394b54adff3058` |

The previous continuation notes confused lack of current consumption with
lack of local bytes. The correct remaining tasks are source-content comparison,
product consumption where needed, incorporation/edition authentication and
historical availability. Acquisition is complete for these three local
candidates. The fourteen original onward-source dependencies remain unresolved.
These Bank reports cannot replace BES Finance Ltd.'s accounts or any of the
three named executed agency agreements.

The 2009 contents page locates the statutory report at printed 173 and the
committee report at printed 176. Native page headings and source images locate
them at PDF 174–176 and 177–178 respectively. The Portuguese statutory report
has three pages; the retained English audit has two. Copying English page
indices would lose the Portuguese opinion/date page. The 2008 contents page
separately lists consolidated certification at printed 245, individual accounts'
certification at 248 and committee report at 250. Those are nominations for
source-image inspection, not an inference that the English page offsets apply.

Two diagnostic mistakes were caught and retained in the plan. The initial
script name `inspect.py` shadowed the Python standard library, failing before
source inspection; renaming fixed it. The first whitespace regex inserted a
matcher into an already escaped space, so the first result's zero keyword
counts are invalid diagnostics. `keyword-nominations-002.json` corrects that
diagnostic using the retained native text without rerunning extraction. The
byte verification and PDF-open results were unaffected. The corrected keyword
matches nominate content/heading pages but are not a completeness test.

Decision: use the verified local sources, and continue the independently
reviewed Portuguese 2009 report consumer. Source authenticity, first-publication
dates, historical availability, missing other entities' originals and legal
incorporation stay open. Metadata dates and the archive link do not settle
those questions. This corrects our inventory and page-selection assumptions;
it supplies no evidence of a fundamental OCR or parser limitation.
