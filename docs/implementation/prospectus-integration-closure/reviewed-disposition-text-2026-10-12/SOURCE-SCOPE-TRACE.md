# What the recovered BES reports currently mean to the engine

The product retains the four recovered report pages, but does not yet represent
their report type, assurance subject, addressee or translation priority as
reviewed source facts. The completed eleven-document consumer contains 231 OCR
occurrences on these pages: 230 UNKNOWN and one image-reviewed HEADER. This is
an observed implementation boundary, not evidence that an OCR or layout package
is fundamentally unsuitable.

## Checked path through the current code

| Step | Actual behavior | Consequence |
| --- | --- | --- |
| `service.source_product` | Builds raw graph; admits supplied corrections and layout into P1 | Source recovery and supplied geometry are present |
| `contract_assembly.assemble` | Accepts OPERATIVE, EXCLUDED, EXAMPLE, HEADER, INSTRUCTION, UNKNOWN; defaults to UNKNOWN | No report-type or assurance-subject role exists |
| `service.construction_product` | Uses raw-unit assembly or BASF construction; applies reviewed dispositions | Supplied P1 region reading is not automatically selected P2 reading |
| `admissions.dispositions` | Verifies full selected-occurrence coverage, source text and assembly hash, then changes the role | Requires supplied interpretation; cannot infer authenticity or report purpose |
| `clause_graph.nominate/build` | Uses a finite effects vocabulary for debt, principal loss, repayment, conversion and related terms | Does not interpret sustainability assurance as an audit opinion or creditor entitlement |
| `service.dependencies` | Considers OPERATIVE and UNKNOWN uses and unresolved source/reference issues | Recovered words do not resolve the fourteen original dependencies |

The reviewed-disposition path also left `continuous_text` stale after role
changes. Five public-service counterexamples and a replay using the retained
BES footer reproduce that independent defect. Rebuilding the reading text from
the final selected roles repairs it. It adds no source-scope interpretation.

## Conditional source reading

These statements use the retained English images and reviewed oracle v2.
The subsequent `../bes-original-acquisition/portuguese-2010/RESULT.md` records
acquisition and image inspection of the corresponding Portuguese sustainability
report, with exact spans and an actual P1 reading. It supports the listed
sustainability subject and limits; independent edition authentication and
historical availability remain unestablished. The 2009 committee comparison
still relies on the retained English report.

| Source | Wording retained | Interpretation supported by that wording | Unsupported extension |
| --- | --- | --- | --- |
| 2009 PDF 176–177, printed 175–176 | Audit Committee report; related unconsolidated and consolidated statements; concurrence with unqualified professional opinions | Committee reporting/concurrence, distinct from the statutory auditors' own opinion | Treating every committee statement as a fresh independent audit opinion |
| 2010 PDF 88 | Independent Limited Assurance Report; sustainability information; ISAE 3000 and AA1000APS (2008) | Sustainability engagement and stated criteria | Assurance on the annual financial statements, solvency, or bond repayment |
| 2010 PDF 88 | Portuguese version prevails in doubt or misinterpretation | Explicit translation-priority qualification in the supplied English document | Resolving ambiguous Portuguese wording without the original |
| 2010 PDF 89 | Lower assurance; nothing has come to our attention; solely to GBES; no other purpose; third-party disclaimer | Qualified negative-assurance conclusion within the stated subject, criteria and audience | Unconditional certification or entitlement for every investor to rely |

The page-89 body/sidebar reading is already source-mapped in a separate P1
consumer. P2 does not automatically consume that reading order. A new adapter
must preserve every source character, sidebar and qualifier and bind a reviewed
region order before it can replace selected text. Cropping away the margin or
marking the whole assurance report as a header would hide evidence.

## Remaining work selected from this trace

1. Introduce a separate source-report interpretation contract, rather than
   stretching construction roles into report categories. It must bind report
   identity, subject, criteria, assurance level, conclusion, addressee, reliance
   limits and translation priority to exact spans. Unavailable facts stay
   unknown, and the report must not resolve contractual principal-loss or
   conversion questions merely because it contains favorable language.
2. Review the contract and freeze expected downstream behavior against the
   original statutory opinion, committee report and sustainability report.
   Counterexamples must swap subjects, drop negative-assurance/reliance limits,
   misorder the sidebar, change dates and supply a different translation.
   The inspected Portuguese 2010 wording is now available for this packet;
   other missing originals or unresolved ambiguous wording still block the
   corresponding claims, not conditional analysis of available source text.
3. Connect the reviewed report contract to a consumer answer/explanation and
   compare matched inputs with/without it. P1 metadata alone cannot establish
   integration. Keep the fourteen onward dependencies unresolved until their
   own identity/date/incorporation evidence is admitted.

No new report classification or scope is admitted in this repair. The next
implementation needs the reviewed contract and source packet just described;
there is no justified automatic promotion from the current UNKNOWN roles.
