# B0 interpretation reliability

B0 adds corruption diagnostics and complete-matrix capacity checks to the
existing `interpretation-assurance` command. The calling interface is unchanged.
Use a new investigation directory: method and settings hashes deliberately
invalidate reuse of an earlier method's results. The previous A7 artifacts remain
historical evidence and are never rewritten.

## Candidate presentation

Read `candidate-presentation.json` when presenting candidate analysis. Each entry
binds its `reading_hash` to the original reading. `NO_PATTERN_DETECTED` provides
the proposal; `WITHHELD_CORRUPT_PROSE` supplies a null proposal and requires looking
at `prose-quality.json` and the original `candidates.json` or search frontier.
Raw originals and their compiled programs remain available for investigation.

The detector scans subject, statement, distinction, candidate assumptions and
questions, and fact meanings and units. It looks for known self-repair chatter,
output instructions and placeholder-only fields. Findings include exact field
paths, field hashes and Unicode character offsets. At most 64 findings per
reading are displayed, with total counts and a truncation flag. Source evidence
fields are excluded; a quoted passage in a narrative field is exempt only when
it is an exact, cited quotation from the retained packet. Quotation marks alone
cannot exempt invented text. Ordinary uncertainty and non-English text are not
corruption criteria.

`report.json` identifies the diagnostic and presentation files and flags affected
candidates at a separate `PRESENTATION` stage. This check includes deferred
frontier readings, even when the assurance candidate limit prevents checking
their executable meaning. It does not give those readings additional source
support. A quality failure leaves the report unresolved; it does not change the
candidate, prune the interpretation tree, or count as a source contradiction.
`execution_complete` can be true while the presentation remains withheld: it
describes completion of the checks, not successful interpretation.

An automatic prose rewrite is not performed. Changing a proposed interpretation
requires a successor reading and the usual source/Java checks. A passing pattern
check does not establish coherence or legal accuracy, and other model prose
(such as inventory rationales) is outside this detector's scope.

## Fidelity capacity and retained partial results

The response schema is still `Fidelity`, with at most 1,000 checks and 30 concerns.
The internal `FidelityAggregate` validates the union, applying the same exact-pair,
source-quote, representation-quote and failing-stage rules. Concerns are retained
in order, including repeated concerns. A deduplicated residual-question list does
not replace this full evidence record.

The configurable settings are bounded by these profile ceilings:

| Setting | Default and maximum | Meaning |
| --- | --- | --- |
| `max_total_fidelity_pairs` | 4,096 | All selected claim/candidate pairs, including cached and unsupported programs |
| `max_total_fidelity_concerns` | 1,080 | All concerns in one investigation matrix |
| `max_total_fidelity_bytes` | 2,097,152 | Aggregate bytes; admission uses a conservative upper bound |
| `max_fidelity_pairs_per_call` | Default 32; maximum 64 | Requested pairs in each model batch; unchanged |

The engine first checks the complete matrix size. It then retains cache/encoder
parts and checks their byte consumption. Before any fidelity dispatch it checks
the pending batch count, at most 30 concerns per batch, and the maximum response
bytes per batch. It reserves one remaining action for criticism. It does not
reserve every possible output repair at this admission step: a later exhausted
repair or deadline still returns incomplete execution. Existing semantic-repair
scheduling retains its separate conservative call reservation.

Capacity errors can occur even if a model might have returned a shorter answer.
The report records the required bound, configured maximum and constraint. Adjust
the scope or explicitly review resource settings; never remove claims or concerns
silently to fit. The limits are engineering resource choices, not confidence
thresholds or a claim that a circular fits this prototype.

Each `fidelity-rounds/round-NNN` contains `plan.json`, validated `batch-NNN.json`
files and locally retained `retained-NNN.json` parts. On success, `complete.json`
contains the full validated matrix. On failure, `partial.json` contains the
admitted rows and concerns; an over-capacity cached part is separately retained
and named in the plan. `retained_pairs` counts rows in all retained parts, while
`aggregated_pairs` counts those admitted into the partial union. An incomplete
matrix produces a null top-level fidelity result and `execution_complete=false`.
All files enter the investigation's integrity manifest.

