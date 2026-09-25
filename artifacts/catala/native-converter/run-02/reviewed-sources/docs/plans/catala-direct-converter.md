# Direct source-to-Catala converter

Status: implementation authorized; the execution audit below supersedes the
original design-only verdict. Prepared on 25 September 2026 against Catala
branch `5290bc53`, which includes committed main `9160ce72`. The execution
revision uses at most 24 calls from the existing shared allowance and does not
raise its ceiling.

## Objective and intended route

The user proposes a direct converter to Catala and asks how to build and test it.
Interpret “direct” as retained legislative/regulatory text plus a declared
question and factual interface, producing native Catala without compiling
through RuleIR. This is a source-interpretation and program-generation task;
the deterministic Catala compiler starts after those judgments are made.

The route is:

    Retained source + question + factual interface
      -> proposed interpretation, assumptions and unresolved issues
      -> native literate Catala candidate with exact source anchors
      -> pinned Catala typechecking/compilation
      -> checked execution and independently assessed behavior

The interpretation record describes actors, definitions, scope, timing,
exceptions, units, rounding, cross-references and uncertainties. It must not
become another restricted executable language that removes Catala's records,
collections, decimals or parameterized scopes. Native Catala is the executable
candidate. Where the source supports rival readings, preserve separate programs
and a distinguishing case; do not force a single answer to make compilation pass.

Two tasks must be evaluated separately: (A) explicit semantic specification to
Catala, isolating code generation; (B) legal source to Catala, measuring the
complete proposed converter. Passing A does not establish B.

## Evidence behind the design

Inspected local implementation:

- `src/legalmath/interpretation/search/models.py` restricts facts/results to four
  scalar types and a small prefix-expression grammar.
- `src/legalmath/interpretation/search/formal.py` turns that grammar into RuleIR.
- `src/legalmath/interpretation/assurance/issue_search.py::validate_issue`
  restricts the current public disputed-antecedent workflow to Boolean inputs.
- `src/legalmath/catala/backend.py` compiles a generated per-node calculation
  program; it is not a native source-to-Catala converter.
- `src/legalmath/analysis/compare.py` rejects defaults, scale and date expressions
  in its solver fragment. Its success cannot verify richer native programs.

Inspected pinned Catala commit `0f895e048d19dbe72f24cdd6d5f3398bfe1335fa`:
`doc/syntax/syntax_en.catala_en`, `stdlib/money_en.catala_en`,
`stdlib/date_en.catala_en`, `tests/scope/good/scope_call.catala_en`,
`tests/exception/good/exceptions_squared.catala_en`,
`runtimes/java/catala/runtime/{CatalaDecimal,CatalaStruct,CatalaMoney}.java`,
and `compiler/scalc/to_java.ml`. These establish the available constructs and
identify integration risks; no new academic theorem is invoked by this plan.

In particular, the Java emitter explicitly reports that tracing is not yet
supported. The completed adapter's RuleIR traversal supplies its trace. A direct
converter cannot inherit that trace or reconstruct it using the RuleIR oracle.
CatalaDecimal exposes an exact rational representation; its floating-point
constructors are not an acceptable exact input boundary. Money conversion can
round, so intermediate precision and the location of rounding must be explicit.

## Implementation

1. **Native task and candidate contracts.** Add versioned contracts under a new
   `legalmath.catala.native` package. Reuse source packets, source hashes,
   checkpoint receipts, allowance accounting and uncertainty records. Do not
   send native candidates through the restricted `Formalization` or Boolean
   `IssueSpec` validators. Inputs include source edition/dependencies, exact
   question/output meaning, typed records/lists/enums, units and currency,
   admissibility dates, collection completeness, and interpretation assumptions.
   Each candidate carries `.catala_en`, declared entry scope, source map,
   interpretation record, unresolved issues and toolchain identity.

2. **Build native vertical examples before model generation.** Write reviewed
   synthetic specifications and small native Catala examples for portfolio
   aggregation, tiered monetary calculations with explicit rounding, and
   month/year deadlines. Execute each through the interpreter and generated
   Java. Check structured input/output, enum cases, negative values, exact
   rationals, empty lists, date endpoints and required standard-library modules.
   These are runtime/bridge checks, not converter ability evidence. Extend the
   toolchain lock to cover every additional standard-library source and compiled
   dependency actually used; the present `--no-stdlib` build is insufficient
   for standard-library calls.

