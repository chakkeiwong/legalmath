# Interpretation-search implementation and execution result

As of 23 September 2026, the missing source-driven generator and tree-search
procedure is implemented. The current full engineering regression passed **310
tests**, including **78 search tests**. P5 attempt 05 passed the one-round live criteria
on both retained circulars. Inspection found a real weakness in the finite
comparison probes; P7 repaired it and replayed the frozen outputs without new
model calls. P8 passed the additional multi-round live acceptance for that
repair. P9 then verified depth-two descent for both schedulers and reran the
full suite. P10–P12 then implemented exact fact aliases and a separate
conditional correspondence review workflow, repaired an out-of-domain fallback
defect, and replayed all 45 P8 comparisons without new model calls. The 33
incomparable pairs now have complete review packets. No independent
legal-accuracy evaluation has been performed.

The executable plan is [master-plan.md](master-plan.md), with its fixed runner
at `scripts/run_interpretation_search_plan.py`. The
[operator guide](operator-guide.md) explains the inputs, sequence, commands,
service operations, Java delivery and interpretation of evidence. This report
distinguishes delivered behavior from acceptance that remains outstanding.

**Scope correction after the user's review-cost concern:** completion of
P0–P12 does not mean the monograph's full method is implemented. The
[automation coverage audit](automation-gap-audit.md) identifies missing
source-facing semantic checks, structured legal challenges and continuing
reinvestigation. The revised [next-phase plan](next-phase-plan.md) prioritizes
that work and public/controlled validation before external consultancy. A
newly commissioned legal review is not a prerequisite for those engineering
phases. Historical results and release restrictions below are unchanged.

## What changed

The previous E01–E09 controller read supplied proposals and repair fixtures.
`src/legalmath/interpretation/search` now generates proposals from source text
using fresh Codex contexts and investigates their differences. Initial readings
are frozen before refinement sees peer evidence. The three roles now have
explicitly different reading methods. Every role must account for six
interpretation dimensions and all supplied source units.

The compiler accepts a restricted typed expression language and retains
readings it cannot encode. Each compiled candidate is executed through Python
and generated Java on boundary probes. Supported SMT domains can establish a
comparison result within the declared domain. The complete declared Boolean
state space is now used when fact definitions match and no caller domain was
supplied; numeric/date cases retain the actual scope of their checks. A generated
counterexample is replayed in both Java candidates. Different fact meanings
prevent automatic comparison, even when names look similar. Exact metadata
aliases use a recorded bijection. Broader correspondences need explicit
assumptions and always produce conditional evidence.

The investigation tree supports BFS and bounded UCT selection, parent/child
lineage, root action limits, visits and backpropagated behavioral-difference
rewards. Refinements receive retained source context and comparison evidence.
Separate reconstruction calls check the controlled-English rendering. Invalid
outputs receive bounded, separately counted repairs; failed originals remain
visible. Grounded and stable argument semantics, distinguishing questions and
complete-link behavioral groups provide additional review aids. The argument
graph currently represents behavioral incompatibility, not legally established
attacks or priorities.

The CLI and service use existing immutable storage, source invalidation,
authenticated identities, archives and release controls. The annotation path
assigns source-first reviewers, records their attestations and requires a
distinct adjudicator. Paired evaluation can load these frozen labels and keeps
unresolved or unadjudicated cases separate. It cannot manufacture independent
human evidence or turn universal abstention into an accuracy win.

## Acceptance evidence

| Phase | Recorded result | What the result establishes |
|---|---|---|
| P0 | Passed | Frozen baseline and small existing correctness suite |
| P1 | Passed | Strict response contracts, isolated provider configuration and counted allowance |
| P2 | Passed | Restricted formalization, comparison, reconstruction request isolation and bounded argument semantics |
| P3 | Passed | Generated tree expansion, BFS/UCT behavior, reports and fail-closed handling in engineering cases |
| P4 | Passed | Search and existing interpretation integration at that phase's source hashes |
| P5 | Passed, attempt 05 | Both retained sources completed generation, accepted child refinement and reconstruction; malformed output was visibly repaired |
| P6 | Passed, attempt 03 | Earlier full suite: 277 passed; sandboxed failures retained |
| P7 | Passed, attempt 02 | 280 tests passed, two dependency deprecation warnings, 165.02 seconds; all 27 saved live pairs replayed |
| P8 | Passed, attempt 01 | Three rounds, three initial roles, accepted children, reconstruction and current Java/report checks for both sources |
| P9 | Passed, attempt 01 | Depth-two BFS/UCT fixture: 2 focused tests passed; full suite 282 passed in 214.38 seconds |
| P10 | Passed, attempt 01 | 21 focused tests passed: exact aliases, total bijections, semantic-change rejection and original Java witness replay |
| P11 | Passed, attempt 01 | 10 tests passed: immutable correspondence records, roles, source changes, concurrent rejection and archives |
| P12 | Passed, attempt 01 | Full suite 310 passed in 258.39 seconds; all 45 P8 pairs replayed, 33 review packets exported; no live calls |

