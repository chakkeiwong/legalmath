# Catala adapter: eight-phase execution plan

The engineering question is whether a pinned Catala implementation can calculate
the existing SPI financial subcondition and exception semantics independently of
RuleIR, and deliver those calculations through Java 17. The comparison target is
the Python reference evaluator at main commit
`66d15b2aee8f0c00076ab1dd24334b5f80dac058`, its hand-specified decision cases,
and its existing Java implementation. This first adapter is optional and draft.

## Eight phases

1. Freeze the comparison target: source and corpus hashes, expected outcomes,
   reference results and the exact Git checkpoint.
2. Pin and audit Catala 1.2.1, source commit
   `0f895e048d19dbe72f24cdd6d5f3398bfe1335fa`, with compiler/runtime hashes,
   dependency inventory, licensing and Java 17 smoke checks.
3. Define the supported semantic fragment. Declare the particular accepted
   rule structures, money units, missing/conflicting inputs, exceptions, scope
   and effective/knowledge times. Reject every unsupported structure.
4. Build independently authored Catala pilots for the SPI financial
   subcondition and the synthetic default/exception fixture. Retain source
   locations and distinguish legal-source material from synthetic semantics.
5. Compare reference Python, current Java, Catala interpreter and Catala Java
   on declared cases, exhaustive small input combinations, temporal boundaries
   and deliberate mutations. Record each layer's contribution; preflight
   decisions are not compiler results.
6. Deliver a draft Java host entry point for those accepted profiles with
   source/version identity and a checked build manifest. Verify failures and
   altered manifests. The current production/release path is unchanged.
7. Prepare and mechanically verify a reviewer packet showing law, interpretation,
   Catala and cases. Record human-reader acceptance as pending until observed;
   file generation or a model score cannot establish reviewer benefit.
8. Decide adoption from the evidence, naming every unmet condition. Execution
   completion, optional-pilot viability and replacement of RuleIR are distinct.

## Evidence contract and research intent

| Item | Contract |
| --- | --- |
| Candidate | Independent Catala definitions plus a declared status/provenance adapter |
| Baseline | Frozen RuleIR Python and existing Java, exact declared cases |
| Expected failure | Native defaults or missing-value handling differs from RuleIR; a wrapper hides the difference |
| Primary criterion | Exact status/type/value agreement across accepted cases, source commitments retained, real Catala execution for computable cases |
| Promotion veto | Any mismatch; unsupported bundle accepted; missing inputs converted to zero as a known fact; incomplete source map; broken Java build or identity binding; missing human-review evidence |
| Continuation veto | Corrupt baseline, unavailable/untrusted toolchain, failed command/time budget, or artifacts that cannot identify what ran |
| Repair trigger | A counterexample isolates a semantic or adapter defect; repair and rerun the affected phase before proceeding |
| Explanatory only | Runtime, output size, source length, number of tests and rendered-review packet |
| Non-conclusions | No legal-interpretation validation, whole-compiler proof, whole-RuleIR equivalence, production readiness or human-readability finding |
| Preserved result | `artifacts/catala/<run>/run-manifest.json`, phase records, command logs, comparisons, source hashes and decision |

Source/provenance checks and exact computed outcomes are separate ledgers.
The pilot must not manufacture a RuleIR execution trace using reference results.
If the Catala interface has a different trace format, record that limitation and
block replacement of the existing evaluator even if values agree.

## Defaults and assumptions

| Choice and provenance | Reason | Failure and early diagnostic | Status |
| --- | --- | --- | --- |
| Catala 1.2.1, official release/tag | Release fixes Java 17 compatibility | Tag/package version may differ; record source and binary hashes as well as version | Pinned baseline |
| Isolated opam switch, OCaml 4.14.2 | Meets upstream >=4.14 and matches upstream 4.14 build family | Build dependencies or conda compiler leak; use system build PATH and retain package inventory | Convenience build choice |
| Existing local Java 17 JDK | Same host target as current code | Worktree lacks ignored JDK; use explicit path and verify `javac -version` | Reviewed project target |
| SPI cents as integers | RuleIR stores HKD cents, no rounding in threshold test | Dollar/cent mismatch; exact threshold and one-cent neighbours | Baseline semantics |
| Separate missing/conflict envelope | Catala inputs are ordinarily concrete | Unknown could be collapsed; full known/unknown/conflict grid and wrapper attribution | Hypothesis to test |
| Synthetic defaults fixture | Existing equal-valued exception conflict test | Same-value exceptions accidentally coalesce; two-true case must conflict | Baseline semantics |
| Bounded supported profiles | Auditable first integration | Accidental generic compatibility claim; schema and structural mutation rejection | Explicit scope |
| `--no-stdlib`, primitive-only pilot | Neither definition calls standard-library functions | Compiler emits its `catala.stdlib` namespace under this flag; retain generated namespace and compile unchanged runtime | Convenience choice, not a full-library test |

## Skeptical audit before implementation

The proposed unrestricted adapter is narrowed to declared profiles because native
Catala missing/error semantics cannot be assumed to equal RuleIR. The other
agent's live files are excluded by branching from the pushed checkpoint. Python
imports must resolve to this worktree, not the main checkout's editable install.
Java compiler discovery must use the existing isolated JDK. Compiler and runtime
must come from the same pinned release. The comparison must execute Catala rather
than call the reference evaluator from the candidate path. Human benefit is not
inferred from generated documentation. These repairs address baseline, proxy,
comparison, hidden-default, stale-state and environment risks. The revised plan
passes audit for an optional bounded pilot, not for replacing RuleIR.

## Toolchain preparation and execution

Download upstream source and opam into ignored `.localresources/catala-toolchain/`.
Build only in that directory, without changing the user's shell, global packages
or existing Python environment. Network retrieval is a preparation step, never
an implicit master-program side effect. Bound initialization to 180 seconds,
compiler bootstrap to 1200 seconds and Catala dependency build to 1200 seconds;
retain logs and report a failed toolchain as a preparation failure. A pinned
source archive and build inventory preserve the input even when a binary must be
rebuilt. The master runner uses bounded commands, a new output directory per run,
and a reviewed program hash. Failed phases cannot be reported as passes.

The project Python is `/home/chakwong/python/legalmath/.venv/bin/python` with
`PYTHONPATH` explicitly set to this worktree's `src`. No GPU or stochastic model
run is involved. After implementation, review the actual program and bind the
review to its code hash before running `scripts/catala_master_program.py`.

Preparation diagnostics exposed inherited Conda `CC`, `CPPFLAGS` and linker
flags after PATH isolation. Clear them and rebuild the isolated OCaml compiler
and dependencies; an environment with a Conda C compiler is not an accepted
toolchain. Ninja is installed only within the ignored toolchain directory.
The opam repository requested security-fixed opam 2.5.2, which replaces the
initial 2.4.1 bootstrap before package installation.
