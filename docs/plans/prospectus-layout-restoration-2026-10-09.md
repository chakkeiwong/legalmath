# Restore the retained CPU layout profile

Question: can the complete pinned Docling profile and its layout model be
restored without relying on the original temporary environment/model directory,
then process the retained BASF page 112 and preserve the designated source
mapping? This extends R6; it does not evaluate new layout families.

Baseline: the installed Docling 2.60.1 CPU sidecar, its complete transitive
distribution inventory and the four retained layout-model files. Verify the
model bytes against the historical download receipt before copying. Preserve
all package files in a project-local binary snapshot with individual SHA-256
identities and a whole-archive hash. Restore into an empty temporary directory
and verify every file, use a fresh venv interpreter and test dependency
consistency. Repeat restoration after deleting only this run's temporary copy.
This is restoration from a verified binary profile on the same host, distinct
from the wheel-based clean installation already tested for core/OCR/finance.

Primary pass criterion: both restored profiles execute Docling on the exact
source/page; normalized text, geometry and mapped source occurrences agree
between the two runs, and the retained shared definition has source matches.
Native libraries, Python standard library and Poppler remain recorded host
dependencies. Package/model hashes veto reuse after a mutation. Missing model
files must request restoration rather than trust an old receipt.

Vetoes: baseline package inconsistency, changed source/model, an archive member
escaping the restore directory, missing expected file, wrong package version,
model auto-download, CPU-profile mismatch, missing completion record, unexplained
mapping difference or budget exhaustion. A failed candidate triggers repair;
it does not reject Docling. Count/runtime are explanatory. No automatic legal
governing relation, unseen-document accuracy, native confinement or independent
legal interpretation is established.

Defaults audit: retained versions isolate restoration from package upgrades;
their target suitability remains conditional. Four CPU threads and the existing
layout-only model are the reviewed historical profile; OCR/table structure are
disabled and cannot be credited. The baseline source and model were previously
exercised; per-file verification precedes inference. No training environment is
modified and CUDA_VISIBLE_DEVICES=-1 precedes scientific imports.

Budget: 10 minutes, 3 GB persistent archive/manifest and 3 GB temporary restored
profile. No network downloads or server start. Exact command:
`python3 -m scripts.prospectus_closure_layout_restore`.
Artifacts: immutable attempts in
`docs/implementation/prospectus-integration-closure/layout-restoration/`.

Skeptical audit: PASS for this restoration claim. Copying a venv and trusting
its old shebangs would be inadequate, so create a fresh interpreter environment
and invoke modules with that interpreter. Restore package files into its
site-packages, validate the entire snapshot, and run pip check. The external
host-library limitation remains explicit. Broader layout testing and Java/
browser restoration remain separate work.