The authoritative current regression evidence is
`artifacts/interpretation/round2/P12/attempt-01/run-manifest.json`, `tests.xml`
and `tests.log`. The manifest binds every tested input hash to base commit
`bb0e8b3b4b9431df22dd5517a124d2952896c6bf`, the command, environment, review and
artifact hashes. These are dirty-worktree implementation results, not a claim
that the changes are already committed. Existing monograph work was preserved.
The current verification record is
`artifacts/interpretation/round2/fact-alignment-evidence-check.json`: it checks
all 191 current acceptance inputs, the 158 frozen baseline files and accepted
phase artifacts. The earlier `final-evidence-check.json` is retained as the
historical P9 check of its 185 inputs; later implementation changes are covered
by P12. No P12 acceptance input changed after its regression.

P6's first two sandboxed supervisor attempts stalled in a TestClient setup and
were interrupted and recovered as counted failures. A direct full suite and a
bounded nested reproduction passed. The same fixed supervisor then passed in
the trusted execution context. This supports using the trusted result for
acceptance; the precise cause of the sandboxed stall is not established. The
earlier diagnosis of a transient stall was explicitly withdrawn in
`p6-repair-02.json`.

## Earlier failed live evidence, retained unchanged

Attempt 03 used the retained public text of **24EC50**, concerning the e-IP
parallel-run extension. All three initial roles returned structured responses.
The program retained five candidate commitments, ran five candidate Java
checks, recorded ten pairwise comparisons and performed one fresh
reconstruction. Some commitments overlap; five candidates do not imply five
independent or materially distinct legal interpretations.

Two candidate pairs exhibited executable differences. They distinguished a
reading limited to the product categories in footnote 1 from a reading covering
any investment product administered by IPD. The hypothetical distinguishing
case was an IPD-administered product outside the enumeration. The generated
readings themselves questioned whether such a product exists and whether the
footnote is exhaustive. The program did not decide either legal or factual
question. This is evidence that the generator constructed a rival commitment
and that the comparison could expose its consequences.

Eight other pairs had incompatible fact definitions and were reported as
`INCOMPARABLE_FACT_BINDINGS`. The reconstruction had
`NO_DIFFERENCE_IN_FINITE_PROBES`; it was not reported as equivalent over all
inputs. The live refinement then cited `u24`, which does not exist in the
retained packet. Exact reference validation rejected it, leaving zero accepted
child candidates. Consequently the pilot failed its branch-expansion criterion.

The relevant evidence is preserved in:

* `artifacts/interpretation/round2/P5/attempt-03/pilot/24EC50/packet.json`;
* `investigation.json`, `report.json` and `history.zip` in that directory;
* the candidate builds under its `java` directory;
* `artifacts/interpretation/round2/P5/attempt-03/live-pilot.log`.

The later code changes have not been retroactively applied to this history.
It is evidence from the exact earlier input hashes recorded in its manifest.

The first two live attempts failed before useful interpretation: the initial
adapter discarded the configured provider route, and the next attempt failed
at startup. The adapter now preserves only the configured route/model, excludes
tools and inherited instructions, and retains bounded diagnostics. These
failures consumed seven invocations; attempt 03 consumed five. They remain
counted, for a total of twelve.

Under the then-authorized ceiling of sixteen, four calls remained. A complete
repaired case budgeted six calls. Attempt 04 therefore produced
`LIVE_ALLOWANCE_INSUFFICIENT` before constructing a provider and consumed no
calls. The user subsequently authorized **100 total live invocations**, including
those already consumed, with “you have 100 tests. continue”. The plan and ledger
were updated together; `authorization-100.json` preserves the earlier twelve
reservations. The ceiling is a limit, not a target to exhaust.

