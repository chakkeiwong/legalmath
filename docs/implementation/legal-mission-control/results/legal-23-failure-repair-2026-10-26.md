# Repair result: separate and contain the 23 P14 failures

26 October 2026 (Hong Kong). The isolated repair now has **23/23 locally validated
correction candidates**. The original raw responses and decisions are unchanged.
The live dispatcher remains active, so this is not deployed or a completed P14
answer review. No new provider call was made.

## What was repaired

The initial failure classification and queues are retained under
`artifacts/legal-mission-control/2026-10-26/failure-repair/`. Their 19/4 split
describes the first observed error, not the final repair outcome:

- **19 mechanical correction packets:** 12 invalid document references, 2 invalid source aliases, 4 source identifiers attached to client-fact/external-authority needs, and 1 ineligible `SUPPLIED_SOURCE` disposition. Their correction contract permits only request-bound selectors and route-valid shape changes. The underlying missing facts or authority remain unresolved.
- **4 attribution-review packets:** missing document/proposition links. Direct
  inspection found exact delivered quotations for all four; absence of the link
  did not establish absence of the source. No missing authority was invented.

Every packet records the original request and raw-response hashes. The verifier confirmed all 23 hashes, the two queues total 23, auto-accept is false, and provider calls are zero.

The initial packets contained descriptive permissions only. That gap is now
repaired by `scripts/legal_context_failure_repair.py`: it reconstructs each
packet from hashed inputs, restricts edits to defective fields, freezes all other
fields and runs the existing canonical validator. The v1 packets remain retained;
v2 adds one reviewed rule that removes an authenticated dependency ID from a
source request while preserving its valid source IDs, query and locators. Unknown
aliases cannot use that rule.

Nineteen explicit mechanical proposals were executed. **18 passed directly**;
one repaired hash exposed a second missing attribution link. The document
selections are evidenced by exact prior needs or already-declared source gaps,
not spelling similarity. The incorrect supplied-source disposition becomes
STILL_REQUIRED because its own unchanged reason says the client facts are absent.

The four initial attribution cases and that secondary case were then reviewed
individually. **All five pass with seven exact citation links.** Three link
existing disposition quotations to their numbered prose. Two concern queries
requesting Footnote 3: the validator scans context queries as assertions, and the
footnote text was already delivered. Its exact text identifies the requested
provision; it does not provide complete adequacy criteria or satisfy the missing
need. The existing checks remain unchanged.

The final union is 23 assignments, not 18 plus five additional legal issues.
Their preserved decisions are **21 UNRESOLVED, 1 REJECT and 1 pre-existing ACCEPT
proposal**. No response becomes legally accepted because its protocol now validates.

The exact candidate transport remains isolated in `/tmp/legalmath-unblock-v2` and the unapplied [candidate patch](/home/chakwong/python/legalmath/artifacts/legal-mission-control/2026-10-25/offline-unblock/candidate.patch) still passes `git apply --check`. Its schema binds answer quotations and source identities to the current request, prohibits source IDs on missing-fact/authority needs, preserves original needs exactly, and leaves canonical legal validators unchanged.

## Verification

- The focused candidate and adjacent regression suite: **98 passed**.
- The saved failure population: **217 complete calls**; unchanged raw responses remain failures.
- Completed exact-reference replay: **194 simulated responses validate and 23
  remain rejected**, 128.87 seconds. The new reviewed repairs address those 23.
- Correction enforcement: **25 focused tests pass**; the earlier 23-test result
  is retained. These tests cover immutable reasoning/decisions, unknown sources,
  stale inputs, duplicate edits and forbidden delivery waivers.
- Six attribution adverse controls reject wrong-document links, invented quotes,
  wrong locators, foreign prose paths, missing links and changed reasoning.
- All **364 protected live source/program files remain unchanged**.
- No live provider call, network request, worker restart, budget change or attempt consumption occurred.

The replay and correction receipts establish local engineering and attribution
integrity. Fresh model behavior, semantic entailment, dated applicability and
actual fulfillment remain separate questions. The recorded source quotations
resolve the missing-link defect; they do not close those substantive questions.

## Why this is the correct boundary

The old response contract allowed models to type hashes, aliases, need IDs and
dispositions. Its validators correctly rejected malformed combinations, but the
failure count mixed protocol defects and missing attribution metadata with
substantive unresolved findings. These categories are now separated. A request
for more evidence is also scanned as an assertion, which explains two missing-link
errors; that behavior has been documented, not silently weakened.

The corpus and baseline blockers remain separate. Corpus qualification still needs dated applicability/later treatment and complete proposition/source-use evidence. P14 and Gatecoin baseline review results remain open/failed in the live master. Those substantive branches cannot be cleared by making JSON shape valid.

## Activation gate

Live use is still pending a safe worker checkpoint, same-master registration,
refreshed binding and bounded live qualification. The additional 20 attempts
require an explicit finite allocation that preserves P14's 7/7, corpus's 6/6,
other questions' protected reserves and all historical charges. They do not
silently reset those counters.

The worker PID 2726366 remains alive in the host process namespace. A sandboxed
`/proc` check temporarily hid it; a trusted `ps -p` confirmed it was still active.
No worker exit, restart or safe activation checkpoint is claimed. The master
ledger was 6,427/8,100 during this package; any further increments belong to the
existing worker. The recorded global deadline remains 27 October 2026 at
13:15:09 Hong Kong.

## Decision and return to product work

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Local repair verified | All 23 explicit proposals pass full canonical checks | Six bad-link/prose controls remain rejected; inputs preserved | Fresh model protocol choices | Safe-checkpoint qualification of the exact-reference profile | Live recovery or accepted P14 answer |
| Preserve substantive findings | 21 UNRESOLVED, one REJECT, one prior ACCEPT unchanged | Missing facts, authority and unsupported conclusions remain open | Correctness and relevance of underlying review | Continue admitted source/answer and matched-tool work | Attribution proves entailment |
| Hold deployment | Existing worker owns current binding | Concurrent rebind would invalidate its execution | Time to a safe worker checkpoint | Use the same-master reviewed activation path | A prepared repair is deployed |

These deterministic results support no model ranking or default-policy change.
The strongest alternative explanation is that explicit local selection repairs
metadata while fresh model reasoning remains inadequate. A live controlled
qualification and complete source-grounded answer review are needed to test that.

Reproduction commands are fixed local actions:

```text
.venv-context/bin/python scripts/legal_context_failure_repair.py verify
.venv-context/bin/python artifacts/legal-mission-control/2026-10-26/failure-repair/execute_reviewed_corrections.py
.venv-context/bin/python artifacts/legal-mission-control/2026-10-26/failure-repair/check_reviewed_bindings.py
.venv-context/bin/python -m pytest tests/tooling/test_context_failure_repair.py -q
```

The current candidate is staged in `/tmp/legalmath-unblock-v2`; its durable patch,
manifest and changed source files remain under `2026-10-25/offline-unblock`.
Reconstruct that exact candidate if temporary storage is lost. This local harness
fails rather than substituting live or mixed source code. No broader command
allow-list permission is needed for these sandboxed local actions.
