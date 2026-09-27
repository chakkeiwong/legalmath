# Refactor review

Root Codex performed this review; it is not an independent human, legal or
separate-model review. The plan was revised before implementation and checked
again against the resulting code and executed evidence.

| Review question | Finding and disposition |
| --- | --- |
| Is interpretation shared, or merely the source packet? | `frontend.interpret` has no target argument. Generation and criticism produce retained models before any target is selected. Both translators consume the same model and review hashes. |
| Is the common model restricted to RuleIR? | No. The typed model has records, lists, decimals, options and payload enums. The rich probe produces no RuleIR bundle and executes native Catala. RuleIR returns a capability report. |
| Does changing target silently change semantics? | Policy is explicit in the model. `ruleir.v1` preserves existing scalar behavior. `complete.v1` performs the same evidence decisions above either target. Rich partial-input translation is explicitly unsupported. |
| Did legacy formalization or execution regress? | Sixteen baseline formalizer comparisons preserve serialized bundles. Imported conformance bundles round-trip unchanged. Compiled scalar checks compare full traces to the original evaluator, including unknowns, lazy errors, rule references and exception ties. |
| Can selection erase uncertainty? | Every generated reading is retained; the native compatibility CLI requires selection when alternatives remain. Questions, ambiguity, deferred coverage, dependencies and adverse criticism block both target builds. The selected reading remains part of the model. |
| Is evidence fabricated or weakened in adaptation? | Original native snapshots are validated first. Field/item evidence is retained. Scalar identifier aliases are deterministic and verifiable; original IDs and the input snapshot hash remain available. |
| Do output hashes alone prove a correct result? | No. Verification checks the model and build, binds outer results to inner execution, checks deterministic adapters, and compares scalar traces or replays native execution and exact references. Rehashed tampering is tested. |
| Can execution run bytes different from verified bytes? | Scalar and native execution copy the verified JAR bytes into a private execution directory. Changed build identity, translation, model, or JAR bytes are rejected. |
| Are model calls bounded and resumable? | At most two generation/criticism pairs. Completed responses are reused only after commitment checks. Interrupted dispatches remain counted and stop rather than repeating silently. Fixture tests exercise this without live calls. |
| Does the refactor create a release approval shortcut? | No. It exposes draft builds and execution. Existing authenticated release hosts retain promotion authority. Model criticism is explicitly provisional. |
| Does passing prove Catala universally better? | No. The source controls are handwritten, and legal adjudication is pending. Native feature checks establish finite implementation behavior. No stochastic ranking or converter-quality claim follows. |

Material repairs were the legacy partial-metadata adapter, native evidence ID
mapping, field/item evidence preservation, strict type-definition response
schemas, retained expression/interpretation consistency, result wrapper binding,
and coherent synthetic source wording for the rich fixture. The result note
records their verification. The old free-form native generator remains explicitly
available for historical tasks outside the shared grammar.

Known limits are documented rather than treated as silently supported: generated
readings have one result; rich models require complete inputs and unconditional
outer scope; rich default/scale nodes, library calls, rounding and helper scopes
need further shared operators and lowering tests. These limits do not prevent
the requested modular boundary or the shared paired checks.

The authored source, tests and documentation pass the whitespace check. Retained
compiler-generated Java includes the pinned compiler's trailing whitespace; those
bytes are preserved because build manifests bind their exact content.
