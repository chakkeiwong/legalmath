# R10 execution record

R10 is registered and bound. Its 108 installed regression checks and actual
P14 production replay passed. The replay matched 36 logical contracts, reused
35 successful responses with their retained provenance, and reproduced the
exact wire request/schema of missing `detail-87`. It made zero provider calls
and left the cumulative ledger unchanged.

The review rejected three prototype assumptions before adoption: reused
successes do not have fresh wire bindings; canonical JSON field sorting changes
encounter-order hash aliases; and some saved successes occur after the failed
account in the requirement loop. `prototype-review.md` records the diagnosis.
The installed checker preserves real provenance and requires the real product
constructor to reproduce the failed wire contract. It changes no encoder and
relaxes no source or response validator.

The staged registration passed and the transaction committed. Registration's
post-commit refresh exceeded the 300-second child timeout. The exact direct
refresh then passed in 375.75 seconds. Binding attempt 28 succeeded; the exact
master `run` completed with exit code zero, preserving its refresh timeout.
Subsequent exact direct refresh and verification passed in 386.76 and 380.39
seconds, respectively. Under existing locks, unchanged program, mission,
binding, state and ledger hashes allowed only the pending timeout to be cleared.
All original timeout events and successful task results remain.

At 05:27 UTC on 16 October, the exact approved command
`.venv-context/bin/python scripts/legal_integration_master.py live` started.
It owns execution from this point: P14 first, then eligible independent
P10/evidence and downstream work. No other supervisor or bound-code writer may
run concurrently. Gatecoin remains failed for its explicit safety refusal and
is not reopened. Live results are pending at the time of this note.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Adopt exact P14 continuation | Installed tests and exact real replay pass | History, charge and request identities preserved | Service availability and later legal output | Execute one authorized continuation and independent ready work | Legal completeness or tool benefit |
| Acknowledge refresh completion | Exact full refresh and verification pass on unchanged inputs | Wrapper timeout retained; no validation bypass | Repeated validation runtime | Use saved successful binding | Performance defect repaired |
| Keep integration open | Four questions, 46 obligations, 35 readings and six-tool effects still required | 0/6 tools fully evaluated at prior review | Full-source/account reviews and actual answer effects | Retain actual results and refresh | Total integration |

Cumulative allocation is ten of ten repairs and nineteen of twenty additional
task attempts. One task attempt remains unallocated. Baseline calls are 2,333
of 8,100, plus 41 separate historical calls. All 48 automatic replacements are
spent. The grant and scheduler deadlines are unchanged. Local validation and
bookkeeping reconciliation add no task attempt or model call.

Evidence: `tests.xml`, `regression.json`, `successor-replay.json`,
`registration.json`, `registration-refresh.manifest.json`,
`binding-finish.manifest.json`, `binding-refresh.manifest.json`,
`binding-verify.manifest.json`, and `binding-recovered.json`.

## Terminal outcome

The run is now settled. The exact P14 account continuation succeeded, retaining
all 36 validated account responses. First-level synthesis retained 20/90
validated responses, five failed provider dispatches and 65 unsent requests.
The shared service circuit opened at slot 2359. P10 and evidence were deferred
before reservation, preserving their attempts. Gatecoin was not reopened.
Completion-review attempt 26 succeeded and the live supervisor exited zero.

Exact direct mission refresh and master verification then passed in 396.08 and
388.90 seconds. The reviewed helper reconciled only the pending wrapper timeout
after checking unchanged input hashes under locks. All historical results,
attempts and charges remain. Calls are 2359/8100 plus 41 separate historical
calls; ten repairs and nineteen additional attempts are used. The original
legal and tool acceptance criteria remain unmet. See `settled-execution.md`,
`remaining-work.md`, both terminal manifests and `terminal-recovered.json`.
