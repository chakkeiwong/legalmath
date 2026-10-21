# P14 and Gatecoin request-format diagnostic

The offline preflight passed, but no alternative request has yet reached the
provider. The diagnostic is waiting for the active P10 owner because that
owner holds the shared provider lock. Its latest request hit the 300-second
timeout; the shared circuit is open and the existing P10 worker has already
scheduled its authorized two-hour retry. Sending a separate request now would
interfere with that retry and bypass the shared outage stop.

The fixtures for P14 slot 2341 and Gatecoin slot 2285 authenticated against
their saved receipt manifests and global charges. P14's stored event reports a
generic `invalid_request`; Gatecoin's stored event reports an explicit safety
block. The three planned representations preserve the complete legal request:
original bytes and schema, an exactly equivalent schema with local references
inlined, and the original schema with only JSON whitespace changed. Fourteen
offline positive and adverse schema checks passed. The plan limits the whole
diagnostic to six calls, with no retries and no product promotion.

The first runner invocation waited for the provider lock and was stopped before
reservation. The live-call ledger remains at 2,972 calls, with zero calls
charged to this diagnostic. The latest charge belongs to P10. The revised
runner now waits for the recorded master owner to settle, verifies the global
grant and service circuit, and sends nothing if the circuit remains open or an
unknown process still owns the provider lock. Its progress and eventual result
are retained under `artifacts/legal-mission-control/2026-10-18/request-variants/`.

This is a scheduling disposition, not evidence that request variants reproduce
or repair either failure. The remaining result is contingent on P10 settling,
the shared service becoming available under its existing recovery policy, and
enough time remaining under the original grant. A successful transport result
will still need the original schema, citation, source and legal checks before
any product use.
