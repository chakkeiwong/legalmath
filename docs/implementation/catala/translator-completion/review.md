# Translator completion review

Root Codex performed this review; there was no separate reviewer or live model
call. The pre-implementation skeptical audit is in the plan.

## Findings and repairs

1. Native defaults can coalesce equal consequences, and native monetary
   conversion can round. Direct lowering would change the shared meaning.
   Version 2 explicitly computes strict guard multiplicity and exact minor-unit
   divisibility in Catala; rounding has a separate typed node and named mode.
2. A whole-fact completeness flag cannot express partially known records or
   distinguish an absent option from unknown evidence. The optional partial
   profile retains typed observations at field/item/payload paths. Incomplete
   list membership prevents aggregation. Evidence references travel through
   compiled dependencies and are checked on replay.
3. A new dependency policy must not masquerade as RuleIR equivalence. Version 1
   keeps its static whole-fact conflict veto. Version 2 explicitly selects
   `partial.v1` or `complete.v1`; RuleIR rejects the new partial profile. A complete
   core-fragment comparison still uses the same model and policy on both targets.
4. Empty exception lists generated an untyped empty metadata fold. A concrete
   zero metadata record fixed compiler ambiguity without changing default meaning.
5. A conflict fixture retained contradictory top-level evidence IDs. Validation
   correctly rejected it; the fixture was corrected, not the integrity check.
6. The pinned Java list-sequence implementation narrows length to a machine
   integer. Lowering handles nonpositive ranges and limits positive length before
   the library call. Calendar offsets are bounded before duration conversion.
7. Expanded structured types can grow far faster than nominal type declarations.
   Validation and generated layouts now have explicit expansion budgets, and
   capability checks reject excessive generated type/depth/source size.
8. The native CLI still selected only one output. It now adapts multiple outputs
   to version 2, returns named results, and verifies every output against its
   reference. Camel-case native output names are retained; older one-output tasks
   keep their version-1 default and may explicitly request version 2.
9. Final diff review found a newly introduced scale-coefficient size limit also
   applied to version 1. A test reproduced rejection of an originally valid
   1,001-digit coefficient. The limit is now restricted to version 2; the
   original validator/evaluator and byte-preserving lowering supply its reference.
10. The replay report initially attempted to serialize floating-point elapsed
    seconds in a canonical format that forbids floats. Integer milliseconds fix
    the report; this was an evidence-writing defect, not a failed semantic case.
11. If complete-input policy blocks every named output, the new native adapter
    must report `ABSTAIN` at the aggregate level, rather than `PARTIAL_RESULTS`.
    The adapter now retains that reason and checks a common model/build identity
    across output evaluations. Verification checks every output and the shared
    abstention reason.
12. Synthetic version-2 fixtures inherited the old six-month task's question,
    subject and distinction even though their quoted text and expressions had
    been replaced. The fixture metadata now describes the actual calculations,
    and a test checks agreement of the question, statement and quoted text.
    Fresh compiled records must supply the final version-2 evidence. Earlier
    passes remain engineering diagnostics, not source-interpretation evidence.

## Evidence interpretation

Independent expected values/statuses are checked before plain-Java and original
Catala-interpreter equality. The host validates evidence and decodes result
records; it does not calculate the new rule expressions. Frozen build checks
test old commitments rather than rebuilding a new baseline. Expected values do
not enter generation, criticism or translation requests.

The strongest alternative explanation for apparent success is incomplete case
coverage: these bounded fixtures could miss combinations of nesting, resource
size or language operations. Exact interpreter comparison constrains compiler
and runtime discrepancies, but it is not a proof of the entire lowering. An
independent counterexample to a declared operation or evidence policy would
overturn the corresponding acceptance and trigger repair. Live source conversion
quality and downstream human legal review remain outside this run.

Final verdict: PASS for this optional, bounded implementation. The full suite
passed 792 tests; repairs passed 69 translation tests; coherent final fixtures
passed 35 affected tests. Together these cover 794 distinct test IDs. The final
retained records contain 91 exact checks and four sealed builds, and their source
hashes match the final implementation. The frozen replay still passes 44 cases
on both targets and seven rich outputs. This verdict does not change the default
backend, legal/source review authority or release approval requirements.