3. **Native input boundary and result contract.** Build exact typed codecs and a
   generated Java caller for the declared scope. Preserve integers, rationals,
   currency units and dates without binary-float conversion. Distinguish missing
   evidence, contradictory evidence, absent optional values and an empty known
   collection. An incomplete collection cannot silently become a complete empty
   list. Initially abstain on required unknown/conflicting inputs unless that
   task has an explicitly implemented and tested partial-information semantics.
   Declare the contract difference from RuleIR's knownness propagation, rather
   than claiming full equivalence on those cases. Do not accept precomputed
   aggregates or legal answers as primitive inputs to evade a capability test.

4. **Native generation and bounded repair.** Generate meaningful scopes,
   records, labels and source-adjacent code. A separate source critic checks
   coverage, conditions, exception attachment, units, timing and unsupported
   assumptions. Give syntax/type failures to a bounded mechanical repair stage.
   A repair that changes the meaning record, factual interface, precedence or
   rounding is a semantic revision and must undergo renewed source review.
   Retain all attempts, rejected candidates and costs. Do not provide hidden
   reference code or heldout expected outputs as repair feedback.

5. **Native verifier and execution evidence.** Implement a separate verifier;
   `verify_candidate` currently assumes a RuleIR bundle and Python oracle.
   Compare interpreter and Java results for backend consistency, then compare
   both against independent expected behavior. Map executed scope/decision
   values to original Catala source locations and retained source quotations.
   Static citations are source navigation, not proof a branch ran. Interpreter
   trace and Java execution evidence must be labelled by the process producing
   them. Probe the pinned Java trace limitation first, then implement explicit
   scope-output instrumentation or a reviewed compiler instrumentation extension
   for the supported native profile. Check instrumented/uninstrumented result
   equality and inject faults into the executed calculation and evidence.
   Do not fabricate RuleIR node traces or claim interpreter logs describe a
   different Java execution. Native Java release verification depends on this
   milestone; converter evaluation can proceed in the interpreter meanwhile.

6. **Workflow and host integration.** Expose a distinct command, tentatively
   `legalmath catala-convert`, plus reusable API entry points. Separate generation,
   checking, execution and resume operations. Add a native build/result profile
   with exact source, entry scope, interface, toolchain, interpretation and output
   meaning commitments. Reuse transactional snapshot/release controls only where
   their contracts apply; do not pass a native program as a fictitious RuleIR
   bundle. Exercise corrupt packages, stale reviews, concurrent host state,
   missing data, release replacement and replay using native-built binaries.
   Retain source-unit and field/item evidence IDs for structured collections.
   Both a missing compiler entry point and an unsupported feature fail explicitly.

Generated candidates may contain only program files and imports in the declared,
pinned Catala profile. Compiler commands, Java bridges, filesystem paths and
plugin settings are controlled by the builder, not supplied by the model. Bound
compile/runtime resources and retain failures. This is directly required by
accepting model-generated programs and imports, not a new human approval step.

## Initial capability coverage

Use a development matrix of six families; the examples below are synthetic
engineering specifications until backed by separately retained legal sources.

| Family | Target | Cases that distinguish ability from a facade |
| --- | --- | --- |
| Portfolio aggregation | Filter a list of structured holdings and sum eligible exposure | Empty/singleton/large lists, excluded entries, incomplete inventory, item IDs, source-defined duplicate policy; permutation only when order is irrelevant |
| Financial amounts | Variable rates, bands, exact intermediate arithmetic, final rounding | Threshold neighbours, half-unit ties, negative inputs where admissible, per-item versus end-of-sum rounding |
| Calendar deadlines | Months/years and explicit calendar conventions | Leap day, month end, before/at/after deadline, conflicting date evidence; no invented business-day calendar |
| Categories and records | Typed classifications and category-specific formulas | Every enum case, invalid/missing categories, mixed records, category reclassification |
| Reusable scopes | Invoke a rule for multiple entities with separate inputs | Distinct inputs in repeated calls, independence, nested use, no snapshot reuse leak |
| Exception hierarchy | Base rule, exception and exception to exception | Overlapping/equal consequences, stated precedence, missing guards and unresolved hierarchy; no automatic adoption of RuleIR's multiplicity policy |

Begin with one complete vertical case from each of the first three families.
Each must accept primitive structured input, compute the substantive result in
Catala, retain source/meaning commitments, and detect a wrong implementation.
Then broaden to the six-family matrix and real retained-source tasks. This order
answers cheap representation/host questions before spending on model evaluation.

## How ability will be measured

Maintain three separate evidence records: program/host correctness, encoded
semantic behavior, and fidelity to the source. Nothing in one establishes the
others automatically.

