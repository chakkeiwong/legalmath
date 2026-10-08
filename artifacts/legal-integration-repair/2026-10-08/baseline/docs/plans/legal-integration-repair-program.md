# Legal product integration repair program

8 October 2026. This program implements the user's request to trace the current
code and execution, enumerate the remaining gaps, review a repair plan, and
execute it. It succeeds the completed tool-gap validation experiment; it does
not extend that experiment's phases or replace its failed results.

## Problem and baseline

The preceding run is `artifacts/legal-tool-gap-validation/2026-10-08`, verified
before these repairs. Its final verdict is INCOMPLETE_WITH_EVIDENCE: 46 original
obligations remain open, 35 original readings remain retained, and 32 of those
readings are unformalized. The product baseline produced 12 candidates and 35
claims, hence 420 required pairs; generation in the combined arm produced no
candidates. Neither arm produced a complete dossier. Component engine checks
cannot answer whether the legal product closes those obligations.

The traced defects are:

| ID | Confirmed problem | Repair and acceptance evidence |
|---|---|---|
| I1 | Broad fidelity receives executable text without the candidate's declared question/meaning, and can misattribute a trigger to fulfillment. | Supply declared meaning separately; it must never count as an executable quote. Test the retained trigger and reject a prose-only ENTAILED anchor. Exact question assignments remain proposals. |
| I2 | Empty candidates pass the file-existence prerequisite, causing three impossible question calls. | Fail before assignment, retain a recoverable prerequisite diagnostic, and prove zero downstream calls. |
| I3 | Four scoped actions cannot cover 420 pairs at batch size 12: at least 70 are needed. | Admission reports the complete denominator and minimum calls before dispatch, blocks impossible full runs, and never silently prunes pairs. |
| I4 | No transport stop is treated as complete even when dimensions are UNASSESSED. | Recompute coverage from both perspectives and every dimension in producer and verifier; agreed UNASSESSED values must not terminate repair rounds early. |
| I5 | Optional tools are a trial wrapper; feedback is replaced by an empty list and raw proposed attacks differ from effective product defeats. | Add a source-bound validated checkpoint interface to the actual workflow, persistent tool evidence, and normalized effective graph checks. Later requests must receive applicable evidence; proposed priorities cannot become accepted priorities. |
| I6 | Wrapper directories cannot resume; successful requests may be lost while interrupted requests risk redispatch. | Durable exact-request caching, immutable failed/reserved records, no silent retry after interruption; test restart and request/source invalidation. Preserve the existing circuit breaker. |
| I7 | Tool-augmented wire hashes can undercount scoped provider calls. | Trace counted reservations through provider provenance; report exact reservation deltas for live diagnostics, and do not infer zero calls from pre-augmentation hashes. |
| I8 | Old verification compares frozen product files with current live source. | Preserve the baseline snapshot, inputs and receipts; verify historical copies separately and explicitly report changed live files. Do not rewrite old evidence. |

The complete inventory, including all original IDs and missing premises, is
generated at `docs/implementation/legal-integration-repair/remaining-gaps.md`.
Product limitations also include missing HK/UK citation support, unimplemented
case analogy/consent classification, restricted Logical English grammar,
restricted LegalRuleML Boolean/conditional interchange, unsupported temporal and
deontic meanings, missing factual records and legal applicability judgments,+and no heldout legal-quality evidence. Each remains open unless specific
evidence resolves it; software repairs alone do not do so.

## Research intent and evidence contract

**Question:** Can the existing tools be connected to validated product stages
with correct scope, complete accounting and safe recovery, and what original
missing premises do their outputs actually address?

**Mechanism:** separate declared and executable meaning; prerequisite and
capacity checks; coverage-based completion; durable optional-tool checkpoints.

**Comparator:** the preserved dirty implementation and its retained failed
executions, not HEAD alone and not an idealized synthetic baseline. Controlled
fixtures are only engineering controls. Retained baseline candidates used in a
diagnostic remain baseline-generated candidates, including in the combined arm.

| Role | Criterion |
|---|---|
| Engineering pass | Meaning survives without becoming proof; no calls with impossible prerequisites; no false completion; actual external tools check validated computations; exact successes survive restart and failures cannot be silently replayed. |
| Applicability evidence | Every output names its source, input scope, missing premise, limitation and next evidence. Successful XML/graph computation supplies no legal warrant. |
| Legal closure | Exact original question, supported source interpretation, established facts and applicability, and reviewed rival/contrary readings. None is presumed closed. |
| Promotion veto | False coverage, changed denominator/source, lost uncertainty, false fulfillment, raw/effective graph mismatch, manufactured legal priority, missing provenance or source identity. |
| Continuation veto | Corrupted evidence, invalid harness, changed unreviewed method, unsafe command, exhausted shared allowance/window, or inaccessible prerequisite for the dependent action. Independent offline work continues. |
| Repair trigger | Reproducible adapter, semantic-context, validation, recovery, or transport failure. Retain the original failure. |
| Explanatory only | Tool counts, timing, graph extensions, parser success, model agreement, retrieval rank and individual answer differences. |

