# Batch 36 timeout successor validated

9 October 2026, Hong Kong. The request-bound source-first successor for batch
36 validated after 213.72 seconds, using provider reservation 40 and repair
entry 7. The failed 300-second call remains charged as reservation 39. Both
attempts, their transport and the hash-bound selected receipt are retained.
The current suite passed 184 tests with no failures, errors or skips.

The successor's wire request and schema were required to match the failed
attempt before dispatch. It reused verified tool evidence and ran through the
same source, candidate, question and executable validators. No previous peer
existed for this batch: qualification-first had never been issued. Normal
execution resumed with that perspective and the final four batches, all under
the ordinary 300-second cap. The original deadline remains unchanged.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Select the valid replacement | Twelve original pairs assessed in source-first | Request/schema identity and original validators passed | Free-text interpretation remains a model proposal | Issue the previously unissued qualification-first role | Legal correctness |
| Retain one reviewed timeout successor | Explicit receipt, transport, reservation and bounded journal | Original call fully terminated locally; no partial output was present | Remote latency and execution are not observable | Complete remaining roles and verify zero-call restart | A general 450-second default or improved service reliability |

The replacement finished below 300 seconds, so this result does not show that
the 450-second ceiling caused success. Service variability is an alternative
explanation. A single failure and replacement do not estimate reliability or
support a statistical ranking. The local settings mismatch found during v3
preflight was an implementation defect and was corrected before any live
recovery call; v4 preserves the correction and its tests.

The decisive evidence is in `roles/36/source-first/receipt.json`,
`roles/36/source-first/attempt-01/receipt.json`, `service-recovery-02.json`,
review v4, and provider-evidence reservations 39 and 40 in the additional-grant
directory. The final report will verify these alongside every other attempt.
