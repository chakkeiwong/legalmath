# Executable master plan: the bounded interpretation workbench

23 September 2026. User authorization: create the next master program, review it,
arrange narrow command approvals up front, then execute it with repairs and refreshed
plans between phases. Scope is E01–E09 of the unified monograph: the public/synthetic
interpretation service, deterministic members, independent inventory, alternatives,
bounded investigation, complete reports and integration with the existing Java and
release workflow. E10–E14 remain subsequent provider, evaluation, search and bank
work. No paid provider, bank system or external message is required in this round.

The question is whether the implemented service enforces the specified identities,
uncertainty, accounting and review behavior. Its comparator is the written contracts
and independently stated adversarial outcomes, plus the existing runtime regression
suite. Passing establishes engineering behavior within the declared scope, not
English interpretation accuracy, ensemble superiority or bank approval.

## Executable supervisor and command policy

`scripts/run_interpretation_plan.py` is the master program. It has a fixed internal
command registry, validates phase names and predecessor results, records immutable
attempt logs/manifests, checks frozen evidence, and refuses to advance without a
review and a fresh plan. It accepts no arbitrary shell command. Commands execute
as argument lists without a shell. All subprocesses have finite time limits.

Use the exact absolute command prefix:

```
/home/chakwong/python/legalmath/.venv/bin/python /home/chakwong/python/legalmath/scripts/run_interpretation_plan.py
```

Only the trailing operation and phase vary. `refresh P1` derives a phase plan from
current inputs and prior outcomes; `review P1 --note PATH` binds a skeptical author
review to that plan and code; `run P1` executes its acceptance commands. A failure
creates a repair request and blocks dependent phases. The implementing agent reads
the actual log, records diagnosis and edits, repairs the code, and uses `repair P1
--note PATH` before re-review and rerun. Repair is code work by the agent, not a
blind repetition of the failing command. At most six failed attempts per phase
are permitted by this version. Changing that budget requires an explicit plan
revision with a reason; a successor does not erase prior attempts.

A passed phase automatically writes the next phase's refreshed draft plan, including
observed failures, changes and inherited uncertainties. Once the next implementation
is ready, refresh again and review the exact current inputs. Author review is not
independent human approval. A hash match is evidence identity, not correctness.

The proposed rule file is `allow.rules`. It allows only the above two-token prefix.
The install command writes that one rule file to the user's protected Codex rules
directory. The executable policy checker must match the real command and must not
match arbitrary Python, another script, a shell wrapper or the relative spelling.
Use the same absolute prefix in every tool call. Trusted execution is required for
service/thread and browser tests because the prior sandbox blocked TestClient
thread wakeups. The permission scope does not include paid calls or deployment.

## Phase sequence

| Phase | Tasks | Deliverable and required evidence |
|---|---|---|
| P0 | Baseline and supervisor | Preserved current source/evidence; runner preflight; existing runtime tests and contract diagnostics; executable plan review. |
| P1 | E01–E04 | Packaged schemas and strict policy/packet validation; independent source inventory; immutable candidate/assumption records; discrepancy identity and issue lifecycle. Tests include unknown fields, source mismatch, missing dependency, unanimous omission, minority preservation, inherited roots and stale revisions. |
| P2 | E05–E07 | Atomic action/outbox accounting; leases/fences; finite deterministic controller and recovery; source-grounded repair; supported formal comparisons and distinguishing witnesses. Tests include last-slot races, crash without refund, stale return, deadlines, no progress, source changes, inconsistent domains and Python/Java witness replay. |
| P3 | E08–E09 | Complete reports and reviewer interface; asynchronous API, explicit cancellation/successors; authenticated issue/report decisions; exact candidate/report/bundle binding in the existing release service. Tests include omitted report collections, false approvals, stale sources, open issues, cancellation recovery, positive synthetic review and blocked real-source packet. |
| P4 | Whole-round acceptance | Full old/new regression suite, regenerated API/contracts, isolated end-to-end demonstration, Java boundary, archive/recovery, packaging and actual browser checks. Record new acceptance separately from T00–T22 historical evidence. |

Each phase has focused files and commands in `master-plan.json`. The master program
records the command actually run, environment, CPU status, input hashes, elapsed
time, exit status, output files, plan and review identities. It leaves failed logs
intact. Completed E tasks receive actual evidence links; they are not completed
merely because files or schemas exist.

## Integration decisions fixed before execution

1. Extend the existing SQLite transactions and immutable content-addressed records.
   A migration adds interpretation tables; existing data and API behavior remain
   valid. Action reservations, counters and outbox entries commit together.
