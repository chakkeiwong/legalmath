# Bond feature classifier: current recovery checkpoint

30 September 2026: the two-case repair and report delivery are complete. The
current report covers **30 bonds: 14 qualified positives, 15 qualified negatives
and one abstention**. Santander and Unilever now resolve, and the original 26
answers are unchanged. ABN AMRO is positive; Enel's calculation-unit field
remains unresolved in the frozen new-family challenge.

The [eight-page PDF](results.pdf), [JSON](results.json), [CSV](results.csv) and
[verification](execution/delivery-verification.json) are current. The complete
[results and limits](../bond-two-case-repair/RESULTS.md),
[active plan](../../plans/bond-two-case-repair.md), and
[recovery checkpoint](../bond-two-case-repair/RESET.md) replace the earlier
28-row delivery instructions. The original baseline remains protected.

585 archived tests and 156 recorded native executions passed. Recovery verified
the unchanged freeze and run artifacts, rebound 7,584 source quotations and
rebuilt/inspected every PDF page. No universal English/legal correctness or
future accuracy is established. The next parser study must preserve the Enel
abstention and use a separate freeze.

The shared main checkout contains an unrelated assurance campaign. Preserve its
unfinished changes. Implementation commit 10272593 is pushed and synchronized with the clean
Catala checkout. The [integration receipt](../bond-two-case-repair/integration-receipt.json)
records the narrow preservation stash and concurrent-work checks. The following material is historical, with
its original counts and limits retained for comparison.

## Historical v1 campaign and diagnosis

The following records describe the protected pre-repair baseline. Their old
counts, Shell limitation and future-tense repair instructions are historical.

Recorded 29 September 2026. Current outputs:
[readable results](results.md), [CSV](results.csv), [JSON with evidence](results.json),
[delivery verification](execution/delivery-verification.json).
26 issue rows: 12 loss absorption, 13 non loss absorption, one unresolved.
Preferred-share securities are excluded. Do not describe the unresolved Shell
row as either a negative or a positive.

The requested UK corporate Tesco and EU corporate Veolia issues return
negative with affirmative principal repayment terms and no unresolved feature
candidate in their declared offering documents. Compass, the eight US
senior/junior controls and CBA also return qualified negatives. CoCos, Sogécap
insurance capital, and NatWest/BPCE senior debt with disclosed statutory
principal-loss provisions return positive. Sector and rank do not determine
the answer. Ordinary creditor-approved restructuring is separately recorded
under the working definition adopted for the user's negative controls.

## Implementation and commands

`loss_absorption_reader.py` validates preserved sources, selected editions and
candidate clauses; `loss_absorption.py` implements a four-premise decision and
generated explanations. `loss_absorption_checks.py` supplies independent
finite/SMT checks and native RuleIR/Java and Catala execution. The source reader
is a bounded recognizer, not an independent proof of English legal meaning.

```
.venv/bin/python scripts/build_bond_feature_inventory.py
.venv/bin/python scripts/run_bond_loss_absorption_classification.py --inventory docs/prospectus/classification-additions/issue-inventory.json --output /tmp/bond-feature-new-run --checks
.venv/bin/python scripts/check_bond_feature_delivery.py
```

Use a new, nonexistent output directory for every attempt. The phase CLI writes
checkpoints, a refreshed next-phase note, source/method hashes and an execution
manifest. A failure writes a repair-required checkpoint. Repairs are reviewed
and executed as recorded in `execution/repair-*.md`; it does not autonomously
invent semantic fixes. No external model allowance, new approval or human
quality label is required. Run native campaigns serially: one parallel attempt
had an `E_SCHEMA` failure at the first RuleIR case and a serial retry passed.
The precise transient cause was not established.

Authoritative successful runs are listed in `execution/delivery-config.json`:
`development-v2-retry`, `exposed-v2-retry`, `holdout-v2`, and
`lloyds-reconciliation`. Earlier runs and rejected explanations remain preserved.
Do not regenerate the development inventory casually: creation timestamps are
part of its run identity. For a new inventory, run a new campaign and receipt.

## Checks and evidence interpretation

447 prospectus tests passed, including 305 dedicated classifier tests. The
independent finite specification covers 256 known/unknown/conflict states;
two SMT equivalence obligations and four distinct formal mutants were checked.
244 native target executions cover all published bond inputs plus deterministic
formal challenge cases in four runs. Kernel-checked formal lowering and
backend agreement establish conditional software properties only.

The delivery verifier checked all 6,822 emitted evidence records against their
preserved source text and page locations. It also rejected six real-source
faults: altered PDF bytes, missing and reordered extracted pages, a missing
named supplement, a different issuer's PDF, and a newer but incorrect base
edition with self-consistent hashes. These are integrity checks, not proof
that every PDF character was extracted correctly or that every clause was
interpreted correctly. Keyword-only comparison is preserved as an explanatory
baseline and is never scored as legal accuracy.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Publish requested corporate negative examples and source-linked reasons | Tesco, two Veolia series and Compass have qualified negatives; all requested existing control rows are retained | Integrity and formal checks passed on final runs | English relevance and complete contract/source closure remain assumptions | Use the report within its stated source boundary | Current legal eligibility or risk-free repayment |
| Retain positive CoCo and statutory-bank examples | Sufficient principal-loss or common-share witness per row | Source identity and formal checks passed | Many subsidiary clauses remain unresolved; origin proposals are not exhaustive | Strengthen subject, condition and reference resolution | Complete reconstruction of every loss mechanism |
| Reject first frozen transfer promotion | Compass/ING produced answers, but wrong-edition injection was accepted | Edition integrity failed; repaired and rerun | Date strings can appear in historical references | Version 2 binds the edition marker to its identified page | A backend pass establishes source identity |
| Publish second frozen challenge as partial | Danske positive, Shell unresolved | No silent forced negative; method hashes unchanged | Shell's monetary repayment/calculation-unit relation is unsupported | Add and independently test exact repayment-unit composition in a reviewed next version | Universal future generalization or a legal accuracy score |

