# Package integration audit reset

Planning continuation, 9 October 2026: the [closure plan](../../plans/prospectus-integration-closure-2026-10-08.md)
and [planning reset](../prospectus-integration-closure/RESET.md) now define the
repair order and closing checks. This is a proposed program; production fixes
have not started. The audit observations and retained probes below are unchanged.

Current task: the user stepped back from execution to request a thorough trace
of current package integration gaps. The audit is complete against source commit
`03883b5f7d914a2678ac4f472e688c9fc1c60006`, feature worktree
`/home/chakwong/python/legalmath/.worktrees/bond-gap-closure`, branch
`feature/prospectus-evidence-master`.

Read [REPORT.md](REPORT.md) before continuing the old source-only next program.
It identifies twenty engineering findings/coverage gaps, plus separate ACTUS/CDM
prerequisites and surveyed alternatives. Seven groups of synthetic probes,
two source-boundary checks and a Cassis CLI format comparison are preserved in
`probe-results.json`, `boundary-results.json` and `codec-results.json`.
`evidence-index.json` records relevant file hashes and import sites.

Key new reproductions: malformed OCR pages accepted; an excluded source can
activate a Z3 premise; AST reference IDs cannot resolve across the raw/assembled
boundary; invalid evaluation source offsets are scored; standalone XMI admission
fails without a type-system argument; solver evidence is dropped by the service;
law/construction retain the twelve-fact limit. Native read tracking is explicitly
cooperative and standalone frozen replay differs from current-input validation.

Docling and INCEpTION have working trial adapters but missing service consumers.
QuantLib's comparator role is valid; source-selected instrument terms still need
their own admission. The BASF profile keeps body text UNKNOWN and cannot be made
operative by merely supplying clause labels. Independent human review is missing,
and its export-to-score integration also needs code work.

Only this audit directory, its plan and reset pointers were changed. No package
installation, network call, production fix, historical verifier, live server,
Git commit/merge/push, or LaTeX change was made. Historical trial evidence remains
unchanged. Do not rerun the three diagnostic scripts into their existing outputs;
they deliberately refuse overwriting. Copy them into a separately recorded new
attempt when comparing a future repair.

Suggested next work is an explicitly reviewed repair plan around the shared
admission boundaries and missing consumers, using the concrete closing checks in
the report. The latest retained regression receipt remains adoption attempt-007
(153 passing tests); this audit did not rerun it or treat it as coverage of the
newly reproduced defects. Preserve main's unrelated work and existing stashes.
Never run `scripts.verify_prospectus_repairs`.

Validation at audit completion: all 76 indexed source/evidence hashes matched, all 67 local
Markdown links and their numeric line anchors resolve, all four retained JSON
files parse, and all four probe/inventory scripts parse. Recorded probe hashes
match their scripts. Tracked and newly written files have no trailing whitespace;
`git diff --check` passed. At that checkpoint only audit files and two reset
pointers had changed; the planning continuation above adds the closure documents.
