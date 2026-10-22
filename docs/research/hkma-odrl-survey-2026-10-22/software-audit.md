# Software inspection record

This supports the [survey](README.md). All findings are **static inspection**, not locally executed test results. No package installation, model calls or enforcement actions were performed. Repositories were shallow-cloned from their public origins into `.localresources/hkma-odrl-survey-2026-10-22/code/`. Existing committed bytecode or result files in a clone are upstream files, not evidence of local execution.

The [manifest](sources.json) records full commits, origins, root licence files and hashes of inspected code. Commit dates below refer to the checked-out commit; a GitHub repository's latest push timestamp can differ. The upstream default branch may change after this snapshot.

| Checkout | Full commit | Commit date | Licence inspected |
|---|---|---|---|
| RUC-MAS/AgentODRL | `22bdc718b02ebd7c3a0a00b70029803c53001562` | 2026-08-31 | Apache-2.0 |
| keman-ruc/wanle-Agentodrl | `d55ed231ba7de6c788b24ba82a4a681d0872e093` | 2026-02-05 | Apache-2.0 |
| Daham-Mustaf/LLM4ODRL | `ee9e30b4a3ce4c2c60c7c7e7764eba4fb6764759` | 2025-06-13 | No repository-level licence found |
| odrl-force/ODRL-Evaluator | `194894a045886dd8ac5ceda9e0df5b9ddb7a2d52` | 2026-02-26 | MIT |
| odrl-force/ODRL-Test-Suite | `7958238e72511059478e43ec9e57b053504cfd2c` | 2025-10-15 | MIT |
| ODRE-Framework/odre-python | `1a2cb06004f085a1f21d3350a7534ac7e9229f0f` | 2026-05-09 | Apache-2.0 |
| DIPS-Tools/ODRL-Engine (OVAL) | `b2838782b7ceea95665e287368ddaf02724540bf` | 2026-10-21 | MIT |
| woutslabbinck/ODRL-shape | `75a222d9e08c91981a9917fd9b90f8092898afa1` | 2024-11-20 | No repository-level licence found |
| eclipse-edc/Connector | `118c7801f626a97eef054194984012aff1fb9cfa` | 2026-10-22 | Apache-2.0 |

## AgentODRL

The original README directs readers to `keman-ruc/wanle-Agentodrl` as the maintained repository. Both were retained; “maintained” is the README's designation, not an inference that its commit is newer. Detailed inspection used the latter checkout.

Inspected `ODRL_V3/E3_orchestrator.py`, selected generation/correction paths in `ODRL_V3/main.py`, and `ODRL_V3/ODRL_Check.py`. The orchestrator explicitly selects direct generation, split-then-generate, or rewrite/split/generate. The reference-rewriting prompt aims to inline dependencies. This is useful method structure, but inlining without retained source maps can sever the evidence for exceptions.

`ODRL_Check.py:46` parses generated JSON-LD using RDFLib and runs pySHACL with RDFS inference. It counts top-level shape blocks and distinct violated result paths. This is a particular structural score, not a count of correctly interpreted clauses. Parsing/validation errors return separate sentinel values. `main.py:532` performs at most the configured number of validation-reflection attempts. It saves the current candidate after the loop even if no explicit validation success was reached. A local adapter must preserve conformance/failure status and validate the final saved candidate rather than equate file production with success.

The scripts contain experimental file layouts, model configuration and substantial concurrency settings. These were not adopted as defaults or executed. Reuse should extract bounded method components and pair them with source coverage and independently reviewed outcomes. The Apache licence permits code reuse subject to its terms; model services and checkpoints would have their own conditions.

## LLM4ODRL and SHACL

Inspected README, `shacl_odrl_validator.py`, and `ODRL_policy_validation_shapes/ODRL_Rule_Shapes.ttl`. The validator parses Turtle, invokes pySHACL and counts validation results/violations. The shape requires properties including creator, description, issued and title; it also imposes a profile property on its selected policy class. These are actual constraints in the code, not merely prose suggestions. They must be classified as W3C requirements, HKMA-profile requirements or project metadata requirements before reuse.

No root licence or conventional licence/copying/notice file was found in the inspected LLM4ODRL checkout. The same bounded licence check found none for `ODRL-shape`. This survey does not conclude that no permission could exist elsewhere; it concludes that public availability alone does not establish the reuse grant. Avoid copying these projects as if an open-source licence had been verified.

