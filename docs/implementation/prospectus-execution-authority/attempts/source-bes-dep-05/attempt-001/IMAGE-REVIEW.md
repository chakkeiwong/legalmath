# Original source review and bounded OCR refinement

The 175-page English Interim Report is Banco Espírito Santo Group/Bank, first
half 2010. Original bytes: SHA-256
`b86022629850867b5bedbdaf701a451a816f46766d102fc487fc51da658b0ea7`.
Ten rendered pages were inspected: 1, 50, 51, 55, 58, 60, 162, 163, 172, 173.
The text inventory covers every page, but it is not a full semantic review.

Page 1 says **Audited financial information**, approved by the Board on
23 July 2010. The introducing prospectus says **unaudited**. Pages 172–173 are
explicitly a **Limited Review Report on Interim Consolidated Financial
Information**, issued by the CMVM registered auditor. Paragraphs 5 and 8 say
**moderate assurance**; paragraph 8 gives a negative-assurance conclusion about
IAS 34 compliance and complete/true/current/clear/objective/lawful information.
KPMG's report is dated **13 August 2010**, not the Board date, metadata creation
date or archive capture. Preserve these distinct source statements. Neither the
cover nor prospectus label authorizes changing the detailed report's scope.

Page 50 separately states adjusted accounting standards for the Bank's individual
statements under Bank of Portugal Notice 1/2005, and EU-adopted IFRS for the
consolidated statements, transposed through Decree-Law 35/2005. The assurance
report covers consolidated information. Do not extend it to individual accounts.
The free English translation expressly gives the Portuguese version priority
in doubt or misinterpretation; the Portuguese original is not recovered here.

Pages 51 and 58 are consolidated balance sheets. Page 55 is a divider, correctly
sparse in native text. Page 60 is the image cash-flow statement. Pages 162–163
contain image tables of sector risk and loan ratings; sparse native text misses
their content. These are actual missing source-content cases, not decorative
images. Retain OCR for exactly 60, 162 and 163 using the previously pinned
English model and 300 dpi profile. The existing hybrid path preserves native
units and adds image-bound OCR words. Geometry/text integrity does not prove
table cell associations or financial values. No broader automatic coverage is
claimed. Full table interpretation remains open even after words are retained.

The source plan is refined to include one 90-second OCR worker and actual P1
build under a 120-second wrapper. Runtime is the demonstrated
`/home/chakwong/miniconda3/envs/tfgpu/bin/python`, with GPU intentionally hidden;
English model comes from the retained legacy-audit request. Model/profile reuse
is a baseline convenience; verify model hash, successful geometry and actual
retained table words before interpreting it. Three selected pages stay within
the existing maximum. Retain a bounded failure if this candidate fails.

Code review identifies a real semantic-model gap: `report_scope.PROFILES` has
statutory financial audit, committee report and limited sustainability assurance,
but no interim financial review. Use explicit unknown identity/assurance fields
and exact subject/conclusion/date spans in the actual consumer. Retain the
unsupported-category rejection and a supplied-but-wrong audit-label probe for
the existing relation/qualification task. Do not force this report into an
inapplicable category merely to obtain a complete scope status.

Matched comparison: same source graph and assembly with and without supplied
readings of context (pp1/50), review (pp172/173), cash flow (p60) and risk tables
(pp162/163). Questions/dependencies must remain unchanged; original BES-DEP-05
stays unresolved. Actual final output must retain moderate assurance, IAS 34,
accounting/translation distinctions and unknown scope status. Corrupted edition,
omitted selected page, changed quote/date and unsupported classification must
reject. This preserves substantive progress while exposing the local model's
limit. A complete relation to pp51–173, independent authenticity and full-table
semantics are not established by this development consumer.
