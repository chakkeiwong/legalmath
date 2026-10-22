# Source coverage and review findings, 12 October 2026

Follow-up evidence narrows two causes. Both pinned bilingual orders recover
the three new-page accent/code checks and the 2009 audit opinion without
losing an earlier matched span; two 2008 accents remain wrong. Language
configuration therefore explains some observed recognition failures, while
not resolving all of them. See `../language-profile/RESULT.md`. For the
negative-assurance phrase, all extraction sorts still mix body and sidebar.
The existing product layout adapter now consumes supplied body/sidebar
regions, preserves the full character partition and passes every page check.
This closes a source-specific adapter-usage gap, leaving automatic region
detection and legal scope open; see `../reading-order/RESULT.md`.

The new source pages exposed several different failures. They cannot fairly be
collapsed into a verdict that PyMuPDF, Tesseract, Poppler or the reference
packages are unsuitable.

| Finding | Checked cause | Repair or remaining work |
| --- | --- | --- |
| Four report pages missing from text | Native extraction retained only headings/page furniture; our explicit OCR selection omitted 2009 PDF 176–177 and 2010 PDF 88–89 | Extend the reviewed selection; retain native text and old OCR by occurrence identity |
| Failed preflight could proceed | Historical runner compares a manifest hash with its result member hash, then validates files without requiring PASS | New coordinator independently checks status, required members, member bytes and path confinement; mutated controls exercise each check |
| Expanded consumer falsely rejected | Harness demanded identical full question objects despite new UNKNOWN units | Compare prior evidence exactly and permit only the enumerated new unresolved units/warning; reject lost prior issues or any other answer change |
| One apparent OCR wording error | Our v1 oracle was transcribed from an insufficiently enlarged view | The 300-dpi crop says “unconsolidated and consolidated”, which OCR read correctly; preserve v1 and publish a bound retrospective v2 |
| “§ 176” treated as a legal citation | OCR combined vertical footer letters and the printed page number; `source_graph.REFERENCE` found §, and the default UNKNOWN role made the occurrence eligible for `service.dependencies` | Supply HEADER only for that image-reviewed, hash-bound occurrence; dropping the disposition must reproduce the false reference |
| Missing Portuguese accents | Raw English-model recognition reads seven inspected issuer tokens as Espirito and a member as Joao | Nine token maps include these eight accent corrections; language-profile evaluation remains separate from display correction |
| Wrong assurance standard identifier | Raw recognition reads AAIL000APS; the image reads AA1000APS | Exact token replacement accounts for this occurrence; do not infer that all numbers/codes are correct |
| Broken body reading order | Sidebar OCR lies between “nothing has come to our” and “attention” in the raw stream | Retain both original spans and an assisted ordered reading. Automatic reading order remains open |
| Large unresolved evidence lists | `contract_assembly.assemble` assigns UNKNOWN to every occurrence without a supplied disposition, and the service includes UNKNOWN uses in reference roots | Preserve uncertainty. Source-specific relevance and role review is required; adding text is not resolution of the fourteen missing-source dependencies |

The distinction between reports matters. The 2009 Audit Committee concurrence
is separate from the statutory auditors' opinion. The 2010 sustainability
report gives limited assurance, specifies criteria, restricts its purpose and
third-party responsibility, and says the Portuguese version prevails in doubt
or misinterpretation. It is not the financial audit opinion at PDF 190.
Recovering these words does not establish that the documents are authentic,
available at the historical query date, applicable to the instrument or
legally sufficient for any of Q1–Q6.

The engineering evidence lives in `attempt-001/` and
`review-repair-001/`. The former retains its failed consumer comparison and
original oracle. The latter records the corrected comparison, source-based
dispositions, display corrections and actual consumer result. Consult each
phase's `result.json` and manifest rather than treating the presence of a
script or a prepared packet as successful integration.

The 771-page inventory is a complete list of page measurements, not complete
text extraction. Forty-one pages were nominated. Six were previously selected
audit pages, four were newly confirmed substantive omissions, and 31 received
contact-sheet triage only. Advertising and map images can contain words; small
images and vector-drawn text can escape the screen. Future text oracles require
enlarged crops for uncertain glyphs before freezing, and broad coverage needs
its own adjudicated evidence.
