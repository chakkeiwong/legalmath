# Repair the exact service probe capacity mismatch

October 26, 2026, 05:47:33 UTC. The installed worker failed before provider
reservation because legal_review_repair_service.recover passed Settings with the
100,000-byte default. The authenticated request is 156,917 bytes. Its original
reviewed common-capacity profile permits 250,000 input bytes and 262,144 output
bytes; the regular product dispatcher already selects those exact limits.
The failure is our recovery adapter, not a model/server failure.

The global ledger remains at 6,471, no receipt for 6,472 exists, and the circuit
has half_open_reserved=false with the exact failed request/schema identity.
The replacement reservation at index 289 and its elapsed five-minute wait remain.
No charge, elapsed wait or attempt may reset. Do not discard started/error files.

Bounded repair: pass the same input_byte_limit and output_bytes helpers used by
BoundDispatch. Test against the actual retained wire request and reject unknown
capacity profiles. For the already scheduled but definitely undispatched probe,
use a dedicated resume helper with the current stage, exact request/schema,
unchanged ledger and false half-open-reserved flag; acquire existing live/service
locks and prove the original worker has exited. No new service reservation is
needed. Complete its retained response into the original scheduled folder so the
existing authenticated restore_deferred path adopts the paused BM25 attempt.

The corrected implementation changes the binding hash. Preserve the original
stage and charge byte-for-byte, and create a successor stage that differs only
in that binding hash. The resume helper authenticates both stages, their exact
relationship and the unchanged pre-dispatch ledger. It does not add logical
calls, stage capacity, replacements or another wait. Any charged original probe,
changed scope/budget, live original process or output is a continuation veto.
Keep the corrected worker logs/finish record separate from the initial failure.
The repair registration preserves all original validation receipts and records
this correction within revision 68, without another detour or branch attempt.

Successor regular recovery must use the corrected capacity helper too. Preserve
the installed program and all sealed earlier validation receipts. This is the
single bounded local correction permitted by the current continuation plan; no
extra attempt, global calls, replacement ceiling or deadline is added.

Skeptical audit PASS: this changes transport byte settings to the request's already
reviewed contract, not the request, schema or legal acceptance. No output/uncertain
reservation is retried. Unit controls plus the actual failed request distinguish
this local adapter defect from service failure. A paid successful response remains
transport evidence only and is never substituted into the legal answer.
