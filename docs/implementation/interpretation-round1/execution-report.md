# Interpretation workbench: executed master program

23 September 2026. **The E01–E09 public/synthetic engineering increment is
implemented and has passed whole-round acceptance.** The final run passed **205
regression tests**, all **35 RuleIR conformance cases**, deterministic regeneration
of **42 contract JSON files**, the new **33-path API**, actual Chromium interaction,
and an offline wheel build/install check outside the source checkout.

The executable supervisor is [run_interpretation_plan.py](../../../scripts/run_interpretation_plan.py),
controlled by [the reviewed master plan](master-plan.md). The actual phase state
and all attempts are in [state.json](../../../artifacts/interpretation/round1/state.json).
The final acceptance is [P4 attempt 03](../../../artifacts/interpretation/round1/P4/attempt-03/run-manifest.json).
Its input hashes bind the exact tested implementation. Immutable copies of every
accepted source input are indexed by
[accepted-source.json](../../../artifacts/interpretation/round1/accepted-source.json).
The environment is the existing Python 3.11 virtual environment, retained Java 17,
SQLite/WAL and local Chromium. These are deterministic CPU-only checks, without
paid model calls, bank connections or external messages. There is no Git repository.

This result establishes tested software behavior for supplied interpretations and
scripted repairs. It does not establish English-to-rule accuracy, independent legal
agreement, ensemble superiority or readiness for bank deployment.

## Phase execution and actual repairs

| Phase | Final result | Attempts | Evidence |
|---|---|---:|---|
| P0: baseline and supervisor | 154 original tests and design diagnostics passed. | 1 | [Baseline manifest](../../../artifacts/interpretation/round1/P0/attempt-01/run-manifest.json) |
| P1: records, inventory, alternatives and issues | 30 focused checks passed. | 2 | [P1 manifest](../../../artifacts/interpretation/round1/P1/attempt-02/run-manifest.json) |
| P2: action accounting and controller | 38 interpretation checks passed. | 2 | [P2 manifest](../../../artifacts/interpretation/round1/P2/attempt-02/run-manifest.json) |
| P3: API, review and release integration | 58 interpretation and selected legacy checks passed. | 1 | [P3 manifest](../../../artifacts/interpretation/round1/P3/attempt-01/run-manifest.json) |
| P4: complete acceptance | 205 tests, Java demonstration, browser, contracts and installed wheel passed. | 3 | [JUnit](../../../artifacts/interpretation/round1/P4/attempt-03/tests.xml), [final manifest](../../../artifacts/interpretation/round1/P4/attempt-03/run-manifest.json) |

The focused phase counts overlap; they must not be added together. The final 205
include the original 154 and 51 new interpretation/supervisor checks. The final
whole-round command took approximately 98 seconds on this machine; this is a run
record, not a performance benchmark.

Four failed attempts were retained. In P1, the installed schema validator accepted
an impossible date; the runtime now also uses the strict calendar parser. Two
fixture setup errors were corrected in the same repair. In P2, the progress measure
passed tuples to canonical JSON and could have counted newly created errors as
progress; it now counts newly resolved discrepancies. In P4, the separate Java
caller used `historical` instead of the actual API's `replay` mode. The next P4
attempt exposed mobile horizontal overflow, repaired by wrapping long IDs and
adjusting quotation margins.

The reviews also produced repairs before acceptance: bind deferred candidate
bundles; reserve space for unseen reading families; preserve issue creation order;
carry unresolved questions and root/parent context into successors; memoize argument
graph traversal; require exact-source inventory review for retained material; store
validated adjudication evidence; and require issue decisions to apply to the selected
candidate. These changes and regression checks are recorded in the
[P1 repair](../../reviews/interpretation-round1/P1-repair-01.json),
[P2 repair](../../reviews/interpretation-round1/P2-repair-01.json),
[first P4 repair](../../reviews/interpretation-round1/P4-repair-01.json) and
[second P4 repair](../../reviews/interpretation-round1/P4-repair-02.json).
These are skeptical author reviews, not independent human or Claude reviews.

