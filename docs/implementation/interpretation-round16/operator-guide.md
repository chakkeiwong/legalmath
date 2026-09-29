# Operating the round-16 local program

The implementation is an explicit next interface, while old experiment contracts
remain reproducible. No model calls, downloads, installation, private bank data
or deployment are part of this round. The exhausted 500-call ledger is checked
byte for byte before execution.

From the repository root:

```text
/home/chakwong/python/legalmath/.venv/bin/python scripts/run_assurance_round16.py audit
/home/chakwong/python/legalmath/.venv/bin/python scripts/run_assurance_round16.py execute --through N4
/home/chakwong/python/legalmath/.venv/bin/python scripts/run_assurance_round16.py execute
/home/chakwong/python/legalmath/.venv/bin/python scripts/run_assurance_round16.py status
```

The full execution command uses the trusted environment for the local regression.
Its exact prefix was approved in this session. The narrower `--through N4`
checkpoint works in the workspace. `repair` uses the same evidence journal and
attempt limits as `execute`; a failed phase consumes a reservation. Inspect its
log, repair the specific defect, then resume. Changed bound code invalidates
completed dependent phases. Identical completed inputs reuse their stored
receipts. At most three attempts per phase and 18 overall are allowed. No repair
operation replenishes live calls.

Read `artifacts/interpretation/round16/phase-results.json` for phase receipts.
Resolve the corresponding `execution/action-*` directory from its receipt
sequence, rather than assuming a number. Every action contains the exact command,
environment, code hashes, wall time, test XML and logs. The master rewrites the
derived `next-phase-plan.json` after each completed or failed phase; immutable
action results retain the earlier history.

## Interfaces available to the next implementer

`legalmath.interpretation.assurance.fidelity_v2.request` takes the complete
packet, retained claims, candidate dictionary, a candidate-to-typed-question
dictionary and optional exact required pairs. Historical CONTEXT claims are not
removed. `validate` checks the response against those same frozen inputs.
`reconcile` accepts validated responses, retains all of them, and returns either
a repair request, a bounded uncertainty report or agreement of proposed labels.
Callers must not treat that agreement as independent votes or legal truth.
Migration in N1 stores the complete old assessment and leaves all new dimensions
UNASSESSED. The existing v1 live engine has not silently changed its schema.

`control_investigation.investigate_scoped` is the executable v2 local route. It
accepts a retained/local provider and persists requests, raw responses,
validation diagnostics and receipts in an EvidenceJournal. Two initial
perspectives are blind to one another. A disagreement or rejected response
executes further rounds up to the specified limit, after which all proposals
remain in an uncertainty report. Transport failure or interruption blocks new
dispatch on resume. N1's `automatic-followups` directory retains the six-call
local worked example. Its calls are scripted fixtures, not live judgments.
The route rejects `live=True` providers until the shared-allowance integration
is separately implemented and authorized; its local limit cannot authorize
additional calls against the exhausted grant.

`temporal_inputs.project` asks whether a specified event occurred for a named STR
in an inclusive factual interval and was recorded by a separate knowledge
cutoff. It accepts only timestamped observed events. A false result needs a
complete-history assertion covering the entire question; without one it returns
UNKNOWN. Relevant disputes return CONFLICT. A RESUBMISSION must name an original
event of the same STR, and the original must be available. `context` keeps source
effectiveness and bundle validity separate; `trigger_and_performance` does not
turn a trigger into a compliance verdict. These adapters do not replace the
three retained child rules or supply missing performance criteria.

`legalmath.java.decimal_boundary.build(bundle, output, jdk,
profile='signed-exact-percent-v1')` creates a JAR with a generated percentage
entry point. `java -jar <recorded-jar>` accepts one external request per line.
The Java host may alternatively call the generated class's
`evaluate(String request)` method. Both use the same adapter. N3's
`cases-before-execution.json` contains complete runnable requests; `build.json`
contains the exact JAR and class. The required request fields are `profile`,
`subject_id`, `facts`, `valid_at`, `known_at`, and `mode: "draft"`.

Each supplied fact uses its declared type and a `known`, `unknown` or `conflict`
evidence record. `fund_manager` and `va_objective` are Boolean;
`intended_va_percent` is a `decimal_percent` string such as `"9.999"`.
Missing facts become UNKNOWN. Known evidence carries `value`, `evidence_ids`,
`valid_from`, `valid_until`, and `recorded_at`. The entry point creates exact
integer numerator and positive denominator fields internally and rejects any
attempt to supply them externally. Negative decimals are permitted only under
the explicitly selected signed arithmetic profile: financial admissibility is
not established. Existing raw-snapshot APIs remain lower-level interfaces and
do not enforce this new boundary. A host must adopt the new entry point.

`legalmath.interpretation.assurance.editions.select` requires the acquired PDF,
the hash-bound page extraction, an explicit manifest hash, one clean edition ID
and exact provision IDs. It rejects marked active editions, mixed editions,
missing declared links and altered inputs. The actual N4 example includes page
76's definitions and structure footnote plus page 77's persistence notice and
application provisions. Its unresolved authority dependencies remain in the
packet. A manifest records a proposed structural review, not a proof that all
qualifications have been discovered or that the edition governs today.

The result-verification command is
`.venv/bin/python scripts/review_assurance_round16.py`. It checks the predecessor
archive, journal, code bindings, full regression, pair identities, packaged Java
evidence and final manuscript. It writes a delivery manifest for a future
increment to preserve before changing this round's bound files.
