# Code-traced gap ledger

Baseline: 119f3d0d, 2026-10-03. Paths below are relative to the repository.
`Defect candidate` means a code path supports the concern but a failing test must
establish it before reporting it as repaired. Closure requires the stated
evidence, not a completed checklist. C0 emits the exhaustive per-case inventory
for this corpus, including unresolved passages in already-positive cases.

| ID | Finding and code/evidence anchor | Class | Closure criterion / phase |
| --- | --- | --- | --- |
| G01 | `master_control.main/run_phase`: completed E0–E8 is a no-op; `next-evidence-program.md` has no N-phase executor | Confirmed workflow gap | Independent reviewed successor with executed phases and refresh receipts; C0–C4 |
| G02 | `master_control.freeze`: two historical repairs already consumed; method changes cannot reuse that allowance | Protocol boundary | Preserve old files/budgets, new plan/state/receipts; C0 |
| G03 | `loss_absorption_reader.clause_features`: an exempt context returns before unrelated semantic witnesses (except one optional-conversion case) | Defect candidate | Mixed redemption/amendment/distribution and independent loss tests; causal repair/replay C1 |
| G04 | `_candidate_features` early WATCH return misses interest forfeiture, leaving LVMH p.103 unresolved | Confirmed bounded-language gap | Identify only distribution subjects, retain principal-loss counterexamples; C1 |
| G05 | Partial redemption grammar covers pool factor/instalments but not LVMH proportional dematerialised-note redemption, pp.107–108 | Confirmed bounded-language gap | Exact redemption relation, cash-vs-forgiveness counterexamples; C1 |
| G06 | Following minimum-nominal-value sentences need their redemption antecedent; `analyze_document` takes 1200 characters of context without a section boundary | Defect candidate / missing construction | Immediate same-scope antecedent, source offsets, absent/intervening/foreign antecedent tests; C1 |
| G07 | Cash candidate in `_candidate_features` uses repayment/par co-occurrence and limited negative guards | Defect candidate | Negated repayment cannot establish cash; preserve legitimate affirmative witnesses; C1 |
| G08 | `analyze_document` exact monetary field witness bypasses normal `series_binding` and checks field starts only for scope | Defect candidate | Check complete field spans and issue references; C1 |
| G09 | `analyze_issue` accepts unvalidated operative/shelf ranges; invalid/overlapping/out-of-range scopes can silently omit a loss page | Defect candidate | Reject invalid declared ranges before deriving any fact; C1 |
| G10 | `load_document` verifies bytes/markers, not extraction fidelity; `master_sources.extract` uses a total text-length threshold and sets preliminary false | Capability / evidence gap | Page-level PDF/text and document-stage review; OCR only under a separate approved dependency policy; C3 evidence review and future source admission |
| G11 | `master_sources.register` binds source identity and family but not all contractual precedence, final-term options or controlling-language equivalence | Capability / evidence gap | Dated issue-specific applicability/precedence review; C3 and external review |
| G12 | BASF final p.2 expressly needs 9 Sep 2022 base and 27 Feb 2023 supplement; German Option I controls (p.7) | Missing public source / language | Recover exact editions, inspect German terms and selections; C3, otherwise remain unknown |
| G13 | Enel agency/guarantee/covenant are recovered but amendment coverage and signed execution remain unestablished; covenant p.6 has a blank signature block | Missing execution/amendment evidence | Inspect authoritative executed versions and applicability; C3 carried source requirement |
| G14 | Unilever programme route returned 403; operative agreements unretained | Missing public source | Bounded public recovery; C3, retain access failure |
| G15 | Lloyds primary SEC filing returned 403; secondary copy is still qualified | Authority/provenance gap | Exact primary filing or independently authenticated equivalent; C3 |
| G16 | SEB fiscal agency agreement July 2023 and 2024 supplements unretained | Missing public source | Exact contracts/amendments and issue applicability; next source queue |
| G17 | LVMH and BBVA complete agreements, incorporated material and later amendments unverified | Missing completeness evidence | Source-specific dependency closure; next source queue |
| G18 | `source_obligations.build`: regex reference windows are candidates, `all_dependencies_found=False`; reviews do not discharge individual reference IDs | Missing functionality | Retain per-reference IDs/anchors/status; reviewed closure records need exact edition/applicability/amendment links; C2 inventory, future closure mechanism |
| G19 | `eligibility.specifications`: retained 2022 HKMA anchors are not current-law verification; IC-1 redirects to new official host | Missing current authority | Review exact redirect host, retain current text/date and match transaction date/jurisdiction; C3 |
| G20 | Issuer power, effective order, implementation, suspension/litigation and legal finality are separate inputs in `eligibility` | Missing real authority facts | Dated primary authority and actual event evidence; never infer from issuer country or AT1 label |
| G21 | `master_mechanisms` Deutsche formulas require external loss/pool/effectiveness and seven write-up conditions; timing/settlement/rounding incomplete | Missing implementation and inputs | Separate source-specific derivation and boundary tests before extending; future calculation protocol |
| G22 | `master_phases.integration` attaches only the UBS instrument engine; Deutsche calculations run separately | Integration limitation | Explicit optional source-bound Deutsche scenario adapter before claiming joined calculation coverage; C2 disclose, future calculation protocol |
| G23 | `input_requirements` marks other applicable loss profiles NOT_IMPLEMENTED; BBVA 6.1 mandatory vs 6.2 opt-out and SEB principal zero vs share rights must stay distinct | Missing issue-specific engines | Source-conditioned formulas/notice/price/settlement implementations; no profile transfer; future calculation protocol |
| G24 | `feature_investigation` registers supplied terms at requested known_at, without independently proved retrieval/force intervals | Provenance/time limitation | Actual provenance/effective/known intervals supplied and checked; C2 disclose |
| G25 | Product assertions/issuer basis/event source are absent in master integration; feature yes is not HKMA scope | Missing supplied evidence | Source-bound product and issuer assertions; C2 list actual missing observations |
| G26 | All 14 bank duties remain; client/mandate/status/suitability/bank-policy/capacity facts unavailable | External/private evidence | Receive authorised supplied facts with dates/provenance; permission remains false; C2 |
| G27 | `master_phases.integration` checks inventory length 14; count alone is weaker than exact duty identity | Acceptance-check gap | Compare exact baseline duty keys as well as revalidation; C2 |
| G28 | Positive `analyze_issue` answers may coexist with unresolved passages; E8 reports aggregate answer counts, obscuring per-case residual scope work | Reporting gap | Emit every unresolved passage and disposition counts, including positives; C0/C4 |
| G29 | `master_control` budgets check elapsed time before a phase; historical receipts exclude themselves from output hashes and state is not an adversarial audit log | Robustness limitation | Successor binds full parent snapshot, receipts/results and phase elapsed time; crash/tamper/stale/no-op tests; C0/C4; no malicious-author security claim |
| G30 | All 36 cases are exposed; no post-final-repair unseen cases or representative sampling | Validation gap | Predeclare fresh families/issues, freeze method before PDF inspection, count unavailable/abstained cases; later independent challenge |
| G31 | Semantic validation and `source_obligations.replay` reuse the reader; Lean/SMT prove declared logic, not English entailment | Evidence limit | Independent source adjudication and adversarial cases; C1 checks engineering only; human legal review remains open |
| G32 | Human document/legal acceptance remains absent; no automatic source review can certify it | Acceptance boundary | Qualified human review of retained terms, law and requested use; do not block reversible development |

