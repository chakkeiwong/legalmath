# Admitted consolidated current recovery

This is revision-49 recovery attempt-007, the seventh cumulative admission.
Follow docs/plans/prospectus-consolidated-recovery-2026-10-14.md. Its skeptical
audit, evidence contract, assumptions, limits and stop conditions apply before
execution. All ten changed production methods are frozen; no production repair
is planned here. Historical evidence and admission limits remain intact.

The runner/probe/finalizer come from immutable attempt-005. Case definitions,
source/model inputs, state order, full products and specific rejection checks
are unchanged. The probe is byte-identical. Runner changes are confined to the
current plan identity, freezing both plans and the tests runner, an exclusive
per-attempt lock and persistent exclusive invocation starts/success/failure
markers before any initialization or state mutation. Finalization also has a
persistent exclusive start and takes the same lock. Never restart a started
state or finalizer. Inspect the retained session first after an interruption.

Run initialization and each of the original eight states separately with the
documented 120-second outer bound and 70-second child bound. Poll each returned
session before its successor. tests-command.json and tests-result.json retain
the focused check command and elapsed time; all other command/session evidence
is retained before sealing. Pinned worktree src and CPU-only policy apply.

Specific deliberately invalid model/image/interval inputs must be refused and
then restored. Any unexpected discrepancy, changed identity, timeout, missing
diagnostic or storage excess stops this sequence for diagnosis. Do not confuse
the deliberate rejections with a continuation veto. Exact restoration and
original Portuguese image/unit equality are required. Counts and time are
explanatory. Shared-code agreement cannot establish independent semantics.

The finalizer validates all controls and copies frozen methods. It links only
byte-identical files inside this attempt, verifies every byte/hash afterwards,
discloses logical/unique/physical size and requires physical size below 60 MB.
An ordinary checkout may expand hard links. No historical file is linked or
edited. Seal once, record partial evidence, refresh, then separately review the
eighth cumulative admission for unchanged recovery-sequence.v1 acceptance.

No legal, automatic, confinement, portability or whole-program completion claim
follows. Continue the reviewed authority audit and substantive routes after
recording; do not stop merely because the finite package passed.
