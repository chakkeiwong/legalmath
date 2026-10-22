# Pre-admission receipt correction

Revision270 has not admitted the new reference attempt. A final code-path
review of `execution_workers.validate` found that the proposed result omitted
the mandatory `task` identifier. Correct `seal()` before any admission, retain
the original freeze/proposal unchanged, and bind a new `freeze-final.json`
through revision271. Keep the original plan, scope, stages and resource limits.
The original twelve admissions remain; the maximum stays thirteen.

The checker compares the whole source-specific result independently; a stage
receipt PASS does not overwrite its substantive classification. The result
must declare `task: basf-references`, PASS and `original_task_complete: false`.
No named whole-task validator or pension acceptance is claimed. Review the
candidate and missing-link question deltas, parent hashes and source mappings
before the expensive stages. Validate final receipt structure before execution.

Skeptical audit: this was a pre-admission harness defect, not a source or package
failure. It must not become another failed substantive admission. No experiment
has run under270, no budget is reset, no margin retry is authorized, and no
sealed evidence changes. The corrected program may proceed after source/test
and authority checks. All other provisions of
`docs/plans/prospectus-basf-relative-notices-2026-10-18.md` remain binding.
