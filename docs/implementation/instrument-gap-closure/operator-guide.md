# Run and inspect the UBS increment

From the repository root:

```bash
.venv/bin/python scripts/run_instrument_gap_closure.py --phase all
```

The runner reserves immutable attempts, checks source/method/tool identities,
requires accepted unchanged predecessors, and writes `next-phase-plan.json`
after each phase. Identical successful results are reused only after checking
every retained output hash. Four attempts per phase are allowed. A failure
requires a causal repair, a focused reproducer and an explicit note, for example:

```bash
.venv/bin/python scripts/run_instrument_gap_closure.py --phase I3 --repair-note 'Describe the actual cause, repair and successful focused reproducer'
```

A changed implementation also requires refreshed earlier phases; changing the
output directory is not a repair. Historical eligibility/capacity/live studies
are separate and must not be reset. This program makes no live interpretation
calls and uses the installed CPU-only Python, JDK, Catala and Lean environments.

`I0` retains the source dossier and a rendered image of the printed formula.
`I1` checks event/calendars; `I2` records arithmetic branch coverage. `I3`
contains independent equations, both compiled targets, the actual-document
report and labelled hypothetical cases. `I4` runs affected regression, builds
the monograph, companion and guide, and freezes the method for future
observations. Rendered-page review is recorded separately after the build.

The callable entry point is
`legalmath.prospectus.instrument_investigation.investigate(request, store, root)`.
`instrument_cases.request` prepares a qualified public-source request. It does
not supply actual private facts. A request binds the original joined request,
the source dossier and an optional scenario by content hashes. A scenario must
declare `HYPOTHETICAL` or `SOURCE_DEPENDENT_PROPOSAL`; neither value asserts
legal truth. Publications and calendars are retrieved from retained bytes.
`revalidate` recomputes the complete receipt and rejects changed evidence.

Inspect the outer `decision`, `current_applicability`, source issues and all
fourteen obligations together with the individual calculation. A conditional
notice schedule may coexist with a qualified price and unknown settlement.
The outer result cannot authorize a transaction. `KNOWN` within a conditional
calculation means all admissible completions agree under its supplied premises;
the accompanying source-proposal provenance still applies.
