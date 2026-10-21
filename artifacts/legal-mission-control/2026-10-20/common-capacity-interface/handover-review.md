# Reviewed handover after retained capacity implementation

The old live supervisor remains alive, processing local failures with repeated
nested history validation. No provider charge has been added since charge 3485.
Adoption is blocked by the old wrapper, whose remaining live owners cannot use
the reviewed capacity interface. The engineering objective is to settle the old
live child safely and let its unchanged wrapper record its actual exit and run
the remaining local commands. The sealed capacity implementation and its 174-test
evidence remain unchanged.

One bounded action is proposed. Authenticate the fixed wrapper and child using
PID plus kernel start identity. Acquire mission.execution.lock followed by
execution-state.lock, nonblocking. Under both locks require zero RUNNING master
owners, zero RESERVED model/native operations, the exact old program, exact live
argv and parent, and no child subprocess. Persist the observation and signal
only that child with SIGTERM. Confirm its exit; never kill the wrapper or invent
its result. The wrapper then records the actual nonzero command exit and performs
its existing run, refresh and verify commands. The already armed capacity deploy
still requires the authentic four-command wrapper result before adoption.

Dependencies: safe quiescent observation requires existing node completion;
wrapper settlement requires child exit; reviewed adoption requires wrapper
settlement. Staging evidence and read-only checks are independent. This action
adds no attempts or model allowance, changes no master task state, and does not
extend the existing live deadline. Timeout is 1800 seconds; failure to find a
safe boundary leaves the old worker alone. A changed identity, active reservation,
child process, changed program or failed signal is a veto.

Skeptical audit: PASS for this narrow handover. A single unlocked observation
would race execution.start; the state lock prevents the next reservation. The
mission lock prevents interrupting an in-process mission commit, while checking
for descendants excludes its refresh subprocess. A RUNNING owner is refused
even if its provider is idle. SIGTERM is acceptable only at this authenticated
idle boundary. The old supervisor lock remains held until the child exits and
the new deploy additionally waits for the wrapper. No production implementation
is edited underneath either process. Local guard tests are engineering evidence
only; the actual handover receipt is required for success.

Race review correction: after locking and finding no owner/reservation, briefly
stop the authenticated child through a kernel pidfd before checking its command,
parent and descendants. This prevents a refresh subprocess from being launched
between inspection and handover. Any refused inspection resumes the child in a
finally callback. Successful handover sends TERM and CONT to that same pidfd.
The callback resumes before the locks are released, including exceptional paths.
Four deterministic refusal-guard tests pass; the sealed deployment manifest
remains unchanged at bd5fb4d10ef7ad9d94ae158fe22cee79c9ed47a25081d28cacc4ce9df4eb037c.

The first execution found zero active owners and reservations but stopped before
signalling: the project Python 3.11 build lacks `os.pidfd_open`. The system
Python 3.10 exposes both required pidfd APIs. The fixed helper now re-executes
its same absolute script under `/usr/bin/python3` for that compatibility case;
no arbitrary command, target or argument is accepted. This changes neither
authorization scope nor process safety conditions. The failed attempt is not
a master owner attempt and consumed no provider call.

The compatibility retry also refused and resumed the old process. Transient
child subprocesses now cause the same bounded wait as a busy lock, with exact
observations retained; command, parent and identity mismatches remain hard
refusals. A refresh child must settle before any TERM signal.
