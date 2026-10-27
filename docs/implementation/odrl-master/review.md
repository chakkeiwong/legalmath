# Review of the policy-to-ODRL implementation program

Verdict: **PASS as a reviewed implementation program; feature not executed.**
Reviewed on 22 October 2026. The program now covers the proposal's six
milestones with 22 bounded tasks, 20 substantive case families and 17 mutation
obligations. The review repaired material source, dependency, recovery and
completion errors in the draft. It does not establish legal correctness,
evaluator compatibility, generation quality or readiness to deploy.

This is the primary agent's source/code review and adversarial local checking,
not an independent model or human opinion. No subagent, external model call,
software installation or third-party evaluator execution was used. The
[verification record](verification.json) retains the actual local check results
and final file identities. All feature tasks remain `NOT_STARTED` with zero
attempts used.

## What was checked

The governing inputs were the [implementation proposal](../../monograph/chapters/08a-odrl-proposal.tex),
its [literature review](../../monograph/chapters/04b-policy-to-odrl.tex), the retained
[technical reading notes](../../research/hkma-odrl-survey-2026-10-22/reading-notes.md)
and [software audit](../../research/hkma-odrl-survey-2026-10-22/software-audit.md).
The official circular body and both annexes are retained with raw-file and
extracted-text hashes in the program. The final source pass inspected the
actual Annex 1 qualifications, thresholds, procedure relief, acknowledgment
and annual-review provisions, and all seven Annex 2 FAQs. It did not repeat
the completed literature search or upgrade unavailable papers into inspected
evidence.

The repository check used the actual main/worktree baseline, the relevant
prospectus/translation implementation, tests and packaging. In particular,
`prospectus/models.py` labels its models synthetic/conditional;
`prospectus/semantics.py:117` rejects negative financial inputs;
`translation/pipeline.py:12` accepts only RuleIR/Catala; observation preparation
distinguishes complete and partial profiles. The successor source graph
retains identity and timing but needs circular-specific reference roles.
The active legal-integration campaign was inspected for scope and left under
its existing worker. Its successful admission did not admit this ODRL task.

The graph review examined every success, completion, alternative and recovery
edge; attempted failure paths as well as the successful path; matched task
outputs to proposal requirements; and checked resource ownership, restart
rules and honest completion. The checker has no dispatch or network path.
Its hypothetical-state helpers do not validate real grants, task receipts,
attempt counters or process identity; those are future S00/executor duties.

## Material findings and corrections

