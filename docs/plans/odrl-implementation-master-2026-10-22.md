# Policy-to-ODRL implementation master program

Status: **REVIEWED, NOT EXECUTED** — 22 October 2026. This program has 22 work
packages. The preparation of the program is complete; every feature task is
still `NOT_STARTED`.

## Result and scope

Build the feature specified in the [proposal](../monograph/chapters/08a-odrl-proposal.tex),
beginning with the 28 July 2023 SFC–HKMA circular 23EC35 and its two annexes.
The first useful result is a manually specified, source-linked ODRL export
that distinguishes the above-threshold designated-account transaction from a
top-up, and missing consent from withdrawn consent. Extend that path to
explanation and annual-review duties, then assess generated interpretations
against the same contracts. Package a local API and CLI with reproducible
examples and explicit limitations.

Use one reviewed `PolicyInterpretation` for norms, references, alternatives
and linked calculations. Export ODRL first. Reuse exact calculations and
selected Catala checks where they fit; independently specified source-based
cases must challenge both representations. Catala agreement is conditional
computational evidence, not proof that the circular was interpreted correctly.

The present instruction authorizes creating and reviewing this program and
its local checker. Feature execution, model experiments and deployment have
not been started. A later implementation instruction activates S00. A live
generation study additionally needs the concrete G14 protocol and its scoped
resource grant; no model, call allowance or cost ceiling is invented here.
The ongoing four-question legal-integration campaign retains its own worker,
register, sources, attempts and grants. This program neither takes over that
worker nor transfers its authority. It creates no new mission-register entry.

The [machine program](../implementation/odrl-master/program.json) is the task
inventory. The [contracts](../implementation/odrl-master/contracts.md) specify
meaning, modules, results, 20 acceptance families and 17 mutation obligations.
The [review](../implementation/odrl-master/review.md) records the skeptical
audit, actual corrections and remaining uncertainties. These three documents
and this plan form one reviewed version; changes require a dependency-impact
review rather than silently rebinding old evidence.

## Baseline and reuse

The inspected main commit is `3c3e462acabfde8c62285f4274f0f8c62b90a790`.
The prospectus commit `e8beb52b13399f18bbbff9aecea9636803729d5f` is already
an ancestor of main. Relevant prospectus and translation code is therefore
available without a merge. Working-file hashes matter because the worktree
also contains unrelated active work. The program binds 28 proposal, research,
source and code files by SHA-256; S00 must diagnose any change before reuse.

| Existing work | Reuse | Required adaptation or limit |
|---|---|---|
| Prospectus successor source graph, construction, references and priorities | Document identity, occurrences, reference closure and retained alternative constructions | Circular/FAQ/incorporated-source roles; no generic date-based legal priority |
| Prospectus clause graph | Source checks and actor/modality patterns | Bond-specific effects do not constitute a regulatory parser; add distinct norm types |
| SPI financial, client, threshold and selected duty models | Inclusive exact-cents arithmetic and conditional component specifications | Reconcile source bindings and all premises; synthetic fixtures do not establish legal completeness |
| LegalRuleModel and observation machinery | Typed calculations, known/unknown/conflicting facts, valid and knowledge times | Name the selected complete/partial behavior; no silent unknown-to-false conversion |
| Translation verification and prospectus symbolic checks | External expectations, execution/replay checks, separately written expressions and mutations | Add ODRL comparison and explicit outcome projection; preserve shared-error limits |
| Existing lifecycle, duty-performance and amendment patterns | Event identity, performance evidence and historical decisions | Bind consent, withdrawal, review cycles and surviving duties to this circular |
| Retained literature and nine pinned software checkouts | Design and bounded qualification evidence | Static audits are not local runtime qualification; unresolved licences prevent copying |

`translation.pipeline` currently accepts RuleIR and Catala, and its build path
assumes executable Java artifacts. Add `src/legalmath/odrl/` and separate
export/validate/evaluate interfaces. Do not implement ODRL by merely extending
the existing target-name list. A generic document parser, ODRL-to-Catala
compiler, LegalRuleML serializer, eFLINT runtime, HTTP service and dataspace
deployment are outside this first program.

