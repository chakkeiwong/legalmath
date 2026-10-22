# Reviewed coverage nominations

Inspected the twelve images in `selected-images.json` against their native
text. Portuguese 2010 PDF pages 190–192 contain the consolidated statutory
audit, dated 4 March 2011. Paragraph 8 separately reports on management-report
consistency and governance-report requirements under article 245-A. Pages
193–194 contain the committee report, dated 7 March 2011; the declaration of
members' knowledge in article 245 is not a separate absolute audit assurance.
Page 189 ends the disclosure annex, 195 is a photographic divider and 196 is
the governance contents page. Thus the substantive scan gap is five pages,
not six. Do not OCR the divider to inflate substantive coverage.

Portuguese 2008 p6 is artwork with a caption. It is a concrete false positive
for a rule equating large-image/low-native pages with missing financial prose.
Portuguese 2009 pp21–22 contain vector maps: most of the large drawing counts
come from the map's many dots. Map labels and the headline describing 734
retail branches, 22 Private centres and 26 business centres are native text.
This disproves the proposed diagnosis that a high vector count alone means
outlined missing letters. The visual label-to-dot connectors still need
semantic relation review; extracting the words cannot establish that mapping.

Portuguese 2008 p129 is a real financing table. The selected step-up row reads
“BES (sucursal de Caimão) / BES CAYMAN Step Up 07/28/10 / USD / 2003 /
55 313 / 2010 / StepUp (1º cupão 3,50%)”. The date above the table is
31.12.2008 and units are thousands of euros. The first-coupon qualifier must
remain attached to the rate. It is not a complete lifetime coupon schedule.

## Reviewed continuation within this admitted package

The retained Portuguese 2010 OCR worker covers only pages 88–89. Older
exploratory 2010 OCR has English source hash `f6c1196f...`, so it cannot supply
these Portuguese scans. The smallest justified repair is one existing-worker
run on Portuguese pages 190–194 with the pinned Portuguese model at 300 dpi,
followed by actual P1 and two report-scope consumers. The 120-second outer
bound remains unchanged. This repairs page intake; it does not establish full
256-page coverage. Source/method mismatch or a raw geometry failure vetoes
dependent consumption and triggers retained review. Review qualifications and
full opinion/date text before admitting source facts.

Also run three new image-reviewed layout regions from existing native P1:
the 2008 step-up row, the 2009 foreign-branch list and the 2009 network-count
paragraph. Adverse cases should drop the first-coupon qualifier, swap a nearby
row/column, change the count and change the edition. The existing adapter is
the actual downstream consumer. No automatic table or vector-relation claim
follows from supplied-region projection.