| Finding | Why it mattered | Final correction and verification owner |
|---|---|---|
| **High — written allocation was an incomplete distinction.** The draft case contrasted written joint allocation only with unresolved entitlement. | Annex 1 3.2(c) and 3.4(a)(iii) expressly supply equal shares in the absence of an agreement for non-associate holdings. Treating known absence as missing entitlement invents a prerequisite. | Contracts/F06 distinguish written allocation, known absence with known holders, and unknown agreement/holder evidence. M15 must catch the invented prerequisite. N02/F06/C09/Q10 own implementation and checks. |
| **High — inherited nonnegative financial inputs were too narrow.** | Annex 1 3.3 defines net assets after liabilities and residence exclusion. They can be negative, while the independent portfolio alternative can still qualify. Reusing the current helper unchanged would return an input error for such a case. | Signed net assets are explicit; the historical helper remains unchanged as a baseline. F01 and M16 test both passing and failing portfolio cases. C09 names typed domains; C09C must disclose any narrower Catala comparison. |
| **High — a consent signature could conceal omitted prior requirements.** | Paragraph 13.1 separately requires written agreement, written criteria, written categories/threshold and explanation of consequences/withdrawal. Paragraphs 7.2/12 and FAQ 4 also matter to information and record evidence. | N02/F06 and F10 retain each premise; M17 detects signature-only acceptance. FAQ 1 remains distinct: it does not impose universal documentary proof of financial disclosures. |
| **High — the amount Boolean could hide continuing controls.** | FAQ 6 supports the designated-account exception but also requires review before new funds and at least at annual review. Paragraphs 8.1–8.5 include percentage-of-AUM thresholds, rationale, warnings and alerts. | Exact amount computation is conditional. Percentage/AUM conversion needs dated evidence and a declared rounding interpretation. F09/F15 and D11 retain controls as evidenced conditions/duties or explicit deferred scope; no default-true aggregate premise. |
| **High — F06 could execute before P05.** | Missing/conflict rules and result categories were specified in the profile, yet the fact task lacked a success edge to it. | Added P05 to F06 prerequisites. The checker and an adverse removal test require that edge. |
| **High — X07 acceptance could precede independent cases.** | A deterministic exporter could certify its own structural negative cases before T03 froze expectations. | Added T03 to X07 prerequisites. Independent-case removal is rejected by the checker. |
| **High — evaluator recovery and full completion conflicted in the initial draft.** | Requiring both primary and recovery tasks to succeed makes a legitimate fallback impossible; bypassing qualification would be equally wrong. | Q10 and full completion require one successful member of V08/R08. The primary failure stays retained. R08 has one attempt, runs after V08, and requires a diagnosed `SUPPORTED_FRAGMENT_INCOMPATIBILITY`. Tests exercise both alternatives and their failures. |
| **High — any failed engine status could have activated recovery.** | Source, expectation, harness or authority failure is not evidence that a second engine is an appropriate remedy. | Added an explicit failure-class contract. Unknown classification blocks the hypothetical recovery; a classified ineligible trigger yields a disposition rather than another attempt. Shared-evidence vetoes remain outside the helper and must be enforced by the future executor. |
| **High — a release label could hide failed prerequisites.** | Checking `A18=SUCCEEDED` alone could promote a state in which facts or duty acceptance failed. | Completion helper traverses success/alternative dependencies. A test gives A18 a success label over failed F06 and requires both release/completion claims to fail. Actual receipt authenticity remains an executor responsibility. |
| **High — later duty work changes previously qualified code.** | D12 writes events/export/evaluator modules also used by eligibility. A pre-change V08/Q10 result cannot qualify the new combined build. | Overlapping writes are serialized. Q13 must rerun eligibility qualification, correspondence and mutations on the combined versions. Preserve the earlier receipt as historical; the release uses the requalified closure. |
| **Medium — optional Catala work lacked an unavoidable disposition.** | Leaving C09C unrun could either block the manual release forever or be silently treated as successful. | A18 has a completion-only dependency on C09C; completion checks enforce a terminal disposition. Actual results, explicit unavailability or a reasoned optional skip are distinguishable. F18 makes exact references mandatory and Catala evidence conditional on actual execution. |
| **High — generation could be silently dropped or block usable manual work.** | The proposal includes an assessed comparison, but a manual feature does not need live generation to function. | G16 remains mandatory for full-program completion and requires its own concrete protocol/grant. K17/A18 depend on the offline interface, not live calls. L19 can report a manual release with full work blocked on generation authority. |
| **Medium — the original gate wording was self-referential.** | S00 itself was described as needing its own completed adoption. | A later implementation instruction admits S00; S00 records the adoption needed by its dependants. No additional permission request is inserted into this planning task. |
| **High — shared fixtures could manufacture correspondence.** | Two outputs from the same mistaken interpretation can agree exactly. Model-judged or syntactic scores do not adjudicate the source. | T03 expectations use source passages and separate specification, C09 uses independent expressions, and mutations challenge known errors. Same-author limitations and conditional alternative readings stay visible. |
| **Medium — published examples could be called a clean holdout.** | FAQ6/consent and other examples already informed the proposal and program. One familiar circular cannot establish broad document generalization. | G14 treats published examples as development, records prompt-held-out contrasts separately, includes preprocessing/correction cost, and predeclares paired units and uncertainty. No ranking from one run or structural score. |
| **High — upstream evaluator defaults and licences were unsafe adoption shortcuts.** | OVAL's promise-of-future-duty setting, float arithmetic, missing-value handling and conjunction-like `andSequence` do not implement the required domain semantics. Public code is not necessarily licensed for reuse. | E04 pins an isolated minimal runtime; V08 checks the actual engine with explicit configuration and domain adapters. FORCE is conditional fallback. No LLM4ODRL/ODRL-shape copying without an established grant. Static findings remain static. |
| **Medium — local success could fail after installation.** | New top-level shape/context files are not covered automatically by current package-data settings, and research-cache paths are not portable runtime dependencies. | K17 must package one authoritative asset source, run the CLI in a clean wheel installation, and verify local contexts, source identities and replay. F20 includes partial-output/tampering controls. |
| **Medium — review text and the machine inventory could drift.** | Counting task IDs alone would miss deletion of a required task's mandatory flag, a release edge or an acceptance mutant. | Checker validates all reviewed dependency lists, mandatory-task set, task bounds, source hashes and F01–F20/M01–M17 contract inventories. Tests remove requirements/edges and reject the modified plans. Final file hashes bind the reviewed package. |

The last three new mutations supplement the proposal's original examples;
they test source errors actually found while reviewing this program. They are
future implementation obligations, not claims that the ODRL implementation
already contains or has passed those tests. Existing prospectus semantics and
the sealed proposal sources were not changed to make this review pass.

## Proposal coverage and sequence

