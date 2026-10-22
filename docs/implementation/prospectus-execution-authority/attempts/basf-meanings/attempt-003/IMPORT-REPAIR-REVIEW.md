# Bounded preparation import repair

The first preparation command failed before entering preparation or writing a
started/result/input artifact. Importing the retained predecessor's
run_definitions also imports its predecessor's generic readings module. Python
then resolves the new worker's `from readings` through that occupied module
name, which has no EARLY identifier. Worktree src pinning does not solve a
collision between two attempt-local helper modules.

This is our harness namespace error. Preserve the exact command/failure and
pre-repair worker. Rename only the new local helper to remaining_readings and
import that unique name. Historical attempts and production methods remain
untouched. Verify both current and predecessor module paths before preparation.
No successful computation exists to repeat. The original source, comparator,
scope, stage/time/storage bounds and cumulative admission are unchanged.

Skeptical review PASS for this one bounded harness repair: module-path inspection
directly tests the diagnosed explanation. An unresolved import or changed
predecessor identity vetoes resumption. This failure provides no evidence about
the legal readings, product behavior or suitability of an external package.