| Question | Baseline and test | Interpretation |
| --- | --- | --- |
| Does the converter generate runnable native programs? | Parse/typecheck/build; interpreter versus Java; exact codecs; first attempt and bounded-repair outcomes | Engineering screen only; compilation is not semantic success |
| Does it implement the specified computation? | Hand-derived cases plus separately implemented small exact reference functions, audited independently of candidate code; finite exhaustive domains where practical | Behavioral evidence conditional on the specification/reference |
| Does it preserve the legal source? | Exact quotations, material-clause coverage, cross-reference disposition, independently reviewed scope/exceptions/timing/units and acceptable rival readings | Source review, with reviewer identity and unresolved judgments retained |
| Does it expose capabilities unavailable in current RuleIR? | Same primitive task inputs; require real lists/records/rates/durations; inspect dataflow/imports for external precomputation | Capability extension; a RuleIR unsupported result is not an accuracy failure |
| Does it improve conversion on shared tasks? | Current source-to-RuleIR-to-Java, minimal direct Catala, reviewed direct Catala under declared comparable budgets | Paired comparison; no ranking from raw pass counts alone |
| Does it detect meaningful mistakes? | Wrong comparison, exception priority, omitted qualifier, currency scaling, rounding location, date convention, list filter; each non-equivalent mutant needs an independent distinguishing witness | Test sensitivity; exclude documented equivalent mutants from denominator |
| Does it generalize? | Whole source/task-family separation; sealed hidden cases and unseen amendments; no feedback from heldout answers to repairs | Limited to the chosen sampling population; public-source memorization remains possible |
| Does it help reviewers? | Counterbalanced review of the same clauses and seeded defects; correctness, omissions, time and assistance recorded | Human study needed for reviewer-benefit claims; self/model review is provisional |

The first declared study should contain development and sealed tasks across all
six families. A planning candidate is four independently authored specifications
per family (two development, two heldout), with three independent model runs per
arm. This is a feasibility design, not an adequate default sample size for a
population claim. Freeze task hashes, source ancestry, split, model/version,
prompts, repair limits, retrieval, exact runtime limits and token/cost allowance
in `study.json` after offline calibration and before live dispatch. Distinct
specifications from one source family remain correlated. Merely changing names
or numbers does not create an independent heldout family.

For the shared fragment compare all three arms. For expanded capabilities,
compare minimal and reviewed native conversion against independent references;
record current RuleIR as unsupported where appropriate. Include hand-authored
native Catala as a target-language/host control, with human effort reported; it
is not a zero-cost automatic method. Count all failed attempts and repairs.
Use the same primitive interface and source context within paired conditions.
Also report useful correctness per cost where arms consume different resources.

Predeclare task-level strict success: all required hidden behaviors and
source-fidelity checks pass, and required uncertainty is preserved. Compiler
failure, wrong meaning, correct abstention, unnecessary abstention and unresolved
source adjudication are distinct outcomes. On ambiguous sources, specify the
acceptable reading set and mandatory uncertainty before generation; never
pretend there is a single authoritative numerical answer merely to score it.
Report automation coverage together with correctness conditional on acceptance,
so a converter cannot appear successful by refusing every task.

Treat task/source family as the inferential unit. Repeated model samples and
many input rows do not multiply independent legal tasks. Report paired
uncertainty intervals at that level under predeclared assumptions. Claim an
advantage only when the interval supports the declared criterion; otherwise
report descriptive differences and viable candidates. A deployment-readiness
claim requires its own target-specific evidence.

## Research intent and evidence contract

| Field | Contract |
| --- | --- |
| Main question | Can direct native generation faithfully automate richer source-grounded computations, and when does its additional expressiveness help? |
| Mechanism | Native records, collections, exact decimals, durations, scopes and exceptions remove RuleIR's representation bottleneck |
| Expected failure | Runnable code misinterprets a qualifier, relocates rounding, treats missing collection items as absent, or copies a wrong assumption consistently into code and tests |
| Primary criterion | Task-level source and hidden-behavior correctness under explicit assumptions, plus demonstrated native computation from primitive inputs |
| Promotion veto | Wrong source meaning, silent unsupported clauses, wrong precision/time/exception policy, dropped uncertainty, fabricated execution evidence, or host integrity failure |
| Continuation veto | Leaked heldout answers, invalid reference/interface, corrupted provenance, irreparable inability to execute the required feature, or exhausted authorized resource grant |
| Repair trigger | Syntax/type errors, candidate semantic failures, unsupported mappings, missing clauses, native Java integration deficiencies |
| Explanatory only | Compile success, test counts, source length, model agreement, runtime and token use without the declared quality/cost comparison |
| Non-conclusions | Formal legal correctness, general compiler certification, universal language superiority, equivalence from finite probes, or production authorization |
| Artifacts | `docs/implementation/catala/native-converter/` for contracts/study/results and `artifacts/catala/native-converter/<run>/` for source packets, attempts, builds, results and manifests |

