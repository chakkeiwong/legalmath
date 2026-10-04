# Executed prospectus repair — 4 October 2026

The isolated candidate fixes all three retained unpaid-cancellation exclusions and both Mizuho paid-amortisation false positives. The full candidate prospectus suite passes 885 tests. The original 293-file reader and prior study results remain the protected comparator.

## What changed

Cancellation evidence now binds the unpaid principal relation to the complete reviewed clause, its prerequisites and exceptions. The final-maturity withholding exception, certified-exhaustion certificate and notice, and deferred-cancellation misconduct exceptions survive source replay. Three-valued evaluation preserves missing facts. Paid amortisation requires its own payment relation and cannot hide a separate unpaid cancellation.

Intake reports empty and partial extraction explicitly and validates declared issuer, class, identifier, edition, role, base reference and required document sets. The first BES intake used final-terms dates as issue dates; manual image review corrected the actual issue dates to 15 July 2011, 21 January 2014 and 8 May 2014. All three bundles remain unresolved for incorporated accounts and precedence review.

The legal component executes typed boolean and date rules over source-bound declared premises. It separates contractual features, measures, recognition, procedure and enforcement. It rejects wrong scope, changed source bytes, mislocated quotations, stage changes and missing/conflicting facts. PDF anchors use the hashed text rather than an unbound page derivative. The 120-day boundary is checked under declared calendar-day premises; service facts and legal time-counting conventions remain external.

## Fixed-input comparison

| Input | Original answer | Candidate answer | Original unresolved records | Candidate unresolved records |
| --- | --- | --- | --- | --- |
| offer-bes-1315263 | Abstain | Abstain | 0 | 0 |
| offer-bes-1922255 | Abstain | Abstain | 0 | 0 |
| offer-bes-1217215 | Abstain | Abstain | 17 | 0 |
| offer-bes-1774077 | Abstain | Abstain | 1 | 1 |
| offer-hypo-1314069 | Abstain | Conditional positive | 2 | 2 |
| offer-hypo-1123807 | Abstain | Abstain | 5 | 7 |
| offer-hypo-843665 | Abstain | Conditional positive | 4 | 6 |
| probe-lease-final-cancellation | Abstain | Abstain | 0 | 0 |
| probe-lease-exhaustion | Abstain | Abstain | 0 | 0 |
| probe-adriatica-cancellation | Abstain | Abstain | 0 | 0 |
| case-105635287 | Conditional positive | Abstain | 9 | 9 |

The seven offering documents move from seven abstentions to five abstentions and two conditional positive readings. Three source probes and the original Mizuho programme are additional fixed inputs. Counts describe this selected stress set; they are not a population accuracy estimate or a finding of actual loss.

## Verification evidence

- Full prospectus suite: 885 passed; zero failures or errors.
- Original clause exclusions: 3/3 repaired with condition witnesses; real paid-amortisation controls: 2/2 preserved.
- Declared legal scenarios: 25/25 match their engineering expectations; 12 conditional, 13 unresolved.
- Extraction: 2 OCR_REQUIRED, 1 PARTIAL_TEXT, 4 TEXT_PRESENT; no automatic OCR performed.
- Public follow-up: 17 requests; 187/212 cumulative; 25 remaining.

Legal scenarios evaluate source-reviewed declarations; their expected labels are not independently adjudicated truth. The general evaluator contains no case-ID dispatch. Unit tests alter dates, stages, claim identity, conditions and source material separately.

## Decisions and remaining gaps

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain isolated cancellation/repayment repair | Five real clause controls pass | No observed regression in 885-test suite | Unseen syntax and distant cross-references | Independent review and unseen paired cases | General English or legal completeness |
| Retain intake checks | Missing/wrong inputs rejected; valid declared control accepted | OCR and dependency vetoes remain | Scanned fields, incorporated accounts, precedence | Review OCR derivatives and complete BES dossiers | Complete issue analysis |
| Retain typed legal evaluator | 25 declared scenarios and mutation checks pass | Independent adjudication absent | Rule interpretation and factual applicability | Independent legal review of premises and outcomes | Legal accuracy or final investor recovery |
| Keep acquisition gaps explicit | All requests retained and budget counted | Missing primary instruments remain | Portuguese Annex 2B; HETA measure/list; original offers; exact Italian bankruptcy articles | Use a specific newly identified official or labelled mirror route | Search snippets or HTTP 200 as legal evidence |
| Keep candidate separate | Reproducible candidate and reviewable patch | No production promotion | External review and unseen-case generalisation | Review patch and adjudicate before default adoption | Production readiness or transaction permission |

The follow-up recovered official historical Italian pages, including Law 130 Article 4. Its Article 67 exemption does not supply the separate Article 65 exemption. The generic bankruptcy pages and their explanatory notes do not replace the missing exact operative articles. Google navigation shells, unrelated Bing results and two HTTP 500 article responses were retained without source promotion. See [acquisition review](ACQUISITION-REVIEW.md).

The remaining source list is Portuguese 29 December 2015 decision/Annex 2B; original HETA decree and debt/guarantee list; Dana 2013 listing particulars; Lloyds 2009 offer/trust deed; Ukraine 2013 offer; Popular/Snoras originals; and the exact historical Italian bankruptcy articles. The three BES incorporation and precedence reviews and independent legal adjudication also remain open.

## Execution review

The initial wrong-interpreter setup run, missing-fixture broad run and empty-extraction failure remain in phases/003-test, 005-test and 008-test. The missing-fixture errors were harness defects; the empty-extraction failure was a candidate defect and triggered its repair. Two overlapping master launches were rejected by the shared lock before creating a phase and were rerun sequentially. No evidence was overwritten to make these failures disappear.

The strongest alternative explanation for many abstentions is deliberately broad input scope or missing document dependencies. The five source-verified clause defects and their paired controls are narrower evidence. An independently reviewed counterexample with a lost qualifier or wrong payment relation would overturn the corresponding repair claim. The weakest evidence remains legal interpretation and unseen-document generalisation. This rejects neither the research direction nor incomplete candidate work; it retains the tested repairs while blocking promotion.

Results are deterministic engineering checks, not a stochastic comparison; no superiority ranking is asserted. The target is condition-preserving classification of the retained passages. The code computes bounded English features and evaluates declared premises. Their equality to unrestricted legal meaning is not proved.

## Reproduction and artifacts

Master entry point: python3 -m scripts.run_prospectus_corner_repair PHASE. Available phases are prepare, diagnose, test, intake, legal, fetch, compare, finalize and verify. Run one phase at a time. Each records a receipt and refreshes NEXT-PHASE.md. Any candidate change makes finalisation and verification reject stale evaluation phases.

Candidate code uses the existing project .venv interpreter for workers and pytest; the master launcher is separately recorded. CUDA_VISIBLE_DEVICES=-1 is set before candidate work; no GPU or paid model calls were used. All random seeds are N/A because these checks are deterministic.

- test: [015-test/receipt.json](phases/015-test/receipt.json)
- intake: [016-intake/receipt.json](phases/016-intake/receipt.json)
- legal: [018-legal/receipt.json](phases/018-legal/receipt.json)
- compare: [017-compare/receipt.json](phases/017-compare/receipt.json)

[Reviewable patch](candidate.patch), [candidate changes](candidate-changes.json), [LaTeX addendum](addendum.pdf), [run manifest](run-manifest.json), [reset memo](RESET-MEMO.md). Human prose acceptance and independent legal adjudication remain pending.
