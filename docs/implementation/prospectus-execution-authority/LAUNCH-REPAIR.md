# One bounded repair after the real launch probe

The first admitted `native-cohort` attempt wrote a job and initial heartbeat,
but no result. Its launch command returned before the work completed. The
heartbeat remained at zero elapsed time after 44 seconds, and a later resume
found no matching process. The controller retained an INTERRUPT event and
selected independent Portuguese source work rather than claiming success.

This is an execution-environment failure of our detached launch assumption,
not a failure of the OCR cohort or an upstream package. PID 8 was local to the
tool's process namespace; another tool invocation cannot safely identify that
worker from PID alone. The first attempt and its evidence remain unchanged.

Reviewed repair: keep the launching CLI alive while the registered child runs,
using the tool's one-second yield/session mechanism. Retain a POSIX attempt lock
across launch and execution so another process namespace can distinguish live
work from a dead attempt. Preserve PID/start/boot/namespace identity as additional
diagnostics. Session disconnection is handled by retained outputs and the live
attempt lock; do not launch a replacement while that lock is held.

The acceptance criteria, original obligations and two-admission lineage budget
stay unchanged. This is the one bounded infrastructure repair authorized by the
implementation plan. Test same-task refusal across process namespaces, interrupted
launch recovery, and a real CLI worker completing under a yielded tool session.
The second real attempt must produce independently validated source evidence and
select the interface consumer. If it fails again, preserve that result and
continue independent substantive work; do not rename/reset the repair budget.

The original shadow receipt comparison still establishes unchanged product
bindings. The changed controller method requires fresh focused checks, not a
rerun of the product ladder. Update the cutover verdict only after the actual
cohort and interface transitions pass. No package install or permission change
is needed for the repaired execution form.
