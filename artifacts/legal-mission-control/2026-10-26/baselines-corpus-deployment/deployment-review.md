# Deployment review

26 October 2026, Hong Kong. Local deployment review passed; external execution
remains held. The source baseline is the dirty worktree recorded in baseline.json,
not HEAD. The original hardened candidate and earlier rejected candidate remain
immutable. The installed projection includes the hardened candidate plus five
deployment-support files/changes: outer program/state validation, mission revision
validation, central provider reservation hold, deployment helper, and its tests.
The live-route selector also directs the repaired profiles to a fresh directory.

The first staged suite had 143 passes and two failures caused by mixed import
roots: one handler looked for evidence in the temporary tree, while another test
loaded the unrepaired live route. The runner now fixes the scripts package path,
uses the staged implementation and explicitly supplies the real retained-evidence
root. The final staged suite passes all 145 tests. These harness failures and
their receipt remain available; no product defect or legal decision was hidden.

The transaction supports new and existing files, checks all inputs before writing,
and refuses concurrent third-party edits. It retains original bytes and has a
recoverable write-ahead journal. A machine crash between individual file renames
requires the same checked transaction to roll forward; this is not a filesystem
transaction across every file. Both registered worker locks, master execution,
mission, state, service, ledger and dispatch locks protect the installation.

All task states, attempts, limits, charges, service checkpoints and the deadline
are unchanged in the staged projection. The held Gatecoin BM25 row remains a
paused reservation, not evidence that its supervisor is alive. The terminal
handover records the dead supervisor and zero RESERVED dispatch rows. Live
activation is refused at the central campaign-reservation boundary, including
when a caller bypasses the usual master route. The service-predecessor chain is
carried through the exact archived prior binding.

The strongest alternative explanation for a successful deployment is that only
the tests changed while production imports or registered hashes stayed stale.
The staged authority check, exact-byte installed check, installed tests and mission
refresh are the required answer to that risk. No call or new legal assessment is
authorized by these checks. Source attribution still cannot establish applicability
or later treatment. P14 target reassessment and full fixed-answer source-use
reviews remain substantive work.

| Decision | Primary criterion | Veto status | Uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Stage repair | 145 tests pass with explicit candidate imports | Corruption and history mutation controls reject | Full registered history still needs validation | Validate and install exact staged files | Legal acceptance |
| Preserve failed owners | All state rows and spent attempts identical | No reopening or allowance reset permitted | Finite follow-up allocation not authorized | Retain checkpoint and request concrete authority if live continuation is wanted | Run complete |
| Hold live activation | Central reserve rejects before charge | Open circuit and exhausted 288 replacements retained | Provider availability after renewed authority | Separate reviewed continuation | Local test success predicts live model quality |
