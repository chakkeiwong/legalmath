# P2: Make the disputed duties explicit

Status: PLANNED_NOT_EXECUTED. The [master program](../legal-interpretation-master-program.md)
controls evidence, default assumptions, resource limits and source-fidelity claims.
Revision 2 — 6 October 2026. Incorporates the [Claude review response](../../implementation/legal-interpretation-program/claude-review-response.md); implementation checks remain pending.

Dependencies: P1.

## Question and inputs

Which different executable consequences follow from the retained paragraph-10 and paragraph-14/footnote-5 readings?

P1 records; full frozen source units and their referenced definitions/footnotes; P0 operative corrections. Read complete relevant clauses and dependencies rather than selected snippets alone.

## Implementation

1. Implement semantics/clauses.py to express actors, activities, objects, quantifiers, modality, conditions, exceptions and cross-reference attachment. Treat a source extraction as a proposed interpretation with warrants and objections. Implement a proposed `clauses.propose(packet, question, retained_proposals, policy)` interface that consumes actual retained investigator proposals and source relations; record unrepresented concerns rather than relying only on hand-entered settled examples. Fresh model generation, if later justified, remains separately budgeted and supplies proposals only.

2. Decompose paragraph 10 into responsibility allocation, supervisory conduct and operational adequacy. Bind footnote 1 explicitly: paragraph 10 says “ultimately responsible”, while footnote 1 says “fully responsible” despite outsourcing and refers to UT Code 6.8 and Tokenised Securities Circular Appendix Part A “where applicable”. Preserve both cross-references and their unresolved applicability premises. No word substitution alone establishes full liability. Construct retained rival readings and newly exposed unsupported combinations without assuming this exhausts the law.

3. Separate paragraph 14's confirmation and demonstration from paragraph 15's third-party verification and paragraph 16's legal opinion. Decompose paragraph 14/footnote 5 along **trigger, object and standard**. Paragraph 14 names management/operational soundness, ownership record keeping and smart-contract integrity, with demonstration “to the SFC's satisfaction”. Footnote 5 names compliance with paragraphs 10–13 and absence of contract vulnerabilities or security flaws, using “at a minimum” and “with a high level of confidence”. Preserve the source wording and alternative attachments of these standards; do not import a numerical confidence threshold. No document-order, typography or footnote default decides priority.

   Inventory at least the following source-warranted proposals: A, request-conditioned paragraph-14 demonstration with the footnote relation still disputed; B, a standing footnote demonstration duty; C, footnote minimum content inheriting paragraph 14's trigger structure. Each must carry its source warrant, assumptions, objections, object and standard, including unresolved content relations. Check whether retained proposals supply each variant. If one is absent, record a separately identified sourced development nomination and unrepresented concern; do not label a hand-entered nomination a retained model proposal or legal answer key. Preserve further supported alternatives.

4. Create source-linked scope diagrams and controlled-English renderings of each branch. Mark constitutive classifications separately from duties; preserve SHOULD without importing a sanction or civil-liability rule.

5. Generate distinguishing assignments from the declared formal alternatives, including retained authority with failed operations, no request, and request present. Compute the no-request query over the full A/B/C inventory: A and C may agree on its trigger under their assumptions while differing on object or standard. Add query/object/standard-sensitive assignments with request present to expose those differences. Keep evaluative standards as explicit inputs or unresolved premises when no sufficient rule exists. Record equality only for the tested proposition and declared domain. These conditional consequences are not legal answer keys.

## Files and validation commands

Proposed semantics/clauses.py; pilot-reading specification and source-to-premise map in the phase output. Store all alternatives and unresolved source relations.

The following test files are planned deliverables, not existing executed tests.
After implementing them, run these exact forms from the repository root:

```text
.venv/bin/python scripts/legal_interpretation_ops.py phase-tests P2
```

Add the relevant existing regression paths discovered from actual touched imports.
Record those exact paths in the phase revision before executing; do not invent a
successful regression result or invoke a broad suite unrelated to the change.

## Discriminating challenges

Condition attaches to the wrong duty; the footnote's object or standard is silently replaced by the paragraph's; trigger-only agreement is reported as full agreement; “ultimately” becomes “fully” without a warrant; UT Code 6.8/Appendix Part A applicability is assumed; a footnote is ignored; responsibility is equated with good outcomes; SHOULD becomes MUST; a provider's act is attributed to an intermediary; every branch is out of scope.

## Acceptance and failure decisions

Each proposed duty has a recoverable actor/action/modality/trigger/object/standard/scope representation. test_clauses.py requires footnote 1 and both cross-reference dependencies with unresolved applicability. test_pilot_readings.py requires the A/B/C inventory or explicit unsupported representations, distinct object/standard records, and the inheritance variant. Query-specific generated assignments expose differences or prove equality only in an explicitly bounded formal domain. Omitting an unsupported proposal to obtain agreement fails acceptance.

If the schema cannot express a plausible reading, preserve it as unsupported and repair P1. If authority cannot choose between readings, keep both. A source quotation alone cannot mark a semantic relation proved.

## Result and next-phase refresh

P3 receives the branch inventory, supporting and opposing warrants, unrepresented concerns, and generated inputs distinguishing the branches. Revise its argument vocabulary to those actual disputes.

Save the executed plan version, input/output hashes, commands, results,
uncertainties, decision and refreshed successor plan under the immutable attempt
directory specified by the master. A planned test command is not run evidence.

Resource boundary: Offline development first. A future proposal generator may nominate readings only under a separately recorded provider route; it cannot supply acceptance labels.