After a failed command, the master program refused to advance, retained its logs,
required an executed repair note, refreshed the phase plan and bound a new review
to the changed inputs. After each successful phase it refreshed the successor's
plan with the actual predecessor outcomes. The next investigation round is now
specified in [next-round-plan.md](next-round-plan.md).

## What is implemented

| Task | Implemented behavior | Acceptance boundary |
|---|---|---|
| E01 | Ten packaged record schemas; strict request models; finite fixture policy validation. | Reject malformed/extra authority fields, invalid dates, weakened checks and paid profiles. |
| E02 | Exact retained-source spans, separately supplied inventory, explicit dependencies and authenticated inventory review. | Unanimous omission and missing dependencies remain visible. Completeness of the supplied legal inventory is not established automatically. |
| E03 | Immutable candidates, assumptions and parent revisions; family reservation, deferred frontier and explicit search-incomplete issues. | Dissent is retained; unsupported assumptions become issues; source changes invalidate current use. |
| E04 | Persistent issue/root/parent identities, processing versus resolution states, revision-checked decisions and validated adjudication evidence. | A stopped issue can remain unresolved; successor creation carries uncertainty instead of deleting it. |
| E05 | SQLite-atomic reservation, counters and outbox; leases/fences, retained uncertain results and no charge refunds. | Last-slot race, dispatch crash and stale completion tests. |
| E06 | Four frozen initial roles, deterministic issue priority, supplied scripted repair proposals, bounded rounds/no-progress and durable terminal outcomes. | Automatic execution of a supplied repair is tested; automatic discovery of the correct English reading is not. |
| E07 | Candidate-linked SMT comparison with retained domains, unsupported/unknown/inconsistent outcomes and Python/Java witness replay. | Existing supported RuleIR fragment only; equivalence of encoded behavior does not settle source meaning. The wrapper's executable witness test was added in P3 and included in P4. |
| E08 | Complete report collections, source/alternatives/issues interface, authenticated asynchronous API, cancellation/recovery and archive preservation. | Actual desktop/mobile browser and keyboard checks; human usability review pending. |
| E09 | Exact candidate/report/source meaning review plus existing engineering, applicability and release controls; current-use/source-change veto and export sidecar. | Legacy API bypass probes and positive synthetic Java release. Enterprise identity and bank host enforcement remain E14. |

Inventory, candidate and issue operations share `interpretation/service.py`; the
planned separate inventory/candidates/issues files were unnecessary in this increment.
`comparison.py` and `reports.py` implement the proposed compare/report responsibilities.
Interpretation workers use their own supervisor and persisted action records;
existing drafting/comparison jobs keep their original semantics. The actual request
shapes are in OpenAPI and the [operator guide](operator-guide.md); the earlier
monograph endpoint table was a proposed interface rather than an implemented API.

The implementation supports a declared family inventory and one scripted repair
action per resolution round. It does not yet generate new legal families using
live models, perform general defeasible argument adjudication, schedule paid
retrieval, or supply a calibrated probability of legal correctness. These limitations
are explicit inputs to the next phase, not hidden completed tasks.

## Whole-cycle evidence

The [demonstration result](../../../artifacts/interpretation/round1/P4/attempt-03/demonstration/result.json)
records these actual executions:

- The retained 23EC46 paragraph-10 candidate was imported against exact source bytes.
  Its original five legal questions and two missing Code/FAQ sources remain open;
  it remains DRAFT and unreleased. The interpretation report records seven material
  unresolved issues: five legal questions plus the two dependencies.