The retained environment has Python 3.11.15, pytest 9.0.2, Pydantic 2.12.5 and
z3-solver 4.16.0.0. RDFLib, pySHACL and `build` were not installed in the
inspected project environment. E04 prepares a separate pinned runtime. OVAL
is the first qualification candidate at `b2838782b7ceea95665e287368ddaf02724540bf`;
FORCE at `194894a045886dd8ac5ceda9e0df5b9ddb7a2d52` is a possible bounded
fallback. Neither is assumed to implement the chosen profile. Do not install
OVAL's entire unpinned web/data-science requirements into the live environment.

## Implementation dependencies

`S` means every listed task must succeed. `C` means completion with an honest
terminal disposition is sufficient. `OR` requires one successful alternative.
An empty cell means no dependency of that kind. Success always means accepted
evidence for the current input versions, not merely a zero exit code.

| ID | Deliverable and acceptance focus | S | C / OR / trigger | Maximum attempts |
|---|---|---|---|---:|
| S00 | Adopt exact sources, code, scope, resources and execution state | — | Later implementation instruction | 2 |
| S01 | Whole-bundle source inventory, reference graph and dispositions | S00 | — | 2 |
| N02 | Reviewed norms, calculation links, alternatives and premise inventory | S01 | — | 2 |
| T03 | Separately specified F01–F20 cases and M01–M17 mutation witnesses | S01 | — | 2 |
| E04 | Isolated pinned runtime, licences and measured resource bounds | S00 | — | 2 |
| P05 | Eligibility vocabulary, shapes, supported semantics and result schema | N02 | — | 2 |
| F06 | Exact facts, complete/partial observations and effective consent state | N02, T03, E04, P05 | — | 2 |
| X07 | Deterministic export, source map and nonvacuous structural checks | N02, P05, E04, T03 | — | 2 |
| V08 | Actual pinned OVAL adapter qualification on adverse cases | X07, F06, T03, E04 | — | 2 |
| R08 | One alternate evaluator/adapter, same scope and same cases | X07, F06, T03, E04 | C: V08; trigger: diagnosed supported-fragment incompatibility | 1 |
| C09 | Independent exact references and scoped correspondence checks | F06, T03 | — | 2 |
| C09C | Selected actual Catala comparison, or explicit unavailable disposition | C09, E04 | Optional claim; never an invented PASS | 2 |
| Q10 | Manual eligibility acceptance and its mutation witnesses | X07, F06, T03, C09 | OR: V08, R08 | 2 |
| D11 | Duty semantics, remaining procedures, calendar/correlation contract | N02, T03 | — | 2 |
| D12 | Duty performance, recurrence and historical replay | D11, F06, X07 | — | 2 |
| Q13 | Duty acceptance plus requalification of the combined eligibility path | D12, Q10, T03 | — | 2 |
| G14 | Comparable generation protocol, split, metrics and resource request | Q10, D11, T03 | — | 2 |
| G15 | Opt-in generator with bounded correction and offline failure tests | G14, X07 | — | 2 |
| G16 | Preregistered generation comparison and assessed results | G15, Q13, G14 | Separate bounded-generation authority | 1 study |
| K17 | Installed wheel, local assets, CLI/docs and affected regressions | Q10, Q13, G15 | Independent of G16 | 2 |
| A18 | Manual release assessment and known gaps | K17 | C: C09C | 2 |
| L19 | Whole-program accounting, exact blockers and restart record | — | C: every other task | 2 |

The six proposal milestones map to this graph as follows: source/norm work is
S01/N02/T03; eligibility export is P05/F06/X07; evaluator qualification and
computational checks are V08/R08/C09/C09C/Q10; duties are D11/D12/Q13;
generation is G14/G15/G16; packaging and assessment are K17/A18/L19.
S00 and E04 establish the shared execution baseline. Consent state is moved
into F06 because prior consent and withdrawal must already be correct in the
first eligibility example; D12 extends that state with duty performance.

On a later instruction to implement, S00 is the first task. After S00 succeeds,
S01 and E04 are independent. After S01, N02 and T03 are independent; expectations
must be written from sources without importing the candidate expressions.
After those prerequisites, profile/export, facts, independent calculations
and duty specification can advance along their declared branches. A useful
sequential order is S00 → S01/E04 → N02/T03 → P05 → F06/X07/D11 →
V08/C09/D12 → Q10 → Q13/G14 → G15 → K17/A18, with C09C attempted or
explicitly disposed of before A18. G16 runs only under its bound protocol.
This order is illustrative; recompute the actual ready set after every result.

