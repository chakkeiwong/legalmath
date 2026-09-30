# Two-case bond reader repair: execution results

30 September 2026. Santander and Unilever now have qualified feature results.
Santander is positive for compulsory common-share conversion. Unilever is
negative within the selected offering documents. The original 26 answers are
unchanged. The extended frozen challenge adds an ABN AMRO positive and an Enel
abstention: the combined report has **30 series, 14 positives, 15 negatives and
one unresolved result**. These are source readings, not a legal-accuracy score.

The implementation and native runs completed before the editor crash. Recovery
verified their hashes and completed the report build and review. The protected
[baseline](baseline/results.md) and every failed attempt remain available.
The [eight-page PDF](../bond-loss-absorption-classification/results.pdf),
[full report](../bond-loss-absorption-classification/results.md),
[JSON](../bond-loss-absorption-classification/results.json), and
[source index for all 30 cases](../../prospectus/CASE-INDEX.md) are current.

## What changed and why

Santander Condition 5.1(c), PDF page 103, puts its conversion action in a numbered
list governed by the Bank's obligation at the start of the list. The repaired
reader retains that actor, obligation and action together, recognises the
copular mandatory-conversion construction, checks the Common Shares definition
on page 86, and retains holder-option and consent conditions. A prohibition on
optional holder conversion does not negate an independently mandatory action.

The recovered Unilever memorandum is the 16 May 2025 edition named by the
selected 20 May final terms. The EUR 1,000 calculation amount and equal final
redemption amount provide the repayment relation. Blank programme forms supply
no selected terms. All 131 memorandum pages are examined, but the separate trust
deed, incorporated financial/constitutional documents, later amendments and
complete applicable law remain outside proved source closure. The negative is
conditional on the declared sources and the bounded English analysis.

The initial construction baseline failed 28 of 47 new checks. The first repair
then passed 430 focused checks, but further adversarial inputs exposed seven
errors involving holder consent, election, and hypothetical/reporting context.
The second repair passed 443 focused checks. These retained failures explain
the scope repairs; they are not omitted from the successful outcome.

## Evidence and interpretation

The archived full prospectus regression has **585 passes, zero failures, zero
errors and zero skips**, including 443 classifier/presentation checks. The two
completed native runs contain **156 executions**: 104 for the 28-case corpus
and its formal challenges, and 52 for the two new cases and formal challenges.
The independent finite specification covers all 256 declared input states;
two SMT obligations, four deliberately wrong formal variants and kernel-checked
lowering are recorded. These properties are conditional on the formal premises.

Delivery verification rechecked 30 derivations and **7,584 source quotations**
against 40 preserved documents containing 3,430 text pages/units. Twenty source
faults were rejected or left unresolved, including 14 mutations of the two
repaired cases. Source identity and exact quotation checks cannot prove English
meaning or discover every applicable contract or law. The rechecked method is
identical to the freeze; the archived regression hash is unchanged.

ABN AMRO and Enel were acquired after that freeze under a recorded issuer order.
Vodafone came first in the corporate category; its final/base downloads failed,
and those failures remain preserved. Enel was selected next before classification.
Its calculation-amount field includes a parenthetical label without the colon
required by the frozen parser. The unit relation remains unresolved; senior
ranking cannot justify filling it in. This is a coverage failure of the present
reader. It does not invalidate the source data, harness, formal target or research
direction. Santander and Unilever are now exposed development cases.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain the two-case repair | Constructed obligations, source witnesses, original-26 comparison and recorded native checks pass | No remaining integrity/formal mismatch in the checked domain | Shared bounded English constructions | Deliver qualified results with exact source links | Universal English or legal correctness |
| Retain Unilever's qualified negative | Named edition, selected repayment fields and candidate checks pass | Missing declared dependencies and tampering force abstention | Incorporated documents and later law are not closed | Extend dependency analysis separately | Principal can never be lost |
| Preserve partial frozen transfer | ABN AMRO supports the feature; Enel abstains | Enel blocks a complete-coverage claim; no continuation veto | Unfamiliar field layout | Separate field-parser study, then a new freeze and new families | Successful transfer on both cases or rejection of the research direction |
| Complete report delivery | All 30 rows and all prose survive PDF comparison; every rendered page inspected | No build/layout/content-loss finding | Human prose acceptance and legal interpretation are separate | Commit and integrate without concurrent-work loss | PDF build certifies legal meaning |

| Inference status | Evidence |
| --- | --- |
| Hard veto screen | Altered sources, wrong editions, missing dependencies and inconsistent formal evidence are rejected in the recorded checks. Enel remains unresolved. |
| Statistically supported ranking | None. This deterministic, selected-corpus study estimates neither accuracy nor comparative superiority. |
| Descriptive-only differences | Two prior abstentions now resolve; the two additional families produce one positive and one abstention. |
| Default-readiness | No promotion to a general legal-interpretation default. |
| Next evidence needed | Construction-derived field/condition tests, separately frozen unfamiliar families, document closure and authoritative-language investigation. |

## Remaining work and post-run red team

The next parser study should accept justified variations in calculation-amount
field punctuation and parenthetical layout while rejecting coupon amounts,
minimum denominations, wrong currencies and terms from a different series.
Enel must then be treated as exposed development material. Preserve its current
abstention and freeze the revised method before acquiring new challenge sources.

The strongest alternative explanation is adaptation to the observed language
families. Enel's abstention demonstrates that ordinary unseen layouts can still
break coverage. A forged or misbound witness, inconsistent formal result, wrong
edition, or unsupported binary answer on a constructed contrast would overturn
the corresponding bounded finding. English relevance and complete source closure
remain the weakest evidence, particularly for negatives. No human answer labels
or model-majority quality scores were used.

The report classifies a specified prospectus feature: principal write-down or
compulsory common-share conversion, including disclosed statutory powers.
It does not determine SFC complexity, suitability, sanctions compliance,
transaction permission or investment risk. Existing issuer-language and mirror
qualifications remain in the full report. Positive rows can contain unresolved
subsidiary clauses because a sufficient witness does not settle every mechanism.

## Reproduction and records

Use the isolated source snapshot and PYTHONPATH=src with the existing virtual
environment. Runs are deterministic and CPU-only. Original run manifests include
commit, environment, sources, commands, wall time and artifact hashes. The
recovery delivery manifest records its own commands and limits; its new checks
are not presented as another 585-test or native execution run.

- [Reviewed plan](../../plans/bond-two-case-repair.md)
- [Resumption audit](resume-audit.md)
- [Original corpus manifest](corpus-001/run-manifest.json)
- [Frozen challenge manifest](fresh-001/run-manifest.json)
- [Full regression](prospectus-regression.xml)
- [Method freeze](../bond-loss-absorption-classification/execution/freeze-two-case-v3.json)
- [Delivery manifest](delivery-001/run-manifest.json)
- [Rendered-page review](delivery-001/visual-review.json)
- [Recovery checkpoint](RESET.md)

Implementation commit 10272593 was integrated into main, pushed, and
fast-forwarded into the clean Catala checkout. Its 301 frozen source files were
verified there. The [integration receipt](integration-receipt.json) preserves the
commit, narrow stash, and concurrent-work checks. A documentation-only follow-up
records this receipt. The unrelated assurance campaign remains in progress.
