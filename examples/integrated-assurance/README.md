# Reproduce a retained circular investigation

The four manifests bind the exact public SFC responses used in round 12. Copies
of those responses are included in `sources/` with their original source hashes.
The
selected control is explicit; surrounding text remains in the source inventory.
An executable candidate represents a proposed interpretation with stipulated
fact meanings. Its JAR does not constitute approval to deploy that interpretation.

From the repository root, the reviewed master command is:

```text
/home/chakwong/python/legalmath/.venv/bin/python /home/chakwong/python/legalmath/scripts/run_closure_master.py execute
```

It checks phase input hashes, requires an executed repair after a failure and
refreshes the next phase plan. Live jobs persist under
`artifacts/interpretation/round12/live-cases`; each phase retains an immutable
snapshot of its evidence. Repeating a completed unchanged job reuses its
recorded proposals and binaries. Calls are reserved in the existing shared
ledger before dispatch and are never refunded after invalid output or a crash.

The reusable product entry point is `legalmath assurance-investigate`. Its
arguments are `--manifest`, `--out`, `--allowance`, `--ceiling`, `--jdk` and
`--at`; the ceiling is an absolute position in an existing authorized ledger.
The command is also available through `.venv/bin/python -m legalmath.cli`.
Use the fixed master above to reproduce this round's reviewed resource policy.

Start with a job's `report.json`. It links the source and interpretation records,
independent cvc5/Java comparisons, clingo argument checks and remaining questions.
The interpretation directory contains `abstractions.json`, `claims.json`,
`candidates.json`, `candidate-presentation.json`, source-fidelity checks and the
search state. Each abstraction retains actors, objects, relations, unit of
assessment, time, assumptions and missing information. Incompatible fact meanings
remain incomparable even when formulas look identical.

For Java, use each entry in `independent.binaries`: it identifies the candidate,
build manifest, generated class and JAR. The generated class exposes the existing
five-argument `evaluate(snapshotJson, ruleId, validAt, knownAt, mode)` API. Fact
snapshots must conform to that candidate's bundle, including classification
meaning, evidence and time. Preserve the accompanying report when inspecting
conditional results; source uncertainty cannot be inferred from a Boolean value.

PDF recovery retains exact route text, page images, located differing regions
and bounded OCR actions. Whitespace equality may close a formatting difference.
An OCR majority never resolves a material difference. The current retained
12-page exercise still has unresolved differences, all preserved in its report.

The engineering evidence and remaining interpretation-evaluation requirements
are recorded in `docs/implementation/interpretation-round12/execution-result.md`.
Actual bank integration is deferred under the user's instruction.
