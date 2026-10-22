# Malformed document dates no longer pass as missing dates

The source graph now parses every non-null supplied document_date, known_from,
valid_from and valid_until before deciding that document's visibility or
extracting its text. Non-string values produce ValueError; malformed strings
use the existing timezone-aware timestamp parser. Parsing applies under all
four supported query purposes. Omitted/null metadata retains the existing
unknown-date qualifications and optional-interval behavior.

Preparation reproduced eight malformed source-metadata cases that left the
contract visible and yielded conditional Q4 YES in the actual selected-source
BASF meeting consumer. The cause was our truthiness-based metadata checks and
purpose-dependent parsing of document_date. The earlier law/fact endpoint
repair did not cover this separate path. No external package defect follows.

## Actual checks

The focused stage passed494 tests with zero failures, errors or skips in
3.1892100162804127seconds. Actual-consumer validation took
2.658676673192531seconds. The complete original answer is unchanged. Eight
omitted/null variants equal complete results computed with the retained old
implementation. All208 malformed supplied-date cases refuse under the four
purposes. Twelve temporal boundary consumers agree with independently specified
datetime comparisons, including six refusals when a bound source is outside
the query's temporal scope. Timezone equivalence and half-open end behavior
are preserved. Reinjecting the old implementation recreates conditional YES
with a false valid_until, confirming regression sensitivity.

The full baseline, positive controls, boundary graphs and answers/refusals,
adverse matrix, known-bad answer, source hashes, frozen methods and test XML
are retained here. The run manifest records actual commands, inherited commit,
interpreter, CPU-only environment, stage times, preparation cost and storage.
The package retains the300-second cumulative and32MiB limits, including
preparation, authority copies, support and1MiB reserve. Earlier attempts remain
immutable; unmeasured historical runtime remains UNKNOWN.

## Decision

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain local input-validation repair and record partial source-authority progress | Complete baseline and eight missing/null results equal;208 malformed cases refuse;12 temporal boundaries agree | No valid-result, source-binding, missing-qualification or resource veto fired | Original publication/authenticity, historical legal applicability, broader source coverage and installed currentness remain open | Refresh authority; continue a distinct remaining source-to-answer requirement and later validate the stabilized installed build | Source-authority task complete, historical dates authenticated, actual participation established, or whole build complete |

## Post-run skeptical review

The retained BASF request combines reviewed selected source text with explicit
hypotheses; its YES remains conditional. Fresh intake here reads selected text,
not the original PDF. The historical law006 attempt's rejection is preserved;
using its hash-verified text and request as a diagnostic baseline does not
promote that rejected attempt. The current baseline was independently retained
before this production change.

The strongest alternative explanation is that these checks validate only the
declared metadata domain while incomplete source interpretation remains. That
limitation stands: no interval-order policy, missing-date inference, legal
meaning, source authenticity or unseen-layout support is added. A malformed
date reaching a conditional conclusion, changed valid complete answer or lost
unknown-date qualification would overturn this local result. Test counts and
timing are descriptive; installed evidence still requires revalidation.