## Completed one-round live pilot

P5 attempt 05 used **eleven additional calls** and passed on both sources:

| Retained source and selected control | Scheduler | Calls | Retained candidates | Accepted children | Java checks | Comparisons | Reconstructions |
|---|---|---:|---:|---:|---:|---:|---:|
| 24EC50: submission channel and transition | BFS | 5 | 5 | 1 | 3 | 3 | 1 |
| 23EC46: gift promotion, fee discounts and product connection | UCT | 6 | 8 | 2 | 8 | 24 | 1 |

These are candidate commitments, not counts of independent or materially distinct
legal interpretations. Both sources are development material, and each run
addresses a selected control with the surrounding source retained as context.
Neither is a complete or current-law certification of the circular.

For 24EC50, two initial readings could not be compiled: one placed prose in a
formal expression and one explicitly had no supported formalization. The
investigator supplied a compilable child for the malformed expression; both
original encoding limitations stayed visible. The remaining pairs had different
fact bindings. Its reconstruction agreed only on the finite probes available
for the date-bearing rule. The report retained 57 unresolved issue records,
four unexpanded nodes and four unreconstructed nodes.

For 23EC46, the first refinement inserted an ellipsis into a purported exact
quotation. Source validation rejected it. A separately counted `REPAIR_OUTPUT`
call returned a valid quotation and two child readings. The original action
remains `FAILED`; the correction is marked
`VALIDATED_OUTPUT_ONLY_MEANING_UNRESOLVED`. The report retained 119 unresolved
issue records, seven unexpanded nodes and seven unreconstructed nodes.
Issue counts can include related questions and are not counts of distinct legal
ambiguities.

The accepted evidence is in
`artifacts/interpretation/round2/P5/attempt-05/run-manifest.json` and each
source's `packet.json`, `investigation.json`, `report.json`, `history.zip` and
`java` directory under its `pilot` directory. No earlier history was overwritten.

## The live-discovered comparison defect and executed repair

One 23EC46 pair encoded the gift restriction as either
`G AND NOT D AND L_direct` or
`G AND NOT D AND (L_direct OR L_context)`, using identical fact definitions.
Here `G` denotes a gift, `D` a fee discount, and the two link facts distinguish
direct from contextual product connection. With scope true, a gift, no fee
discount, no direct link and a contextual link, the bodies return false and
true. Python and both generated Java classes confirmed this substitution.

All 128 old finite probes missed the interaction. Their stored
`NO_DIFFERENCE_IN_FINITE_PROBES` result was accurate about what was tested, but
the coverage was insufficient to expose this material encoded difference.
The revised comparator invokes the existing SMT encoder over the complete
declared `{T,F,U}` domain for identical Boolean facts. A caller-supplied domain
is preserved. Solver unknown/unsupported results remain visible; no numerical
range or business-feasibility constraint is invented.

P7 replayed the exact earlier candidate and source bytes. It found three
different pairs among the 24 23EC46 comparisons, including the missed pair;
21 remained incomparable. All three 24EC50 pairs remained incomparable.
Replay consumed no model calls and did not change old reports. The first P7
attempt passed 280 tests but failed because its replay harness used the strict
rule-data parser on fractional manifest timings. After the narrow parser repair,
attempt 02 passed the full suite and replay. The
[comparison audit](live-comparison-audit.md) contains the pre-run contract,
diagnostic and decision.

This repair establishes a behavior difference between encoded readings. It does
not establish which reading is faithful to the English, whether the witness is
feasible in bank operations, or an independently checked solver proof.

## Multi-round live acceptance

P8 used three investigation rounds and at most twelve model calls per source,
requiring at least two actual rounds. It consumed 18 calls (nine per source),
bringing the persistent allowance to **41 of 100**. Both sources passed the
engineering criteria, with no model-call failures or unrepaired output
failures:

| Source and selected control | Scheduler | Candidates | Children | Maximum depth | Java checks | Reconstructions | Comparisons | Terminal stop |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 24EC50: e-IP submission route and transition | BFS | 7 | 4 | 1 | 7 | 3 | 21 | `ROUND_LIMIT` |
| 23EC46: gift-promotion restriction | UCT | 11 | 6 | 1 | 11 | 3 | 24 (bounded) | `ROUND_LIMIT` |

