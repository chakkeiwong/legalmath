# Finite resource and command review for the focused answer trial

12 October 2026 Hong Kong. The original grant remains 400 provider calls with
an absolute deadline of 12 October 2026 04:28:01 UTC. The latest retained
successor ledger has 17 charged calls. The proposed focused method has exactly
20 distinct call stage IDs: two source-reader attempts, a reading proposal,
an argument proposal, and an answer plus review for each of baseline, six
individual tools and all six together. Its maximum aggregate ledger length is
37, so it cannot consume the 383 remaining global calls simply because they
exist. No retry IDs or refunds are included. The older baseline-core stage
balance remains sealed and is not treated as transferable funding.

At the 300-second validated per-call ceiling, 20 sequential calls take at most
6,000 seconds of provider time; the runtime guard also reserves 600 seconds for
review. This is a clock admission bound, not a latency forecast. Source-reader
wire requests measured 66,611 and 66,644 bytes against the 200,000-byte cap.
A controlled combined six-tool answer request using the retained 55-unit source,
three reviewed historical candidate inputs and the questioned graph fit the
same cap. Actual model-generated reader, reading, graph and tool-result lengths
cannot be certified before execution. Each actual request is measured before
dispatch; an oversized stage fails without dropping evidence. Two separate
reader failures do not prevent an otherwise valid answer arm from using the
full source, but they limit the inference about multi-reader coverage.

The selected model is the previously exercised `gpt-6.1-sol` route. Its service
identity is not remotely attested; the exact configured route and transport
code are bound before any call. CPU devices are intentionally hidden. No seed
control is available. The method is a focused answer comparison, not the old
full-matrix investigation. The live whole-route guard stays in refusal mode.
The present user instruction and earlier 400-call/48-hour authorization are
read together as authority to review a bounded successor, not automatic
authority to dispatch a different method before mission registration and a
separate post-implementation admission record.

Command forms are literal `.venv/bin/python scripts/legal_mission_answer_tools.py`
plus one enumerated action. The repo rule file allows those forms and mission
check/status/admit/refresh; `codex execpolicy check` confirms `offline` matches
and `launch` does not. Host installation of the rule file is a separate,
potentially privileged act, after live admission. The script's `execute` and
`install-rules` paths require the registered `answer-tools-live` task to be
active. No host file was written and no provider call was made by this review.

Decision: local preparation is resource-feasible within the original ceiling,
subject to a registered focused method, exact source and case review, finite
ledger integrity and the original clock. The complete legal-product route is
still unqualified; passing this resource screen cannot promote it.