There is no dispatcher installed by this package. The checker verifies the
proposed graph and bindings; its frontier helper evaluates hypothetical states.
It does not reserve work, enforce runtime budgets, inspect actual worker
receipts or certify task success. A future executor must record these duties
at S00 before dispatch. Until then the actual ready set is empty for feature
execution, and all 22 tasks retain zero used attempts.

## Independence, failures and shared writes

Source work and environment preparation have disjoint outputs. N02/T03 can
advance independently, but their common fixture root must have named subpaths
and serialized edits. F06 and X07 have distinct modules; D11 can be specified
without any evaluator success. D12 can build an adapter-neutral duty monitor
even if V08 fails. It cannot claim qualified combined evaluation until Q13.
C09 and C09C do not depend on an ODRL engine passing. G14/G15 preparation can
continue without an external-call grant, and K17/A18 can complete without G16.

`events.py`, `export.py`, profile assets and `evaluators/` are shared between
eligibility and duty work. Serialize overlapping writes. Q13 reruns eligibility
qualification, correspondence and mutations against the combined versions;
an older V08/Q10 receipt does not qualify modified adapter code. Packaging and
documentation edits likewise have one writer, and no task may modify the
existing legal campaign's register, worker, grants or sealed evidence. A broad
active writer is a conflict to resolve, not a reason to overwrite its files.
No concurrency instruction authorizes subagents.

A V08 mismatch is first classified as source/expectation invalidity, exporter
bug, adapter bug, unsupported fragment, or declared semantic disagreement.
The normal two-attempt bound allows one diagnosed in-contract correction.
R08 is available only for a retained `SUPPORTED_FRAGMENT_INCOMPATIBILITY`
failure. It chooses one minimal separately specified evaluator/adapter or one
qualified FORCE fragment, once. It must evaluate the exported policy rather
than echo a precomputed final decision. Changed expected labels or a narrower
profile under the old version cannot rescue the old acceptance claim.

If V08 succeeds, R08 is explicitly skipped as unnecessary. If V08 fails for
another reason, retain that reason and mark R08 ineligible; source corruption,
authority failure and exhausted resources cannot be bypassed as evaluator
recovery. If both qualified alternatives fail, Q10 and its success dependants
remain blocked. Continue source/export verification, C09/C09C and D11/D12 when
their own prerequisites and scope permit. Retain descriptive exports with
their supported/unsupported scope. Do not convert them into an evaluation release.

A candidate's semantic failure vetoes promotion of that candidate. It does
not stop another already planned study arm, a declared recovery or an
independent work package. Invalid shared evidence, conflicting active writes,
invalid scoped authority, an unknown in-flight external request, or an exhausted
explicit global grant/deadline are continuation vetoes for the affected shared
scope. Record whether the problem invalidated the harness, source, implementation
or only the candidate before choosing the next task.

## Assumptions to test before adoption

