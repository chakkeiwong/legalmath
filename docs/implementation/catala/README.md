# Optional Catala backend

New source conversion uses a [shared typed interpretation and deterministic
translators](modular-translation/README.md). Both RuleIR and Catala consume the
same frozen model. The compiler described below supplies Catala's scalar
compatibility pass; richer shared expressions lower directly to native Catala.

The current backend generates Catala calculations from validated RuleIR 0.1
bundles. RuleIR remains the authored rule source. The generator covers all
current expression operators and types, with explicit unknown/error/conflict
statuses, exact integer money arithmetic, and lazy if/default selection. It
accepts arbitrary validated bundle identities rather than a fixed pilot list.

`legalmath.catala.generator` emits a Catala scope for each calculation or branch
selector and a typed Java bridge. `legalmath.catala.backend` compiles these into
the ordinary `hk.legalmath.Policy_<bundle hash>` API. String and Map snapshots,
draft/production/replay modes, result hashes, and full RuleIR traces use the
existing Java contract. The optional backend is selected explicitly:

```python
from legalmath.java.manifest import build_candidate, verify_candidate

build = build_candidate(bundle, output, jdk, backend="catala", catala_toolchain={
    "compiler": ".localresources/catala-toolchain/opam-root/catala-clean-1.2.1/bin/catala",
    "upstream": ".localresources/catala-toolchain/catala-0f895e048d19dbe72f24cdd6d5f3398bfe1335fa",
    "lock": "docs/implementation/catala/toolchain-lock.json",
})
report = verify_candidate(build, cases, jdk)
```

`Releases.build`, `host_package.prepare`, and `prepare_interpretation` accept the
same keyword options. `legalmath build-java` accepts `--backend catala` together
with `--catala`, `--catala-upstream`, and `--catala-lock`, in addition to its usual
stored-bundle, identity, cases, output and JDK arguments. It creates a candidate;
the normal separate review, applicability and release approvals still apply.
The default backend is Java. No production release is created by this branch.

Deployment needs Java 17 and the built JAR. The Catala compiler and OCaml are
build-time tools. The JAR includes the verified Catala runtime and license,
canonical bundle, generated sources, source map, shared host sources and build
identity under `META-INF/legalmath`. Builds use fixed ZIP metadata and relative
source names. The compiler executable and complete Java runtime inventory must
match the supplied reviewed lock. A new compiler build requires a reviewed lock;
it cannot silently replace the pinned compiler.

Each `source-map.json` entry connects a RuleIR node to its rule and source spans.
Calculation entries also name the Catala scope and source lines. The host records
actual returned Catala values while traversing the rule, so the trace describes
what executed. It does not consult the Python evaluator. Full verification uses
Python as the reference and checks all result fields except the deliberately
distinct engine and result hashes; each hash is checked independently.

The backend shares Java snapshot validation, fact/time admissibility, static
input-conflict checks, traversal, provenance, and hashing with the original Java
engine. Event replay and transaction/release controls are also shared. Agreement
therefore provides engineering conformance evidence, not independent validation
of those shared components. Input failures rejected before traversal test the
host boundary, while traced calculations exercise Catala. Native Catala defaults
can coalesce equal consequences; the generated selector explicitly implements
RuleIR's required multiplicity conflict instead.

The remediation plan, skeptical review, and executable are
`docs/plans/catala-gap-remediation.md`, `gap-remediation-review.md`, and
`scripts/catala_remediation_program.py`. Its source fingerprint is stored in
`gap-remediation-review.json`. From this worktree:

```bash
PYTHONPATH=src /home/chakwong/python/legalmath/.venv/bin/python scripts/catala_remediation_program.py --out artifacts/catala/remediation-01
```

Use a fresh output directory. The program checks the reviewed inputs, executes
full comparisons and integration regressions, retains sources/logs/results,
checks build reproducibility, and records the remaining adoption questions. The
result report is `gap-remediation-results.md`. Compiler/JVM resources remain
bounded; unusually large valid bundles can fail compilation rather than receive
a fallback result. Finite conformance is not a formal equivalence proof, and
human reviewer benefit and institution-specific acceptance require further work.

The original two handwritten examples, four-bundle adapter, eight-phase program,
and runs 01–03 remain historical pilot evidence. Their old review fingerprints
refer to the pilot implementation and intentionally do not authorize the revised
backend. `execution-report.md` describes that earlier restricted implementation;
its draft-only, projection-only limits do not describe the new optional backend.