2. Keep the book's ten record schemas as the persisted interchange. Add strict
   runtime packet/request shapes and relational checks where the record schemas
   deliberately do not encode authentication or transactions. Reuse registry roles:
   `author`, `meaning`, `engineering`; derive identity from authentication.
3. Source inventory is separate from candidate extraction. Retained source units
   have exact text/source identities and explicit dispositions. An unavailable
   source or unsupported interpretation can be reported but cannot become reviewed
   by repeated model agreement. Synthetic fixture authority is visibly distinct.
4. Freeze blind member outputs before reconciliation. Preserve families and dissent;
   caps leave explicit unexplored-family issues. Every discrepancy is recorded.
   Source truth is not inferred from a majority vote or a priority score.
5. The default scheduler is the chapter-6 deterministic order. A repair must change
   a stated proposition against retained evidence and rerun affected checks. Repeated
   unanswered definition questions remain unresolved. Fixture budgets are examples,
   not chosen production settings. Paid policies are rejected in this round.
6. Bind every interpretation-origin bundle to its investigation as soon as it is
   retained; creation of a report is not needed to establish the release block.
   Existing manual bundles keep their reviewed legacy route. An investigation-bound
   bundle cannot bypass the new block by using the old API, starting a clean run,
   superseding an issue or deleting a UI association. All bound runs are checked;
   a reviewed successor explicitly supersedes only the matching earlier evidence.
   This is a scoped extension, not a claim that all old controls have ensemble evidence.
7. A ready report never grants release. Meaning review binds candidate, report and
   source identities; existing engineering/build/applicability reviews remain
   required. Source invalidation, candidate changes and unresolved issues veto
   approval, release and use of the affected current release. Historical replay
   remains tied to the recorded historical version.
8. Late results are retained as observations without rewriting closed reports.
   Issue adjudication before a report and meaning acceptance after a report are
   distinct records; no circular hash dependency is introduced.
9. Preserve all original source/oracle/run evidence. The frozen baseline under
   `.localresources/interpretation-round1/baseline` supports historical identity
   checks after intended implementation changes. New tests validate the new code;
   the old 154-test record is never relabeled as a run of new code.

## Skeptical audit and defaults

The initial audit found and settled three material risks: phase tests alone could
hide runtime regression (P4 runs the complete suite); a post-report attachment could
allow release before an investigation completes (bind at candidate creation); and
an old acceptance hash audit could incorrectly reject intentional source changes
or falsely certify the new version (preserve the old baseline and issue a new run
manifest). Contract records do not implement real locks, provider deadlines or
identity; each is exercised through the service, not inferred from schema validity.

Python 3.11, Java 17, SQLite/WAL and the local identity registry are inherited
prototype choices. Existing regression and migration tests are the early checks.
The six-attempt phase repair limit and scripted controller policy are explicit
engineering bounds; their failure mode is an exhausted run with unresolved work,
which is reported and never treated as a pass. Candidate scores schedule work;
they are not legal probabilities. Tests use controlled clocks, deterministic
providers and CPU-only execution. No statistical ranking is claimed.

Promotion criteria are the named acceptance assertions and required independent
checks at the code/data boundaries. Vetoes are broken source identity, missing
provisions, budget overrun, unauthorized/stale release, corrupted storage, lost
history, unbounded execution or a failed required regression. Each defect triggers
repair and rerun of the affected phase. A deliberately blocked legal candidate is
expected evidence for the next scenario, not a reason to abandon implementation.
Only invalid infrastructure/evidence, unmet external authority or exhausted explicit
repair budget stops dependent execution. Routine code choices do not require a new
user approval. Current plan review passes with these explicit boundaries.

## Whole-cycle completion

The delivered service must (a) repair the explicit omitted promotional route,
(b) retain persistent ambiguity and block release after bounded attempts,
(c) identify unanimous omission from an independent inventory, (d) survive a
last-slot race and a dispatch crash without refund, (e) invalidate approval after
a source/footnote change, and (f) recover a complete report after cancellation or
failure. A separate fully resolved synthetic scenario must pass authenticated
meaning/engineering review and invoke the actual exported Java library. The real
23EC46 packet keeps its five unresolved issues and two missing dependencies.

Finish with a phase-by-phase execution report, actual E01–E09 task dispositions,
new test/Java/browser evidence and an updated next-round plan for E10–E14. That
refresh must use observed implementation limits and failures, not simply repeat
the earlier literature survey. Independent legal effectiveness and bank adoption
remain outside this engineering acceptance.
