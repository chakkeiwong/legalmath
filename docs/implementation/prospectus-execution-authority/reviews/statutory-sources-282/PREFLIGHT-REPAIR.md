# Offline fixture correction before admission

The first offline preflight failed before invoking its simulated curl because
its temporary root did not contain the plan and method files counted by the
real storage accountant. This is a test-fixture defect; no network or actual
consumer ran. The fixture now creates those two local placeholders. The real
accountant still refuses missing bound files. The failed command was
`.venv/bin/python -m scripts.prospectus_statutory_sources_preflight`; its wall
time was not instrumented and remains UNKNOWN. This is preparation, not a failed
primary-source trial or evidence about a legal package.

Before admission, review also found that failed extractions lacked receipts and
the child-process timeout did not bound HTML decoding/parsing. The source tool
now retains failed local receipts, refuses unfinished local stages, bounds the
whole extraction body and counts both preflight receipts. The revised preflight
is saved separately as `preflight-v2.json`; the earlier result is unchanged.
Decoding and injected whole-stage timeout checks passed offline. The preflight
script joins the frozen method bindings. No live request has occurred.

The final preparation adds explicit original-context retention and package
sealing. Review caught a self-accounting problem before execution: a seal must
record its completed local receipt before querying an accountant that refuses
unfinished stages. The final offline `preflight-v3.json` passed eight groups,
including this ordering and exclusive final output creation. Earlier preflight
receipts remain unchanged and counted. These are preparation corrections; no
failed live source or consumer call is being relabelled.
