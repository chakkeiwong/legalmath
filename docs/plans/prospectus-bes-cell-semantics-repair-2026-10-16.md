# Repair the 9M2010 memorandum reading and execute its controls

The current work-selection review reproduced two defects in BES-DEP-01
attempt-003. Its `parse_literal` assigns the ECB memorandum values -1,071,215,
-2,005,438 and -4,506,647. The source identifies these as amounts included in
deposits from central banks; the parentheses do not justify an additive negative
amount. Its `adverse-controls.json` consists of fixed labels written by the
script, with no omitted-cell, period-swap or altered-value executions.

Repair the supplied development reading in one additional admission of the
same source task. Preserve attempts 001–003 and their status. This is a distinct
reproduced semantic/evidence defect; a repeat of successful release-category or
incorporation checks would not address it. No shared production edit is needed
because the product does not consume that reading yet. Do not describe this
repair as financial-statement integration.

## Evidence contract and research intent

Question: can the complete 9M2010 statement reading retain source literals,
periods and unknown dashes while correcting the ECB sign inference, and can
actual malicious alterations demonstrate refusal rather than asserted labels?
Baseline: exact original P1 from attempt-002, original pages 37–38 from
attempt-001, the image-reviewed transcription from revision117 and the actual
attempt-003 map. Reinspect the original images; do not transfer Q1's row count
or coordinate windows. This source has 49 balance rows, 28 income rows and
203 cells over 304 page occurrences.

Primary criterion: every numeric source word belongs to exactly one correctly
anchored cell; all 203 literals agree with the original image reading; stock
dates are 30 September 2009, 31 December 2009 and 30 September 2010; income
periods are the nine months ended September 2009/2010. The ECB row retains its
three magnitudes and original literals with additive signed value UNKNOWN.
Discontinued operations retain negative reported values and remain non-additive.
Printed dashes remain UNKNOWN. Compare the new map with the old map and account
for every change in meaning.

Run at least the eight actual adverse cases exercised on Q1, plus a control
that restores the old negative ECB inference. Preserve the altered input and
actual exception for each. Reconsume the retained original products through
the current Python consumer in frozen mode and compare its complete answer
with the losslessly retained original answer. This checks the existing consumer;
it cannot show consumption of the new map or fresh native extraction.

Promotion vetoes: lost/duplicate token, changed source literal or period,
unknown-to-zero coercion, inferred negative/additive ECB amount, changed source
or method, missing real control execution, changed protected answer, or false
integration/current-extraction claim. Invalid source/method bindings or an
ambiguous mapping stop this package. There is no automatic repair retry.
Counts and arithmetic are explanatory; legal/authenticity acceptance remains
unresolved. A semantic failure rejects this reading, not the PDF library.

## Defaults, pre-mortem and audit

The original images support the finite row counts and label/column layout.
Use their native geometry with a 2-point row tolerance because inspected offsets
are below 1.5 points and rows are separated by more than 10 points. Verify unique
assignment and complete token coverage to expose an incorrect window. The
transcription is agent-reviewed development evidence, not independent evidence.
The source title mismatch (prospectus 9H10 versus release 9M10) survives.

Success could mislead if a detached map is presented as production integration,
if an unknown dash enters arithmetic as zero, or if the old static control labels
are counted as executed tests. Keep those distinctions in the result and actual
manifest. Failure could be transcription, geometry, or consumer currentness;
retain the precise failing comparison before considering another proposal.

Skeptical audit: PASS for this bounded repair. The wrong sign and unexecuted
control claims are visible in inspected code and retained output. The fix is
discriminating because the old ECB reading must now fail a real validation call.
Scope and obligation lineage are unchanged. The explicit cumulative revision
is 3 to 4 admissions for BES-DEP-01 only; no native-binding extension follows.

Run one CPU-only diagnostic through `timeout 120 .venv/bin/python` with
one-second yields. Set GPU hiding before imports. Retain up to 20 MiB of new
evidence, exact input/method hashes, actual argv, environment, git identity,
wall time, result note and outputs manifest before recording. Do not call
native tools, OCR, network, models, installers or external parties. One
admission and one diagnostic; a fifth admission is not implied. Record the
actual outcome, inspect its history event, refresh, and review independent work.
