# One execution authority for the prospectus program

Status: admitted for implementation after the detailed audit below. This plan
does not change existing receipt bindings, approved
scope, sealed evidence or the separate legal-interpretation mission.

## The problem the authority must solve

The current closure controller selects the next stale R0–R8 validation phase.
When all receipts are current, it points to `NEXT-PROGRAM.md`; it does not select
the substantive work needed to close the remaining capabilities. Its
`program_complete` result is hardcoded false. The geometry runner correctly
finishes its own bounded package, but cannot govern all prospectus delivery.

The current gap register contains 20 gaps, five external requirements and six
residual-scope entries. All 20 gaps retain remaining scope or specified missing
repairs/inputs. The current prose summary does not replace that full inventory:
BASF source/agent authority, financial conventions, automatic relations and
package dispositions must remain visible alongside OCR. E04 (ACTUS) and E05
(FINOS CDM) currently have empty `affects` lists; the migration must explicitly
account for them rather than silently lose them. Their mandatory/deferred scope
must follow the retained reviewed decisions, not a new assumption.

The intended result is one authority that selects authorized work, retains
results and failures, refreshes dependencies and computes delivery status from
substantive evidence. Existing executables remain workers and validators. The
authority must not mistake a validation pass for completion of its parent
obligation or attempt to automate the legal judgment of an independent reader.

## Authoritative records and entry point

Use a prospectus-only directory,
`docs/implementation/prospectus-execution-authority/`, with these roles:

| Record | Role |
| --- | --- |
| `program.json` plus immutable reviewed revisions | Sole active specification of scope, obligations, dependencies, task criteria, permitted handlers and cumulative resource bounds |
| `history/` and referenced immutable attempts | Accepted events: admission, start, result, verification, repair, interruption, scope revision and next-task reason |
| `state.json` | Rebuildable projection of specification and accepted evidence; never a manually edited source of PASS decisions |
| Generated status, reset and next-work documents | Human views of the same state, carrying its revision/hash; they cannot override it |

The single entry point is proposed as
`.venv/bin/python -m scripts.prospectus_control`. It must pin this worktree's
source, since the editable environment can otherwise import main's code.
Commands are `check`, `status`, `admit`, `run`, `record`, `refresh` and `resume`.
These names are proposed interfaces, not commands that exist today.

`check` validates schema, obligation coverage, cycles, permitted handlers and
evidence references. `status` is read-only. `admit` selects and freezes the next
ready task and its dossier. `run` dispatches a registered worker within that
admission. `record` retains externally produced or agent-produced evidence,
then invokes its validator; it cannot accept an arbitrary `done=true`.
`refresh` recomputes status and next-task selection with a recorded reason.
`resume` reconciles a saved attempt with its actual process and output state.

Use a single writer lock, atomic state replacement and an append-only event
history. Replaying the reviewed specification and accepted events must recover
the same state. Program revisions are explicit events. Criteria cannot be
weakened by an ordinary refresh or an unsuccessful candidate.

## What every obligation and task must contain

Each original obligation keeps a stable ID, source location/hash and declared
scope. One obligation may require several tasks; completing a task closes only
the evidence requirements it actually satisfies. Every open obligation must
map to a concrete task, an explicit external dependency, or a reviewed scope
disposition. Mandatory omissions make `check` fail.

Each task needs its parent obligations, intended product behavior, dependency
IDs, required dossier, executor kind, fixed handler ID and validated arguments,
input/code/environment bindings, comparison baseline, required result evidence,
acceptance validator, promotion vetoes, continuation vetoes, repair triggers,
resource bounds and downstream consumers. Add a next-action reason, external
input/owner where applicable, and the reviewer/independence requirements for
human evidence. Explanatory metrics stay separate from closing criteria.

Executor kinds must distinguish deterministic local commands, agent work
(implementation, source analysis, literature or image review), and external
human inputs. The authority governs admission and acceptance for each; a Python
runner does not itself perform every reasoning or legal-review task. Codex
continues an admitted agent task using its dossier and existing permissions.

A handler registry in code owns commands. JSON must not contain executable
shell strings or arbitrary imports. Existing closure, geometry, source and
runtime tools are invoked through narrow adapters. An admission grants no new
filesystem, network, installation, GPU, external-messaging or approval rights.

## Execution and repair policy

The ordinary transition is admission, execution, retained result, verification,
obligation update, refresh and the next ready task. A completed checkpoint is
not a reason to end execution when independent authorized work is ready.

