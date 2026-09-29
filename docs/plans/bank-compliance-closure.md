# Executable bank-compliance gap closure

## Question and completion boundary

Can a single evidence-bound transaction investigation derive the declared
requirements, evaluate supported rules, preserve unresolved law and private
policy, execute the same formal rules through RuleIR and Catala, and invalidate
its conclusions when facts, sources, policy, time or transaction events change?

The starting comparator is `src/legalmath/compliance.py`: a caller-supplied
requirement/finding compositor with conditional CMIC and ownership functions.
It is not a legal oracle. The target is an integrated, reproducible investigation
with independently checked formal consequences. Universal natural-language
interpretation, exhaustive world-law discovery and unavailable JPMorgan policy
are not engineering completion criteria. Their absence must remain explicit in
every affected decision. No human labels or human approval are quality evidence.

## Research intent and evidence contract

| Role | Criterion |
| --- | --- |
| Main question | Does the integrated path prevent unsupported transaction clearance while computing the supported formal consequences? |
| Mechanism | Content-addressed inputs, a fixed versioned obligation inventory, sourced conditional rule specifications, shared lowering, independent checks and event replay. |
| Expected failure | A green finding hides omitted obligations, a quote/hash is mistaken for legal entailment, an old decision survives an amendment, or both backends share the same wrong rule. |
| Promotion criterion | All required focused regressions, independently specified formal obligations, native backend executions and mutation challenges pass; the integrated real-source example retains every missing-input/meaning/coverage qualification. |
| Promotion veto | Counterexample, omitted mandatory inventory entry, unsupported certainty, corrupted evidence, native execution disagreement, absent required proof or fabricated bank-policy fact. |
| Repair trigger | Any failed engineering invariant or missing evidence adapter; repair and rerun affected phase and successors. |
| Continuation veto | Cannot preserve unrelated work, cannot inspect a necessary source, or cannot run a necessary checker after bounded repair. Unavailable private inputs block their conclusion, not independent engineering phases. |
| Explanatory only | Test counts, source counts, execution time, cross-backend agreement and matched source text. |
| Must not conclude | Complete legal clearance, currentness of all law, natural-language entailment, future-law prediction, actual account compliance, or superiority of either target language. |
| Artifacts | `docs/implementation/bank-compliance-closure/`, `docs/compliance/`, `src/legalmath/transaction/`, focused tests and a reproducible program. |

## Defaults and assumptions

| Choice / provenance | Reason and status | Failure mode / earliest diagnostic |
| --- | --- | --- |
| Existing seven-layer design | User-approved architecture; retained baseline | One rule per category falsely proves completeness; omit a rule within a represented layer. |
| Explicit finite jurisdiction/activity catalog | Bounded engineering scope, not universal-law authority | Missing law outside catalog; always report global coverage unestablished and list catalog exclusions. |
| Three-valued facts plus explicit conflicts | Existing qualification semantics, reviewed design | Missing facts become false; challenge deletion, disagreement and stale support. |
| Exact integers/rationals | Existing project convention | Threshold/ownership rounding; exact boundary cases and independent equations. |
| Source timestamps and amendment dependencies | Declared metadata, never automatic legal meaning | Retrieval date substituted for legal effective date; distinguish known/effective/freshness times. |
| Public sources and synthetic fact scenarios | Available inputs; scenarios are engineering fixtures | Invented client/policy presented as real; prohibit a real-account-clearance label and retain unavailable policy. |
| Existing pinned Java/Catala/Lean tools | Reusable environment, must pass preflight | Stale build receipts; bind actual compiler, method and source hashes and execute both targets. |
| Rule sources are interpretation proposals | No independent universal English semantics theorem | Source hash promoted to proof; separate provenance, formal proof and legal meaning in output. |

## Skeptical plan audit before execution

The naive plan to add seven successful example findings is rejected: it would
repeat the original coverage defect. A second rejected approach would label
quoted text as an entailment certificate or use agreement between two generated
programs as legal truth. A third would apply all US account obligations to a
foreign branch without checking each provision's territorial predicates.

The revised design fixes the obligation inventory independently of the request,
retrieves and verifies actual evidence content, computes findings from rules,
and preserves source-meaning and coverage uncertainty separately from formal
execution. Internal policy stays unavailable until genuine documents exist.
RuleIR/Catala use identical inputs and are each checked against independently
written semantics. Old prospectus results are reused only within their scope.

Pre-mortem: the program could pass while merely certifying invented premises.
The first integrated scenario therefore uses preserved public documents with
missing real account and internal-policy data and must remain qualified. Native
compiler failures are implementation/environment evidence, not legal findings.
Unknown solver results and timeouts fail the formal phase. Finite generated
tests establish their declared domain only. No stochastic ranking is planned.
The revised plan passes this scoped audit; unavailable facts do not authorize
substituting convenient true values.

## Phases, repair and refresh

1. **Evidence and applicability.** Add validated content-addressed source/fact
   retrieval, source dependencies and temporal checks, typed transaction roles,
   a versioned obligation catalog and a deterministic public evaluation command.
   Missing or altered evidence must prevent an affirmative result.
2. **Supported rule packs and data.** Encode separately sourced conditional
   entity/CMIC, bank-control, private-account, product and operational rules;
   add program-specific sanctions-list ingestion and identity qualifications.
   Preserve missing internal policy and unsupported jurisdictions/actions.
3. **Independent execution.** Reuse the shared model, produce kernel-checked
   formal-to-model certificates, discharge independently written SMT obligations,
   execute real RuleIR and Catala builds on identical cases, and compare both to
   the independent evaluator. Include unknown/boundary and deliberate mutants.
4. **Events and end-to-end challenges.** Bind decisions to the full input and
   method snapshots; implement typed duties and deterministic lifecycle replay.
   Test source/fact/policy/route changes, chronology, duplicate events, corporate
   actions and stale decisions. Run a public-source investigation across all
   seven categories and preserve its unresolved requirements.
5. **Review and delivery.** Run focused existing regressions, inspect all new
   claims against the implementation, repair findings, update documentation and
   reset memo, and record precise remaining data/research gaps.

Every phase writes an attempt receipt, actual commands, input/output hashes,
result, repair record when necessary and refreshed next-phase instructions.
Successful prior artifacts may be reused only if their full dependency identity
still matches. Failed attempts remain preserved. Refreshing a plan never turns
missing legal evidence into success. A code repair changes method identity and
requires rechecking dependent phases.

## Commands and environment

Use `.venv/bin/python` in `/home/chakwong/python/legalmath`, CPU only with
`CUDA_VISIBLE_DEVICES=-1`. No GPU libraries or external model calls are needed.
Use the installed pinned toolchain recorded by the existing prospectus program.

Planned repeatable entry point:

```sh
.venv/bin/python scripts/run_bank_compliance_program.py
.venv/bin/python -m legalmath.transaction --help
.venv/bin/python -m pytest -q tests/compliance tests/prospectus tests/translation/test_qualification_windows.py
git diff --check
```

Public-source downloads use the already authorized `curl` command and explicit
official URLs. No permission changes are needed for in-workspace implementation,
tests or retained local evidence. Actual bank policies and account facts are
external inputs, not assumptions to fill in. No trading or reporting action is
part of this program.
