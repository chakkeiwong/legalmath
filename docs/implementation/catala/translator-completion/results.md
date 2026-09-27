# Shared Catala translator completion

The shared frontend and Catala translator now support the feature families in
the reviewed plan: scope and explicit result states for rich rules, strict
defaults/exceptions, exact scaling and separate rounding, typed calendar/numeric/
collection operations, reusable calculations, multiple generated outputs, and
partial observations inside records, lists, options and payload variants.

These features are available through shared model version 2. Version 1 retains
its existing interpretation and lowering. The compiler computes the new
expressions and state propagation; the host validates evidence and decodes
results. The native CLI adapts multiple outputs to the common frontend and checks
every output. A source reading, its helper definitions and its executable outputs
remain one commitment.

The partial profile is explicit. `partial.v1` uses dependencies actually evaluated,
including field/item paths, and is rejected by the RuleIR target because its
policy differs from RuleIR's static whole-fact conflict veto. `complete.v1`
continues to require all declared inputs. No existing default backend or
evidence policy was replaced.

## Evidence and decisions

The frozen baseline replay passed all 44 cases through both targets, plus seven
rich outputs, and verified nine existing builds without regenerating their
commitments. The full trusted regression passed 792 tests in 966.75 seconds.
Final review exposed an overly broad new scale-coefficient bound; a new test
reproduced rejection of an originally valid large RuleIR coefficient, and the
repair restricted the bound to version 2. Aggregate complete-input abstention was
also preserved in the multi-output adapter. The 69-test translation suite passed
after these repairs in 209.22 seconds.

Final fixture metadata and compiled records are accounted for separately in
`validation.json`: an old synthetic task question was replaced with the actual
calculation description, then the affected tests were rerun. Earlier regression
logs remain tied to their own source checkpoints; they are not presented as one
full-suite invocation against the final metadata.

That final run passed 35 affected tests in 129.00 seconds. It retains four sealed
version-2 compiler builds and 91 exact execution/reference checks in
`artifacts/catala/translator-completion/checks.json.gz`. The full regression and
focused follow-ups cover 794 distinct test IDs, including the two added review
checks. No tests were skipped. The final source hashes match the retained
version-2 validation manifest.

| Decision | Primary criterion | Veto diagnostics | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Preserve version-1 behavior | Frozen paired cases and rich outputs pass; old builds verify | No changed model/translation/build commitment in replay | Finite retained corpus | Keep versioned lowering and compatibility tests | Formal proof of all old programs |
| Use version 2 as an optional translator extension | Exact handwritten references checked in instrumented Java, plain Java and original Catala interpreter | Wrong status/value, dropped evidence or altered result fails verification | Bounded fixture coverage | Use the documented model/observation interface within its limits | Complete Catala-language support |
| Keep partial policy explicit | Known-field projection, incomplete membership, option absence and conflict cases retain distinct meanings | Wrong policy is rejected by target capability checks | Broader application requirements | Select the profile as part of the shared source task | Equivalence of partial.v1 and ruleir.v1 |
| Keep interpretation/release authority unchanged | Shared generation/criticism schemas and source commitments remain enforced | Open questions and challenged source readings block executable promotion | No live interpretation-quality study | Conduct a separately planned paired study if quality claims are needed | Legal correctness, human approval or production readiness |

This was deterministic engineering validation. There was no stochastic method
ranking, live model call, allowance use or compiler installation. Case counts and
compiler success alone are not superiority evidence. Catala can now execute more
of the shared model, while the preserved common fragment retains its previous
results.

## Remaining limits

The shared vocabulary is deliberately closed and typed. It does not include every
Catala operator or arbitrary module import. Helpers and types must be acyclic.
The generated interface remains subject to 30 native types, depth 12, 40 inputs/
outputs and 64 KB candidate source, with additional parser, observation and
expanded-type budgets. State encoding consumes some of these resources; an
oversized model receives an unsupported report. Calendar and sequence operations
enforce their documented domains before native narrowing conversions.

The compatibility API currently evaluates the sealed program once for each named
output it returns; batching can reduce this overhead later. Rich partial outputs
use an explicit child-state representation rather than a fully known value.
There has been no live source-conversion quality study for the new grammar.

The strongest alternative explanation for passing fixtures is untested nesting
or resource combinations. An independent counterexample to a declared operation,
policy or provenance result would require repair. The three execution paths and
frozen baseline limit implementation discrepancies; they do not certify source
interpretation or production suitability.

The [plan](../../../plans/catala-translator-completion.md), [review](review.md),
[interface guide](README.md), [validation manifest](validation.json) and
[reset memo](reset-memo.md) retain the decisions and reproduction details.
