# Closing the remaining prospectus gaps

Date: 2026-10-04. Checkout: `.worktrees/bond-gap-closure`, branch
`feature/prospectus-evidence-master`. Protected delivered comparator: `2d6b737b`.

Status: implemented successor under `close`, with S0–S7 dispatch and explicit
evidence, protocol and human-review waits. Execution receipts and the reset memo
record the current validation and delivery. Conditional numerical capabilities
cover named Deutsche, BBVA and SEB calculations; full adjustment, settlement,
other-issuer calculations, source closure and independent acceptance remain
subject to the criteria below. The older `continue` campaign remains protected.

## Question, comparator and acceptance

Can we turn each remaining source, interpretation, calculation and factual
requirement into a decision supported for a specified issue, date and use, with
automatic reopening when its evidence changes?

The comparator is the delivered continuation: C0/006, C1/005, C2/005, C3/004,
C4/003; 36 exposed issues; 18 qualified yes, 17 qualified no and BASF unknown.
Its classification SHA-256 is
`0a49c13b478fe4100720a9a2feb9a0602c6a6c50cd60515df764eb1a9b82405d`.
The 842 regression tests, 36 replays and 120 native executions establish the
reported bounded engineering checks. They do not independently establish the
English or German interpretation. All 14 bank obligation identities remain
required, and transaction permission remains false with the current facts.

Keep three distinct acceptance records: implementation tested; evidence
sufficient for the named issue and assessment dates; independent acceptance
for the named use. A tested intake form does not close a missing-facts gap. A
completed controller does not close the work it schedules.

Primary engineering criterion: evidence-bound decisions reject incorrect or
stale inputs and invalidate downstream results; reviewed source additions and
repairs produce reproducible, explicitly reviewed changes. Source closure
requires actual applicable evidence. Broader acceptance additionally requires
fresh validation and qualified independent human review.

Promotion vetoes: wrong edition or issue, unverified decisive extraction,
unresolved controlling-language or precedence conflict, missing required
dependency or fact, unsupported formula, unreviewed answer or disposition
change, missing bank duty, failed regression, or stale evidence. A veto blocks
the affected conclusion and normally triggers repair; independent work proceeds.

Continuation vetoes: damaged protected history, an invalid comparison,
contamination of a purported fresh challenge, exhausted applicable execution or
request budget, or three identical infrastructure failures without new evidence.
These stop the affected activity, not every independent issue or workstream.
Repair triggers are a reproduced implementation defect, source conflict,
changed dependency, or failed contract boundary. Counts, extraction length,
HTTP status, runtime and replay agreement are explanatory diagnostics only.
No population accuracy, complete law, actual loss or trading permission follows
merely from running the program. This is a deterministic engineering programme;
no stochastic method ranking is proposed.

## Sequence and concrete closure criteria

