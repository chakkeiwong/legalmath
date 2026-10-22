# Prospectus Git checkpoint, 22 October 2026

User requested a commit of the prospectus branch and merge into main.
The checkpoint preserves the current source, tests, fixtures, plans, authority
program, history, dossiers and compact decision records. Complete execution
outputs, duplicated worktree snapshots and local runtime/source caches remain
in this original worktree. This commit is not a complete execution backup and
does not establish legal or whole-program acceptance.

Before staging, the local authority check passed at revision 444. Status reported
no next task and no running task; admission refused because no task is ready.
Those are execution-state observations, not a reason to drop the remaining work.
No substantive prospectus task was dispatched for this Git operation.

Engineering checks: 366 changed-area tests passed in 55.03 seconds using the
context environment with this worktree's source. A broader CPU-only run using
the development environment and explicit parent/child source paths stopped at
five failures after 2,378 passes (235.18 seconds). Its saved log and JUnit report
list the exact failures: frozen registration/dispatch expectations and OCR method
identity checks, plus two annual-group tests missing the v7 fixture. The suite
did not pass. Initial attempts using the wrong checkout/environment are not
validation evidence.

The staged snapshot is the commit boundary because additional work is still
arriving in this worktree. Later changes stay local. Source-bound fixture and
historical whitespace is preserved. No tests or validity checks are relaxed to
make this checkpoint appear complete.

The merge must preserve main's legal-interpretation instructions and this
branch's prospectus-specific authority. A separate integration worktree keeps
the active legal worker's bound source intact.