For pySHACL, repository metadata and README were retained. Its documentation declares Apache-2.0 and describes RDF-against-SHACL validation. The engine's internal implementation was not audited. A pilot can use it for the specific question “does this graph conform to these shapes?” The shapes and their target coverage still require review: a graph that never targets the intended shapes can produce a misleadingly clean result.

## OVAL

Inspected README, `documentation/evaluator_feature_support.md`, and the relevant paths in `ODRL_Evaluator.py`: constraint evaluation, state initialisation/matching, monitoring, access settings and duty collection. Test directories and normalisation/comparison components were inventoried, not run.

The most consequential findings are:

- `evaluate_ODRL_access_request_on_dataframe`, around line 1001, defaults to `semantics_for_duties=1`. Its docstring says requests may be accepted before duties are satisfied, on a promise that they will be. `-1` requests explicit prior fulfilment. The prior-consent part of the HKMA pilot requires deliberate settings and scenario verification; the default cannot be inherited silently.
- `semantics_by_default` can permit, prohibit or leave unmatched requests unspecified. This is an application-semantic choice. Failure to qualify for streamlined procedures must not be presented as a prohibition on every ordinary-route transaction.
- The current constraint evaluator returns `None` for missing values in its optional null-matching mode and `False` in ordinary matching. Application-level missing-evidence handling therefore needs an explicit contract; it is not safe to infer legal falsity from one Boolean return value.
- Around lines 392–603, logical `andSequence` is evaluated as conjunction with short-circuiting. It is not an event-sequencing implementation for “consent before transaction” or recurring reviews.
- The `count` operand uses stored rule matches. It does not itself establish a sliding three-year history in the same product category.
- Numeric equality/inequality now first attempts `float(value)`/`float(right)`, falling back to strings; relational numeric comparisons also use floats. This differs from the feature document's statement that equality is lexical. Use exact, explicitly typed financial preprocessing and boundary tests before relying on these comparisons.
- The date parser includes a timezone TODO. Explicit times/timezones and calendar interpretation are necessary in the pilot.
- The feature document lists unsupported constructs including `rightOperandReference`, explicit `unit`/`dataType` handling, `inheritFrom`, `implies`, and some special temporal operands. Generic custom IRIs are accepted, but this does not implement the legal meaning of an HKMA-specific operand.

The October code has capabilities beyond the July paper, including additional reasoning/configuration paths. Neither the paper's feature matrix nor stale documentation is a complete specification of this checkout. The recommended next step is a small evaluator acceptance trial with pinned settings, explicit domain adapters and known expected results. It is not adoption as a general compliance authority.

## FORCE evaluator and test suite

Inspected `ODRL-Support.md`, `src/evaluator/Evaluate.ts`, duty-related portions of `Atomizer.ts`, `src/util/policy/PolicyUtil.ts`, `src/shapes/Shapes.ts`, and `src/rules/detective/deontic-states.n3`. The support document states that permissions do not yet consider duty reports and says duty rules are unsupported. The source nevertheless has duty entries in its atomizer and inference rules mapping duty activation/performance to deontic states. Those facts are compatible with partial reporting support and incomplete permission-prerequisite support. They do not establish full duty enforcement.

The helper `policyToQuads` links a `Duty` to a policy through `odrl:duty`, while W3C policy-level obligations use `odrl:obligation`. This is a concrete compatibility point to resolve for the intended input path; it is not a claim that every FORCE input is generated by that helper. `Evaluate.ts` validates RDF/triples and materialises dynamic policy before invoking the engine. The inspected ordinary path does not itself settle the duty-support discrepancy.

The test-suite README describes the reusable structure particularly clearly: policy, state of the world, expected compliance report, description and optional access request. Its retained result table reports 67/68 for an activation-similarity comparison and marks duty cases as unsupported. Those are upstream reported results for a specified comparator, not local test evidence or a full legal-compliance score. A missing duty could escape an activation-only metric. HKMA tests should compare authority to use the approach and actual duty performance separately.

FORCE is therefore recommended for its test/report design and as a second evaluator to investigate. Before depending on it, test a fulfilled/unfulfilled prior-consent pair, a requested-explanation duty, and a policy-level annual-review obligation. Report divergence from OVAL as a semantic question to resolve rather than selecting whichever answer is preferred.

## ODRE Python

Inspected `pyodre/odre.py` and the nested-constraint sample `test/policices/basic-experiments/1-policy_constant_lt.json`.