No accuracy rate, stochastic ranking, general English equivalence, legal
correctness, default-readiness or full 420-pair live completion will be inferred
from the bounded diagnostics. Full live completion is under-budgeted: the
baseline arm has nine reservations left and the combined arm fourteen, below
the 70-call scoped minimum before any other stage or retry.

## Assumptions and pre-mortem

| Choice | Provenance and status | Failure mode and earliest diagnostic |
|---|---|---|
| Same 46 obligations, 35 readings, four questions and 60 source units | Frozen predecessor; baseline | Shrinking denominator conceals failures. Check exact IDs/hashes before every result. |
| Same model route, 180-second maximum call | Existing authorization; reviewed bound | Timeouts can persist. Preserve failure and stop dependent live actions; no provider substitution. |
| Two perspectives; batches up to 12 | Existing scoped design; hypothesis | Schema validity conceals UNASSESSED dimensions. Adversarial two-perspective control and coverage recomputation. |
| Optional tools remain optional | Existing comparison; reviewed design | Successful tool invocation is mistaken for legal truth. Explicit scope and uncertainty in every checkpoint. |
| Graph limit 12 for criticism | Product limit; bounded engineering choice | Exponential enumeration grows. Exercise a 12-node control; reject larger input explicitly. |
| Exact response reuse | Existing EvidenceJournal; reviewed mechanism | Different source/settings/context reuse evidence. Bind all inputs and retain frozen per-request context. |
| CPU only; installed pinned tool environments | Existing tool setup; convenience retained | Wrong environment invalidates results. Record executables/hashes and run actual tools, with CUDA hidden. |
| Development controls, no new training | Available evidence; limited scope | Overfitting to known examples. Explicitly defer heldout legal-quality claims. |

A command can pass while checking raw attacks, discarding unformalized readings,
or accepting unanimous UNASSESSED judgments. The controls must catch these
before any live dispatch. A provider timeout rejects that attempted execution;
it is not evidence against the tools' legal usefulness. A sound conditional
graph or expression does not establish its source premises.

## Finite execution and phase refresh

1. **R0 — preserve and enumerate.** Snapshot dirty source and predecessor receipts;
   generate all 46 obligation and 35 reading entries. Record budgets and the
   exact implementation baseline. No provider calls.
2. **R1 — repair product contracts.** Implement I1–I4 with meaningful regression
   tests. Verify original denominator, partial coverage and adversarial controls.
3. **R2 — integrate and recover.** Implement I5–I7 using validated checkpoints,
   retained evidence and exact request identity. Exercise actual tools on retained
   product inputs and a complete controlled product workflow. No legal closure
   claim follows from the controlled run.
4. **R3 — bounded live diagnostic.** Only after R1/R2 pass, reuse the original
   two responsibility/demonstration pairs from the 420-pair matrix with both
   perspectives and the same source/question in both arms. Maximum two calls
   per arm, four total, no automatic repair dispatch. Combined receives checked
   Boolean evidence/retrieval, baseline does not. This tests the repaired path;
   it is not another full product trial or superiority experiment. Stop that
   dependent stage on transport failure; preserve other completed evidence.
5. **R4 — verify and hand off.** Recheck preserved baseline hashes, all new
   receipts and call/repair deltas. Record the engineering decisions, live
   limitations, all residual gaps and next justified evidence. No appended
   phases or automatic new budget.

Between phases the fixed runner records findings, passed/failed prerequisites,
the next phase's evidence question, remaining budget and any veto. Implementation
repairs are recorded as one bounded batch against the old repair ledger, without
resetting its start time or caps. At most four live reservations use the existing
`product.baseline` and `product.combined` arms. There is no new allowance.

Commands use `.venv/bin/python scripts/run_legal_integration_repair.py` followed
by exactly `check`, `execute`, `status` or `verify`. No shell passthrough, package
installation, provider substitution, budget extension, Git publication or rule
editing occurs in execute. Local preparation/tests need no additional approval.
If network execution needs approval, request this single narrow wrapper once.
The proposed command policy lives beside this program; protected global policy
files are not edited by ordinary sandboxed tools. The official Codex rules page
returned HTTP 403 in sandbox and trusted contexts, so local policy-check output
is the evidence for command matching, not an assertion about managed-review bypass.

## Skeptical review before implementation

**PASS WITH REVISED SCOPE.** Rejected a fresh full live run: the original limits
cannot fund it, and shrinking the matrix would answer a different question.
Rejected merely adding prose to executable representation: that would allow
unimplemented promises to pass as source fidelity. Rejected checking raw model
graphs: blocked premises, typed attacks and inherited defeats alter the product
target. Rejected silently rerunning interrupted tool wrappers: counted requests
must remain durable. Rejected rewriting old verification receipts after source
edits: historical snapshot and current-method claims must be separate.

Remaining risks are explicit: late exact-question proposals remain provisional,
source claims themselves can be wrong, optional tool coverage is restricted,
and four development calls cannot rank legal quality. Early adversarial controls
and a complete fixture test answer the engineering question; all original legal
gaps remain in the inventory. The planned commands produce evidence for these
limited questions, preserve existing work, and have finite failure conditions.
