# Reconcile retained Portuguese sources before further acquisition

The current handoff says the other original-language editions remain to be
acquired. Existing 11 October receipts instead report complete Portuguese
2008, 2009 and 2010 PDFs in `attempt-001/bes-YEAR-pt-resumed/response.bin`.
The first task is to distinguish availability from scope, consumption and
authentication. No network request is justified before that distinction is
checked.

Evidence contract: verify every receipt-listed file against its retained hash,
open each PDF in the existing CPU-only PyMuPDF interpreter, inspect the native
page inventory and bind the archive's exact href to the receipt URL. Compare
the retained 2010 bytes with the subsequently acquired copy. A mismatched hash,
PDF parse failure or inconsistent URL stops admission of the affected file.
Successful opening establishes usable local bytes only; neither PDF creation
dates nor HTTP dates establish historical publication or legal incorporation.
Report-page keyword matches are nomination diagnostics, not complete text or
image review. Preserve historical receipts and the duplicate copy.

Skeptical audit: filenames such as `Relatorio_Gestao` do not establish that the
needed financial opinions are inside. English and Portuguese pagination may
differ. Inspect page identities from each source independently. A successful
download cannot close any of the fourteen onward-source dependencies. Source
graph consumption and independent authenticity remain separate. This audit
passes as a bounded read-only source reconciliation with new result files; it
does not change code bound to the active R4 controller run.

Command: `CUDA_VISIBLE_DEVICES=-1 /home/chakwong/miniconda3/envs/tfgpu/bin/python docs/implementation/prospectus-integration-closure/bes-original-acquisition/source-inventory-2026-10-12/inspect_sources.py`.
Save per-page native diagnostics, receipt verification and source status under
that directory. Limit keyword excerpts to 200 characters, preserve full native
text on disk and return only a compact result. Seeds are N/A. The only promotion
is from "not inventoried" to "locally retained verified bytes"; no package,
legal interpretation, language-default or historical-availability conclusion.

The first launch used `inspect.py`, shadowing Python's standard-library module
when PyMuPDF imported it. It failed before any source inspection or result
creation. Rename the diagnostic to `inspect_sources.py`; this is a local script
naming error, not a PyMuPDF failure. The next launch uses the corrected name.
