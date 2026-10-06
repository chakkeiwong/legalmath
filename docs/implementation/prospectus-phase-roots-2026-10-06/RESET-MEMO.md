# Reset memo — P0–P6 investigation

Worktree: /home/chakwong/python/legalmath/.worktrees/bond-gap-closure.
Branch: feature/prospectus-evidence-master.
Checkpoint commit: 7fd9c4e864c22da1e8a5df8ed7bc5c59331eb25f.

The requested checkpoint commit is complete. Its 958 files preserve the earlier
successor execution and manuscript; 18 oversized evidence files have a verified
lossless compressed restore path in the checkpoint directory. Original local
files and historical phase receipts were preserved. No push/merge was requested
in this turn.

## Current result

The [diagnosis](ROOT-CAUSE-AND-SOLUTION.md) records 18 findings plus one control.
Most serious: P4 ignores the actual declared premise list and can return YES
with a required false premise; P6's BASF request inherits UBS AT1 classification
and dates; P3/P6 read P1 rather than consuming their declared stage products.
Other failures concern source occurrence/paragraph coverage, references,
contract alternatives, law-source/time validation, financial schemas/grouping
and evaluation independence/scope.

The [literature review](LITERATURE-REVIEW.md) extends the earlier seven-paper
technical review with Docling, Build Systems à la Carte and official QuantLib,
Docling and build-model code inspection. Five new public fetches are retained,
hashed and listed in literature/new-source-manifest.json. Existing
ResearchAssistant extracted both new PDFs. No model/API, GPU, dependency
installation or source-law acquisition was performed. Prospectus retrieval
ledger is unchanged at 188/212; new literature/code fetches are separately five.

The [proofs](PROOFS.md) are mathematical engineering arguments, not mechanically
verified proofs and not legal-validation results. The isolated reference code
reuses existing prospectus.semantics.possible_decision. It changes no production
successor code.

Executed reference checks: 8 groups, 7,068 truth-table comparisons, 6,052
consistent completions of decisive answers, 675 time-boundary cases, 1,690
exact allocation cases, 64 line partitions, plus source/AST/dependency/context/
reviewer mutations. All passed. See reference-results.json and its manifest.
An earlier 19-record audit preserves current counterexamples and code trace.

## Documentation

The reader-facing LaTeX now records the defects and corrects the earlier claim
that phase integration was already implemented. Rebuilt monograph has 387 pages,
companion 90 and process guide 25. The build checker retains 137 citation
documents, 319 occurrences and 207 original source-unit labels.
See MANUSCRIPT-REVIEW.md and final-verification.json for the final rendered
review, exact hashes and verification. The previous reset memo's page counts
and finalization receipts describe the earlier committed checkpoint.

## Next action

Implement [R0–R6](../../plans/prospectus-phase-repair-2026-10-06.md).
Start with R0 false-answer/context containment, then R1 actual product consumption.
Do not start by rerunning the old master program; it will reuse PARTIAL receipts
and cannot execute the prose repair obligations. Production repairs remain
proposed. Independent legal review and useful real-document accuracy are still
unestablished.

Preserve these counterexamples as baseline evidence; the old audit asserts
observed defects and will need a separate forward regression mode after repair.
Do not change its expected observations and call that closure. Development
and independent evidence are distinct. Missing reviewers block promotion,
not offline implementation.

## Reproduction

- python3 -m scripts.audit_prospectus_phase_roots
- python3 -m scripts.check_prospectus_phase_reference
- python3 -m scripts.prepare_prospectus_phase_literature
- python3 -m scripts.build_reader_facing_monograph
- python3 -m scripts.finalize_prospectus_phase_audit

The first two pin worktree source/application interpreter and deliberately hide
GPU devices. The literature extraction uses the installed ResearchAssistant
adapter; manuscript work uses the interpreter with PyMuPDF. Exact environments
and commands are in the manifests.

Ordinary worktree/tmp edits are authorized. The sandbox's intermittent
/mnt/wslg/distro mount error affects some read tools; it is not a lack of
authorization to edit. The image viewer could not mount its sandbox, so rendered
page bytes were read with an explicitly trusted, read-only base64 command for
visual inspection. No broader permission policy was changed in this investigation.