A wrong candidate triggers the next planned repair. It does not invalidate direct
conversion as a direction. Missing human evidence blocks a human-benefit claim,
not offline implementation. Invalid reference data or leaked hidden answers
block the affected comparison until repaired. Missing native Java trace blocks
native Java release acceptance, not interpreter-based converter investigation.

## Default audit and pre-mortem

| Choice | Provenance / justification / status | Risk and early diagnostic |
| --- | --- | --- |
| Direct source and native code | User direction; central hypothesis | Hidden RuleIR pass or opaque precomputed aggregate; inspect candidate dataflow on a collection case |
| Retained source packets and accounting | Existing project infrastructure; reuse candidate | Restricted scalar/Boolean validators leak into new path; reject that architecture in contract tests |
| Catala 1.2.1 | Existing pinned, locally working toolchain; starting baseline | Stdlib/Java feature mismatch; compile real feature examples before model runs |
| Exact rational/decimal boundary | Inspected Catala runtime and current exactness requirement; reviewed principle | Double conversion or implicit cent rounding; independent tie/intermediate tests |
| Conservative missing-data policy | Native required-input boundary; initial explicit hypothesis | Excessive abstention or false completeness; partial-information reference cases and coverage reporting |
| Three pilot families | Concrete gaps in current RuleIR; convenience development selection | Overfitting a synthetic toy; whole-source heldout and amendment tasks later |
| Proposed study counts and repetitions | Feasibility planning only, not power analysis | Correlated tasks and wide intervals; report uncertainty, expand by declared criterion before ranking |
| Separate source critic | Existing source-assurance practice; hypothesis | Correlated model errors; independent references and human adjudication, not votes as truth |
| Bounded repairs | Existing operational discipline; target-specific limit to calibrate | Semantic drift and cost inflation; retain attempts and compare meaning/interface hashes |

A misleading pass could arise from grading the model's own tests, exposing the
hidden gold program, preprocessing away the hard computation, confusing compiler
agreement with legal agreement, skipping rejected tasks in the denominator, or
reporting a static source map as runtime evidence. The test contracts above
explicitly address these before a comparative experiment.

## Skeptical review verdict and next step

PASS for offline implementation of the three native vertical examples and new
contracts. The plan checks baselines, proxies, hidden defaults, environment
compatibility, stop/repair rules and whether each artifact answers its question.
It corrects two easy architectural mistakes: using the existing Boolean reading
schema for richer rules and reusing RuleIR verification/traces for native code.

Live comparative execution must first have the concrete frozen study manifest,
reviewed references and split, calibrated bounds, and an existing authorized
allowance. Those are execution inputs still to be prepared, not a reason to ask
for permission to start reversible offline implementation. No live conversion
accuracy, reviewer improvement, or completed native converter is claimed by
this design note.

## Execution audit, 25 September 2026

The user's subsequent instruction is to review thoroughly and execute. Root
Codex performed this review; it is not an independent or human review. The
original plan is sound as a research direction but was not executable as
written. The following material findings revise its first execution:

1. **The interpreter's JSON decimal output loses precision.** Pinned
   `compiler/shared_ast/encoding.ml::rat_encoding` tries a float before a rational
   string; money has the same problem. Parsing the float as Decimal cannot
   recover the lost value. Supply exact input literals and check exact expected
   values inside a generated Catala verification scope returning a Boolean.
   Java exports numerator/denominator strings directly. These are separate
   checks against the same independently specified expected value, not a
   tolerance-based float comparison.
2. **Unbounded native language versus bounded deployment profile.** Version 1
   supports primitive integers/Booleans/exact rationals/money/dates, acyclic
   records, lists and nullary enums. Programs may use native scopes and labelled
   exceptions. External imports and includes are rejected initially; all six
   pilot families can use pinned builtins, including explicit date rounding.
   A missing library is an explicit unsupported result, not silently rewritten
   arithmetic. Imported standard-library modules require a later locked profile.
3. **Evidence must come from the actual process.** Instrument generated Java
   at scope-output construction, retain executed scope/field values and source
   anchors, and compare instrumented and uninstrumented builds. The supported
   evidence is scope/output values, not a claim to complete branch tracing.
   Tampered results and evidence must fail verification. Static citations alone
   do not count as execution evidence.
4. **Source review and behavior are different decisions.** Store exact quotes
   and clause coverage; a separate fresh model critic may challenge or leave a
   candidate unresolved. A critic's acceptance cannot replace independent
   behavior checks or human legal adjudication. Preserve rival readings and
   unresolved issues, blocking ordinary accepted execution until resolved.