Each source had three validated initial role responses and a blocked terminal
report. Every compiled candidate received a Java check; every accepted run kept
unexpanded and unreconstructed nodes visible. The live trees did not reach depth
two within three rounds. P9 supplies separate deterministic evidence that both
schedulers can descend to a grandchild when the bounded fixture presents one.
24EC50 retained 102 unresolved issue records, four unexpanded nodes and four
unreconstructed nodes. 23EC46 retained 141 issue records, eight unexpanded
nodes and eight unreconstructed nodes. These are review records, not counts of
distinct legal ambiguities. One reconstruction in each run explicitly reported
uncertainty even though its tested behavior agreed; that uncertainty stayed
visible.

The repaired comparator found encoded behavioral differences in both live
sources. For 24EC50, one difference concerns treating the footnote 1 product
enumeration as exhaustive versus descriptive; the hypothetical outside-list
product remains an unresolved factual and legal question. For 23EC46, six of 24
bounded comparisons were `DIFFERENT`, three were equivalent within the complete
Boolean domain, and 15 were incomparable because fact definitions differed.
Witnesses include `UNKNOWN` versus a definite decision and `OUT_OF_SCOPE` versus
a result. These statuses are execution distinctions, not legal classifications
by themselves. No generated statement was promoted to a bank rule.

The P8 pilot result is
`artifacts/interpretation/round2/P8/attempt-01/pilot/result.json`; source
packets, investigations, reports, histories and Java builds are beside it.
The phase manifest is
`artifacts/interpretation/round2/P8/attempt-01/run-manifest.json`, which records
the 1,351.762-second trusted live-pilot execution. The 100-call ceiling has 59
unused slots; consuming them is neither required nor evidence of completeness.

## P9 tree-depth regression

P9 adds `test_bounded_search_descends_to_a_grandchild_and_keeps_frontier` for
BFS and UCT. A deterministic source fixture returns three distinct roots and
distinct refinements. Each scheduler produced a depth-two node, preserved its
immediate parent and root identity, performed exactly ten bounded model actions,
ran Java checks for every compiled node, and left the grandchild in the
unexpanded frontier. The focused test took 50.169 seconds; the full suite took
215.908 seconds. This is a traversal and accounting result. It does not rank
BFS versus UCT, prove search completeness or say anything about a circular's
meaning.

## Defects found during review and repaired

The [fact correspondence result](fact-alignment-result.md) documents the
P10–P12 extension, its pre-run audit, exact commands and the new review API.
The frozen P8 replay keeps 18 of 21 24EC50 pairs and 15 of 24 23EC46 pairs
incomparable. It finds no new exact-alias opportunity. A preselected 24EC50
mapping, assuming the same submission event, date convention and channel,
finds no difference in 36 finite probes; it remains conditional and unapproved.

The same audit exposed an inherited comparator bug: after a solver returned
UNKNOWN or UNSUPPORTED for a declared restricted domain, finite probes could
return a witness outside that domain. Three regressions reproduced the error.
The repair preserves the unresolved solver status with no unconstrained
fallback for caller-declared domains. All 15 comparator tests and the current
310-test full suite pass. Failed diagnostic evidence remains available.

