# Independent P14 and Gatecoin request tests

The diagnostic no longer waits for unrelated P10 execution. All six requested
calls ran with `gpt-6.1-sol` on the existing approved route, while the original
P10 supervisor and live worker remained active. All six returned JSON satisfying
the original response schema. P14's earlier generic invalid request and
Gatecoin's earlier explicit safety block did not recur in these observations.

| Question | Exact retained request/schema | Expanded local schema references | Indented request JSON |
| --- | --- | --- | --- |
| P14 | Valid; slot 3097; 22.841 s | Valid; slot 3100; 29.854 s | Valid; slot 3103; 28.593 s |
| Gatecoin | Valid; slot 3099; 54.512 s | Valid; slot 3102; 40.302 s | Valid; slot 3105; 29.945 s |

The original form preceded each question's variants. Six calls used the same
aggregate six-call diagnostic allocation across all predecessor authorities.
There were no retries, extra owner attempts, new calls beyond that allocation,
or deadline renewals. Actual dispatch and completion occurred on 18 October
2026 from 05:19:54 through 05:23:08 UTC. Each arm preserves its exact command,
interpreter, git commit, request, schema, events, stderr, usage, reservation,
timing, output, validation result and manifest in the existing
`artifacts/legal-mission-control/2026-10-18/request-variants` directory. The
provider seed is unavailable. GPU devices were intentionally hidden.

The old diagnostic acquired the master's nonblocking service-worker lock and
therefore waited for the entire master to finish. This was a scheduling defect:
neither question consumes a P10 result. The successor retains its deduplication
lock, atomic shared accounting, authority/deadline checks and genuine shared
outage veto. It does not take any master, supervisor or service-worker lock.
Current v2 stage accounting keeps diagnostic charges separate from P10's stage
quota. It cannot become a half-open recovery probe, and successful diagnostic
calls do not modify the service circuit.

Focused controls exercised the actual reservation and circuit methods against
isolated ledgers: occupied master lock, twelve competing production/diagnostic
reservations, master stage quota, open circuit, half-open ownership including
identical request identity, aggregate predecessor ceiling, legacy stage veto,
and valid/invalid-request/safety/503 receipt writing. All passed. Fourteen schema
equivalence controls also passed. These are engineering checks; actual provider
observations are the six receipts above.

The returned answers still identify incomplete legal evidence in these historical
inputs. Direct inspection confirms that P14's delivered source table contains
closing guidance, contact details and page metadata rather than the operative
request clause and footnote. Gatecoin's delivered source text is a noisy,
incomplete Handbook custody extraction; it does not deliver the judgments'
reasoning. The full retained corpus and current acquisition progress are separate
from these replay fixtures. Passing requests does not fill those evidence gaps
or establish correctness of the legal conclusions. These responses remain
diagnostic material outside production checkpoints pending normal citation,
source, decoding and legal review.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Limit |
| --- | --- | --- | --- | --- | --- |
| Close the requested bounded diagnostic | Six terminal responses pass original schemas | No authority, shared service or diagnostic-integrity veto fired | Cause and future frequency of earlier errors remain unknown | Preserve receipts; continue the existing substantive master frontier | No acquisition attempt reopened |
| Accept the scheduling repair for this diagnostic | Real reservations overlap the original live P10 workers; isolated production accounting checks pass | No master lock acquired; global accounting retained | One additional sequential worker does not establish general concurrency capacity | Keep actual resource dependencies rather than whole-worker barriers | No general load or reliability claim |
| Keep legal integration open | Replay outputs preserve unresolved evidence | Legal/citation acceptance has not been performed | Missing operative material in replay inputs; current master outcome remains separate | Continue substantive acquisition/answer review under existing authority | No completion verdict |

| Inference status | Finding |
| --- | --- |
| Hard veto screen | None of the six observed calls was rejected or failed the original schema; offline veto controls passed. |
| Statistically supported ranking | None; one call per form cannot rank formats or models. |
| Descriptive differences | Elapsed times, usage and wording differ; no causal attribution follows. |
| Default readiness | No new request format or acquisition policy is promoted. |
| Next evidence needed | A provider explanation or a separately authorized controlled reproduction would be needed to identify the old error's cause; substantive integration needs its normal source and answer evidence. |

Post-run review: successful unchanged originals show that neither historical
failure is universal over these observed requests. Intermittent provider or
gateway behavior remains an alternative explanation; formatting cannot be
credited as a repair. The original HTTP envelopes were not retained and cannot
be compared. A future authenticated recurrence would overturn any expectation
of reliable replay, while leaving this six-call observation intact. The weakest
evidence is causal diagnosis and substantive answer adequacy, neither of which
this diagnostic establishes. The four original questions, 46 obligations and
35 readings remain governed by the existing master; no tool is declared fully
evaluated by these transport results.
