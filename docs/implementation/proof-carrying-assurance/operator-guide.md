# Executing and reviewing an assurance dossier

The master is `scripts/run_proof_carrying_master.py`. Its reviewed plan is
`docs/plans/proof-carrying-assurance-integration.md`; its fixed command policy is
`allowlist.json` in this directory. Current acceptance records live under
`artifacts/proof-carrying-assurance/verified-execution-v3`. The older sibling
P0–P5 directories belong to a rejected implementation and must not be used as
accepted evidence. The `verified-execution-v2` campaign is also closed without
current acceptance; its passed commands and exhausted attempts remain historical
evidence. V3 runs in an isolated copy and transfers results back only after
checking that material inputs still match.

Run the master from the repository root:

```sh
.venv/bin/python scripts/run_proof_carrying_master.py audit
.venv/bin/python scripts/run_proof_carrying_master.py execute --through P4
.venv/bin/python scripts/run_proof_carrying_master.py execute --from P5 --through P5
```

P5 requires the trusted host context for the repository's HTTP tests. The master
constructs exact argv; no URL, package name, shell expression or model prompt is
accepted. The operating-system command approval is distinct from the project
allowlist. The current approved prefix is the repository Python interpreter
followed by `scripts/run_proof_carrying_master.py`.

The final JSON identifies the accepted phase manifests. Each identifies exact
inputs, predecessor manifests and output hashes. Follow the P2 dossier reference
in that report, rather than choosing a directory with the largest attempt
number: a later attempt can be failed or incomplete. In the dossier, each runtime
method points to an evidence envelope containing the cases, build manifest,
verification report, detailed results and JAR. The generated source files remain
beside the corresponding build manifest. Java and Catala rows identify their
class names. Those are draft executables for the stated interpretation, not
approved bank controls.

The application also exposes a manifest-based interface:

```sh
.venv/bin/python -m legalmath.cli assurance-dossier --help
.venv/bin/python -m legalmath.cli assurance-dossier-verify --help
```

`assurance-dossier` requires `--repository`, `--manifest`, `--out` and `--jdk`.
The repository defaults to the current directory. Catala is configured with all
three of `--catala-compiler`, `--catala-upstream` and `--catala-lock`. Without a
configured backend its result is unavailable; it is never counted as agreement.
The output directory must be new and within the repository. This keeps a prior
execution from being overwritten.

A `ReplayInput` manifest names the source packet, candidate dictionary, criticism
proposal and retained source files by SHA-256 and path relative to that
repository. It also declares assessment time (six fractional UTC digits), origin,
probe/pair budgets, required backends and whether fresh generation is required.
`replay-input.json` is the concrete five-candidate example. Its `origin` is
`ARCHIVED_MODEL_PROPOSALS`. The raw circular and every quotation are checked;
the archived packet's missing FAQ remains missing. The adapter does not contain
an SFC circular number or a legal predicate. Another retained investigation can
use the same interface without changing implementation code.

For a new circular, existing `interpretation-search`, `interpretation-assurance`
and `assurance-investigate` commands are the generation/investigation layer.
They require their own retained sources, settings and bounded allowance. Once
their proposals are retained, a dossier manifest can bind those files. The dossier
command itself does not generate fresh alternatives, acquire missing authorities
or extend the language. Unsupported formalization produces an extension question;
a new grammar needs its own semantic and translation tests before acceptance.

Exit code zero means the command produced a valid result. It does not mean the
interpretation is settled. Consumers must inspect `status`,
`evidence_files_verified`, every blocking reason, and the permanently false
`release_eligible` field. Parsing a dossier without supplying an evidence root
returns `EVIDENCE_FILES_NOT_VERIFIED`. A successful finite runtime comparison is
CHECKED. No general proof certificate is accepted by this version. Stored file
hashes detect alteration; they do not authenticate an independent party's
historical execution or the regulator's intended meaning.

After a failed/interrupted phase, inspect its command log and manifest. Write a
JSON repair note in this directory with `failure`, `changes` and `regression`,
then run:

```sh
.venv/bin/python scripts/run_proof_carrying_master.py repair --phase P5 --note docs/implementation/proof-carrying-assurance/p5-render-repair.json
```

That example note is already consumed in the present execution; it is not a
blank approval for a different failure. The repair command runs the prescribed
check. A phase retry still executes the whole phase and is bounded by the
three-attempt ceiling. `refresh` rechecks staleness and writes the current next
plan. It does not erase failures or grant a new retry budget.

For the exact distinction between surveyed research, existing components and
checks executed by this increment, see [method coverage](method-coverage.md).
The [successor specification](../../plans/proof-carrying-assurance-next.md) records
the unfinished source, proof and prospective-evaluation work.
