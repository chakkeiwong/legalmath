# Preserve exact evidence without requiring a unique solver witness

Reasoning011 reproduced and repaired the Boolean/integer comparison error, and
its first complete replay passed. Its second replay failed at exact equality of
`solver-record.json.gz`. The solver interface permits multiple witnesses and
unsatisfiable cores. The261 plan explicitly allowed independently valid choices,
but the new whole-file replay matcher did not implement that exception. Diagnose
the exact differing fields before changing any comparison. Do not attribute this
to Z3 numerical failure or weaken answer/source comparison.

Run at most three solver evaluations in one process, keeping all records and
the independent enumeration results. Compare each with the protected010 record;
retain exact changed field paths and values. This is a bounded debugging sequence
to distinguish nonunique witnesses/cores from changed decisions, sources or
products, not a new performance comparison. Bound the diagnostic60seconds/8MiB.
If differences escape case-level valid witness/core choices, stop this repair
design and diagnose the semantic change instead.

The proposed repair verifies every solver record independently before comparing
it. Require exact case identifiers, expression/facts/constraints, expected
consequences, typed statuses, reasons, missing/conflict sets, limits, source
identities, full product/consumer records, domain boundaries and controls. Permit
only case-level Z3 witness/core choices already proved valid by independent
truth-table enumeration. Use canonical JSON equality for everything else; keep
False/0, True/1 and integer/float refusal controls. Add a discriminating test with
two different valid witnesses and a wrong witness that violates an observation.

The011 producer also wrote a provisional PASS before its final validation and
left it beside a failed stage. Preserve that contradictory sealed result. The
new validator must refuse any failed/incomplete/duplicate stage before replay,
and the producer must write the final failure disposition when validation fails.
Use before/after method copies. Recording011 after the reviewed method repair
must reject it; the failure remains evidence, never a completed task.

Retain original261/262 methods/results and unchanged production wheel. One
reviewed12th reasoning admission reuses010's exact installed execution evidence
and performs the repaired current replay and full-answer forgery test. Register
no new generic acceptance mechanism or product claim. Charge all261–263 support,
diagnostics, failures, proposals, revisions and admissions to the original
720seconds/128MiB envelope with2MiB reserve. Each stage110seconds; no unchanged
retry. Historical pre261 unmeasured time remains unknown.

Skeptical audit: exact bytes are the correct comparator for sources, inputs and
complete product answers; they are the wrong criterion for a solver's freely
chosen valid witness. A mere status comparison would be too weak, so independent
truth and premise checks remain mandatory before the narrow normalization. The
provisional-PASS issue is our producer/validator integration defect and requires
its own adverse control. Proceed only after the actual differing-field diagnostic
supports this design. Source-authority remains the next substantive work; no
external opinion or holding facts are required for this repair.