5. **The proposed large study has no sampling frame or reviewed references.**
   It would be misleading to label 24 newly invented examples a generalization
   study. Execute six development capability tasks first, one per family,
   plus a retained-source task if its factual abstraction and oracle can be
   checked. Freeze these before live dispatch. Do not report superiority,
   heldout generalization or reviewer benefit from this development pilot.
   Leave the larger paired study explicitly unexecuted pending its evidence
   prerequisites; do not manufacture independent tasks through renaming.
6. **Resumption and host acceptance need concrete failure tests.** Hash-bind
   source, question, interface, candidate, review, compiler, builder and snapshot.
   A changed commitment cannot reuse a checkpoint or approval. Native release
   controls must test stale approval, replacement, changed host revision,
   incomplete collections, replay and corrupted binaries without pretending
   native programs satisfy the RuleIR schemas.

Execution sequence: contracts and exact codecs; three compiled vertical probes;
all six controls and independent reference cases; native generation/critic and
bounded repair; CLI/resume and native host controls; frozen live development
pilot; regression checks and result/reset notes. Fix candidate failures within
the declared limits rather than treating them as rejection of the direction.

Environment: branch `feature/catala-adapter` at `5290bc53`, Python
`/home/chakwong/python/legalmath/.venv/bin/python`, `PYTHONPATH=src`, pinned Catala
1.2.1 and the existing JDK 17. GPU is not used and no ML runtime is imported.
Commands will be recorded verbatim in the result manifest. Pilot artifacts go
under `artifacts/catala/native-converter/run-01/`. Existing remediation evidence
will not be rewritten.

Resource defaults for this development pilot: compiler 120 seconds per command;
execution 15 seconds per case; source 64 KB; JSON request 1 MB; list 10,000 items;
acyclic type depth 12. These are engineering limits, not measured optimal values.
Early diagnostics are boundary rejection tests and a large-list control. Live
calls use the existing shared 500-call grant (153 consumed at inspection), with
an additional cap of 24 calls for this pilot: six generators and six critics,
plus at most one revision and renewed criticism per task. The existing shared
ledger, not a forked allowance, is authoritative. Each call has a 180-second
limit and retains usage. No allowance ceiling is raised. This bounded live
exercise follows the user's execution instruction; it is not the proposed
large comparative study. Provider failures count and stop the affected task;
failed semantics trigger the one bounded repair. Hidden expected answers never
enter model prompts, criticism or repair feedback.

Audit verdict: PASS after these revisions. The comparator is an independently
specified exact reference, while handwritten native programs control the
runtime. Compiler success and model agreement remain explanatory checks.
Wrong semantics blocks acceptance; invalid references, corrupt commitments,
leaked answers or exhausted allowance stop the affected run. No current
unexamined default is treated as evidence of accuracy or default-readiness.

Offline calibration completed: all six handwritten controls pass 39 independent
exact cases. The initial 26-test integration run exposed duplicate trace events
from generated copy constructors; instrument only calculation assignments and
exclude output-copy constructors. A repeat passed all 26 tests. These are
engineering evidence, not converter success. The retained-source development
task is SFC 23EC35 Annex 1 paragraph 3.3 only: subtract supplied liabilities from
supplied assets, then exclude supplied primary residence. Bind the original PDF,
text and quote offsets/hashes. Asset classification, attribution, FX, full SPI
eligibility and real effective-date interpretation are outside its question.
Its four exact cases bring the frozen pilot to seven tasks and 43 cases. The
same 24-call ceiling covers all seven tasks; baseline generation plus criticism
requires 14 calls, with remaining calls available for bounded repairs in declared
order. This remains a convenience development sample.

### Acceptance-harness repair after run-01

The live pilot discovered an implementation failure, not a failed language
hypothesis: source critics returned SUPPORTED with positive explanatory findings,
but the converter required an empty findings list and wasted revisions. Stop the
affected acceptance loop, retain all responses and original source bytes, and
honor the explicit critic verdict; findings are retained observations. A targeted
regression now uses a supported review with positive findings. Run-01 consumed
19 calls (shared allowance 172/500), including eight unnecessary revision/review
calls. They are not refunded or hidden. A corrected successor may reuse the
identical saved requests/responses with explicit reuse provenance; it must not
call them fresh samples. New requests still use the original absolute ceiling
177, leaving at most five more calls. Preserve all seven original task/reference
hashes and continue runtime checking. No source/behavior accuracy is reported
from the invalid acceptance loop. This is the plan's harness-repair continuation,
not a new study or a larger grant.