| Defect | Repair and discriminating evidence |
|---|---|
| Invalid source IDs ended investigation without a corrective output pass | Bounded fresh correction receives exact error, permitted IDs and the rejected response; a test preserves the failure and accepts a valid corrected child |
| Raw output was marked a successful action before schema validation | Persist raw output separately; validate before successful completion; invalid output now has a failed action |
| Repeated identical malformed repairs could collide with an earlier action | Bind each correction to the preceding request hash; two malformed corrections remain distinct charged attempts |
| Report verifier checked only some report fields | Recompute the entire report; tests reject forged release flags, probabilities, statuses and call counts |
| A reused creation key could change search settings outside the legacy policy | Bind all search settings and reject conflicting idempotent creation |
| Truncated Cartesian probes could leave leading facts unknown in every case | Start with known baselines and single-fact variations; a multi-fact scope test confirms a known outcome is exercised |
| Unchanged field names could mask changed fact meanings | Require identical declared fact bindings before comparison; report incompatibility |
| Annotation assignments could be replaced | Make assignment immutable; enforce distinct reviewers/adjudicator and source identity |
| Supplied reference labels were not connected to the annotation workflow | Add evaluation from frozen adjudications; unresolved readings remain unadjudicated |
| A live provider could be constructed without a durable allowance | Require an allowance before any dispatch; add a rejecting test |
| A manual ceiling edit briefly produced 116 instead of 16 | Correct it with structured JSON; no call occurred; pilot now checks ledger ceiling against the reviewed plan |
| Pilot acceptance rejected even successfully repaired output failures | Preserve all failures, distinguish validated repairs from unresolved failures, and test the repaired path without granting meaning approval |
| Finite probes missed an interacting gift/discount/product-link condition in actual live output | Use the complete declared Boolean domain when appropriate; replay the frozen missed pair and require both generated Java classes to confirm the witness |
| Replay parsed measured fractional timings as strict rule data | Parse the supervisor manifest as ordinary JSON; retain strict parsing and hash checks on source and investigation data |
| Differently named identical declarations prevented comparisons | Unique total metadata correspondence, AST substitution and original Java witness replay; all 243 three-valued assignments of a five-fact permutation checked |
| A semantic mapping could conceal changed meaning or input decomposition | Explicit per-link and output assumptions, total bijection and conditional status; changed units, missing facts and hidden exceptions are rejected |
| Unresolved restricted-domain checks could return an out-of-domain probe witness | Preserve UNKNOWN or UNSUPPORTED for caller domains; retain three failing reproductions and the passing repair |

The review is author self-review with executable adversarial tests. No fresh
external code-review verdict or independent human legal review is claimed.

## Decision and evidentiary limits

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Unsupported conclusion |
|---|---|---|---|---|---|
| Accept P7 engineering regression and comparison repair | 280 tests and frozen-pair replay pass in trusted supervisor | No current regression failure; prior stalls and parser failure retained | Untested environments, solver/encoding trust and finite tests | Preserve the repair and use it in held-out evaluation | Absolute software correctness |
| Accept P8 live engineering behavior | Both sources completed three rounds with accepted children, reconstructions, Java checks and blocked reports | No model-call or unrepaired-output failure; unresolved frontiers remain | Same-model omissions, incompatible facts and missing authorities | Obtain independent human annotations and test held-out sources | Correct English interpretation or independent accuracy validation |
| Accept P9 tree implementation evidence | Both schedulers create and account for a depth-two fixture node; 282 tests pass | No current regression failure; synthetic fixture only | Behavior outside the fixture and production load | Add deeper cases only when a concrete defect or source need justifies them | Search completeness or BFS/UCT superiority |
| Accept P10–P12 correspondence engineering | 310 tests pass; 45 saved pairs replayed; original histories and allowance preserved | No current test failure; unresolved definitions remain visible | Whether mapping and output assumptions are correct | Review the 33 supplied packets; extend representation only under explicit semantics | Legal equivalence, completeness or production readiness |
| Withhold legal-accuracy and production claims | Requires independent source-first labels, adjudication and bank controls | Those evidentiary prerequisites are absent | Shared model omissions, missing authorities and operational fact definitions | Obtain independent annotations and define a held-out protocol | Correct English interpretation or production readiness |

| Inference status | Result |
|---|---|
| Hard veto evidence | Nonexistent references and inexact quotes were rejected; failed originals were retained; both accepted P5 reports remained blocked |
| Statistically supported ranking | None; no independent paired legal-accuracy experiment was executed |
| Descriptive evidence | P5 attempt 05 retained five and eight commitments; P7 found three different pairs among the saved 23EC46 comparisons; counts are not accuracy estimates |
| Default readiness | Research search only; no change to legal release authority |
| Next evidence | Independent source-first annotations, adjudicated held-out circulars and a preregistered paired evaluation |

The strongest alternative explanation for apparent breadth is that fresh
contexts repeat the same omission while varying wording or fact decomposition.
The live comparisons already demonstrate the fact-decomposition problem.
Independent annotations that identify an omitted duty would overturn any
stronger reading of the current evidence. The weakest evidence is the fidelity
of generated commitments to the original English; it remains unproved and
unevaluated by independent experts. Formal consistency and Java conformance
cannot fill that gap.

The [next-phase plan](next-phase-plan.md) preserves the remaining work and the
conditions for continuing it. Engineering acceptance does not authorize a bank
deployment.
