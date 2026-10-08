# What the tool tests established

8 October 2026. The reviewed program ran all five phases and verified its
retained evidence. It used 62 of 96 provider reservations and seven of twelve
repair entries over approximately 105 minutes. Its result is
**INCOMPLETE_WITH_EVIDENCE**: the tests identify useful tool capabilities and
specific product defects, but do not establish complete integration or resolution
of the legal questions. All 46 original obligations remain open; 32 of the 35
original readings remain unformalized.

The [governing program](../../plans/legal-tool-gap-validation-program.md) contains
the evidence criteria, reviewed assumptions, phase refresh mechanism and stop
conditions. The [machine-generated report](../../../artifacts/legal-tool-gap-validation/2026-10-08/G4/attempt-1/result.md),
[decision](../../../artifacts/legal-tool-gap-validation/2026-10-08/G4/attempt-1/decision.json)
and [run manifest](../../../artifacts/legal-tool-gap-validation/2026-10-08/G4/attempt-1/run-manifest.json)
preserve the executed comparison and its limits.

## Tool results

| Tool or method | What ran and what it established | Limit for the product gaps |
|---|---|---|
| PyArg and Carneades | Both matched the declared local grounded/preferred semantics on 65 graphs derived from the retained product graph. | Agreement checks computation on supplied arguments. No completed live product graph was available for the final integration test; source-to-argument accuracy remains open. |
| LegalRuleML | Fourteen conditional rules, three paragraph-14 controls, three original paragraph-10 Boolean readings and six newly generated product expressions passed their schema/preservation checks after the identifier repair. Mutated conditions/source references were detected in the applicable controls. | Preserves the selected representation; it does not establish its legal meaning. The 32 unformalized original readings remain outside the supported profile. The live combined trial reached no successful XML check. |
| Logical English | The author's example, legal conditional, changed-trigger and malformed declaration/query controls passed after a repair confined to a local copy of the pinned parser. | Controlled-language execution is demonstrated for these inputs; general English interpretation and source equivalence are not established. |
| Lexical retrieval and BM25 | All 46 original gap queries and 35 reading queries ran in three modes with exact source offsets. In the separate four-question development set, lexical overlap found 12/22 targets, whole-unit BM25 16/22 and window BM25 10/22. | Passage retrieval missed useful text. These are descriptive location checks with unequal text budgets, not legal accuracy or superiority estimates. |
| eyecite | US full-citation and Id. controls worked; both HK citations and the UK control were missed. | Target-jurisdiction citation coverage is insufficient. Extraction supplies no later-treatment or authority determination. |
| Case factors and authority functions | Ten target-boundary controls across the two judgments preserved unresolved authority and rejected unknown factor sources and submissions mislabeled as holdings. | The functions check references and declared status. An automatic consent/analogy classifier is not implemented. HYPO/CATO/AGATHA reuse is conceptual, not deployment of their original engines. |

The 46 gap queries had 113 inherited citation-target occurrences: lexical overlap
retrieved 77, whole-unit BM25 81, and window BM25 24. All inherited quotes occurred
in the frozen corpus. These labels come from earlier model role responses rather
than independent legal annotation; the 35 reading queries have no relevance
labels. Across all 81 queries, retrieved character totals were 4,213,526,
3,874,612 and 513,255 respectively. The markedly different text budgets and the
requirement that a whole quoted target fit within one passage preclude treating
these counts as a fair accuracy ranking.

The other candidates received recorded prerequisite/overlap decisions, not
invented integration passes. SARA-IE lacks a verified root reuse licence and
target extraction protocol; the original CLERC engine/corpus remains unqualified;
MAPIE lacks an independent target calibration set. Tweety/s(CASP), KeY and
LangGraph lack a distinct justified test for the present gaps beyond the existing
reasoning, proof and orchestration mechanisms. Existing OCR, document processing,
code and proof tools were retained where applicable, without a new claim that
all were exercised by the incomplete product trials. The exact dispositions are
in the frozen [benchmark](benchmark.json).

## Live answers and actual product integration

