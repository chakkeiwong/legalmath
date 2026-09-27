# Modular translation results

The shared front end and both target translators are implemented. One frozen
interpretation now determines the executable meaning and evidence policy for
both RuleIR and Catala. The existing search formalizer delegates through the
shared model while preserving its RuleIR output. The native generation CLI uses
the shared workflow by default; its historical generator remains an explicit
compatibility option.

The deterministic source replay passed all **44 cases on both targets**: four
net-assets cases, sixteen gift cases, eight network cases and sixteen consultation
cases. Each pair has identical model and interpretation hashes. Each compiled
result also matches the original RuleIR evaluator's complete semantic trace.
The source packet and formulas were frozen handwritten controls from the earlier
study, so this establishes translation agreement on those controls, conditional
on their interpretations. Their legal adjudication remains pending.

Seven richer outputs passed native Catala execution, uninstrumented Java and
exact checks inside the original Catala interpreter: record/list filtering and
aggregation with option handling, payload enum matching, optional presence,
optional absence, a payload constructor, exact decimal multiplication, and money
aggregation. RuleIR explicitly reports the rich model as unsupported. These
checks confirm that the common representation no longer forces rich programs
through RuleIR.

The [validation manifest](validation.json) records code hashes, baseline commit,
environment, exact command, source packet identity, elapsed time, and result
locations. The paired results and generated programs are retained under
`artifacts/catala/modular-translation/`. No live model calls were made.
Sixteen comparisons against the baseline formalizer also preserved the exact
serialized RuleIR bytes, including its legacy minimal-metadata callers.

All **759 collected tests have passing coverage across runs**, including 34 new
translation tests. The first full-suite invocation stopped at an API TestClient
hang after 494 passing progress records. The exact API test passed in 0.81 seconds
outside the sandbox; all 266 tests from the integration modules onward then
passed in the trusted environment in 349.36 seconds. This is combined coverage,
not a claim of one uninterrupted full-suite run. The final metadata and fixture
repairs also passed their targeted checks and the complete remaining run. The
[regression record](regression.json) identifies every covered test and log hash.

## Review and repair

The skeptical plan review rejected three shortcuts: merely sharing the source
packet, putting RuleIR itself at the common boundary, and applying native
complete-input behavior to every legacy RuleIR program. The implementation uses
a wider typed model, explicit policy selection, and the existing scalar engines.

Implementation checks exposed and repaired compatibility and provenance edges:
older formalizer callers supply partial reading metadata; native evidence IDs
may contain characters RuleIR identifiers cannot; rich evidence must survive at
field/item level; retained formulas must agree with their typed expressions;
and structured model responses need explicit type-definition schemas. Target
builds and translation records are rechecked before execution, and verified JAR
bytes are copied for execution to avoid a file replacement race.
The final audit also found that a valid inner scalar trace could accompany an
altered outer result. Verification now checks their agreement, validates the
deterministic identifier mapping, binds the original snapshot and model, and
replays native results before accepting their provenance. Regression tests reject
self-consistently rehashed alterations as well as changed JARs and manifests.

The first replay completed its semantic checks but could not serialize its run
manifest because canonical JSON forbids floating-point numbers. Wall time is now
recorded as integer milliseconds. The replay then verified the existing builds,
reran its cases and successfully wrote the manifest. This was a reporting defect,
not a disagreement between targets.

A final fixture audit replaced inherited scalar-example wording in the rich
synthetic source with the actual collection/option calculation and corresponding
factual meanings. The earlier probe is inventoried as superseded; the corrected
fixture was compiled and independently checked again. It remains an engineering
fixture, with no claim of source interpretation quality.

## Decision

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Accept the modular engineering change | Same model, same policy and exact scalar results; direct rich execution; regression coverage complete | No mismatch in the retained checks | Finite cases and bounded shared grammar | Use this boundary for future paired conversion studies | Better model interpretation or universally better Catala |
| Keep richer Catala translation available | Seven exact native outputs, with explicit RuleIR capability failure | No instrumentation/interpreter disagreement | Additional native language features need explicit shared operators | Extend one construct at a time with exact checks | Full Catala language coverage |
| Preserve draft-only authority | No new release or activation path | Unresolved questions and dependencies block builds | Independent legal and human review still pending | Use existing review hosts for any promotion | Legal correctness or production acceptance |

The strongest alternative explanation for the scalar agreement is the deliberate
reuse of the existing compiler and host. That is expected: the claim is preserved
meaning across a modular boundary. The direct rich probes distinguish this
design from a renamed RuleIR wrapper. A discrepancy on a valid model, lost
uncertainty, changed evidence policy, or unequal retained commitments would
overturn the engineering acceptance and require repair.

This run does not rank converters. A later quality comparison needs prospective
source tasks, a fixed common interpretation workflow, independently adjudicated
references and an uncertainty analysis appropriate to the claimed ranking.
