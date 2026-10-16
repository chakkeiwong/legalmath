# Final correction review within the original local attempt

10 October 2026 UTC. The second verification passed 162 tests and both scripted
product arms. Its retained-target diagnostic delivered all 189 baseline request
constructions, then reproduced a candidate-only scoped-request overflow. The
first rejected candidate request used 213,569 encoded bytes against 200,000.
Its tool context included twelve question-bound BM25 retrievals with source
passage text and exact offsets. The shared codec recognized two-field quotation
objects but did not recognize this different representation of the same source
text. The source already exists in the unchanged packet.

The justified correction is exact encoding of the retrieved text by its existing
unit/start/end coordinates. Preserve every rank, query, target, status, raw result
hash and other field; reject incorrect coordinates. Decode back to the identical
augmented request before dispatch. This does not summarize a tool result or
select which findings the model may see. Test overlapping passages, Unicode,
repeated text, altered offsets and marker-like ordinary data.

The code review found a second material issue: core fidelity's conservative
aggregate reservation still multiplies the raw output cap after the new route
allows larger expanded responses. It must reserve the effective expanded cap.
That stricter check can reject even a small matrix under a wide expansion bound;
the existing optional incremental admission policy is appropriate for the
scripted fixture because it checks and retains each actual expanded part against
the unchanged aggregate bound. It is not being promoted for a live run. Verify
both refusal before dispatch and bounded incremental acceptance/overflow.

Also make the staged-review setting apply to an unpartitioned source inventory;
otherwise the setting can bypass review and then fail when search requires its
records. Test both independent readers and retained qualifications.

Interaction responses must account for each nominated directed edge, not only
the set of endpoint claims. Two relations can have the same endpoint set.
Require exact edge accounting, reject self-nominations, and retain the complete
interaction bindings in the downstream cross-review records. This is structural
coverage only; it cannot attest to the substantive quality of an interaction review.

Before those corrections, `.venv/bin/python -m pytest -q
tests/assurance/test_route_final_boundaries.py` reproduced eight failures and
one pass in 0.45 seconds. These are deliberately new regressions, not a claim
that the earlier 162 tests covered these boundaries. The incremental acceptance
case already passed; its conservative counterpart incorrectly dispatched.

These are corrections within the same admitted attempt, with the same absolute
deadline and zero live calls. Preserve verification 2 and its source snapshot.
Verification 3 repeats affected tests and the scripted full route. Recheck the
exact retained augmented requests through the changed transport; the installed
tool outputs are unchanged, so re-executing their computations is unnecessary.
Requests never prepared because of the separate tool-action limit remain
unqualified. Do not turn this replay into evidence of a complete legal dossier.

Acceptance remains split: exact input preservation and bounded execution are
engineering evidence. The original stage allocation, full-reader completeness,
actual responses, reductions, legal warrants and matched answer effects remain
separate requirements. A byte improvement cannot change those verdicts.

Verification 2 completed all 189 input attempts in each arm, then failed while
writing its final summary because canonical JSON rejects floating-point wall
times. Every request and tool report was already retained. Recover a separately
named summary from those records, record the reporting failure, and retain the
source snapshot. Use integer milliseconds in new diagnostic reports. This is a
reporting correction, not authority to repeat tool work or discard failed rows.