`_rules` selects rule identifiers through permission, prohibition or obligation relationships but returns only the identifiers. The subsequent `enforce` loop evaluates every selected rule through the same path. No rule-type dispatch in that path distinguishes granting a permission from respecting a prohibition or fulfilling an obligation. This is a material reason not to treat that function as a generic deontic evaluator.

`_constraints` queries `odrl:operator`, `odrl:leftOperand` and `odrl:rightOperand` directly on the rule identifier. The inspected sample instead places them on a nested `constraint` node, as ordinary ODRL does. If the query yields no constraints, `enforce` sets the decision true. This static mismatch is a concrete test to reproduce before adopting the implementation. No failure was executed here, and no claim is made about all ODRE implementations or a later fixed revision.

The template and operand/action adapter idea remains useful. The Python code and the paper's explicitly synchronous demonstration do not justify selecting it as the circular's first complete compliance evaluator.

## Eclipse Dataspace Components

Inspected `PolicyEngineImpl.java` and `JsonObjectToPolicyTransformer.java` in the control-plane libraries. The engine registers constraint and rule functions by type/context, filters policies by scope, evaluates the selected policy and runs pre/post validators. The JSON-LD transformer handles permission, prohibition and obligation structures and selected policy types.

These are concrete integration facilities for a dataspace application. They do not determine how a client qualifies as an SPI or what a dispensation means. An HKMA integration would still have to supply reviewed functions, scope bindings and evidence sources. EDC is consequently a deployment option if the product later needs that infrastructure, rather than the initial research translator.

## Local repository baseline

Main: `3c3e462acabfde8c62285f4274f0f8c62b90a790`. Prospectus branch: `e8beb52b13399f18bbbff9aecea9636803729d5f`. The committed prospectus/translation source trees have no differences between those references. Inspected selected source files have no worktree changes against HEAD. No separate worktree was switched or merged.

`prospectus/models.py` and `semantics.py` already encode conditional SPI financial, client, threshold, eligibility and selected-duty calculations. They explicitly document external premises, including ownership/aggregation entitlement, valid monitoring arrangements, currency conversion and other applicable requirements. `make_model` marks its input as a synthetic specification, and generated source bindings leave entailment and completeness unestablished. These are valuable reusable fixtures, not already-certified legal interpretations.

`prospectus/checks.py` has an independently written symbolic reference and mutations for some of these models. `translation/verification.py` accepts external expected results and checks runtime/replay consistency. These checks were read, not rerun. They can be extended to an ODRL projection while keeping source-review evidence separate.

`translation/pipeline.py:12` currently accepts only `ruleir` and `catala`. The source/assembly/clause machinery can preserve the circular's evidence, but its bond-specific concepts need adaptation. Lifecycle and duty-performance modules retain evidence and unresolved compliance status; the examined instances concern other product workflows and should not be presented as an existing SPI/ODRL integration.

## Decision record

| Decision | Primary criterion status | Veto / uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|
| Use the repository's source-linked model and existing SPI fixtures as the starting point. | Relevant code and actual circular provisions inspected. | Existing fixtures explicitly assume substantial legal/factual premises. | Review clause coverage and add an ODRL profile/export. | Full circular formalisation already exists. |
| Trial OVAL for a declared fragment. | Paper and current implementation inspected. | Duty defaults, float arithmetic, unknowns, temporal and feature limits. | Run the proposed source-based cases under pinned semantics. | Production readiness or superiority over FORCE. |
| Reuse FORCE's test/report design. | Code/README inspected. | Duty support and comparator coverage need resolution. | Compare the particular normative outcomes the pilot requires. | Passing activation checks proves fulfilment. |
| Study AgentODRL/LLM4ODRL generation methods. | Direct methods/evaluation inspected. | Synthetic/model-judged metrics; LLM4ODRL licence not established. | Bounded, equal-input comparison with an independent source oracle. | Existing reported scores predict HKMA legal accuracy. |
| Keep Catala as calculations and additional checks. | Existing code and the compilation-proof boundary inspected. | Shared interpretation errors and missing cross-language correspondence. | Define the exact common fragment and independent expected cases. | Compilation proves source fidelity or ODRL validity. |

The strongest alternative explanation for a successful future pilot would be that easy fixtures and shared assumptions concealed the difficult source interpretation. FAQ 6, withdrawal, requested explanations and missing facts are therefore essential early counterexamples. A successful structural check alone would not change the present recommendation.
