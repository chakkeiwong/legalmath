# Resume: paired real CoCo purchaser cases

Latest task: find two actual CoCo offering documents with a defensible positive
and negative result, test them and document them in the monograph.

Completed engineering run: `attempt-002`, all five phases passed. Read
`result.md`, `review.md` and `summary.json` first. `attempt-001` is a preserved
failed conflict fixture, repaired in 002. Do not report it as a passing run.

The pair is Barclays PLC 7.625% February 2025 (US06738EDC66) versus Standard
Chartered PLC 7.625% January 2025 (US853254DF47 / USG84228GP72). Same hypothetical
US-resident individual, own account/benefit, not a QIB, USD 200,000 principal.
Only the specified original-offering purchaser condition passes/fails. Neither
result is full SFC, SEC or private-bank clearance. Both integrated bank receipts
keep seven layers/fourteen obligations and `may_execute_transaction=false`.

Implementation: `src/legalmath/prospectus/purchaser_cases.py` and
`scripts/run_coco_purchaser_cases.py`; inputs and original links in
`docs/prospectus/coco-cases/`. The runner accepts no arbitrary commands/paths,
records source/method/tool identity, preserves attempts, and refreshes the next
phase after successes or failures. Native inputs have no expected answer labels.

Evidence: 165 regression tests; 157 cases/314 native executions; 276 complete
native results matching independent evaluation and 38 abstentions; all 512
Boolean assignments covered by the independent SMT relation; six caught
mutants; one Lean preservation certificate. No stochastic method ranking.

Monograph §2.4.5 is in `chapters/02b-bank-compliance.tex`. It includes both
documents, their contrasting distribution routes, QIB/beneficiary definitions,
the formula, counterfactuals, results and remaining limits. Build passes:
332/78 pages, 133 cited documents/288 occurrences. Source and manuscript
renderings, protected baseline and document-review receipt are retained here.

Do not change the Standard Chartered preliminary-text flag to hide its generic
electronic cover notice. The dossier records the dated, priced final offering
inside that wrapper. The unreadable November 2025 document is a different
security and was not used. CFR sources are explicitly the 2025 annual edition;
complete original-date/current law is unproved.

No humans are quality authorities. Source inspection, constructor preservation,
formal equivalence and native agreement have separate scopes. English meaning,
exhaustive law discovery, actual client/JPMorgan policies and future legal
generalization remain unproved. Further work should add a supported rule or
actual evidence, not manufacture a full-approval label for the positive case.

The checkout was already extensively dirty on main. Unrelated work was
preserved. This task did not create a commit or push.