The four questions, four conditions and two repetitions produced 32 answers.
Thirty-one passed structure and exact-quotation checks. One Gatecoin answer
contained altered quotations and nonexistent source IDs and remains rejected.
Seven of the eight original Gatecoin answers also wrongly compared a combined
packet hash with individual judgment-file hashes. Both later diagnostic answers
corrected that distinction when given the verified object types and retained
the legal qualifications. These two diagnostic successes do not replace the
original failures.

Both full product trials were incomplete. The baseline retained twelve
candidates but timed out during fidelity checking, did not complete criticism,
and stopped at an incompatible grant interface. Its fidelity representation
also dropped the candidate's explanation that a Boolean result meant duty
activation. That led the reviewer to attribute a fulfillment claim that the
original candidate had expressly excluded. The combined trial timed out during
generation, produced no candidates, then wasted three requests assigning
questions to an empty candidate set. Neither produced a final dossier or graph.

The primary combined trial made eight retrieval calls but used task names as
queries. The adapter now extracts the actual selected question. It made zero
successful live graph or XML checks. The six successful XML checks on baseline
candidates were subsequent offline checks and did not influence those answers.

The grant-interface repair uses the existing authorization and shared call
ledger. It enabled both arms to complete two scoped perspectives on identical
retained baseline records. All four responses kept the narrow DUTY_TRIGGER
question distinct from responsibility fulfillment, while preserving the
footnote alternative. This verifies that stage and its authorization adapter.
It does not recover the combined trial's failed generation or demonstrate that
retrieval caused the correct answers. See the [substantive review](g3-final-review.md)
for the comparison and alternative explanations.

## Remaining product work

The [46-gap matrix](../../../artifacts/legal-tool-gap-validation/2026-10-08/G4/attempt-1/gap-tool-matrix.json)
retains each original identity and its missing premises. Categories overlap:
31 obligations need authority/applicability evidence, 31 need factual inputs,
28 involve source interpretation, 27 need a normative standard, nine involve
question mismatch, and five involve representation. More successful solver calls
cannot by themselves supply those premises.

The next justified product work is specific:

1. Preserve candidate meaning and typed question identity before broad fidelity
   review. Verify on the retained failure that a trigger is judged as a trigger,
   and that a fulfillment question still requires substantive performance.
2. Stop downstream dispatch when generation yields no candidates; retain a
   recoverable failed stage. Test timeout recovery on the exact retained product
   request before attempting a new full comparison.
3. Complete matched baseline/combined investigations that return dossiers and
   graphs, and confirm that external checks actually reach subsequent reasoning.
   The current scoped replay cannot substitute for those missing stages.
4. Obtain the warranted legal standards, source/footnote reconciliation, current
   authority analysis and dated client records identified by each original gap.
   Formalize a reading only to the extent those premises support it.

These are remaining requirements, not automatically appended phases or a newly
authorized experiment. The failed trials do not reject tool reuse as a direction;
they show that its complete downstream benefit has not yet been measured. The
unused allowance is a ceiling, not a reason to repeat a known inadequate trial.

## Execution and verification

The fixed runner is `scripts/run_legal_gap_program.py`. From the repository root,
with shell login disabled, its allowed forms are:

```text
.venv/bin/python scripts/run_legal_gap_program.py check
.venv/bin/python scripts/run_legal_gap_program.py setup
.venv/bin/python scripts/run_legal_gap_program.py execute
.venv/bin/python scripts/run_legal_gap_program.py status
.venv/bin/python scripts/run_legal_gap_program.py verify
```

The already approved setup installed
`/home/chakwong/.codex/rules/legalmath-gap-validation.rules`. Positive and negative
policy checks passed for these forms. The CLI rejects arbitrary shell actions,
provider URLs and budget overrides. Existing managed approval review still
applies; the repository cannot promise zero host prompts.

Sixteen focused harness tests passed before the final execution. G4 preserved all
46 obligation identities, all 35 reading identities and all three retrieval modes
per record. The three original Boolean readings passed; the 32 others remain
explicitly UNFORMALIZED. All ten case-boundary controls had their expected
outcomes. The exact `verify` command returned VERIFIED for G0–G4 with 62
reservations and the unchanged INCOMPLETE_WITH_EVIDENCE verdict. Verification
confirms retained engineering evidence, not legal correctness. No commit, push,
provider substitution or production-default promotion was performed.
