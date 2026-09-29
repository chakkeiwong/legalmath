# Round 13 operator guide

This program investigates the frozen STR, gifts, equity-options margin and e-IP
cases left by round 12. It produces typed control proposals, source findings and
conditional Java execution evidence. Its outputs are development evidence, not
bank release approvals. The source snapshots and assessment timestamp are fixed;
rerunning the program does not search for every subsequent regulatory amendment.

## Entry point and authority

Run from `/home/chakwong/python/legalmath`:

```sh
/home/chakwong/python/legalmath/.venv/bin/python scripts/run_decision_master.py audit
/home/chakwong/python/legalmath/.venv/bin/python scripts/run_decision_master.py repair
```

The interpreter and relative script argument match the narrowly approved command
prefix. The script accepts fixed subcommands, not arbitrary shell commands. The
application environment, assurance sidecar, pinned JDK 17 and Catala toolchain
are already installed. Document compilation uses the existing PyMuPDF/XeLaTeX
environment. GPU devices are deliberately hidden for these CPU checks.

The shared allowance remains 500. The first round-13 increment stopped at 320
consumed reservations. The reviewed continuation may reach 400; it has not
created another 500-call allowance. Every failed or interrupted reservation
remains charged. `completion-checkpoint.json` binds the previous STR evidence.
Do not edit or delete a journal, quota ledger, failed response or checkpoint to
make a run continue.

The authoritative reviewed execution journal is
`artifacts/interpretation/round13/execution-reviewed/journal.json`. The earlier
`execution/` directory retains the initial repaired attempts; the still earlier
`preliminary-retained/` records were rejected as insufficient. The three-attempt
phase limit counts both repaired execution journals. A completed phase is reused
only when its inputs, dependencies and all recorded output files still validate.

## What the program executes

P0 verifies the round-12 starting evidence and runs focused fault checks. P1
anchors the current margin Code provision, the earlier e-IP circular and three
English/Chinese STR provision pairs. P2 checks twelve retained PDF pages against
located development annotations; only the evidenced footer relocations are
resolved. P3 validates the complete claim and reading inventories, requests two
control assignments, splits invalid routing and fidelity responses, and retains
all required, excluded and unresolved comparisons. P4 builds and runs the typed
STR and e-IP Java examples, cvc5 comparisons, the STR Catala build, event replay
and authority-change invalidation. P5 runs the full regression suite and builds
the unified monograph while checking preservation and citation bindings.

Before each phase, `next-phase-plan.json` records commands, input hashes,
substantive findings from earlier phases and remaining reservations. Integrity
failures stop dependent work. A legally unresolved proposal does not stop the
independent engineering checks. The repair record explains each observed harness
failure and the change made before retrying it.

## Reading the outputs correctly

After execution, start with `evaluation.json`, `final-report.json`, and the
written `execution-result.md` in this directory. The phase summaries point to
the full evidence and its hashes. `delivery-manifest.json` binds the retained
round-13 files. Each phase also has its exact commands, environment, Git commit,
wall time and start/end quota counts.

`COMPLETE` in a comparison ledger means every required pair has a recorded
outcome. A deterministic inability to encode a candidate is an explicit
`NOT_ESTABLISHED` outcome, not a model examination of executable meaning. The
result note must report these separately. `ENTAILED` is a source-checking model's
judgment with validated quotations; quotation validation does not prove legal
entailment. An excluded pair is backed by two proposed question assignments, not
a proof of legal irrelevance. Concern counts include repeated occurrences across
batches and must not be read as counts of independent errors.

The 48 Java development cases test the supplied rule meanings and stipulated
facts. They cannot validate the full English interpretation. The old five STR
references remain visible: four align with the certificate-applicability
question, while urgent blackout contact is a different question. These mappings
were authored after generation and are not an independent unseen benchmark.

The monograph's canonical PDF remains `docs/monograph/monograph.pdf`; its copy at
`docs/proposal/proposal.pdf` must be identical. Earlier chapter content, equations
and references are preserved. Author inspection and automated rendering checks
remain distinct from target-reader acceptance.

## Resume and next work

Allow an active run to finish before invoking another `live` or `repair` command;
the model journals prevent concurrent writers. A quota refusal is not a reason
to reset counters. If a continuation is justified, first freeze its remaining
work and resources in a new reviewed plan, reuse only verified exact responses,
and continue charging the existing shared allowance.

The next research work is specified in `docs/plans/assurance-after-round13.md`.
It targets particular unencoded controls, scope disagreements and source
differences. Independent legal accuracy, empirical error correlation across
model families and observed reviewer effort remain separate evaluations. Actual
bank integration is deferred at the user's direction.