| Phase | Gaps and implementation | Closed when / retained output |
| --- | --- | --- |
| S0 preserve and implement successor control | Protect both old campaigns and implement a new namespace under the existing literal script prefix. Bind method, source, review and fact versions; retain failed attempts and refresh after every phase. | Controller tests demonstrate crash recovery, budget accounting, stale-result rejection, dependency scheduling and no-op resume. An executable dispatch table distinguishes implemented phases from planned work. Retain baseline manifest, method archive and controller test receipt. |
| S1 source admission, reference closure and dates | G10, G11, G18, G24. Implement explicit document-stage and page review, issue-specific edition/option/precedence/language binding, per-reference decisions and provenance intervals. | Wrong editions, missing decisive pages, unsupported stage, incorrect issue, circular unsupported dependencies, invented dates and stale reviews cannot satisfy a requirement. Source/review changes reopen dependants. Retain admitted-source records, dependency decisions and a per-issue residual graph. This closes the capability; evidence closure still depends on S2/S3. |
| S2 recover and admit the missing documents | G12–G17. Build the exact document shopping list below; search existing retained material before spending requests. Route discovery can start after S0; admission uses S1. | Each required document is retained, authenticated to its origin, reviewed for edition, execution/amendments, controlling language and applicability, and linked to the exact requirement. Missing documents remain open individually. Retain failed routes as well as admitted editions. |
| S3 authority and factual intake | G19, G20, G24–G26. Integrate reviewed IC-1 and relevant circulars; extend existing intake where necessary. Record real authority, issuer, event, bank and client assertions independently of the requested assessment time. | Each material assertion has evidence, provenance, applicable/known intervals and scope. Actual orders, implementation, stays/litigation and finality are checked where material. Absent private facts remain absent. Produce a fact request packet and registry/investigation receipts; preserve all 14 duties. |
| S4 resolve the remaining clause constructions | Residual limits of G03–G09 and G31. Group the 1,467 unresolved issue-level records by exact source construction while preserving each issue's scope and selections. Inspect controlling source text before proposing each semantic repair. | Every changed witness and exclusion, including those in already-positive cases, has a source-based decision and adversarial regression. Unfamiliar or ambiguous constructions remain unresolved. Retain a before/after disposition audit and all counterexamples. |
| S5 complete and join numerical profiles | G21–G23. Finish Deutsche timing, rounding and settlement; join its profile to the bank investigation. Then derive and implement separate BBVA, SEB and other necessary issue-specific profiles. | Each supported profile has a checked source derivation, explicit input/units/date requirements, boundary and adverse-case tests, and downstream bank integration. Unsupported profiles and missing inputs cannot yield an operational calculation. Retain derivations, scenario receipts and integration comparisons. |
| S6 freeze and validate on fresh cases | G30–G31. Predeclare new families/issues and adjudication rules; archive the final method before opening their PDFs. Evaluate against source adjudication independent of the reader/replay implementation. | Record every selected case, including inaccessible and abstained cases, errors and disagreements. A repair consumes the exposed set as development evidence and requires another untouched set for post-repair validation. Retain the selection/freeze, adjudication and challenge report. |
| S7 obtain scoped human acceptance | G32 and unresolved interpretation/application judgments. Prepare a review packet linking governing documents, selected clauses, derivations, authority and actual facts. | A qualified independent reviewer records acceptance, disagreement or unresolved points for specified instruments, dates and use. Human rejection triggers repair; absent review blocks acceptance while reversible development continues. No third-party messages are sent without authorization. |

S2 discovery, S3 intake development and S4/S5 work on already available sources
can proceed independently. One missing BASF document must not block an unrelated
Deutsche engineering repair. Admission and promotion depend on the requirements
of each issue; final challenge execution depends on freezing all components
being evaluated. S7 can review prepared portions early, but final acceptance
must identify the actual final versions.

## First implementation: S1 acceptance contract

Relevant current paths are `source_obligations.build/verify`,
`master_sources.extract/register`, `feature_investigation.investigate`, and
`transaction.intake.record` / `transaction.evidence.Registry`.
`source_obligations.build` currently inventories candidate references and sets
edition/amendment completeness to `NOT_ESTABLISHED`. Adding reviewed closure is
unfinished implementation, not solely an external-document blocker.

Use existing immutable source and reference IDs. A decision binds the issue,
reference ID and quote/span hash, original and derivative hashes, selected
edition and document stage, applicable option and language, precedence,
amendment search scope/cutoff, assessment dates, reviewer identity/role and
reasoning with source anchors. A review's existence or nonempty prose does not
establish that its interpretation is correct; preserve whether it is agent
review, independent adjudication or human legal acceptance.

Candidate decisions are unresolved, satisfied within a stated scope, or
inapplicable with a reviewed reason. A source reference is initially a candidate,
not automatically a missing contract. Deduplicate review work for shared source
passages, but retain every issue-specific binding and do not copy applicability
between issues merely because their PDFs match. Enumerating all regex matches
is not proof that all legal dependencies have been found.

Store decisions separately from historical reports; derive current status from
their bindings. A changed source, extraction, edition, selection, review,
amendment cutoff, discovered dependency, fact or calculation method invalidates
affected decisions and downstream reports. A reference cycle is not its own
evidence. Contradictory or multiply controlling editions require resolution.

