# ODRL implementation contracts and acceptance cases

Status: proposed engineering semantics, 22 October 2026. These contracts refine
section 8.3 of the proposal. The retained 2023 bundle is a historical case;
implementation, legal certification and current regulatory completeness are not asserted.

## Meaning, observations and results

PolicyInterpretation owns stable norm identities, source-version hashes, exact
occurrences, raw wording/modality, interpreted norm kind, actor, affected party,
action, object, applicability, conditions, exceptions, temporal rules, sourced
priority, evidence requirements, calculation references, interpretive alternatives
and unresolved dependencies. Its norm kinds include permission, prohibition,
duty, dispensation, definition and state-changing power. Retaining a norm does
not imply that the selected ODRL profile executes it. Raw wording such as “should”
is retained beside the interpreted effect; each mapping needs a source argument.

A calculation reference identifies the LegalRuleModel hash, rule ID, input types,
unit, domain, premises and result type. Its receipt binds request, client,
intermediary, account, category, valid time, knowledge time, observation hash,
calculation version and component results. An unbound eligible=true assertion
or reviewer/model score is not a fact. Agreement with a reviewer is not a
source-entailment proof.

Every source unit has one primary disposition: exported, retained as
interpretation/dependency, deferred with reason, or unresolved. Additional links
may associate it with several norms. Cover headings, annexes, footnotes and
external references. A dropped FAQ is visible in the source denominator even
if every emitted RDF rule validates. Missing Code of Conduct or Professional
Investor Rules dependencies remain explicit conditions, not presumed complete.

The individual financial limb is portfolio >= 4,000,000,000 HKD cents OR net assets
excluding the primary residence >= 8,000,000,000 cents. It is not full SPI
qualification. Use exact integers with explicit allocation/FX evidence. Net
assets after liabilities and residence exclusion can be negative under Annex 1
paragraph 3.3. Support that signed result; a negative asset limb must not prevent
an established portfolio limb from satisfying the disjunction. The existing
nonnegative-only financial helper cannot be reused unchanged for this domain.
Portfolio/exposure/threshold amounts remain nonnegative. Invalid types or units
produce an input error, not ineligibility. Other client types stay outside the
initial individual-client profile until separately specified.
The initial arithmetic consumes assessed integer-cent totals. Allocation or FX
that produces fractional cents needs retained exact intermediate values and an
explicit reviewed rounding rule to supply those totals; otherwise it remains
unresolved. Do not truncate a share or conversion silently at a threshold.

Paragraphs 3.2(c) and 3.4(a)(iii) specify an equal share for joint holdings with
non-associates in the absence of a written allocation agreement. Known absence
with known account holders therefore permits the source-specified allocation;
unknown agreement/holder information remains unresolved. Associate accounts
and qualifying wholly-owned investment-holding corporations have distinct
source conditions. Do not invent a universal written-allocation prerequisite.

The conditional amount expression is (gross <= maximum) OR
(valid_designated_arrangement AND NOT adding_funds). Arrangement validity includes
the declared controls; an account name is insufficient. Bind Annex 1 paragraphs
8.1–8.5 and Annex 2 FAQs 6–7. Gross exposure must account for leverage and the
required transferred-out noncash exposure. The proposal's initial pair uses
gross HK$12m and threshold HK$10m, with all other premises expressly stated.
The threshold may be an absolute amount or a percentage of AUM (paragraph 8.1).
The initial calculation consumes a sourced amount: percentage conversion needs
its exact ratio, bound AUM valuation, effective date and rounding interpretation.
Unspecified conversion stays unresolved. Preserve the setting rationale, review
before new funds, annual discussion, material-transaction warning and breach
alert requirements as separately evidenced conditions/duties or explicit deferred
scope; the amount Boolean does not establish them.

Known false, unknown and conflict stay distinct. Proposed Boolean combination
for known/unknown inputs uses true OR unknown = true and false AND unknown =
false; unused unknowns remain in explanations. A conflict in a referenced
premise blocks the affected decision as CONFLICT even if a separate branch is
true. This conservative policy is an engineering hypothesis, not supplied by
the circular, and belongs to the profile version. Unrelated conflicts do not
contaminate other requests. Explicitly reconcile complete/partial model behavior.