| Choice and provenance | Why use it | Failure mode / earliest diagnostic | Status |
|---|---|---|---|
| Retained 2023 body and both official annexes; survey manifests | Fixed historical case with known FAQ counterexamples | Missing or changed annex changes meaning; hash and reference closure at S01 | Historical baseline, not current-law completeness |
| Individual-client initial scope; proposal and SPI fixtures | Bounded qualification problem | Other client types silently coerced into it; explicit scope-rejection case at N02/F06 | Supported-domain choice |
| Exact HKD cents and inclusive OR; inspected SPI model and Annex 1 | Preserve boundary arithmetic | Float conversion, unsigned net assets, invented written-allocation prerequisite or FX assumption; equality/one-cent, signed-asset and equal-share cases at F06/C09 | Source-linked calculation; historical helper needs signed-domain adaptation |
| Unknown logic and conservative referenced-conflict propagation; contracts | Preserve uncertain evidence and reproducible decisions | Over-blocking an irrelevant branch or collapsing missing facts; F02/F10 and cross-request controls | Engineering hypothesis, profile-versioned |
| UTC ordering, Hong Kong calendar, half-open effective intervals | Reproducible consent/replay | Ambiguous same-time amendments or year boundaries; F11/F12/F15 before automatic calendar rules | Proposed convention; assessed due dates first |
| OVAL first; retained technical paper and code audit | Smaller bounded trial than a new general evaluator | Future-promise consent, floats, missing facts or sequence misuse; real engine FAQ6/top-up/consent test at V08 | Candidate, not qualified default |
| Separate Python 3.11 runtime; project packaging | Compatibility without changing active runtime | Dependency conflict or missing wheel assets; E04 import/pin check and K17 clean install | Compatibility baseline; versions selected at E04 |
| Separate source-based case specification; existing verification patterns | Challenge implementation and shared-model errors | Same-author expectations repeat a source error; retain alternative readings, mutation witnesses and provenance at T03 | Engineering independence, not human legal adjudication |
| Two attempts per normal task, one fallback and one study | Bound repair and prevent success-seeking reruns | A real defect needs a different scope; preserve failure, review revision, never reset counters | Resource-policy choice, not empirical optimum |
| Model/settings/repetitions/call and cost ceilings unbound | Avoid transferring unrelated defaults or grants | Unfair or under-budgeted comparison; G14 must bind them before G16 | Explicit future prerequisites |

## Evidence and generation study

The engineering question is whether the supported ODRL projection preserves
the declared eligibility and duty results for this historical source bundle.
The comparator is the separately specified source-based cases, with independent
exact expressions for common arithmetic. Actual Catala output supplements the
declared shared fragment. It does not replace the case specification or source
argument. Finite tests establish only their executed cases; a symbolic proof
must name its encoding, input domain and preserved result projection.

The primary pass criteria are complete source dispositions, exact required
result fields on all mandatory families, honest unsupported/unknown/conflict
behavior, witnesses for every required mutation, and installed replay integrity.
An inverted modality, lost exception, fabricated prerequisite, wrong request
binding, false duty fulfillment or silent unsupported construct vetoes the
affected release claim. Invalid sources or expectations trigger a diagnosed
repair before candidate results are interpreted. Graph conformance is required
for export; coverage percentages, test counts, compilation, speed and model
judgments are explanatory evidence and cannot compensate for semantic loss.

G14 preserves the research question separately from its implementation checklist.
It compares a manually reviewed reference, a simple ontology-guided baseline
and a reference-aware method using the same source/profile and consumer
contract. The manual reference is the comparator, not a stochastic arm claimed
to be superior. The protocol must specify the mechanism, expected failure,
primary semantic outcome, promotion vetoes, continuation vetoes, repair triggers,
explanatory diagnostics and limits on conclusions. It also binds models and
settings, repetitions, independent/paired units, uncertainty analysis, seeds
where available, calls, total tokens/correction allowance, cost and deadline.
Reference preprocessing and failed corrections count in the total resource use.

Freeze source-linked development and prompt-held-out cases before calls.
Published/proposal cases are development examples. Newly authored contrasts on
the same circular can test prompt-held-out behavior, but source familiarity and
single-author specification do not create an untouched generalization benchmark.
Retain omissions, malformed outputs and exhausted corrections; no discarded
failure may silently improve a score. Under-budgeted evidence is inconclusive
for ranking, even if one candidate passes a hard screen. Report hard vetoes,
viable candidates, supported rankings (if any), descriptive differences and
the next evidence needed. One registered study may contain its planned
repetitions and arms; it does not permit another study until a method succeeds.
G16 can succeed as an assessed experiment even if every generated candidate
is rejected. That result must not enable automatic generation by default.

Every nontrivial execution retains commit and dirty-path identities, exact
command/action, environment, sources, profile/evaluator settings, inputs and
outputs with hashes, timestamps/wall time, seed or N/A, CPU-only status, plan,
attempt and result note. Serious comparative results add decision and
inference-status tables, strongest alternative explanation and what would
overturn the conclusion. No new experiment is run by this planning package.

## State, restart and completion

Keep the reviewed program immutable as a baseline; future execution state lives
under `artifacts/odrl-master/`. Each attempt has its task ID/number, input
closure, commands/actions, timestamps, outputs/hashes, failure class and next
ready set. A normal task gets at most two attempts; R08 gets one; G16 gets one
preregistered study. A failed command, interruption or candidate is retained,
not overwritten by a successful retry. Editing task names, phases or result
directories cannot replenish these bounds.