| Proposal obligation | Responsible tasks | Required evidence before the claim |
|---|---|---|
| Whole circular/annex/reference coverage and richer norm model | S01/N02/T03 | Source-unit denominator, exact locators, dispositions, premises and alternative interpretations |
| First manual eligibility export | P05/F06/X07 | Bound source/profile/calculations, exact facts, local shapes with actual target coverage and independent negative cases |
| Executable semantics and limited Catala correspondence | V08 or R08; C09/C09C/Q10 | Actual qualified engine/adapter, independent reference results, declared proof domain or finite cases, actual Catala receipt if claimed |
| Continuing consent and duties | F06/D11/D12/Q13 | Historical state, correlated performance, recurring reviews, surviving/relieved duties and combined-version requalification |
| Generation comparison | G14/G15/G16 | Frozen protocol, bounded authority, all candidates/failures, matched semantic outcomes and uncertainty appropriate to the design |
| Installed feature and final accounting | K17/A18/L19 | Clean-wheel API/CLI, portable profiles, source/replay integrity, exact open gaps and separate manual/full completion verdicts |

Consent handling occurs earlier than the proposal's fourth milestone because
the first manual permission already depends on it. D11 is independent of
evaluator success; D12 can implement an adapter-neutral monitor, while Q13
requires a qualified integrated path. This preserves useful work after an
engine failure without claiming qualified evaluation. An assessed failed
generation method is a valid G16 result; study success is not candidate
promotion. These distinctions avoid both premature stopping and endless repair.

## Remaining assumptions and risks

**Source interpretation remains conditional.** The pilot is the historical
2023 bundle and initial individual-client scope. Definitions incorporated from
the Professional Investor Rules and Code, any relevant amendments, qualitative
reasonable-satisfaction assessments, product categories and external ordinary
duties need explicit closure or conditions. Whole-source accounting may include
deferred units; it is not a claim of full executable coverage. S01/N02/T03 must
review each intended executable norm before accepting it. Negative net assets
and known absent allocation agreements now have concrete cases, but that is
not an exhaustive economic or legal interpretation of every holding.

**The runtime remains unqualified.** OVAL is a first candidate chosen from
inspected work, not an empirically superior engine. The exact dependency lock,
resource bounds, chosen configuration and evaluator behavior are still future
E04/V08 results. FORCE or a minimal adapter may also fail. Export availability
survives that branch failure; evaluation release does not. Catala availability
and the selected common arithmetic domain must be evidenced when used.

**Time and uncertainty policies are modeling choices.** Half-open intervals,
UTC ordering, Hong Kong calendar context and conservative referenced-conflict
propagation are explicit proposed conventions. Annual-review due dates remain
assessed where interpretation is unresolved. They must be versioned and tested,
not attributed to the circular merely because software implements them.

**Expectations can still share the author's mistake.** Separate specifications,
source links and adversarial cases improve the evidence but do not provide
independent legal adjudication. The strongest alternative explanation for a
successful future pilot is that accepted premises and convenient cases conceal
an omitted source condition. A contrary source passage or valid counterexample
should reopen the affected interpretation and dependent receipts. It must not
be dismissed because two backends agree.

**Execution discipline is specified, not installed.** The task register is a
reviewed program, not a running supervisor. The checker does not enforce
reservation locks, live budgets, attempts or receipt authenticity. S00 must
retain actual state and worker identities, and any later dispatcher needs its
own behavioral checks before it can claim those controls. The initial drafting
helper under `.localresources/odrl-master-2026-10-22/` is historical and predates
review corrections; rerunning it would overwrite the reviewed program.

**The generation study is deliberately unbound now.** Models, run counts,
tokens/cost and deadline are material G14 decisions. Setting them here without
target evidence or an instruction to run would invent defaults. Absence of
that grant does not prevent later authorized local implementation; it does
prevent the live G16 study and therefore full-program completion. Results from
one circular cannot establish general regulatory translation accuracy.

## Final decision

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not established |
|---|---|---|---|---|---|
| Retain this reviewed program | All proposal milestones assigned; source and dependency defects corrected; focused checks pass | No unresolved planning defect found in this scoped review | Legal interpretation, real engine behavior and generation remain untested | Deliver program/review; on an implementation instruction, begin S00 against current files | Feature implementation or legal correctness |
| Preserve manual/full distinction | Manual path has current semantic and install dependencies; study remains mandatory for full completion | Unavailable optional comparison cannot be labeled passed; failed prerequisite cannot be hidden by release label | Future grant and actual receipts | Report exact branch outcomes and continue authorized independent work | Completing L19 proves product success |
| Use ODRL first with exact computations and selected Catala checks | Matches source norms, existing repository strengths and inspected software limits | Shared-source agreement alone cannot support fidelity | Whether chosen profile/evaluator meets source-based cases | Build manual source interpretation and cases before generation | A universal Catala-to-ODRL or ODRL-to-Catala correctness theorem |

The final verification contains planning tests and file/binding checks only.
No stochastic comparison was run, so there is no ranking or statistical
performance conclusion. This review accepts the program for future execution
within its stated scope; implementation acceptance remains the task-specific
evidence defined in the contracts.
