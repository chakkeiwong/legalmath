# B6: final integration repair and closure

The final red-team audit found completion-status and run-input gaps after B5 had
started its frozen acceptance. Preserve that historical run and add B6 as a
successor repair phase, rather than editing evidence or resetting an attempt.

Question: does the integrated monitor retry actually incomplete work and preserve
the exact inputs used, while keeping substantive uncertainty distinct from a
failed check? Comparator: accepted B5 inputs. Pass criteria: unavailable requested
example queries and unexecuted required partitions make execution incomplete;
nonterminal argument-limit results cannot mark an investigation complete; exact
settings/replay bytes are retained; timeout and unsuccessful monitor results are
visible at the scheduler's top level. Substantive uncertainty without an execution
failure stays an unresolved completed investigation, not an endlessly retried job.

The repair is deterministic and requires zero model calls. Add targeted negative
regressions, run focused checks, record the executed changes and current-input
review, then run the full suite and the same local Java source-update acceptance.
Inspect original and successor manifests and the unchanged global allowance.
Use the existing fixed supervisor; keep B4 empirical and B5 institution acceptance
unfinished. If the full suite fails, preserve the attempt and use its normal
repair/refresh/review mechanism.

The review rejects test count as legal proof, a successful subprocess as completed
semantic work, and a missing call as mere legal ambiguity. Those are different
targets. No source labels, evaluation thresholds, provider choices or authority
claims change in this phase. Once these repairs and the final evidence report
are complete, the remaining continuation vetoes are the live-study budget/outcome
design and the absent institution-owned deployment configuration.
