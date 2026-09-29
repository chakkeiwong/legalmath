# Operating the round-15 master

Run from `/home/chakwong/python/legalmath` with the project environment:

```text
/home/chakwong/python/legalmath/.venv/bin/python scripts/run_assurance_round15.py audit
/home/chakwong/python/legalmath/.venv/bin/python scripts/run_assurance_round15.py execute
/home/chakwong/python/legalmath/.venv/bin/python scripts/run_assurance_round15.py status
```

`execute --through P1` stops at a recorded checkpoint. A subsequent `execute`
replays accepted phases through the immutable journal and continues. `repair`
uses the same journal and resource limits; it does not reset calls or erase a
failed attempt. A changed source or corrupted result requires investigation,
not a new directory chosen to evade the limit.

The trusted command prefix is the full project Python path followed by
`scripts/run_assurance_round15.py`. The live provider and the two fixed public
SFC downloads require trusted network execution. Offline tests and result
inspection do not require a model call. No credential, private bank record,
external message, production deployment or transaction is part of this master.

Read `artifacts/interpretation/round15/phase-results.json` for accepted phase
receipts and `execution/journal.json` for every attempt. The fidelity work is
under `fidelity/`: `pair-manifest.json` preserves the 231 executable restored
pairs, `result.json` also retains the one unencoded pair, and `batches.json` records the exact executable
universe, and `model/model/journal.json` binds fresh requests and responses.
Historical CONTEXT rows remain scheduled. A completed response is counted once;
cached reuse is never a new independent observation.

Every schema/reference failure receives at most one structured repair. A still
invalid batch may split once, subject to the shared 500-call ceiling and this
round's thirteen-action cap. A transport failure stops further live requests.
A stopped live investigation does not prevent child verification, source
acquisition, PDF packet construction or numerical checks. The final report
must still disclose every pending pair.

Each deterministic phase keeps its own files in the selected `execution/action`
directory. Resolve that directory from its receipt, not from an assumed action
number. P2 retains child builds, probes and backend results. P3 retains original
PDFs, request receipts and extracted text. P4 supplies `review/index.html` and
PNG context crops. P5 contains unchanged and mutated Java policies, exact-ratio
cases and their comparison records.

`ENTAILED` is a model judgment with quotations, not a legal proof. A child
conformance pass does not discharge its parent. A retrieved appendix does not
establish that every incorporated provision has been interpreted. A page footer
resolution removes only the precisely located layout discrepancy. A wrong
asset classification can still change an otherwise correct numerical decision.
The generated JARs remain development artifacts with `release_eligible: false`.

After the completed run and document revision, use
`.venv/bin/python scripts/review_assurance_round15.py` to verify delivery and
`run_assurance_round15.py status` to inspect the retained phase status. The
historical execution's `audit` checks the then-current round-14 external files;
those document paths are superseded by the new book. Their exact old bytes are
preserved in `round14-external-baseline`, which the delivery verifier checks.
Do not restore the old book merely to make a historical audit pass.

The delivery review also repaired a shared-list defect in the summary writer.
The immutable phase results did not change. `summary-repair.json` records the
exact reconstruction and the executing/repaired code hashes; the executing
files remain under `pre-summary-repair`. The final regression checks the repaired
code. Additional interpretation requires a new reviewed continuation and new
bounded authorization; `repair` cannot replenish the exhausted allowance.

The common-error study should reuse the existing four-arm evaluation machinery:
`legalmath.interpretation.assurance.evaluation` and `declared_evaluation`.
Admissible reference judgments, source/provision splits, an explicit error and
coverage estimand, adequate resources, and a separately configured second
family must be frozen before it runs. Public worked examples and targeted
judgments can supply reference evidence. A comprehensive consultancy is not an
automatic prerequisite for each rule, and same-model labels cannot substitute
for that evidence.
