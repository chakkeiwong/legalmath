# Catala backend remediation results

The implementation gaps have been repaired and the reviewed eight-phase program
passed on 25 September 2026. The optional backend now generates Catala from
canonical RuleIR and participates in the existing Java trace, raw-snapshot,
transaction and release interfaces. **344 complete decision comparisons, eight
shared event cases, and 202 regression tests passed.** A build repeated in a
different directory produced identical manifests and JAR bytes.

The previous pilot's limitations were implementation choices: two handwritten
scopes, four recognized bundle hashes, projected results and a typed draft host.
They did not establish that Catala was worse than the project's rules. The
repaired implementation removes those restrictions while keeping RuleIR as the
authored source. There is still no measured ranking of languages, performance,
legal quality, or human reviewer comprehension.

## Main synchronization and resulting changes

Main `9160ce72a17a255242299cc8ab33046f2501f42b` was merged without conflict in
`5c47153f712b34dbd69fb344b74c87931c4e0b92`. The remote main reference was checked
again after implementation and still matched. Main's committed changes add the
bounded interpretation-assurance and resumable issue workflows; they do not
change the RuleIR, Java or release contracts. Their regression tests passed with
the backend changes. The CLI extension preserves those new commands.

The separate main worktree's uncommitted work was preserved. `main-sync.json`
records the 618 paths observed at synchronization, including the untracked
assurance diversity module and monograph/research evidence. They were not a
reviewed committed baseline and did not alter the RuleIR or host contracts used
here. No main files were staged, reverted or overwritten by this remediation.

| Implementation gap | Repair and reason |
| --- | --- |
| Separate handwritten rules and exact bundle whitelist | `catala/generator.py` lowers validated RuleIR trees and emits a source map; changing a threshold, operator or consent rule changes compiled execution |
| Incomplete operator/type coverage | All current operators and bool, integer, HKD minor-unit and date types are lowered or explicitly handled by the shared host; unsupported/invalid bundles fail before compilation |
| Native default coalescing conflicts with RuleIR | Generated selectors implement RuleIR's multiple-true conflict and unknown/error precedence explicitly, including equal consequences |
| Projection-only results | The Java calculation hook records real Catala results during traversal; complete traces, reasons, evidence, diagnostics and independently checked hashes agree with the reference |
| Typed draft-only host | The normal generated Java String/Map API accepts raw snapshots and draft/production/replay modes; actual Catala-built JARs passed independent caller and transaction tests |
| Missing release and portable-package integration | Explicit backend options reach the existing build, review, export, restore and host-package paths; normal approvals and meaning descriptors still apply |
| Compiler/runtime identity and deployment burden | Build inputs and runtime sources are pinned; source/build identity and license are retained in the standalone Java 17 JAR; Catala/OCaml are only needed at build time |
| Misleading independent-checker claim | Shared validation, traversal, provenance, hashing, events and release infrastructure are disclosed as correlated components |
| Reviewer benefit | Source navigation is available; the human comparison remains pending and no readability advantage is claimed |

## Executed evidence

The implementation checkpoint was
`4a7ce12d8c9e128753673b30f6cb3eab1367cb97`. The retained run is
[`artifacts/catala/remediation-01`](../../../artifacts/catala/remediation-01/).
Its `inputs.json` and `review.json` bind 263 source/test/fixture/plan inputs;
`reviewed-sources/` retains their exact bytes. The input fingerprint remained
unchanged throughout execution. The plan audit is the executing agent's
skeptical review, not an independent model or human review.

| Phase | Result |
| --- | --- |
| Synchronization | Committed main is an ancestor; live uncommitted main work preserved |
| Pinned toolchain | Catala 1.2.1 compiler digest, version, runtime inventory and license checked |
| Existing conformance | 35 language fixtures plus 32 SPI control scenarios, grouped into 13 actual compiled bundles; full result comparison passed |
| Interactions | 277 comparisons in an additional compiled bundle passed: three-guard truth tables, nested conflicts, error precedence, lazy branches, reused rules, 130 exceptions, date endpoints and 6,000-digit exact integers |
| Integration/regressions | 202 passed, zero failures/errors/skips; 14 corpus-test instances were deselected because the preceding phases ran those exact comparisons into retained evidence |
| Reproducibility | Identical build manifests and JAR bytes from distinct temporary/output paths |
| Reviewer material | Node-to-rule/source/Catala-line maps and an engineering review guide retained; human study pending |
| Decision | Optional backend viable under the engineering contract; default unchanged; no production approval |

Of the 344 decision comparisons, 341 traversed real Catala calculations and
three stopped at shared input/version preflight checks. The latter demonstrate
host-boundary behavior, not compiler behavior. Eight event comparisons exercise
the shared event engine. The 202 regression tests include the original Java
backend, merged main assurance workflows and actual Catala-built binaries in
forced transaction interleavings, consent withdrawal, release replacement,
idempotency, release/export/history restoration, corrupt JAR rejection,
overlapping/stale evidence rejection and portable package meaning checks.

Three semantic bundle mutations changed observed decisions. A separately
compiled faulty literal returned nine where the canonical bundle required seven:
nine appeared in the result and trace, and full conformance rejected the build.
This demonstrates that the trace is generated from execution and that the
comparison can detect an incorrect calculation. Missing dispatch fails closed;
the Catala JAR refuses the plain-Java dynamic Runner fallback. Verification also
rejects engine substitution and altered compiler/JAR bytes.

The exact command was:

```bash
PYTHONPATH=src /home/chakwong/python/legalmath/.venv/bin/python scripts/catala_remediation_program.py --out artifacts/catala/remediation-01
```

`run-manifest.json` records the commit, commands, environment, input versions,
phase results and 259,130 ms total wall time. Each comparison directory retains
its corpus, generated source, source map, build log/manifest/JAR, verification
report and complete results. `tests.log` and `tests.xml` retain the regression
outcome. `artifact-hashes.json` covers the final evidence inventory. Runs 01–03
of the earlier pilot remain unmodified historical evidence.

## Decision and post-run audit

| Decision | Primary criterion status | Veto diagnostic status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Keep the generated backend as an explicit option | Complete-result and integration checks passed | No engineering veto in the retained run | Finite corpus and shared host machinery | Review institution-specific rules and deployment constraints before adoption | General compiler equivalence or legal correctness |
| Preserve current default | Engineering compatibility established, default-change evidence not sought | Human and institution acceptance absent | Reviewer comprehension and operational suitability | Counterbalanced human review with the same source, rules and questions | That either language is superior |

The strongest alternative explanation is correlated Java infrastructure:
validation, admissibility, traversal and provenance can share the same defect.
Full Python comparison reduces that risk on these cases but does not prove the
whole implementation correct. The fault-injection check addresses fabricated
traces; it does not validate every possible trace or operator combination.

An accepted-input counterexample, incorrect lazy branch, lost exactness,
unbound runtime, altered artifact accepted at verification, or failed transaction
invariant would overturn the engineering pass and trigger a repair. Such a
failure would reject the implementation under that contract, not automatically
the language or research direction. The weakest evidence remains unmeasured
human reviewer benefit and institution-specific operation. Compiler/JVM resource
limits can also reject unusually large valid bundles; no fallback silently
accepts them. These limits are documented in the backend README.