Page review covers decisive pages and the declared operative scope, with a
document-wide omission check. Retain rendered-page comparison, extraction tool
and page hashes; investigate blank, image-only, reordered, table and special
character problems. A long text extraction is insufficient. Document stage is
explicitly reviewed; never default `preliminary` to false as proof of finality.
If OCR is necessary, record its tool/dependency policy and validate its decisive
output before use. No OCR installation is assumed in this plan.

Keep observed retrieval/recording times, evidenced legal effective intervals and
the assessment's requested known/effective times distinct. A user-requested
`known_at` must not manufacture a historical retrieval record. Unknown timing
must remain unknown; preserve original timestamps when migrating retained
evidence. Explicit hypothetical scenarios stay separate from actual assertions.

Meaningful tests must demonstrate at least: wrong-edition rejection; partial
page/quote tampering; unknown document stage; wrong issue/option; source or
review amendment reopening dependants; newly discovered reference reopening;
cycle handling; expired/not-yet-known evidence; duplicate conflicting review;
missing facts; and preservation of unaffected issue decisions. Include a real
retained-source integration example and inspect its output. Synthetic fixtures
test mechanics and do not count as source/legal acceptance.

## Missing-document work orders

| Gap | Exact evidence sought | Completion boundary |
| --- | --- | --- |
| G12 BASF | Base prospectus dated 9 September 2022, supplement dated 27 February 2023, final-term selections and controlling German Option I | Read the selected German terms and their dependencies. BASF stays unknown until the relevant missing-source and interpretation requirements are met. |
| G13 Enel | Authoritative executed agency/guarantee/covenant documents and relevant amendments | Resolve the retained blank signature block and execution status with authoritative evidence; an unsigned specimen cannot be silently treated as executed. |
| G14 Unilever | Separate operative agreements and applicable amendments | The denied programme route is an acquisition failure; a programme landing page alone does not supply the agreements. |
| G15 Lloyds | Primary SEC filing/exhibit or equivalently authenticated primary retained copy | Match issuer, instrument, filing identity and bytes; keep the existing secondary-origin qualification until authentication is established. |
| G16 SEB | July 2023 fiscal agency agreement and relevant 2024 supplements | Establish exact edition, incorporation and issue applicability. |
| G17 LVMH / BBVA | Complete applicable agreements, incorporated documents and subsequent amendments through the assessment cutoff | Evidence-bound dependency decisions for the relevant issues; do not equate LVMH's qualified negative feature answer with full agreement completeness. |

Use the retained metadata to identify alternative issuer, regulator or exchange
routes. Keep document requests separate from sending messages: preparing a
request packet is local work; contacting custodians or counterparties requires
authorization. Do not repeatedly request the same 403/404 route without a
specific new reason. Retrieval alone never changes classification.

The official HKMA IC-1 V.3 PDF dated 6 October 2017 is already retained. G19 now
needs applicability, related circulars and registry integration; downloading it
again is not the next useful step. G20 needs actual dated authority/event
evidence, including implementation and legal finality where relevant.

## Calculation and factual safeguards

Deutsche currently has separate conditional arithmetic; only UBS is joined in
`master_phases.integration`. Start with the missing Deutsche adapter and derive
timing, notice, settlement and rounding from the applicable controlling text.
A capital ratio alone does not supply the externally required loss amount.
Boundary tests must cover equality at the trigger, eligible pool membership,
currency and unit consistency, rounding/denomination effects, date boundaries,
write-up caps and discretion, and missing or contradictory actual inputs.

BBVA Condition 6.1 mandatory conversion and 6.2 opt-out require distinct paths.
SEB principal reduced to zero does not imply zero economic recovery: preserve
share rights and valuation inputs. Every further profile needs its own source
derivation and issue/edition binding. No formula is transferred by issuer label.
Where the sources have not established an exact rule, implement an explicit
unsupported result or conditional input, not an invented default.

For G25/G26, extend and test intake using synthetic fixtures, then request only
the missing real product, issuer, event, holdings, client, mandate, suitability,
bank policy, booking entity, jurisdiction and capacity evidence. Those real
facts cannot be generated by code. Prepare the smallest per-use request packet;
do not require private customer facts to finish a public-source feature study.

