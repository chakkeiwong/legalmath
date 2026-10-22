# Recheck acquisition receipts at downstream use

The source-authority continuation review traced source_graph.build,
construction_product and consume. Intake verifies a supplied acquisition receipt's
hash, but the later paths visibly recheck only source-document bytes. The question
is whether a changed receipt can still be reported as bound by a saved product.
This is a candidate implementation gap, not yet an established failure. It is
distinct from the completed archive-consumer harness and does not authorize
another archive trial.

## First discriminating diagnostic

Create one clearly synthetic text source and a separate receipt inside this
review's local controls; construct all P1–P5 products and retain the complete
baseline. Change only the receipt bytes, then call construction_product and the
frozen final consumer with those unchanged products. An accepted frozen answer
with acquisition_status still BYTES_BOUND establishes stale receipt validation;
a rejection refutes this proposed defect. Restore only the diagnostic's receipt
and verify the original complete answer. No production edit or original-source
mutation occurs during reproduction. Bound this local diagnostic to20seconds
and2MiB; record actual time and bytes. No native, network, OCR or model calls.

Evidence contract: exact baseline products/answer; changed receipt with unchanged
document and request; actual downstream accepted/refused result; restoration
equality. A changed document, changed request, mocked consumer or omitted result
invalidates the diagnostic. Success exit or test counts alone do not decide it.
The synthetic example proves a software boundary only, never publication truth
or legal authenticity. The receipt's bytes are provenance evidence, not authority
to infer authenticity. This distinction is part of the existing source_graph
status, not a new legal default.

Skeptical audit PASS for the diagnostic: it tests the exact difference between
initial receipt binding and downstream document-only checking. It preserves
frozen extraction semantics; no requirement to rerun extraction is assumed.
If reproduced, review a small receipt-recheck repair and an original-product
regression under the original source-authority task, with cumulative budget
lineage retained. If not reproduced, record why and return to other source work.
Global authority/evidence failures stop this branch; other ready work continues.

## Reproduced result and reviewed repair

The retained diagnostic passed its validity checks and reproduced the defect:
construction and frozen consumption accepted the modified receipt with complete
answers unchanged, while current consumption rejected it. Restoration recovered
the exact original answer. Evidence is reviews/acquisition-receipt-366/reproduction.json.
This is our downstream validation omission, not an external package defect.

Extract the existing receipt-byte check into a source_graph helper with exactly
the current optional-receipt behavior and error semantics. Reuse it at intake,
construction and final consumption, before any substantive downstream work.
Do not introduce extraction into frozen mode. This does not authenticate a
receipt or its author; it enforces the same retained-byte premise already checked
at intake. A maliciously replaced request with a new binding remains a different
input, not something hashes alone can authenticate.

Dependency map: A (completed reproduction) precedes B (helper and both downstream
calls). C (focused changed/missing receipt and valid restoration tests) and D
(baseline source bindings and profile preparation) follow B independently. E
freezes methods and admits reviewed source-authority009 under revision366. F
runs the unchanged complete BASF CLI against reference100, and G builds a local
isolated wheel. H needs F/G and verifies installed complete equality. I is a
completion-only result review; J seals/records/refreshes I. Tests and packaging
can proceed independently after admission. A formal failure is retained; no
unchanged retry or new archive harness is authorized. Invalid common evidence,
invalid authority or exhausted bounds are global vetoes.

Primary repair criterion: changed/missing receipts refused at construction and
frozen/current consumption; exact valid ordinary and installed answers equal
reference100 in every field; all four original BASF receipt files verified.
Adverse controls also preserve the existing changed-document refusal and missing
optional-receipt behavior. No old source, sealed result or receipt is mutated:
only synthetic control files may be changed and restored. All supplied document
receipts are checked, including documents excluded by their temporal metadata.
Unit totals, wheel count and runtime are explanatory, not legal correctness.

Skeptical repair audit PASS: narrow repeated boundary, real reproduction, exact
unchanged-answer comparator, no new third-party or law assumption. Validity
requires source/import pinning to this worktree, rejection before assembly, and
complete normal/installed evidence. The record must explicitly distinguish
source-integrity repair from publication-date/authenticity determination.

One original source-authority admission8→9 is reviewed for this distinct defect.
Preserve prior1–8 results and the archive006+ measured/accounted809.2133805187261
seconds /106200129bytes. These are a known suffix, not a complete lifetime total;
earlier/manual time remains UNKNOWN. Add at most900 measured seconds (including
the diagnostic, preparation and tests),120 conservative control seconds and
160MiB with4MiB seal reserve. Extend known006+ aggregate to1900 accounted seconds
and384MiB. Consumer workers have380second bounds; other commands120seconds.
Preparation has60seconds. No original limits are erased or named retries reset.
No network, model, native/OCR/GPU, external calls, subagents or branch operations.
Offline wheel install uses existing environment and --no-index only. Keep
one-second yields and retained sessions; wait for completion before dependencies.

The result and exact unresolved source-authority requirements stay in
attempts/source-authority/attempt-009. The next master selection must distinguish
this repaired byte-integrity boundary from missing original publication and
authenticity evidence; no task-completion claim follows from this repair alone.
