# Recovery and transport diagnostic review

The initial 92 tests passed on the initial runner. The first provider attempt
failed before turn start because the sandbox made the Codex state database
read-only. An explicit trusted successor attempt cleared that problem but
timed out after 180 seconds on a 40,754-byte request. Its only events are
thread.started and turn.started. No completed output was retained. The cause
of that timeout is not established. Two reservations remain consumed.

The v2 runner returned the initial test receipt after code had changed. That
was a cache defect: it was **not a fresh passing test run of v2**. It also used
the original attempt's journal while checking a repaired result, constructed
the wrong tool-report directory, and allowed a generic sandbox repair reason
to be reused for an unrelated failure. These are orchestration defects; no
successful legal result was produced or promoted through them.

The v3 change binds test receipts to all reviewed runner/test file hashes,
checks the selected repair's actual journal, retains and verifies prior failed
evidence, corrects tool-report lookup, and restricts the sandbox recovery to
its established error. An interrupted repair stays blocked. New tests cover
the changed method, selected attempt, foreign pointer and timeout controls.

Skeptical audit: PASS conditional on fresh tests. Do not run another unchanged
12-pair attempt after the timeout. The next fixed `diagnose` action uses at
most five additional reservations, all charged to the existing 14-call repair
allocation within 100. One tiny schema sentinel tests current route availability.
Only if it passes, both perspectives in each arm assess two retained source
claims against the first unformalized reading under its original satisfaction
question. The complete source packet remains unchanged. Stop this ladder at
the first failed dispatch or rejected/incomplete response. Preserve all logs.

A successful sentinel would show service response for that small request,
not reliability. Successful small assessments would establish applicability
on those two pairs, not completion of the 492-pair matrix or a justified batch
size for it. A failed sentinel is a continuation veto for dependent live
execution, while local verification and gap analysis proceed. If only the
large request fails, an independently reviewed size/representation remedy is
needed; reducing the pair count without revising the budget cannot complete
the original matrix. Model agreement remains descriptive and uncalibrated.

The original plan and v1/v2 reviews stay immutable. This supplement revises the
recovery procedure and adds one closed diagnostic command. It changes neither
the provider route nor the original deadline. The saved wrapper prefix already
permits the fixed actions; no further global allow-list edit is needed.