## Successor executor and repair/refresh behaviour

The fixed `close` namespace in `scripts/run_prospectus_evidence_master.py`
provides `status`, `check`, `phase`, `run`, `verify`, `rules`, `inspect` and
`render`. It uses independent state, receipts and finite budgets. The exact
relative command prefix matches installed approval rules.

Use new state and attempt directories under
`docs/implementation/prospectus-evidence-closure/`, and new inputs under
`docs/prospectus/evidence-closure/`. Snapshot both historical campaigns, their
source data, reviews, receipts, method archives and request ledgers. Source-code
changes can make historical results stale relative to current code; historical
receipts remain historical evidence. Verify them using their archived method
and source bindings. Never rerun the old campaign just to relabel it current.

After each attempt: verify outputs; record acceptance level and remaining gap
IDs; execute any already-reviewed deterministic repair; record the actual diff,
checks and replacement receipt; invalidate affected downstream results; derive
the next ready action from dependencies and current evidence. A new semantic
or formula repair needs source analysis, a counterexample and a plan amendment
before execution. The controller must not equate generating a repair request
with executing the repair, or silently synthesize its own legal approval.

Waiting for an unavailable document, private fact or human review is a per-gap
state. Continue independent ready work. An unimplemented phase is explicitly
unimplemented and cannot return success. Final output distinguishes completed
software work from supported issue decisions and independently accepted uses.
Preserve manifests with exact command, git commit and dirty-file hashes,
environment/CPU mode, data/review hashes, deterministic seeds marked N/A,
elapsed time, input/output paths, plan, results and next-action decision.

All routine commands should retain the literal approved prefix:
`.venv/bin/python scripts/run_prospectus_evidence_master.py`.
Use structured local inputs, no shell snippets or arbitrary command fields.
Local edits are already authorized; do not add confirmation between phases.
Actual sandbox restrictions still apply, including the previously observed
bubblewrap mount problem. Existing approvals do not guarantee that every
future command or protected-path write will be permitted.

## Bounds, defaults and fresh validation

Public recovery retains the existing total allowance of 12 dispatches, seven
already consumed: five remain across this work and any continuation fetches.
Carry the ledger forward without resetting it; reserve before dispatch and
count redirects/retries. Retain two dispatches per exact URL, 45 seconds and
32 MiB per response. Review exact HTTPS hosts/URLs before extending the queue;
do not modify historical receipts or widen to arbitrary destinations.
If five requests cannot recover the required material, report the exact
unavailable documents and proposed additional budget. Do not claim full source
closure or silently start a new request allowance.

Proposed local execution bound for the successor is four hours of automated
phase time, 15 minutes per child command and at most three identical failed
attempts per method/input. These are convenience execution limits, not evidence
thresholds or a delivery-time estimate. Test timeouts and crash charging early;
record justified changes before expanding the bound. CPU only with
`CUDA_VISIBLE_DEVICES=-1`; use the existing environment. No package installation,
paid model calls, private retrieval, external messages or transaction execution
is necessary for preparing and testing the engineering extensions.

The inherited 36 cases are exposed development evidence. Source grouping is a
review-efficiency choice whose risk is false sharing; the earliest check is
issue/edition/option separation. Existing arithmetic is a baseline hypothesis
until source-specific derivation and downstream checks pass. Existing source
dates and document-stage fields are assertions to audit, not reviewed defaults.
The narrow LVMH constructions remain protected regression cases; do not restore
the rejected broad interest/forfeiture exemption to lower the unresolved count.

S6 needs a completed challenge subprotocol before acquisition or evaluation:
named eligible families/issues, exclusion and substitution rules, exposure
audit, exact source/request budget, independent adjudicator and rubric,
primary error/abstention criteria, and the decision the sample can support.
Require mechanism diversity (ordinary repayment, temporary/permanent write-down,
mandatory conversion and optional provisions). Choose sample size against the
claimed error bound; a small purposive set supports bounded case evidence only.
The remaining five recovery requests are not an implicit fresh-challenge budget.
Until these fields are filled and resources available, S6 is not execution-ready.
Model review may find defects but cannot substitute for qualified human legal
acceptance or make the shared reader's replay an independent semantic test.