## Repairs and qualifications that must survive a reset

Cash redemption, partial repayment, instalments, coupon cancellation, price
definitions, share-issuance authorisations and hypothetical tax clauses initially
produced false mechanisms. The failed runs are preserved and controlled tests
cover the causal repairs. Final summaries use one sufficient common-share
conversion witness where available, retaining the other candidates in JSON.
Unresolved secondary clauses can coexist with a positive existential feature;
they cannot support a negative.

The first fresh Compass/ING challenge became development material after the
edition failure. The later Shell/Danske files were acquired only after the
second freeze. Shell specifies £1,000 redemption per calculation amount, but
the frozen reader does not establish the equality to the selected principal
unit. Its abstention is an implementation limit. The source-family extension
therefore did not meet the planned complete positive/negative transfer target.
The source data, harness and formal rule were not invalidated; the current
reader failed this additional construction. A future repayment-unit repair
must retain this failure and use new unseen sources for a new transfer claim.

Standard Chartered's issuer-published executed deed replaces a circular with
completion-warning language. Deutsche Bank's German text prevails over the
English translation; equivalence is unproved. Lloyds' final HTML filing mirror
was present in the archive and initially overlooked; it is now included with
ISIN US539439BF59 and an explicit mirror-authenticity qualification. Its HTML
text unit is not a PDF page. Other ISINs in that filing describe preferred
shares and must not be attached to this AT1 issue.

Ordinary issuer financial statements, separate complete trust/agency contracts,
later amendments and current legal changes are not all closed dependencies.
No natural-language legal entailment or correctness for every unknown future
situation is proved. The product feature remains independent formal evidence
and explicit qualified conclusions, never human-labelled legal scoring.

Post-run red team: the strongest alternative explanation for apparently good
source performance is recognizer adaptation to this development corpus and
agent-supplied scope. The fresh Shell failure demonstrates the weakest point:
unseen but ordinary wording/layout can defeat coverage. A wrong supporting
clause, edition fault or counterexample under the declared formal premises
would overturn the relevant conclusion. Additional frozen source families,
automatic document-link resolution and proof-preserving monetary composition
are the next discriminating work; passing more in-corpus examples cannot
replace them.

## PDF and source review, 29 September 2026

The user requested the complete report as PDF and a correctness assessment.
`results.pdf` contains all 26 rows, all qualifications and the added
`source-review.md`. The conversion uses installed Pandoc/XeLaTeX and can be
repeated with `.venv/bin/python scripts/render_bond_feature_report.py`.
The six rendered pages were inspected; all report fields and prose survive
text comparison, with no overfull boxes or missing characters. Source links
in the PDF use the archived issuer/mirror URLs. Build hashes and commands
are in `pdf-build/manifest.json`.

The bounded source review found two real explanation defects. Standard
Chartered's previous summary selected a Newco reorganisation clause; its
corrected reason uses the retained conditional principal-write-down clause
on PDF pages 42–43. Duke's 2054 reason selected the 2034 repayment clause;
the publisher now selects the 2054-specific clause. All 26 decisions remain
unchanged. Four focused presentation regression tests passed, and the
delivery verifier again checked all 6,822 quotations and six source faults.
The earlier 447-test/native evidence remains the frozen run's evidence.

The frozen reader and its candidate evidence were not changed. Its broad
subject/condition matches still need semantic repair; a better summary does
not prove that repair. The updated source review explicitly distinguishes
the user's feature test from SFC complexity and transaction eligibility,
and preserves the restructuring exclusion and the Shell abstention.

## Follow-up gap diagnosis

The user asked what gaps remain and how to avoid similar errors. Bounded
debugging probes through `analyze_issue` now demonstrate three semantic
failures, saved with full inputs, evidence and the reader hash in
`execution/reader-gap-diagnostic.json`: a notification duty produces a false
mandatory-conversion positive; a negated write-down statement produces a
positive; a principal-forfeiture paraphrase is missed and the ordinary
repayment baseline produces a negative. A direct automatic-conversion
control produces the expected positive. These are synthetic construction
counterexamples, not a legal-accuracy score or an independent legal oracle.

This is stronger evidence than the prior two explanation defects: the reader
can emit wrong facts and therefore wrong decisions. The earlier presentation
repair does not remove those failures. Existing real-bond outcomes were not
changed or independently disproved by these synthetic inputs; they remain
qualified source findings. Do not present the archived 447 passing tests or
backend agreement as semantic validation of this reader.

The next-phase plan now prioritises action/negation scope, issue identity,
negative-decision completeness and shared decision/explanation derivations
before the Shell repayment-unit extension. The finite formal decision logic
and research direction remain viable; the current reader's general semantic
reliability is rejected. No implementation repair was executed in this gap
diagnosis. Unsupported source interpretation must stay explicit, and future
claims require new frozen challenges rather than rescoring exposed examples.
