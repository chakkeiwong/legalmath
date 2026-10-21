# Independent diagnostic scheduling review

Decision: PASS for the bounded request-format diagnostic after the isolated
production-method controls pass. This changes scheduling, not legal acceptance.
Neither branch reads P10 output. The retained runner unnecessarily waited for
the whole master lifetime to avoid its nonblocking service-worker lock. The new
runner never takes that lock, the supervisor lock, or the master run lock. It
does retain diagnostic deduplication and the actual atomic shared ledger lock.

The comparison is the retained exact P14/Gatecoin input, not a neighboring
payload, a canary, or the number of historical owner attempts. The six prepared
requests and original-schema checks stay unchanged. The original precedes each
branch's equivalent variants; any explicit safety block stops later forms of
that branch. A generic invalid request does not block independent work.

The four predecessor authorities and new authority share a six-call ceiling.
Every reservation validates the unchanged grant, binding, route, source, plans,
review, historical ledger prefix, service scope and deadline. Require current
v2 stage accounting so charges cannot consume P10's stage quota. Real global
authority checks stay in CampaignAllowance.check; the offline fixture isolates
that check and scope resolution while exercising the real locking, reservation
and circuit implementations. Concurrent diagnostic/production reservations must
retain all twelve distinct synthetic slots and allow all six master charges.

Set expected request/schema to None for the diagnostic circuit check: even a
matching request cannot borrow a master's half-open probe. This check runs under
the production circuit lock. Diagnostic success writes no service-success
transition. An actual no-output terminal service failure opens the shared
circuit and stops subsequent calls. This is an actual shared service dependency.
The runner has no retries or recovery allocation. Concurrency capacity is an
unproven bounded choice: one diagnostic request alongside one master, not a
load test. The existing 300-second request and 3,600-second batch bounds apply.

Skeptical audit checked stale authority, process identity/restart, stage races,
lost ledger writes, quota resets, circuit ownership, wrong baseline, proxy
promotion, and unsupported causal claims. The stopped predecessor used no
calls, and runtime still reconciles every saved reservation/charge and worker
identity before dispatch. The diagnostic never edits active P10 source, stage,
binding, grant or task. Admission does not grant more calls or acceptance.

Request rejection rejects the current arm only. An explicit safety block stops
that question's later variants. Invalid common authority, deadline/budget,
shared outage, tool execution, corrupt inputs, unknown terminal behavior or
uncertain dispatch stop the affected batch. Those conditions do not imply that
P10's legal analysis depends on a diagnostic answer. The controls are engineering
evidence; provider success only establishes an observed schema-valid response.
Neither establishes legal correctness, complete integration, production
readiness, or a causal formatting improvement. One call per form has no
statistical ranking power. Retain actual commands, charges, outcomes and refresh
the mission after this package, including failures and undispatched arms.
