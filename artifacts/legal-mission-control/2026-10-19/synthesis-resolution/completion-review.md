# Completion review of the pending synthesis repair

19 October 2026. This review continues the existing synthesis-resolution
amendment. It does not reset attempts, extend the deadline, change the original
acceptance criteria or authorize new provider calls.

The production replays were started before this review and remain the primary
engineering comparison. P14 has passed its no-call replay: eight account roots,
21 retained first-level results and 69 missing requests. The other three replays
are still running. No production source will change while they run.

One additional boundary needs a focused check before registration. Reduction
currently rejects an atomic intermediate that exceeds the old input bound
before trying the explicitly selected larger envelope. A synthesis response
can fit its output bound while its downstream request, including the complete
supporting sources, exceeds the old input bound. The larger-envelope option
must apply to such a new intermediate as well as to a pair of smaller ones.

The diagnostic will use the real reduction controller with a deterministic
capacity meter and scripted responses. The comparator is the current controller.
The pass criterion is that a new intermediate inside the selected envelope
continues, while an intermediate outside it fails before dispatch. The old
profile must still reject the same oversized input. Exact original member
populations must be retained and normalization must remain finite. This is a
controller regression check, not an estimate of model capacity or answer quality.
If reproduced, repair only the early capacity selection and rerun the focused
suite plus production replay under the final implementation identity. Preserve
the first replay results as predecessor evidence.

The runner review also confirms that its detached worker drains live work and
then records refresh and verification. Ready local commands and agent tasks
remain the supervising agent's responsibility in this same execution session;
the worker's exit is not a completion verdict. Inspect and drain that frontier
after live settlement. A failed question blocks only its success dependants.

Skeptical audit: the baseline is the actual failed production and the current
controller. The proposed diagnostic has a specific falsifiable boundary and
does not substitute a fixture for legal acceptance. No source truncation,
repeated sampling of success, expanded output bound, hidden time renewal or
unbounded retry is permitted. A historical identity mismatch remains a veto.

The initial replay has now settled. P14 and Gatecoin passed. P10 and evidence
completed their first retained synthesis level but failed exact request
reconstruction at the next level. Those failures are preserved in the original
production-replay directories. A separate initial frontier diagnostic used the
campaign module's historical default envelope instead of the configured current
envelope; its apparent source changes are invalid diagnostic evidence. The
corrected diagnostic explicitly uses the production configure() selection.

The intermediate-capacity regression reproduced the predicted controller bug:
the enlarged-profile 35000-token case failed before trying the selected 70000
bound; the old-profile case and 71000-token refusal passed. Repair the blocked
atomic case by repacking the complete population under the explicitly selected
larger profile before refusal. Retain the existing finite normalization bound,
source population and exact historical request checks. This is an implementation
failure, not evidence against the synthesis approach. Audit PASS for this local
repair; registration still requires the complete final-source production replay.

The corrected production-envelope diagnostic found exact historical grouping at
level 1 in both branches. All ten differing P10 requests and all three differing
evidence requests preserve the exact source-record population, exact verified
locator-binding population and every other field, including full payload and
input identity. The sole difference is ordering of those two derived lists.
`source_records()` walks response dictionaries in insertion order; canonical
JSON storage sorts their keys, changing citation encounter order on reload.

Restore the historical list ordering only within the explicitly reviewed
synthesis-recovery profile, after authenticating the saved phase, dispatch,
wire, receipts and charges. Require equal complete populations without duplicate
identities and exact equality of every remaining field; return the original
saved request. Original unreviewed recovery remains strict. Changed text,
locator ranges, membership, payload, schema, missing/duplicated records and
other changes must still fail before dispatch. Skeptical audit PASS for this
bounded reconstruction repair. This preserves the actual old wire and result;
it does not permit reusing a response for a changed request. Test these adverse
cases and rerun all four production replays under the final source hashes.
