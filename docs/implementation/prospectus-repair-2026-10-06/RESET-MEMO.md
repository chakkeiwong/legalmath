# Resume the ordered repair

Updated 7 October 2026. Branch `feature/prospectus-evidence-master`, worktree
`.worktrees/bond-gap-closure`. Read [RESULT.md](RESULT.md) and the
[execution plan](../../plans/prospectus-phase-repair-execution-2026-10-06.md).

Current receipt state: P0/P1 attempt-009; P2/P3 attempt-008;
P4/P5/P6 attempt-007; P7/P8 attempt-004. All nine are current. The installed
consumer uses all five products; it passes five corruption rejections and three
changed-input pairs. Replay preserves the partial/blocked results.

Verification: 983 broader tests before the final BASF source correction;
90 focused tests on the final code, including two new pinned-source regressions.
Current manifest: `finalization/run-002/manifest.json`. Historical broad manifest:
`finalization/manifest.json`. `finalization/run-001` preserves the failed
whitespace-sensitive test assertion; the source was not changed to satisfy it.

The manuscript build passes: 387-page monograph, 90-page companion, 25-page guide,
319 citations and 207 source-unit labels retained. Changed pages and source
images are in `document-review/`; human reader acceptance remains pending.

Do not rerun the historical defect auditor expecting its old broken-behavior
assertions to pass. Use:

```text
python3 -m scripts.prospectus_delivery status
python3 -m scripts.prospectus_delivery check
python3 -m scripts.prospectus_delivery repair --record <reviewed-record.json>
python3 -m scripts.verify_prospectus_repairs --focused
```

The phase dispatcher sets CPU-only execution and pins this worktree's source.
No OCR installation is needed. Retained PyMuPDF/Tesseract output is read with
word geometry and separately bound corrected transcription. Do not overwrite
old extraction/review receipts by running historical workers.

First substantive repair: finish the 83 remaining BASF brackets, fields,
numbering and incorporated-reference dispositions. There are 77 recorded
operations and no unbalanced delimiter. A printed p112 margin requires the
common reference-period definition for every Actual/Actual option even though
the optional final-terms reference-period box is empty. Do not regress that
source-reviewed correction. The 195–209 versus 209–290 printed range discrepancy
remains unresolved. The generic AST is present but not the complete BASF path.

The remaining work is not solely external review: generic exclusion/override
accounting, multilingual interpretation, indirect reference scope, more agreement
sets and complete settlement remain engineering. Actual legal/event/client facts
and independent readings cannot be fabricated. P7/P8 stay blocked until real
bound records are admitted. A current receipt is not phase or release acceptance.

Large exact products are preserved locally; the lossless checkpoint manifest
documents their portable compressed copies and restore command. All 84 archived
files passed separate round-trip verification; all 63 phase receipts have their
outputs present. No evidence log is silently ignored. After a fresh checkout,
run `python3 -m scripts.archive_prospectus_successor_checkpoint restore --campaign repair`
before checking the phase state. The restored outputs must reproduce their
original receipt hashes. Main checkout, remote branches and historical successor
receipts were not changed by this run.
