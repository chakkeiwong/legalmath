# Five additional SFC circulars

Development integration corpus for **23EC49, 24EC16, 24EC50, 24EC57 and
26EC23**, with 25EC48 as a separate announcement-only negative control. The
original 23EC35 and 23EC46 examples remain separate regressions.

`circulars.json` is the source-written oracle: each case states the selected
meaning, explicit fact definitions, literal expected outcomes/rationales,
remaining legal questions, and two deliberately incorrect readings.
`source-freeze.json` binds its bytes and the official source snapshots.
`source-text/` retains the exact derivatives used for source spans; the raw JSON
and MMF appendix PDF live under `.localresources/sfc/`.

The corpus has 75 named scenarios. It is authored by the same implementing
agent and is **not independent legal adjudication or a held-out translation
benchmark**. The second oracle revision makes Canada's prior settlement regime
an explicit external fact. Its timing relative to execution is disclosed in
the freeze and result note.

The rule builder deliberately lives outside the oracle in
`tests/integration/multi_circular_support.py`. Expected outcomes are literal
scenario data and never calculated by the RuleIR builder or evaluator. Inputs
such as completed calendar months, covered securities, Type 9 discretion,
IPD submission classification and price-deviation thresholds require separate
bank-owned definitions. Synthetic rule/fact validity intervals are test harness
intervals, not inferred legal effective periods. Historical trade/submission
dates are explicit facts. A TRUE response clears only the selected subcondition;
it never authorises a transaction or certifies full compliance.

Run:

```sh
.venv/bin/python -m pytest tests/integration/test_multi_circular_interpretation.py -q
.venv/bin/python scripts/run_multi_circular_integration.py \
  --output /tmp/legalmath-circular-verification-new/report.json
```

Use an empty output directory. A local Java 17 toolchain is required; the runner
accepts `--jdk`. It preserves source packets, candidate and mutant RuleIR/Java,
full execution traces, immutable initial readings, repairs, unresolved reports,
and database export/restore evidence. No model, network request, client data or
real meaning approval is involved.

[Executed results](../../docs/implementation/interpretation-round1/multi-circular-result.md)
explain all five slices, scenarios, limitations, prior attempts and next steps.