Keep separate result fields:

- Processing: OK, INVALID_INPUT, INTEGRITY_ERROR or UNSUPPORTED, with reasons.
- Procedure permission: PERMITTED, NOT_ESTABLISHED, UNKNOWN, CONFLICT or
  UNSUPPORTED. PROHIBITED requires a supported explicit applicable prohibition.
- Each duty: inactive, pending, fulfilled, violated or unresolved, plus a separate
  later-cure record. Activation is not performance.
- Scope, premises, source conditions, missing facts and unsupported constructs.

NOT_ESTABLISHED means failure of this streamlined route on known facts. It says
nothing about general permission to trade. An operational service may withhold
a procedure pending evidence, but must not rewrite an unknown legal result as false.

The first profile is hkma-spi-eligibility-v1; hkma-spi-duty-v1 adds supported
duties later. Bind action applyStreamlinedApproach, request target, intermediary
assignee, context, vocabulary, operators, schemas and executable semantics. These
are LegalMath profiles, not HKMA-issued profiles. A local URN namespace is an
initial engineering choice; public IRIs need a controlled persistent namespace.
Do not deploy example.org identifiers from the illustrative proposal.
Use odrl:Set; regulatory authority belongs in source provenance rather than an
invented transaction assigner. Classify validation findings as W3C core,
LegalMath profile or project metadata requirements. Source metadata must not
accidentally become a claimed W3C condition.

Unknown profiles, unimplemented operators, unreviewed priority, inherited policies,
temporal andSequence, remedies and consequences yield explicit UNSUPPORTED before
a permission result. Descriptive export may retain them as unresolved metadata.
Executable export cannot silently omit them. Narrowing scope after a failed test
requires a new profile version and invalidates acceptance of the previous scope.

## Time and duties

Use explicit UTC instants for ordering, retain Asia/Hong_Kong as business calendar
context and preserve distinct recorded/knowledge times. Proposed effective
intervals are [from, until). Same-time ambiguous amendments yield unresolved
order unless an explicit sequence resolves them; ingestion order is not legal
priority. Reject naive timestamps. Calendar conventions require boundary and
leap-day checks before automation; do not replace years with fixed day counts.

Consent records bind client, intermediary, categories, threshold, execution time,
effective interval and evidence. Require valid prior agreement and continuing
state; later consent cannot retroactively authorize an earlier request. Withdrawal
closes the corresponding state. Category/threshold amendments preserve earlier
states. Replay uses what applied and was known then; corrected evidence produces
a separate reassessment. A consent snapshot must be computed from bound evidence,
not accepted as an unqualified Boolean.
The prior package includes all paragraph 13.1 components: written agreement,
written assessment criteria, written categories/threshold and explanation of
consequences/withdrawal. Paragraphs 7.2, 8.2 and 12 require their own information
and record evidence. A signature alone is insufficient. Where evidence of these
premises is missing, report the affected condition as unknown; do not strengthen
FAQ 1 into a universal documentary-proof requirement for financial disclosures.

Annual review is recurring, not an up-front obligation to complete all future
reviews. Require an assessed due date with its basis where the calendar rule
remains interpretive. Missing interpretation yields unresolved. Performance
records identify the cycle, qualification/agreement checks and required reminders.
One review cannot discharge all cycles; late performance cannot erase prior breach.

Explanation/material-query duties bind request, client, duty and required
response. A response for another transaction cannot fulfill them. Dispensations
identify the ordinary duty and condition granting relief; export supported
remaining duties with links to relieved duties. An unresolved external ordinary
duty makes the result conditional. Relief is never a prohibition of the procedure.

## Module, API and file boundaries

Create src/legalmath/odrl/ with model.py, source.py, profile.py, facts.py,
events.py, export.py, validation.py, verification.py, cli.py and
evaluators/base.py and evaluators/oval.py. Add an alternative only through R08
and its declared trigger. Import existing source identity, exact-value and model
validation functions where their contracts fit. Keep regulatory norm classes
separate from the bond recognizer's effects.