## Skeptical audit and next action

The code trace rejects these shortcuts: use a completed no-op runner as the next
program; count documents downloaded as admission; turn all regex references
into legal requirements; mark a document final because extraction succeeded;
reuse `known_at` as retrieval provenance; join only UBS while reporting general
calculation coverage; count tests or fewer flags as English entailment; call
the exposed 36 cases fresh; or treat missing client evidence as a software bug.

The revised design uses the correct delivered comparator, distinguishes proxy
diagnostics from acceptance, preserves issue-level scope and all 14 duties,
defines stop/repair rules and resource bounds, and does not assume a new
environment or available private facts. Independent activities can proceed
after a failed candidate. It names the missing executor instead of advertising
unimplemented commands as executable. Design audit passes for S0/S1 development.
S2 evidence closure, source-specific S3–S5 promotion, S6 execution and S7 final
acceptance remain conditional on the concrete requirements above. This audit
is supervising-agent review, not independent legal adjudication.

The first delivery should be S0/S1 with actual admission/invalidation tests and
one inspected retained-source integration example, followed by per-issue source
work and the Deutsche adapter. Do not make unavailable BASF or private client
evidence prerequisites for that reversible implementation.

Existing baseline verification command, executable now in the feature checkout:

```text
.venv/bin/python scripts/run_prospectus_evidence_master.py continue verify
```

This checks the delivered comparator; it does not execute S0–S7. Completion
must be reported from actual new phase receipts, never inferred from this plan.

## Implementation review before the successor run

The resumed S0/001 regression passed. The subsequent code review found material
defects: unconsumed source and review inputs, omitted UBS integration and existing
authority sources, request bytes outside phase integrity checks, and missing
adjudication handling. Repair these before accepting successor results. Added
tests cover actual factual intake, source amendment binding, linked-file
invalidation, request tampering and challenge contamination.

Source intake now requires versioned document identities, exact issue selection
reviews and admissions before changed sources enter the development inventory.
S1 recomputes classification and reference requirements from that inventory.
Clause review records desired and actual dispositions separately: an expected
disposition never edits the reader. S4 audits every changed or removed record.
S5 must join all three declared conditional profiles, preserve factual assertions
and retain all bank duties. The original UBS profile and authority sources remain
in S3. Known acquisition times come from retained receipts; unknown times remain
unknown.

S6 can freeze a valid protocol before sources, then evaluate a complete
denominator against separately recorded source adjudication. The proposed
Danske family is already exposed and is ineligible as a fresh issuer family.
No fresh challenge may begin without an eligible exact selection, independent
adjudicator and separately approved request allocation. S7 accepts only a dated,
version-bound review with a matching retained human attestation. Recorded scoped
acceptance cannot clear missing upstream evidence or grant transaction permission.
Model-generated text cannot supply human acceptance.

Final review also requires verifying every retained attempt and external response
before a rerun. A source work order may be satisfied only by a review covering its
exact affected issue set, current admitted sources, resolved reference decisions
and controlling-source quotes. Tests must show valid review intake can advance a
phase while missing or stale submissions remain open. The factual intake
regression exposed a missing media-type field; source records now preserve the
declared media type so typed JSON assertions reach the existing bank investigator.


Skeptical audit passes for the repaired controller, source/fact/review intake,
conditional calculations and bounded source recovery. The comparator, source
hashes, 14 bank duties and four-hour/15-minute bounds are unchanged. Test counts,
HTTP success and review forms are explanatory diagnostics, never legal closure.
Continuation stops on altered protected history, corrupted evidence or budget
exhaustion for the affected activity. Missing documents trigger source work;
missing adjudication blocks challenge acceptance while other work proceeds.

Execute with:
`.venv/bin/python scripts/run_prospectus_evidence_master.py close run`.
Then run `close verify` and a no-op `close run`. Record phase results, remaining
source/implementation/human requirements and any failed-route evidence in the
successor reset memo. Do not update this versioned plan merely to log routine
progress, since plan changes intentionally invalidate phase results.
