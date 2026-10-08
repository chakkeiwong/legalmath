# Supplying scoped evidence to an investigation

Select semantic profile `legalmath.semantic-investigation.v3` explicitly in
`CompleteInvestigation(..., semantic_options=options)`. Keep the existing
`settings` and `case_limit` keys. Supply serialized
`semantics.scoped_standards.Inputs` as `runner.run(..., semantic_inputs=value)`.
The v2 profile and disabled semantics reject this new input.

The input names the exact investigation packet hash, source catalogue, standards,
assessment, evidence documents, observations, declared premises and proposed
attachments. Construct it for the source edition and readings being investigated;
a different packet or missing reading/question attachment is rejected. Every
attachment names a reading hash, question hash and exact rule IDs, and states its
proposed warrant. Supplying a warrant does not establish that it is legally sound.
Rules without attachments and branches without rules remain explicit.

Observations describe events and their declared validity, exact actor/provider/
product/component/activity/jurisdiction, occurrence dates and knowledge date.
Their evidence documents retain UTF-8 text and its SHA256. The adapter derives
only the fixed `recorded.*` requirements returned by `recorded_requirement(kind)`.
Those definitions cannot be replaced with an adequacy, consent or title claim.
A ledger-entry event cannot supply customer-access; changed terms cannot supply
terms-acceptance. Relationships involving a different actor or provider do not
transfer. Negative observations require an explicit completeness premise.

Observed validity must cover the whole assessment interval. Partial intervals
are not pooled. The evidence must be known by the cutoff, and the event cannot
occur after it or after its stated knowledge date. A past appointment may have
declared validity over a later interval; the adapter does not infer that validity.
Late remediation never supplies a retrospective cure rule.

Use `PremiseEvidence` for separately supplied authority, interpretation and
factual-classification premises. Every declaration names its premise kind,
scope, evidence bytes and basis. An assertion about a rule's adequacy remains a
premise even when syntactically accepted. A quotation is not automatically
authority, applicability, factual truth or a sufficient interpretation.

The dossier's `semantic_stage.report.standards` contains original event records,
admission/exclusion reasons, declared and derived premises, four-state support,
conditional rule results, all branch attachments and unmatched rules. The full
v3 context is bound to every semantic branch and to the actual action journal.
Both `complete_investigation.verify` and
`investigation_observations.check_stages` reconstruct and check it. Changed
source, evidence, scope or attachment creates a different investigation revision.

The standards results are a separate Python computation. S3 does not lower them
to the legacy Java Boolean formula: `standards_lowering=NOT_IMPLEMENTED` and
`legacy_formula_relationship=NOT_ESTABLISHED` make that limit explicit. A failed
antecedent yields NOT_DERIVED and never proves an opposite legal conclusion.
Conflicting support remains distinct from absent or negative support.

For an executable local example, see
`scripts/legal_interpretation_s3_data.py::product_inputs` and
`execute_product`. That fixture combines exact retained SFC quotations locally
and labels its facts and diagnostic implications synthetic. It is not client
evidence, an official publication or a legal answer key.

The fixed master command is `python3 -m scripts.run_legal_interpretation_master resume`.
It selects only implemented, reviewed phases and writes immutable attempts.
Use `verify` for independent checking and `status` for the current phase.