Proposed Python interfaces, not callable today:

    export_policy(interpretation, profile, output_dir) -> ExportReceipt
    validate_policy(export_dir) -> ValidationReport
    evaluate_policy(export_dir, request, observations, events, valid_at,
                    known_at, evaluator_config) -> EvaluationReport

Keep these separate from translation.pipeline.build, which assumes RuleIR/Catala
and Java artifacts. Proposed CLI: python -m legalmath.odrl export|validate|evaluate,
with explicit paths, profile/config and decision/knowledge times. Help and an
isolated example must work from an installed wheel. Known negative outcomes are
not process failures; malformed input, unsupported operation and integrity error
need distinct documented machine reports and nonzero exits. Refuse to overwrite
an output directory with different bindings.

Export files: policy.jsonld, optional policy.ttl, interpretation.json,
source-map.json, coverage.json, capabilities.json, validation.json and manifest.json.
Evaluation adds snapshot/event history and evaluation.json. Manifest identities
cover source, interpretation, profile, shapes, exporter, dependencies, configuration,
calculation model and any Catala build. Canonical JSON byte identity and RDF graph
isomorphism are separate checks; neither is a semantic-equivalence proof.

Profile assets originate under schemas/odrl/hkma-spi/. The current package-data
configuration does not include that new top-level directory: K17 must arrange
one authoritative asset source, include the bytes in the wheel and verify them
after installation. Tests go under tests/odrl/ and tests/fixtures/odrl/hkma-spi/,
both new. A released example must use permitted packaged fixtures or explicit
hash-checked public-source acquisition; local research cache paths alone are
not a portable release dependency.

Resolve JSON-LD contexts and SHACL imports only from pinned local resources in
the pilot. Disable remote fetches and implicit network loads. Treat documents
and policy strings as data, refuse path/symlink escape, and never execute generated
Python. E04 measures the real bundle before choosing finite input/event/RDF
limits; record provenance and reject resource excess as an error, not a legal finding.

## Substantive acceptance inventory

These are obligations to write independent cases, not existing test results.
T03 retains exact source spans, premises, expected fields and reasons. Write
expectations without calling candidate exporters/evaluators; do not import their
expressions. A single author may do this work, so independence means separate
specification/implementation, not independent human adjudication.