Use `NOT_STARTED` and `RUNNING` before honest terminal dispositions:
`SUCCEEDED`, `FAILED`, `BLOCKED`, `SKIPPED`. `BLOCKED` records exact unmet
prerequisites or authority; it satisfies a completion-only review dependency
but no success dependency. `SKIPPED` is available only for an unnecessary or
ineligible recovery, or the expressly optional Catala claim, with a reason.
An unavailable Catala runtime must be recorded explicitly before A18; no
unrun comparison receives a success result. G16 cannot be skipped to claim
full-program completion. Later resolution reopens a blocked task under its
original ID and cumulative attempts.

Before reuse after a restart, match the saved worker/process identity and
input/output hashes. Adopt an authenticated completed result, diagnose a dead
worker's partial outputs, and do not duplicate an external request whose
completion is unknown. Changed source, interpretation, case, profile, evaluator,
event or configuration invalidates affected results through the dependency
closure. Keep old results as historical evidence. Recompute the frontier and
continue authorized independent work after every checkpoint or failure.

| Reported outcome | Required evidence | Meaning |
|---|---|---|
| Descriptive export available | S01/N02/P05/X07 with supported scope | Reviewable representation; no qualified evaluation claim |
| Manual release accepted | A18 success after the current K17/Q13/Q10 dependency closure and explicit C09C disposition | Installed historical eligibility/duty feature under declared premises; generation may remain pending or rejected |
| Generation study assessed | G16 successful execution and assessment of its registered protocol | Evidence about candidates; no automatic promotion or broad legal generalization |
| Full program complete | Every mandatory task succeeds, either V08 or R08 succeeds, and L19 verifies the retained closure | All proposal work accounted for, including the study; no claim to all policies or regulatory sign-off |
| Blocked or partially complete | Exact failed/unmet prerequisites, attempts and available outputs | Continue remaining authorized ready work; if none remains, report the precise blocker |

L19 runs after all other tasks have terminal dispositions, including blocked
ones. Its accounting can succeed while the feature or full program fails.
For example, a successful manual release with no generation grant is reported
as manual completion and `BLOCKED_ON_GENERATION_AUTHORITY` for the full program.
Do not silently make G16 optional or require both alternative evaluators to
succeed. An optional engine/Catala failure remains visible even when the
applicable release criterion succeeds.

## Preparation and verification record

The preparation dependency map was P1 baseline/scope → P2 task/contracts →
P3 checker and P4 skeptical review → P5 final package. P3 and the non-checker
parts of P4 were independent after P2; shared program edits were serialized.
The pre-execution audit passed for this bounded planning/checker work: the
actual baseline was the proposal and inspected code, execution authority was
kept separate, and no plan test was treated as feature or legal evidence.

| Preparation | Result |
|---|---|
| P1 | Complete: proposal, retained survey, source/code baseline and active-campaign separation inspected |
| P2 | Complete: 22 tasks, 11 requirements, precise contracts, F01–F20 and M01–M17 |
| P3 | Complete: read-only checker and adverse planning tests; no dispatcher |
| P4 | Complete: source/code, semantic, dependency, recovery, resources and completion review; corrections retained in review.md |
| P5 | Complete: final verification record and restart memo retained with this package |

The required legal-mission `check`, `status` and `admit` commands were run
with `.venv/bin/python scripts/legal_mission_control.py`. They reported
PASS, WORK_REMAINS and ADMITTED_MASTER_WORK for the existing four-question
frontier. That admission is not an ODRL grant, and its running worker was
left with its original scope. No new mission dispatch or register edit was made.

Recheck this planning package from the repository root with:

```text
.venv/bin/python scripts/check_odrl_master_program.py
.venv/bin/python -m pytest tests/tooling/test_odrl_master_program.py -q
```

The [verification record](../implementation/odrl-master/verification.json)
contains the actual results and final file hashes. The
[restart memo](../implementation/odrl-master/reset-memo.md) distinguishes the
completed planning task from future implementation. The planning checker
passing establishes graph/binding invariants only. Author review is not an
independent human or model assessment, and no ODRL runtime, Catala comparison,
generation experiment or feature implementation has been executed here.
