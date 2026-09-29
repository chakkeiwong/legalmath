# Post-run review repair: live-study continuation

Review of the prepared, unexecuted transport driver found that it skipped an
existing response file without checking its status or identity. After a failed
call, that could allow a later invocation to describe an incomplete study as
completed. No live call occurred and no live result is affected.

The driver now permits reuse only for a structurally validated result bound to
the prepared request and retained result hash. A failed, unbound or altered
record requires reviewed repair; dispatch does not silently move past it.
This is an implementation fault, not evidence against model comprehension.
Add a focused continuation regression, then rerun the content-bound phases
because their prepared-study code identity changed. Existing accepted attempt
files remain unchanged.