Task execution states distinguish READY, RUNNING, RESULT_RECORDED,
REPAIR_REQUIRED, WAITING_EXTERNAL, INVALIDATED and COMPLETE. Readiness is derived
from dependencies, criteria and bounds, not supplied as an unchecked flag.
Capability verdicts remain a separate dimension: unsupported, partial,
assisted-validated, automatically validated or explicitly outside the agreed
scope. A reviewed input cannot be credited as automatic extraction.

A valid candidate failure blocks its promotion and triggers the predeclared
repair. It does not cancel another ready task or a later task designed to
repair that failure. A corrupt comparator, invalid environment or changing
method invalidates the affected run and its dependents. Independent tasks
continue. Unchanged failed inputs cannot be retried as a fresh repair.

Repair and infrastructure-detour budgets attach to the original obligation,
not a phase name or new directory. Each detour needs a reproduced blocker, a
bounded attempt and an explicit return to the substantive task. Budget or
scope revisions require a recorded skeptical review; ask the user when the
revision changes project direction, cost or authorization. Routine authorized
implementation repairs do not create a new approval checkpoint.

WAITING_EXTERNAL records exactly what is missing and what would satisfy it.
Missing client facts may leave a conditional analysis possible. Missing genuine
independent readings blocks that acceptance decision, while local preparation
and other ready work continue. Package deferrals remain visible and do not
count as completed integrations.

## Completion and scope

Compute separate decisions for engineering delivery, finite assisted legal
validation and each declared automatic capability. The initial financial scope
is the existing reviewed fixed-rate schedule/accrual/payable-amount contract,
with existing AT1 conditional regressions preserved. Do not invent a requirement
for unlimited automatic legal interpretation, and do not close BASF by showing
that a different instrument works.

For an agreed delivery scope, completion requires every mandatory obligation's
substantive predicates to pass with current, valid evidence; no applicable
promotion veto; all required installed/downstream consumers; and required
source or independent-review inputs. Empty task lists, exhausted ready work,
test totals, invocation counts and current receipts are insufficient. Overall
completion combines the decisions required by that scope. Removing an
obligation changes scope; it does not repair the obligation.

The checker validates consistency and evidence identity. It does not prove
source authenticity, human qualifications, independence or legal truth merely
because those fields are populated. Those conclusions need the specified
substantive evidence and review.

## Crash recovery and short tool calls

Freeze attempt identity, task/program revision, command, input/method hashes,
PID plus process-start identity, output paths, heartbeat and resource limits
before launch. Store full output in files and return small job/status records.
Use one-second tool yields for long workers, bounded polling and regular
progress messages. A stream interruption does not authorize a duplicate job.

Resume by checking process identity and retained outputs. Reattach to a live
matching worker; validate a completed result; record an interrupted attempt if
the process died without valid output. Resume partial work only when its
handler specifies a checked resumable boundary. Never overwrite an old attempt
or infer success from an exit code without the required artifacts.

## Ordered implementation and cutover

1. **Freeze and reconcile the entire obligation inventory.** Map all G01–G20,
   E01–E05, residual scopes, BASF/source obligations, fourteen onward dependencies
   and package dispositions to concrete tasks. Preserve original IDs, scope and
   evidence hashes. Produce a migration report listing unmapped or conflicting
   obligations; those must be resolved before cutover. Keep completed repair
   packages as evidence, not new work to repeat.
2. **Implement the smallest authority.** Add the schema, immutable events,
   dependency/readiness calculation, substantive completion rules, lock and
   read-only status. Keep it separate from product source so introducing
   governance alone does not fabricate a need to repeat all product tests.
3. **Connect existing workers and agent dossiers.** Add narrow adapters and
   criteria validators for the actual remaining tasks. Reuse existing R0–R8
   receipts when current. Preserve their conservative invalidation until any
   finer dependency mapping has its own evidence. Do not merely wrap pytest
   and describe all remaining source/review tasks as executable.
4. **Prove recovery and misleading-completion cases.** Run focused fault and
   acceptance tests below, preserving their artifacts. Allow one bounded repair
   of the authority if a reproduced failure blocks the next substantive task;
   further detours require a reviewed revision, not a renamed program.
5. **Shadow-check the current state.** With no product re-execution, require the
   authority to report the present engineering receipts as current, all open
   obligations as open, independent acceptance as pending, and a concrete ready
   substantive task. Reconcile differences against evidence before cutover.
6. **Cut over and execute real work.** Add a prospectus-specific instruction in
   the applicable worktree instructions naming this sole selection authority.
   Keep the separate legal mission untouched. Generate current reset/next-work
   views from it and mark historical runners as evidence or delegated workers.
   Admit and execute the next actual source/native coverage package, retain its
   result, refresh and continue to the next ready task. This real task transition
   is required to establish that the authority works beyond synthetic checks.