## Executed closure status

Final accepted attempts: C0 attempt-006, C1 attempt-005, C2 attempt-005, C3 attempt-004, C4 attempt-003. The final reader passes 842 regression tests and all 36 source/derivation replays. Only LVMH changes (unknown to qualified no); BASF remains unknown. The original 32 answers remain unchanged. See [reader-result-review.md](reader-result-review.md), [results](phases/C4/attempt-003/results.md), and [disposition-audit.json](disposition-audit.json).

There are 1,467 unresolved issue-level clause records after repair, compared with 1,472 before. Exactly five source-reviewed LVMH passages were resolved. The C0 inventory contains 4,990 candidate source-reference records. These counts can repeat shared passages/references across issues: they are neither counts of confirmed legal defects nor distinct missing contracts. The full source requirements remain in C2 attempt-005/evidence-requirements.json.

| ID | Final disposition | Executed evidence or remaining requirement |
| --- | --- | --- |
| G01 | Closed for this protocol | C0–C4 executed; refreshed dependency-aware next plans; repair-004 and restart tests. |
| G02 | Preserved boundary | All 2,570 parent files verified; old freeze and budgets untouched. |
| G03 | Bounded repair executed | Coordinated independent loss preserved; shared-consent and cash-paid reductions stay attached. General clause interpretation remains incomplete. |
| G04 | Bounded repair executed | Exact deferred-interest forfeiture reviewed; broader exemption rejected after four failing counterexamples (repair-005). |
| G05 | Bounded repair executed | Two proportional dematerialised paid-redemption constructions checked against LVMH pp.107–108. |
| G06 | Bounded repair executed | Immediate same-scope antecedent retained with source offsets and hashed context witness. |
| G07 | Bounded repair executed | Negated par repayment counterexamples pass; arbitrary linguistic negation is not certified. |
| G08 | Bounded repair executed | Full field spans and explicit issue assignments checked; unrelated benchmark ISIN regression retained. |
| G09 | Closed for declared range validity | Malformed, duplicate, overlapping, empty and out-of-page ranges rejected before interpretation. |
| G10 | Open | Extraction fidelity, OCR and document-stage admission still need page-level source review; IC-1 extraction has no blank pages but is not independently validated. |
| G11 | Open | Edition, precedence, option selection and controlling-language admission remain qualified. |
| G12 | Open; recovery attempted | BASF route 404 and two search retry pages; exact 2022 base, 2023 supplement and German Option I remain missing. |
| G13 | Open | Enel executed agreements and amendment completeness unestablished. |
| G14 | Open; recovery attempted | Unilever route still 403; separate operative agreements absent. |
| G15 | Open; recovery attempted | Primary Lloyds SEC route still 403; secondary provenance qualification retained. |
| G16 | Open | SEB July 2023 agency agreement and relevant 2024 supplements not recovered in this queue. |
| G17 | Open | Complete LVMH/BBVA agreements, incorporated material and later amendments unverified. |
| G18 | Inventory delivered; closure mechanism open | C2 retains source-reference IDs and anchors per issue; individual dependency discharge still needs implementation and source evidence. |
| G19 | Retrieval closed; applicability/integration open | Official current landing page and IC-1 V.3 06.10.2017 retained and reviewed; related circulars, transaction-date applicability and law-registry integration remain. |
| G20 | Open | Actual authority/order/effectiveness/implementation and legal-finality facts absent. |
| G21 | Open | Deutsche timing, settlement, rounding and required scenario facts still incomplete. |
| G22 | Open | Only UBS is attached to the bank instrument investigation; no Deutsche adapter was claimed. |
| G23 | Open | Other issuer-specific numerical profiles require their own source derivations and implementations. |
| G24 | Open | Independent actual retrieval, effective and knowledge intervals remain unproved. |
| G25 | Open | Product/issuer/event facts are explicit missing inputs, not inferred from feature classification. |
| G26 | Open | Actual client, mandate, suitability, bank-policy and capacity facts absent; every permission remains false. |
| G27 | Closed for tested integration | Exact 14 obligation identities compared with protected receipts for each of 36 investigations. |
| G28 | Closed for reporting | C0 inventory, C1 clause inventory and C4 per-issue output include unresolved passages in positive cases. |
| G29 | Bounded engineering repair executed | Protected parent/receipt/result checks, crash budget, restart and dependency refresh tested; no malicious-author security or general termination proof. |
| G30 | Open | Zero fresh post-final-repair cases; future challenge must freeze method before new source exposure. |
| G31 | Open | Shared reader/replay interpretation remains; native/formal checks concern declared premises. |
| G32 | Open | Independent human legal acceptance has not occurred. |

The old future-tense defect-candidate descriptions above preserve the audit baseline. The executed dispositions in this table supersede them. A bounded repair closes its tested construction, not the whole space of prospectus language. HTTP recovery and successful tests do not close applicability, private evidence or human-review requirements.
