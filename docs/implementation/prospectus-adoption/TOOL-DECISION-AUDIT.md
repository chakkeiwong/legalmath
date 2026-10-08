# Reasons for tool rejection and deferral

8 October 2026. This audit qualifies the adoption decisions using retained
execution evidence and inspected code. It does not rerun a parser, change an
acceptance threshold, or promote a package. Historical attempts remain unchanged.

## Question and skeptical audit

Question: does each decision establish a package defect, an integration or usage
problem, a scope mismatch, or simply an untested capability?

The Docling comparator is the retained raw-word reconstruction in A3
`attempt-005/layout-source-maps.json`, compared with the same attempt's actual
Docling JSON. It is not an independent new transcription of the PDF. The
diagnostic removes whitespace exactly as the current mapper does, then reports
every remaining character edit without forgiving punctuation changes. Quote
presence is explanatory only: it cannot establish a unique source occurrence,
correct attachment, legal meaning, or readiness for adoption.

Pre-run audit for the retained-artifact report: PASS. No model, GPU, network,
environment change, fresh inference, or new benchmark is involved. Missing or
inconsistent retained references would invalidate the attribution. The historical
model/configuration and two exposed development pages cannot establish current
package-wide performance. The artifact is `tool-decision-audit.json`; its command
and input/code hashes preserve the static diagnostic. Existing rejection remains
in force for the tested integration until a separately reviewed repair passes.

## Docling: mixed upstream transformation and local integration issues

The installed Docling 2.60.1 `PageAssembleModel.sanitize_text` removes a line-final
hyphen when the adjacent extracted words are alphanumeric. This occurs before
the document JSON is assembled. In the five failed text items, both exported
`orig` and `text` contain the resulting normalized text; selecting `orig` alone
would not recover the lost characters.

The retained comparisons have exactly six non-whitespace edits across those five
items, all deletions of `-`. Examples include `Zinsberechnungs- zeitraum` becoming
`Zinsberechnungszeitraum`, and `Insolvenz- oder` becoming `Insolvenzoder`. These
examples require different treatment: a generic deletion rule cannot establish
that every removed hyphen is merely a typesetting break. The normalized export
does not meet our exact-quotation requirement as used.

Our `layout_adapter.map_layout` discards the entire item's character map when
any non-whitespace character differs. A3 then calls a critical line missing if
any of its characters lacks a map. Thus the fourteen failed line mappings are
not fourteen demonstrated omissions from Docling's output. Thirteen of those
fourteen quoted strings occur in the corresponding failed paragraph after
whitespace removal. This is failure attribution, not replacement acceptance.
Earlier local ordering and list-marker repairs reduced twenty unmapped critical
lines to fourteen; that history also establishes a local adapter contribution.

There is a separate evaluation limitation. `adoption_trials.layout_trial` writes
`baseline_failure_resolved = False` and the unresolved governing-attachment text
as fixed values. These express absent implementation/evidence; they are not a
measured test of Docling's ability to identify the legal scope of a margin. Layout
regions and legal governing relationships need a separate explicit mapping and
evaluation. No downstream attachment improvement has been established.

The trial used historical layout-v2 weights (`docling-layout-old`), two
born-digital pages, and disabled OCR, tables and VLMs. Both page conversions
returned SUCCESS. The result is therefore rejection of this configuration and
integration for exact legal-source use. It does not establish failure of Docling's
OCR, all layout models, all configurations, or its underlying architecture.

A justified repair candidate would preserve the existing raw words, offsets and
punctuation; use Docling's regions/order as structural proposals; and record any
display normalization through explicit source transformations. It must test
meaningful hyphens as well as typesetting breaks, unique occurrences, negative
controls and separately reviewed margin relationships. Merely removing hyphens
from the comparator would weaken the requirement and is not a repair. Test the
same failures first; no wider cohort or default change is justified yet.

## Other decisions

| Component | Supported diagnosis | Next justified action | What is not established |
|---|---|---|---|
| INCEpTION/Cassis | Exchange now passes. Many earlier failures came from our driver: readiness, authentication encoding, endpoint/state names, import metadata, display offsets and browser selectors. Retained upstream documentation/runtime inconsistencies and a one-off negative-duration error also occurred. Discontinuous evidence needs linked spans; ordinary XMI export does not supply the storage metadata needed by our attempted REST overwrite. | Complete unlabelled authoring and real authentication, using the passed browser-edit path and preserving raw reader exports. | Fundamental platform unsuitability; genuine reader independence; complete authoring validation. |
| ACTUS | Deferred before a local runtime trial. The retained wrapper requires core 1.1.0 and Java 17 while its README describes an older webapp/core and asks for core access. The inspected core license has specific conformance, attribution and distribution terms. These require a version/use-specific check, not a blanket incompatibility conclusion. | Identify a concrete event-model requirement; verify current core access/version/license and its mapping to supplied contract terms before a bounded trial. | A failed ACTUS computation, incompatible license, unavailable current core, or package-wide defect. |
| FINOS CDM | Deferred because no required receiving-system format or demonstrated local representation gap has justified the adapter. The inspected settlement model requires asset, amount, parties and dates; it does not supply the missing contractual interpretation. | Specify a consuming-system or event-model requirement, then test a finite bidirectional mapping. | A failed CDM implementation or inherent inability to represent the intended transactions. |
| QuantLib | Accepted as a bounded comparator. The initial long-first-coupon discrepancy was our expected-value arithmetic error. The nine fractions and six adjusted dates subsequently agreed. Broader use still lacks admitted instrument conventions and event/entitlement inputs. | Supply and independently check instrument-specific premises, then extend the downstream calculation tests. | A QuantLib calculation failure or complete settlement support. |
| Other OCR/parser or legal runtimes | Surveyed or screened without sufficient local trials to make adoption claims. | Revisit only for a named failure and a discriminating test. | Empirical rejection or proof of inferior performance. |

These decisions have different evidence strengths. The exact-map failure is a
supported engineering rejection of the current integration. ACTUS/CDM deferral
is a scope and feasibility decision. INCEpTION's remaining work is an incomplete
integration/evaluation obligation. None supplies a population comparison among
packages or completes the prospectus's legal interpretation.

## Evidence

- [Static attribution report](tool-decision-audit.json): retained differences,
  quotation-presence checks, configuration and inspected-code hashes.
- [A3 source mappings](phases/A3/attempt-005/layout-source-maps.json) and
  [critical-line result](phases/A3/attempt-005/critical-span-results.json).
- [Actual Docling settings](phases/A3/attempt-005/layout/result.json).
- [Local mapping adapter](../../../src/legalmath/prospectus/successor/layout_adapter.py)
  and [trial evaluator](../../../src/legalmath/prospectus/successor/adoption_trials.py).
- [INCEpTION repair history](../prospectus-inception/RESET.md) and
  [passed bounded exchange](../prospectus-inception/RESULT.md).
- [Survey source inspection and deferral rationale](../../research/prospectus-adoption-2026-10-07/SURVEY.md),
  including the retained ACTUS wrapper/license and CDM settlement schema.
