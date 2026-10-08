# Resume the prospectus adoption work

The user's request was to survey tools and literature that could close the
remaining prospectus gaps. That survey is complete; the next implementation and
trial sequence is specified, not executed.

Worktree: `/home/chakwong/python/legalmath/.worktrees/bond-gap-closure`.
Branch: `feature/prospectus-evidence-master`.
Survey baseline: `a05e18bbdeefbf278d29a6755e274124f97bda35`.

Read [SURVEY.md](SURVEY.md), the
[adoption program](../../plans/prospectus-adoption-program-2026-10-07.md), and
[reading-ledger.json](reading-ledger.json). The first implementation is A0/A1:
freeze the evidence slice and complete interval dispositions in the existing AST,
including selected, excluded, replaced and shared definitions. Preserve BASF's
printed p112 instruction applying its reference-period definition to every
Actual/Actual option. Keep the two supplement p12 ranges unresolved until an
admitted source-backed interpretation exists.

Reuse existing Z3/Hypothesis; use the enumerating evaluator as a comparator on
its supported domain. Trial Docling, an INCEpTION export bridge and QuantLib in
isolated environments only with explicit input conventions and acceptance tests.
ACTUS/CDM runtime migrations and broad new OCR/model installations are deferred.

The OCR toolchain already exists in the pinned tfgpu Python through PyMuPDF.
Do not infer it is missing from the app venv or from a missing `tesseract` CLI.
The retained profile is English at 300 dpi; it is not evidence of multilingual
accuracy. The inventory is CPU-only and does not assess GPU availability.
Avoid the elan shim for a casual version probe: it timed out during this survey.

All retrieval receipts and failures are retained. Logical retrieval budget is
96/120, conservatively charging 33 for the lost initial discovery bundle.
The repaired discovery's twelve nominations were metadata-screened; none was
adopted as a technical source. No exhaustive literature coverage is claimed.

Useful local commands:

```text
python3 -m scripts.prospectus_adoption_survey validate
```

The seven-page [PDF](SURVEY.pdf) is rendered from the same report. Its build
receipt and geometry diagnostic are retained. `render` regenerates it using the
installed Pandoc 2.9 API and explicit table widths; a different Pandoc API needs
review of the table adapter first.

Rebuild the source manifest only after a deliberate source/record update, then
validate it. Do not rebuild it merely to erase a hash mismatch. Acquisition and
parsing need the existing ResearchAssistant environment; validation uses the
standard library. The helper's inventory reads versions and OCR receipts, not
prospectus models or accelerators.

No production package, release/default policy, source evidence receipt, main
branch or remote was changed. No real independent readers were contacted.
P7/P8 and actual-event/legal release remain blocked on their existing evidence
requirements. Engineering continuation is still possible; do not turn those
promotion vetoes into blanket continuation vetoes.
