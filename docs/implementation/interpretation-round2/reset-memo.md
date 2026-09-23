# Reset memo — 23 September 2026

The implementation is in `src/legalmath/interpretation/search`. Read
`execution-report.md`, `operator-guide.md` and `next-phase-plan.md` in this
directory before continuing. The source-driven generator, bounded BFS/UCT tree,
formal/Java checks, output repairs, reports and source-first annotation tools
are implemented. P12 attempt 01 passed 310 tests, including 78 search tests,
and replayed all 45 recorded P8 pairs. P9 retains the two-scheduler depth-two
descent check; P7's frozen-output replay and P8's multi-round live pilot also
passed. No production or legal-accuracy claim is supported.

P10–P12 add `alignment.py` and `alignment_review.py`. Exact metadata aliases
permit a total symbol rename; changed definitions require explicit assumptions
and always remain conditional. Original Java classes replay differing witnesses
using separately named snapshots. Five API routes store proposals, analyses and
distinct reviewer decisions without modifying completed investigations or release
authority. Source invalidation, stale hashes, role forgery, concurrent rejection
and archive portability are tested. Read `fact-alignment-result.md` for the
worked cases, results and limitations.

P12's frozen replay found zero additional exact-alias matches and retained all
33 incomparable pairs. Readable and JSON review packets are under
`artifacts/interpretation/round2/P12/attempt-01/replay/{24EC50,23EC46}/review-packets/`.
A preselected hypothetical 24EC50 mapping found no difference in 36 finite
probes; it is unapproved and not a proof of equivalence. No actual human mapping
review was performed. Candidate-exposed packets are not blind reference labels.

The P12 audit also reproduced a real inherited bug: after an unresolved solver
response, generic probes could ignore a caller-declared domain and report a
difference outside it. Three failing regressions are retained in
`domain-fallback-before.xml`; the guard then passed all 15 comparator tests in
`domain-fallback-after.xml`. Caller-declared UNKNOWN/UNSUPPORTED comparisons now
have no unconstrained fallback. The full P12 regression covers the repair.

P5 has four retained non-passing attempts. Attempt 03 produced actual readings
for 24EC50, but its refinement cited nonexistent `u24` and was rejected. The
repair passed locally and attempt 05 passed on both sources, including an
actual rejected-and-repaired inexact quotation on 23EC46. Attempt 04 was an
allowance preflight: no model call was made because the then-remaining four
calls could not fund a six-call complete case.

Review of attempt 05 found a Boolean interaction missed by the 128 finite
probes. P7 changed comparisons with matching Boolean fact definitions to use
the complete declared `{T,F,U}` domain and replayed all saved pairs. No numeric
or date bounds are invented, and incompatible fact meanings remain incomparable.
The old histories are unchanged. P7's first attempt failed only in its manifest
parser; its repair and successful retry are retained.

The live ledger is `artifacts/interpretation/round2/live-allowance.json`: 41
reservations, authorized maximum 100, leaving 59. P8 used nine calls for each
retained circular and left both reports blocked with unresolved frontiers. P9
and P10–P12 used no live calls. The source packets, raw responses, failed actions, reports
and Java builds are under `artifacts/interpretation/round2/P8/attempt-01/`.

The first two P6 supervisor attempts stalled only in the tested sandboxed full
supervisor context. Smaller nested probes and a direct full suite passed; the
same fixed full supervisor passed in the trusted context. The exact cause is
unresolved. Use the narrow absolute runner command and trusted execution for
the API regression and live phases. Keep the earlier failed manifests and withdrawn transient
diagnosis.

No commit or push was made for this increment. Numerous unrelated monograph and
paper-library changes predated this task and remain untouched. The current
acceptance manifest records the base commit and actual working-tree hashes.
`artifacts/interpretation/round2/fact-alignment-evidence-check.json` is the current
check of 191 tested inputs, 158 frozen baseline files and accepted phase
artifacts. `final-evidence-check.json` remains the historical P9 record. The
OpenAPI export was refreshed after P12 without changing acceptance inputs;
all old route definitions remain present and unchanged.

Priority correction on 23 September: the user treats external legal consultancy
(their estimate: 0.5–1 million, currency unspecified) as a last resort and asks
for continuing automated detection of future interpretation errors. Read
`automation-gap-audit.md` and `automation-next-phase-plan.md`. Many mechanisms
in the monograph are not implemented: structured legal arguments and critical
questions, case-based theory constructors, original-source semantic checking,
dependency acquisition integrated with search, and continuous challenge/replay.
P0–P12 completion must not be called completion of that larger design.

Build the missing source-facing checks and common-omission challenges before
commissioning external review. Use public authoritative examples, frozen
controlled challenges and, only if later authorized, existing internal decisions.
Actual legal accuracy still needs appropriate reference evidence, but absence
of a newly hired legal team does not block these engineering phases. Preserve
release controls and uncertainty. The old plan is kept as
`next-phase-plan-after-p12.md`; current A1–A6 are proposed deliverables, not
accepted executable phases. This documentation audit used no model calls and
did not change P12-tested source inputs.
