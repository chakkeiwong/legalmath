# Admission-lock refusal before the first stage

The first invocation of `timeout 55 .venv/bin/python -m
scripts.prospectus_2010_eps_cash prepare` exited1 at
`Authority(ROOT).lock()` with `BlockingIOError: [Errno 11] Resource temporarily
unavailable`. The admission command's tool session91911 was still running.
The agent incorrectly scheduled the dependent command before inspecting the
poll result for actual exit. No worker bindings, stage start, stage result,
renderer or analysis ran; the attempt has no `stages/*/started.json` or
`stages/*/result.json` after this refusal.

Session91911 was subsequently polled to actual exit0 and confirmed admission007.
The changed prerequisite is completed admission and release of its lock. The
first actual prepare stage can now run; no consumed stage is being repeated and
no admission is reset. This failed command remains part of the execution record.
From here, dependent launches follow a separate tool-result inspection confirming
exit, never an assumed exit within a multi-call execution cell. Registered
stage retries remain prohibited. This was an agent scheduling error, not a
source problem or a defect in the financial packages.
