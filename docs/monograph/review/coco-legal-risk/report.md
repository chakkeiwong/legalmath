# CoCo legal source survey and implementation result

Completed 29 September 2026. The previous prospectus procedure was partial:
statutory-resolution mentions were retained as candidates, but Swiss powers,
amendments, judicial history and the specific HKMA selling restrictions were
not systematically represented. The monograph had no detailed survey.

Section 2.3 now supplies that survey in about 3,500 words, printed pages 27--35
(PDF pages 49--57). It introduces AT1, CoCos, CET1, non-viability and bail-in
before discussing their legal effects. It separates contractual conversion and
write-down, ordinary resolution, emergency powers, actual orders, judicial
review, repayment and the investor/service-specific distribution decision.
The full monograph is `docs/monograph/monograph.pdf`; a section excerpt with
the bibliography is `coco-legal-risk-section.pdf` in this directory.

The source dossier is `docs/prospectus/legal/manifest.json`, with 21 records.
It preserves primary legislation, regulator circulars with annexes, judicial
texts and existing instrument documents. Original-language text is retained.
The text derivatives and originals have separate hashes. No human-labelled
eligibility answers, model-agreement scores or human quality approvals were
used. Source-inspection notes disclose an executor's limited paraphrase review;
they are not legal-correctness certificates.

## Findings and executed repairs

- The Swiss example cannot be represented as all Swiss CoCos becoming zero.
  The issuer/instrument, contractual mechanism, legal basis and actual order
  have different scopes. The preserved UBS conditions implement conversion,
  with additional notices, priority and later-law provisions.
- The emergency provision's commencement is 19 March 2023 at 20:00. Repeal
  adopted on 6 September took effect on 15 September 2023. Dates were checked
  against the promulgated texts rather than inferred from their titles.
- The retrieved Banking Act copies labelled January 2023 omit article 30b/30c
  headings introduced by AS 2022 732, effective 1 January 2023. The first draft's
  old article 31 account was corrected using that amendment and the 2024
  consolidation. The inconsistent copies remain archived and excluded from
  applicable-law use. A structural check now detects the missing headings;
  it does not prove semantic incorporation merely from their presence.
- The 2025 FINMA Insolvency Ordinance repeals the older banking ordinance and
  expressly applies to pending proceedings. Opening date alone therefore does
  not select every procedural rule for the whole proceeding.
- The Credit Suisse dossier records FINMA's 2023 action and asserted basis,
  the October 2025 partial annulment, and the separate merits appeals/stay
  recorded in the March 2026 Supreme Court judgment. That March judgment is
  procedural, not a decision on the merits appeals or evidence of repayment.
- The 2022 HKMA circular restricts registered institutions' distribution of
  in-scope products to professional investors, with carefully scoped service
  arrangements and exemptions. Generic bail-in exposure does not itself prove
  product scope; equity-form preferred shares and deposits are expressly
  excluded from that debt scope. Exclusion is not general sale permission.
- Three HTTP-success PDF requests returned HTML. They were rejected. The HKMA
  circular/annexes were recovered from its official regulatory repository.
- The first PDF build exposed an unbreakable encoded UBS URL in the bibliography.
  It was replaced with a descriptive hyperlink retaining the target. Rendered
  review also shortened a split heading and moved citations beside their
  respective propositions. The final build has no unresolved diagnostics.

## Verification and scope

`legal_review.py` adds conditional authority and distribution guards, explicit
valid/knowledge times, separation of procedural and merits outcomes, source
change detection and the amendment-heading diagnostic. The legal dossier is
bound into campaign phase identities and the prospective method. Changes make
old results stale; the program was rerun instead of relabelling old passes.

The 13 new regression tests check the four-premise restriction against an
independently stated forbidden-state relation for all 256 four-valued inputs,
and eight necessary sale conditions for all 65,536 four-valued inputs. Other
tests cover scope counterexamples, the actual retained heading discrepancy,
source mutation/removal, exact time boundaries, unknown exceptions, conflicts,
inadmissible procedural complaints, repayment non-inference and rejection of
quality-label fields. All 63 prospectus/qualification tests pass.

The seven-phase master completed and terminal verification passed. It retained
6 Lean propositions and 12 SMT obligations for the existing formal models;
all 206 native RuleIR/Catala executions on 103 shared inputs matched independent
formal evaluation. Those are existing model checks: the new legal-review guards
are conditional Python checks, not newly proved translations of Swiss law into
both backends. There is no legal-accuracy or backend-superiority result.

The linked manuscript build passes. The book has 322 PDF pages and the
technical companion 78; the exported process guide has 13. The checker retained
all 207 protected source-unit labels and all protected mathematics/listings.
All 245 pre-existing citation contexts remain, with 24 new occurrences and
117 cited documents in total. The touched pre-existing Chapter 2 text is
byte-for-byte unchanged except for the new section input. All nine section
pages were rendered and visually inspected. No empirical reader-acceptance
claim is made.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain scoped section and dossier | Primary-source pinpoints, archived bytes, citation/build checks passed | Source discrepancy and rendering failure repaired | Later law and appeal developments | Refresh relevant official editions/dockets for each actual decision | Complete current law |
| Retain conditional guards | Exhaustive finite checks and regression counterexamples passed | Unknowns/conflicts cannot create unsupported permission | English-to-formal entailment and scope premises | Extend only with checked derivations or explicit qualifications | Autonomous legal interpretation |
| Retain existing backends | 206 executions and formal checks passed | No mismatch in supported models | Full notices, schedules and new legal constructors | Extend shared models with independent specifications | Catala or RuleIR is legally superior |

The strongest alternative explanation for a passing campaign is correct
execution of an incomplete legal specification. The tests cannot exclude that
possibility, so current law, complete issue packages and interpretation
obligations remain explicit unknowns. A missing amendment, materially different
clause or changed merits disposition would reopen the affected conclusion.

## Refreshed next phase

The executable master's `next-program.json` now explicitly carries Swiss
legislation/merits-docket checks and SFC/HKMA scope and service exceptions into
its source-completion phase. The next smallest implementation targets are the
full UBS notice/conversion schedule, fund and depositary-share legal form,
cross-border recognition and formal source-language entailment. The latest
inspected judicial procedural account is dated 5 March 2026; this survey does
not assert a final September 2026 outcome of the separate merits appeals.

No human quality verification is scheduled. An unsupported premise remains
qualified until independently supported within a declared formal/source
fragment. Future-law generalisation is still unproved, and the current dossier
is development material rather than an untouched prospective sample.
