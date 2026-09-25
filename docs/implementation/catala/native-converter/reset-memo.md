# Native converter continuation memo

User instruction: thoroughly review and execute the direct source-to-Catala
plan. Implementation and bounded development execution are complete. Read
`results.md`, then `README.md`, and `docs/plans/catala-direct-converter.md` before
continuing. This route is separate from the completed RuleIR-to-Catala adapter.

Worktree: `/home/chakwong/python/legalmath/.worktrees/catala`, branch
`feature/catala-adapter`; main's unrelated work was preserved. The only shared
main artifact changed was the explicitly named model-call ledger, under its
existing grant. Its authoritative path is
`/home/chakwong/python/legalmath/artifacts/interpretation/round7/live-allowance.json`.
Do not substitute the Catala checkout's stale copy of that ledger. Balance after
this work: 175/500; this task used 22 calls under an absolute ceiling of 177.
Do not interpret the unused global balance as permission to run a new large
study or reset this task's allowance.

`src/legalmath/catala/native` contains contracts, exact boundary/bridge, builder,
source generation/criticism and bounded repair, CLI, and SQLite development host.
The public commands are under `legalmath catala-convert`. Generic generation has
no fixture whitelist and never invokes RuleIR. Imported Catala modules are
explicitly unsupported in the version-1 builtin profile.

Evidence under `artifacts/catala/native-converter`:

- `run-01`: first controls and model calls; preserve its invalid acceptance-loop
  verdict and the exact executed sources. SUPPORTED reviews with positive
  findings were wrongly rejected, consuming eight unnecessary calls.
- `run-02`: corrected acceptance; reuses 11 exact saved completions and makes
  three fresh calls. Seven source tasks pass 43 exact cases. No heldout or
  comparative ranking claim.
- `hardening-01`: unchanged generated code rebound to explicit source-domain
  bounds where required. All 48 cases pass. Six compiled semantic mutants have
  independent witnesses; four forged execution records fail real replay.
- Broad regression: 242 pass before final bounds/probe additions. Final native
  suite: 28 pass. Wheel and CLI checks pass. Preserve the earlier failed
  exception-probe log as a corrected baseline error, not a compiler failure.

Do not rerun old frozen study commands with today's changed code and relax their
fingerprints. Old runs retain copied sources; new implementation changes require
new result directories. The native interpreter's decimal/money JSON is lossy:
verification compares exact expected values *inside Catala* and exports a Boolean.
Java reads exact numerators/denominators. Java trace instrumentation excludes copy
constructors and observes scope outputs only. Identical literal exceptions can
coalesce under pinned native semantics; RuleIR multiplicity is different.

Remaining research work: independently adjudicated real-source tasks, complete
rival-reading investigation, representative heldout splits, comparable paired
budgets, quality/cost uncertainty and human review studies. Remaining deployment
work: institutional authentication/approvals, production integration, imported
stdlib profile and additional types. These are not established by current tests.
