# Grouped approval for the integration master

The master program is `docs/plans/legal-integration-master-2026-10-13.md`.
The concrete method, resource review and independent dependencies are in
`integration-master-execution-review.md`. The exact hash-bound request is
`artifacts/legal-mission-control/2026-10-13/master/approval-proposal.json`.

One approval covers:

1. Install `legalmath-integration-master.rules` in the protected user rules
   directory. Rules name fixed master actions; no generic Python or shell rule.
2. Install the missing `libreoffice-writer` component and ten dependencies
   (16.0 MB download; 59.5 MB installed), using noninteractive sudo if available.
   Failure remains local to document rendering and does not cancel product work.
3. Start a **maximum 8,100-call campaign over six days**, using
   **gpt-6.1-sol** through the currently configured **visioncoder** route and
   account. The route URL and all settings are in the proposal. No authoritative
   price schedule was inspected; this is a call/time ceiling, not a monetary cap.

The campaign covers four original questions, all original requirements, full
source acquisition, a baseline and six separate tool arms per question,
matched assessments, cross-question checks and a terminal substantive review.
It starts with eight source/reviewer canary calls. A failed canary blocks only
its dependent question. It re-budgets actual generated populations before
subsequent work, preserves failures, and resumes completed identical requests.
No extra service retry or repair is silently authorized. Capacity or quality
failures can leave a branch open; completion is not promised by the budget.

The exact grouped command is:

```
.venv-context/bin/python scripts/legal_integration_master.py approve-and-run
```

After approval, the exact resume command is:

```
.venv-context/bin/python scripts/legal_integration_master.py live
```

This separate approval is needed because the historical live grant has expired
and the rules directory/system package installation are outside ordinary
worktree edits. The requirement for a concrete fresh grant is in the completion
contract's “Before P” paragraph and the registered master's approval section.
Historical 41/400 calls and all earlier attempts remain untouched. The new grant
and ledger are separate. The grouped action must not be invoked on the strength
of old approvals alone.
