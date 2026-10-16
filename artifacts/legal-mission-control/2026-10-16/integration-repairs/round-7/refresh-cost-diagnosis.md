# Why the refresh timeout recurs

This is a read-only code diagnosis during settlement of R10. It adds no repair,
task attempt, call allowance, service scope or changed implementation.

The full direct commands have already passed on settled inputs. Registration's
direct refresh took 375.75 seconds; binding's direct refresh took 386.76 seconds
and its independent master verification took 380.39 seconds. Their command
manifests are retained in this directory. These observations exceed the inherited
300-second wrapper timeout. A timeout therefore does not establish that evidence
validation failed, and it also cannot stand in for a successful validation.

The inspected call path explains repeated work:

1. `MasterExecution.sync_mission` in `scripts/legal_integration_master.py`
   updates the history, builds a summary, calls `control.validate`, saves the
   mission, and then starts a separate mission `refresh` process with a
   300-second timeout. The initial validation occurs before that child timer.
2. In `scripts/legal_mission_control.py`, `refresh` calls `status`, which calls
   `validate`. It then calls `admit` when applicable, which calls `validate`
   again. Each validation reconstructs the master summary through a new
   `MasterExecution` instance.
3. `Execution.__init__` calls `validate_program`. For the current repair,
   `validate_revision` in `scripts/legal_integration_repair_execution.py`
   authenticates frozen references and recursively validates the projected
   predecessor program under the historical-evidence mapping.
4. `verify` in `scripts/legal_mission_execution.py` reads and hashes the resolved
   reference on each invocation. The same retained history is revisited by
   successive validation calls and separate processes.

This establishes repeated complete-history validation, not a measured
per-function attribution of its cost. No profiler was run, and no asymptotic
complexity or guaranteed speedup is claimed. The observed deferral-to-timeout
interval can exceed five minutes because it includes validation before the
timed child. The running processes and successful direct checks distinguish
this from a new provider hang.

The current approved remedy remains exact direct refresh and verification on
unchanged settled inputs, followed by narrow timeout reconciliation under the
existing locks. It preserves full evidence checks and every failed event.

A future authorized performance repair should first measure one frozen actual
refresh, then remove duplicate validation within that operation while preserving
all graph, authority, source, result and historical-projection checks. Any reused
validation result needs an explicit input identity and mutation boundary; a
path-only or persistent unchecked cache is unsafe. Adverse checks must cover
changed bytes, changed predecessor mappings, changed task state and a concurrent
writer. A new timeout should follow actual runtime measurements. Raising the
timeout alone would reduce spurious timeouts but would leave the repeated work.
The existing ten-repair authorization is exhausted, so this note adopts none of
those changes.