Missing, unexpected and repeated pair errors now identify exact claim and
candidate IDs and occurrence counts. Feedback includes at most 64 identities in
total, with exact group counts and an explicit truncation flag. The existing
bounded output-repair loop receives this diagnostic and preserves both the
invalid and corrected responses. A corrected schema is still a model judgment,
not a proof that the English interpretation is right.

## Executing and continuing the master program

The fixed runner is `scripts/run_interpretation_reliability_plan.py`. It supports
the established `preflight`, `refresh`, `review`, `run`, `repair`, `recover` and
`status` operations. Its B0 command runs the full tests and deterministic
revalidation of retained 23EC46/24EC16 responses. No live model can be dispatched
by this acceptance script. A failed attempt requires a recorded executed repair
and refreshed review before retrying. Accepted attempts cannot be overwritten.

The new program protects 4,676 A7-era evidence files, including the unchanged
78/100 live-call ledger, as well as the earlier frozen comparator and evidence.
Use `artifacts/interpretation/round4/state.json` and the attempt manifest to
inspect execution. Successor plans refresh automatically after acceptance. B1–B6
engineering acceptance has now run; see the phase result notes and current state
JSON. B4's empirical study remains under-budgeted. Local B5 integration and final
B6 repairs passed their reviewed commands. The final suite passed 503 tests.

## New operational commands

`assurance-compose` takes `--investigation`, `--spec`, `--jdk` and a fresh `--out`.
The specification binds packet, claims and complete final candidate hashes. Each
component identifies its selected claim IDs and alternative candidate IDs, output
meaning and assignment basis. The command emits separately scoped rules in Java
and preserves all unresolved upstream concerns. The result is a draft candidate.
Use `artifacts/interpretation/round4/B2a/attempt-01/composition/23ec46-spec.json`
as a retained real-input example, with the referenced A7 investigation. Do not
reuse its hashes after changing a source or candidate.

The assurance manifest can now name `authority_registry`, `example_registry`
and an explicit `example_scope` with issuer, jurisdiction and issue IDs. Paths
are relative to the manifest. Example data are in
`.localresources/sfc-authorities/b1/catalog.json` and
`.localresources/sfc-examples/b3/registry.json`. A selected issue is
`paragraph.3.11.applicability`. The current FAQ edition remains historically
uncertain; adding this registry does not silently resolve that uncertainty.
`examples/interpretation-assurance/authority-and-examples.json` is a complete
public-source manifest; `authority-monitor.json` in the same directory supplies
the corresponding registry configuration. Both are development examples.

`assurance-evaluate` takes `--frozen`, `--out`, `--jdk`, and either the persistent
`--allowance`/`--total-calls` pair or explicit `--replay-responses`. A study is frozen
through `legalmath.interpretation.assurance.evaluation.freeze` before dispatch.
The CLI checks the entire reserved budget first. The retained B4 acceptance study
is a development fixture; its hidden expected results cannot evaluate general
English correctness. No live study ran in this continuation.

`assurance-schedule` takes `--config`, `--resource-root`, `--out`, `--jdk`, `--at`,
`--settings` and provider arguments as for `assurance-monitor`. `--ticks`,
`--interval-seconds` and `--tick-timeout-seconds` bound execution; the default is
one tick. The wrapper copies registry and source bytes under `--out`, records
dispatches and invokes the fixed monitor command. It does not install a service.
The assessment time is explicit and fixed for the invocation: an institution
scheduler must supply the intended current assessment time on later invocations.
See `b5-operator-contract.md` for the local-to-institution integration boundary.

Exact command help is available through `.venv/bin/python -m legalmath.cli
COMMAND --help`. CLI JSON statuses must be inspected; process exit zero does not
mean that an interpretation is resolved or that a release is authorized. The
generated Java package's manifest, source commitments and typed result must be
checked before it is considered for an institution-owned release workflow.