- A separate visibly synthetic encoding omitted the product-type promotional route.
  The frozen named case `g02` detected that compiled error. A supplied scripted repair
  restored the disjunct. The corrected Java build passed 22 named scenarios and all
  729 T/F/U assignments using the unchanged oracle representation. A solver witness
  was replayed in both Python and Java. Initial and corrected candidates are retained
  in [repair-evidence.json](../../../artifacts/interpretation/round1/P4/attempt-03/demonstration/repair-evidence.json).
  The repair investigation remains blocked for unresolved meaning/structural review;
  it is not a legally approved circular implementation.
- Persistent ambiguity exhausted two no-progress rounds and produced a blocked
  report with competing records. A malformed member produced an explicit failure
  issue and missing-role entry. Cancellation produced a durable report.
- Two concurrent reservations competed for the last slot; exactly one succeeded.
  A dispatched action was recovered as result unknown, with zero refunds; its late
  completion was retained without changing the outcome.
- A different fully specified synthetic financial condition passed exact meaning
  review and the existing engineering release process. A separately compiled Java
  caller invoked the generated class from the exported JAR. History export/restore
  reproduced the investigation, and a subsequent source-footnote change blocked
  current export even though the predicate had not changed.

The [browser record](../../../artifacts/interpretation/round1/P4/attempt-03/browser/result.json)
confirms a blocked real-source approval request, five retained initial/repaired
candidates, seven visible unresolved issues, keyboard expansion, no JavaScript
errors and no horizontal overflow at 390 pixels. Rendered desktop and mobile
screens were inspected after the repair. The
[package check](../../../artifacts/interpretation/round1/P4/attempt-03/package/result.json)
built and installed a wheel offline and loaded its API, all ten schemas, migration
and UI resources from the installed directory rather than the source checkout.

## Decisions and remaining uncertainty

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action |
|---|---|---|---|---|
| Accept this engineering increment | Final fixed-command suite and whole-cycle checks passed. | No outstanding failure in the declared acceptance. Failed attempts and repairs retained. | Scripted inputs do not measure legal interpretation quality. | Build restricted provider contracts and independent annotation tooling. |
| Release real 23EC46 candidate | Not satisfied. | Five legal issues, two dependencies and missing review/checks block release. | Correct scope, classifications and authoritative source versions. | Independent source/meaning adjudication in an explicit successor. |
| Select an ensemble or search default | Not evaluated. | No fair live-provider evaluation or independent reference corpus. | Correlated errors, false clean outcomes, abstention and reviewer burden. | Register E11/E12 study before comparison. |
| Deploy to bank | Not satisfied. | No enterprise identity, bank-owned interpretation or host approval. | Real data, source monitoring and transaction enforcement. | E14 shadow integration after bank authorization and review. |

The strongest alternative explanation for favorable cases is shared authorship of
source interpretation, scripted proposals and test expectations. The tests establish
internal engineering behavior and detect specified wrong encodings; independent
legal reviewers could still find a common omitted duty or incorrect classification.
Any such finding must reopen the relevant investigation and add a discriminating
case before the candidate is reconsidered. No statistical ranking is claimed.

## Preservation and command approval

The original 153-file source/document baseline and 350 protected evidence files
passed the supervisor's before/after checks. The 23EC46 source, oracle and original
results were not rewritten. The pre-existing README/hash discrepancy in its old
manifest remains documented in the earlier readiness assessment. New results are
stored separately from the old 154-test acceptance.

Both distributed monograph PDFs remain identical and **232 pages**. The book is the
preserved design/history; this execution report and its linked ledger provide the
current implementation status without deleting or relabeling historical evidence.

The approved allow rule is installed at
`/home/chakwong/.codex/rules/legalmath-interpretation.rules`, with its reviewed
project copy in [allow.rules](allow.rules). It matches exactly this command prefix:

```
/home/chakwong/python/legalmath/.venv/bin/python /home/chakwong/python/legalmath/scripts/run_interpretation_plan.py
```

All phase runs used that trusted prefix. The runner accepts fixed operations and
phase names, never arbitrary shell commands. Reviews, repair notes and refreshed
plans are retained beside the phase evidence; no repeated phase-command approval
was needed after the upfront authorization.
