# Running and resuming the integration repair

Use the exact command form from the repository root:

```text
.venv/bin/python scripts/run_legal_integration_repair.py check
.venv/bin/python scripts/run_legal_integration_repair.py execute
.venv/bin/python scripts/run_legal_integration_repair.py status
.venv/bin/python scripts/run_legal_integration_repair.py verify
```

`execute` checks the reviewed source/plan identities, preserves completed phases,
refreshes the next-phase record and stops on invalid evidence. The only live
actions are the reviewed two perspectives in each arm, at most four reservations
against the unchanged 96-call/12-repair/24-hour program and unchanged 24-call arm
caps. Completed results are reused. An interrupted live phase is reported for
review; restarting does not silently redispatch it. No command accepts shell
code, custom paths, new limits, package downloads, alternate models or publication.

The local `allow.rules` and `policy-check.json` document matching. The narrow
wrapper prefix can be approved once in the execution approval UI. This session
cannot promise to bypass a separate managed approval reviewer. The protected
global rules file is not written by the runner. Avoid interpreter aliases,
shell substitutions, environment assignments and wrappers around these commands
when relying on the exact prefix match. The runner sets CPU-only execution itself.

For application use, `CompleteInvestigation(..., optional_tool_backend=backend)`
selects the optional checks. The installed-tool implementation is
`scripts.legal_integration_tools.ProductToolBackend`. The default product path
remains available; enabling the backend changes the method/revision identity.
Tool reports and backend identity are bound into the dossier. Unsupported
candidate profiles are retained explicitly, never converted to Boolean results.

The old G0–G4 live-source verifier is stale after these repairs by design. Use
this runner's `verify` for the preserved historical snapshots, predecessor
receipts, append-only budget history, current reviewed method and new results.
An old passing verification must not be represented as a review of repaired
source. No prior result has been rewritten to make the repaired program pass.