## Acceptance tests for the authority

- All nine validation phases PASS while a mandatory source/native task is
  pending: delivery remains incomplete and the ready substantive task is selected.
- A missing human review does not block independent OCR/source/runtime work;
  supplied or previously exposed readings cannot satisfy independent acceptance.
- Candidate failure selects its changed, predeclared repair or other ready work;
  corruption of the shared baseline invalidates dependent experiments.
- Missing G/E/residual coverage, including an unlinked E04/E05, refuses cutover.
- Stale methods, altered artifacts, missing downstream evidence and a changed
  running specification cannot yield accepted completion.
- Repeated refresh is idempotent; replay rebuilds the same state; concurrent
  dispatch cannot start the same task twice; crash/resume cannot duplicate a job.
- Renaming a repair or creating another directory does not reset its budget.
- A historical replay cannot become evidence of current installed behavior.
- A real task produces the required downstream evidence and selects its next
  task without a manual checkpoint; changed scope cannot masquerade as closure.

## Skeptical audit of this design

The baseline is the retained closure ledger and current validated product,
not a historical runner whose checks are easier. The main risk is replacing
missing substantive work with another elaborate controller. The inventory,
shadow check and real-task cutover test directly expose that risk. The design
keeps the dispatcher small, reuses workers and bounds infrastructure detours.

Another risk is that software flags appear to certify legal truth. Separate
substantive evidence predicates, actual human requirements and explicit scope
prevent that inference; they cannot manufacture missing facts. A third risk is
stale manual documents competing with executable state. Generated views carry
their revision and cannot control admission. Historical sealed evidence remains
unchanged and is never regenerated to fit the new authority.

Audit verdict: proceed with the staged implementation after the obligation
inventory is reconciled. This design establishes no completed authority,
product improvement or legal acceptance by itself. Successful implementation
must pass the adverse controls and perform an actual substantive transition.

## Implementation admission: audit findings and corrections

Code and source inspection confirmed the baseline: `closure_program._refresh`
selects stale validation receipts, all G01–G20 retain unresolved scope, the
external register has E01–E05, and the BASF next-source program has five distinct
packages. Fourteen BES dependency rows and nine package dispositions must also
survive migration. These entries overlap; their count is not a progress metric.

The audit found four material omissions in the initial design. First, a generic
agent-written PASS record could turn an unsupported assertion into completion.
The implementation must require a reviewed acceptance specification and
validate named, hashed downstream evidence. Independent legal evidence remains
subject to the existing real-reader rules. Tasks without an implemented or
reviewed acceptance validator can retain work but cannot silently close.
Second, a repair must depend on the failed attempt, not require its parent task
to pass. Repairs use a named failure trigger and the original budget lineage.
Third, immutable successful evidence can become stale: status must recheck the
admitted input/method hashes and propagate invalidation through dependencies.
Fourth, a PID alone is insufficient for recovery. Process start identity,
attempt binding and a result written atomically before verification are needed.

No scope is removed during migration. General legal completeness and unlimited
solver capacity remain explicit limitations rather than impossible new delivery
requirements. ACTUS/CDM remain separately visible evaluations with their original
prerequisites; they are not reclassified as integrated or fundamentally rejected.
The original ledger and completed packages will be frozen as migration evidence.
The new authority's current views will be distinct from those historical records.

Implementation evidence contract: compare against the current retained ledger,
the existing nine receipt identities and the already reviewed native follow-up
plan. Pass requires complete migration coverage, tested refusal of false/stale
completion, deterministic recovery, and actual substantive worker output followed
by the correct next-task admission. Test counts, task counts and generated prose
are explanatory only. Corrupt source bindings, duplicate execution, scope loss
or a false acceptance verdict veto cutover. Existing successful product methods
must remain current; no whole-product rerun is justified by this new controller.

Resource choices: use standard-library state/locking/process facilities, local
JSON records and existing workers; no new dependency or remote call is required.
These are maintainability choices, not scientific defaults. Focused verification
is bounded to 120 seconds per invocation, with one-second tool yields. Worker
timeouts retain their reviewed per-task limits. No native/GPU package imports
are required for governance; PDF inspection explicitly hides GPUs. Retain
implementation audit, migration, tests, shadow comparison and cutover results
under `docs/implementation/prospectus-execution-authority/`. The first substantive
task freezes source-bound native/layout coverage; its successor consumes that
cohort to define the native candidate interfaces. Neither task closes the native
repair or legal acceptance. Audit verdict: proceed under these corrected rules.