| ID | Source basis | Required contrast and expected distinction | Owner |
|---|---|---|---|
| F01 | Annex 1 paras 1–5 | HK$40m equality/one cent below, independent HK$80m limb, both below; negative net assets with passing portfolio and with failing portfolio; qualification distinct | F06/Q10 |
| F02 | Financial provisions | Missing portfolio plus established asset limb can pass; neither established UNKNOWN; referenced conflict CONFLICT | F06/Q10 |
| F03 | Annex 1 para 4; FAQ 2 | Degree or postgraduate diploma, finance qualification, one-year experience and five category trades are distinct routes | F06/Q10 |
| F04 | Annex 1 paras 4–7 | Four/five trades, wrong category, incomplete history, three-year boundaries and representative attribution | F06/Q10 |
| F05 | Objectives/PI provisions | Wealth alone insufficient; missing PI, conservative/unknown objectives; no invented numeric reasonable-satisfaction score | F06/Q10 |
| F06 | Paras 3.2–3.4 | Written non-associate allocation vs known absence/equal-share rule vs unknown agreement/holders; associate/corporation scope, liabilities, residence exclusion, explicit FX | F06/Q10 |
| F07 | FAQ 3 | Loss-absorption product category; bond label cannot override operative terms | F06/Q10 |
| F08 | Paras 8.1–8.5; FAQ 6 | HK$12m/HK$10m valid designated internal transaction satisfies amount limb; matching top-up fails; ordinary route distinct | F06/Q10 |
| F09 | Paras 8.1–8.5; FAQs 5–7 | Gross leverage/noncash exposure, percentage/AUM conversion, rationale and required monitoring/review premises, no invented unwind duty | F06/Q10 |
| F10 | Paras 7.2/12/13.1; FAQ 4 | Missing/later/continuing consent; missing written criteria/categories/threshold or consequences explanation; wrong client/account/category, stale or mismatched receipt | F06/Q10 |
| F11 | Para 13.1(d) | Withdrawal changes later requests; historical replay retained; late evidence produces reassessment | F06/Q10 |
| F12 | Paras 13.2(c)(iii)/(d)(iii) | Category/threshold amendments, overlap and ambiguous order; old state retained | F06/Q10 |
| F13 | Paras 10–11 | Solicited/unsolicited, complex product, information conditions; relief preserves surviving duties | D11/Q13 |
| F14 | Paras 10–11 | Explanation/material query, matching performance vs unrelated response | D12/Q13 |
| F15 | Para 14; paras 8.3–8.5; FAQ 6 | Due/completed review, omitted reminder/breach alert, second cycle, late cure, unresolved date; designated-account review before new funds/annual review remains separate from amount test | D12/Q13 |
| F16 | FAQ 1 | Consistent disclosure and reasonable KYC vs contradictions; no invented universal documentary proof | F06/Q10 |
| F17 | Profile contract | Unknown profile/operator/IRI, reassigned target, remote context, malformed RDF and empty SHACL target coverage fail visibly | X07/V08 |
| F18 | Correspondence contract | Independent exact financial and amount results agree on declared inputs; actual Catala checks only when run on its stated domain; unknown/conflict retained | C09/Q10; C09C for Catala |
| F19 | Version/source contract | Dropped annex, altered hash, broken reference, hidden premise or changed event/profile invalidates affected output | S01/X07/K17 |
| F20 | Install/replay contract | Clean-wheel CLI, local assets, exact replay, changed inputs and partial output recovery | K17 |

T03 expands the families into concrete cases; no finite case count substitutes
for source coverage. Every interpretive alternative retains conditional expectations.

Required mutations: M01 >= to > (F01); M02 financial OR to AND (F01/F02);
M03 drop FAQ 6 (F08); M04 omit consent (F10); M05 ignore withdrawal (F11);
M06 count unrelated categories (F04/F07); M07 relief to prohibition (F13);
M08 unknown to false (F02/F10); M09 activation to fulfillment (F14/F15);
M10 unrelated performance (F14); M11 empty shape targets falsely pass (F17);
M12 replay after changing profile/evidence (F19/F20); M13 unbound eligible=true
(F10/F19); M14 omit leverage/noncash exposure (F09);
M15 invent a written-allocation prerequisite instead of the equal-share
rule (F06); M16 reject signed net assets before testing the portfolio alternative
(F01); M17 treat a signature as the whole prior-information/explanation package
(F10). Retain a witness per mutant. A surviving mutant blocks the affected claim
and triggers diagnosis.

## Evidence contract and promotion

Question: does this supported projection preserve declared procedure eligibility
and duty outcomes on the historical bundle? Comparator: separately specified
source-based cases and, for common arithmetic only, exact references and selected
Catala computations. Primary criteria: exact expected result fields on mandatory
cases, complete source dispositions, implemented unsupported/result semantics,
mutation witnesses and install/replay integrity. Wrong permissions, lost exceptions,
fabricated prerequisites, silent unsupported terms or collapsed unknowns veto
promotion. Invalid source/input/harness evidence must be repaired before interpreting
a candidate failure. Engine failure does not invalidate the entire direction.

RDF conformance is necessary for graph release, not proof of source fidelity.
Coverage percentage, test count, model-judge scores, speed and compilation are
explanatory diagnostics. No aggregate score compensates for semantic loss.
Catala/evaluator agreement cannot prove their shared source interpretation.

Every implementation run retains commit, dirty-path hashes, command, environment,
source version, evaluator/configuration, seeds where relevant, CPU-only status,
wall time, plan, input/output hashes and result note. Deterministic seeds are N/A;
no GPU is needed. Separate source argument, engineering correctness, conditional
formal proof and experimental evidence.
