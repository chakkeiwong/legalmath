# Separate output limits from Bubblewrap's private runtime copies

The first boundary launch failed before executing Python: Bubblewrap could not
copy the 25,555,040-byte interpreter because our launcher imposed a20MiB process
file-size limit intended for captured output. A single RLIMIT_FSIZE applies to
Bubblewrap's private file copies too. This is our launcher resource-limit error,
not a namespace permission failure or package defect. No escalation is indicated
by this particular error.

Retain the failed invocation/receipt/stderr and original method. Give internal
runtime copies the already reviewed512MiB bound, while enforcing the separate
20MiB stdout/stderr limits in the parent as it drains nonblocking pipes. Bound
stdin and the deadline in that same loop, kill/reap on timeout or output excess,
and preserve nonzero child exit codes. An early-exiting child must not hang on
stdin. Add actual subprocess checks for excessive output and early failure.

Skeptical review PASS: this restores the original separate bounds; it does not
raise the output or runtime budget, weaken file validation or add a host mount.
Keep all original OCR/downstream comparisons. This consumes the second and
last allowed inventory/launcher repair. Retry the boundary once under a distinct
stage name and retain any further failure rather than silently repairing again.
