# Conversion input validation: repaired local parser and admission rules

The declared conversion inputs now reject malformed quantities and blank holder
identities on both active and inactive branches. The three complete original
financial case records are unchanged. Eight valid controls agree with a separate
decimal price calculation and exact integer share allocation; 92 malformed
controls return UNSUPPORTED. Two retained final reports demonstrate the existing
secondary financial_cases route. Unrelated carrier questions remain unchanged.

This is entitlement006 under revision226. Failed005 remains a sealed REJECT: its
12 zero-denominator exceptions exposed a second parser that the earlier fixed
coupon repair did not cover. The defect is our inconsistent validation across
code paths. No external package is implicated by this result.

## Checked changes and evidence

The existing active conversion kernels require positive price and FX inputs.
financial_profiles now applies those same six requirements before selecting a
branch. whole_shares rejects whitespace-only holder and registration identities
while retaining nonblank spelling and grouping. master_mechanisms.amount now
normalizes Fraction's zero-denominator exception to ValueError. Valid exact
values and the existing unsigned domain are preserved; no fallback value is
introduced. The focused tests retain all failed005 cases and add direct parser,
trigger-rate, holding and closing-price denominator controls.

The tests stage passed 353 tests with zero failures, errors or skips in
2.927765104919672 seconds. The consumers stage passed in 1.7729572812095284 seconds.
The preparation cost of 0.05694426316767931 seconds and failed005 test cost of
3.1215953528881073 seconds remain charged to the same 300-second budget. Final
sealing time and cumulative storage are retained in run-manifest.json.
The original v1 runner, failed005 outputs and their hashes are authenticated
before each v2 stage. All production source hashes are pinned, with changes
limited to the three reviewed files relative to the retained preparation.

Original PDF and extraction hashes remain checked. The BBVA price control gives
501/100 and three whole shares for aggregate amount20; the SEB control gives
price3 and three whole shares for aggregate amount10. Deutsche's original
write-down result remains unchanged. Synthetic holder premises remain explicit.
The injected original validator again accepts a zero input on an inactive
branch, demonstrating that the control detects the reproduced pre-repair defect.

## Decision

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain this local repair; record partial entitlement progress | Three complete original records equal; eight valid controls agree;92 malformed controls refuse; report routes preserve results | No valid-result, source-binding or adverse-control veto fired | Original interpretation, broader entitlement domains, settlement and installed currentness remain open | Refresh the authority; continue the next substantive route; revalidate installation after the production batch stabilizes | Whole entitlement task or whole build complete; actual ownership/conversion/settlement; package defect |

The inputs, complete outputs, independent checks, test XML and two report records
are preserved here. The runner records the actual commands, inherited git commit,
interpreter, sources, methods, stage times and CPU-only environment. Counts and
runtime describe this finite deterministic coverage; they do not certify broad
legal or financial correctness.

## Post-run skeptical review

The strongest alternative explanation is shared dependence between validation
and the finite cases. Separate arithmetic and the known-bad validator control
address calculation agreement and regression sensitivity, but do not prove that
the original sources have been interpreted completely. The report checks use
the same secondary financial_cases route as jobs.p5, not direct original
BBVA/SEB P1-to-P6 primary-Q5 integration. A changed valid complete record, accepted
malformed premise or lost original binding would overturn this local result.
Current-source checks do not renew stale installed evidence.
