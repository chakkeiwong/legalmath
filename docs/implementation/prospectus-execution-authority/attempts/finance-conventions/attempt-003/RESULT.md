# Danske 30/360: exact optional arithmetic passes; finance delivery remains open

The missing BondBasis convention was our implementation gap. Adding the
explicit THIRTY_360_BOND_BASIS name to fixed-coupon.v1 and the existing QuantLib
sidecar now gives 1/4 and DKK12,750 through both actual direct and selected-term
P1–P5/final consumers. The same first period on a separately declared hypothetical
DKK1.25 billion principal gives DKK15,937,500. These are conditional calculations,
not findings that a holder is entitled to those payments.

The frozen pre-edit kernel rejects the name. The retained direct baseline reports
UNSUPPORTED; the selected baseline raises the retained unsupported-convention
error in P5. Current positive consumers retain all five products and their final
answers. Q1–Q4, source graphs, and matched P2–P4 payloads remain unchanged. Both
routes preserve partial construction, unknown actual events, and false independent
legal acceptance/transaction permission. The selected v1 route returns no invented
schedule.

## Why this computes the defined fraction

Final terms p4 names 30/360 and the short period from 25 August through, excluding,
25 November 2026. Base p71(v) defines the target: replace a start day of 31 by 30;
replace an end-exclusive day of 31 by 30 only when the adjusted start day exceeds
29. Otherwise use the stated calendar days, with no February correction. For
valid calendar days, min(start_day,30) is exactly that first rule. Its result is at
most 30, so the second condition is equivalent to adjusted_start_day == 30. The
implemented branch therefore substitutes the defined endpoints into exactly
[360(Y2−Y1)+30(M2−M1)+D2−D1]/360. For the named period this is 90/360=1/4;
1,000,000 × 0.051 × 1/4 = 12,750, without a rounding difference.

The retained independent literal endpoint table has eleven cases, including leap
February, year boundaries, end31 with start29/30/31, and a positive interval with
zero counted days. All local fractions equal their rational expectations exactly.
The one executed QuantLib1.38 BondBasis comparator agrees on the identical inputs
within the predeclared 1e-12 floating tolerance. It uses neither evaluation-date
state nor a missing-reference fallback. Official v1.38 thirty360.cpp maps
BondBasis/ISMA to ISMA_Impl and implements the same rules.

The actual August–November case alone cannot identify the variant. Manual
inspection of the retained code gives, for 28 February–31 March 2025, BondBasis33,
USA31, European32 and ISDA30 counted days with no termination date specified.
USA checks its end31 condition before adjusting the February start. These other
variants were not executed or admitted; variant-inspection-repaired.json records
the derivation and that boundary explicitly.

## Verification and the retained harness failure

The corrected comparison passes112 checks;197 focused tests pass. Twelve actual
controls retain ambiguous/unsupported aliases, unexpected references, wrong
source, misuse of the regular printed amount, aggregate and no-entitlement
scenarios, stale selected bindings, premise overrides and actual-event claims.
The v2/v3 profiles remain ICMA-only. Legacy ACT/365 Fixed, ACT/360 and ACT/ACT ISDA
match the frozen kernel on all eleven endpoints. Both sealed Shell v2 scenarios
and both forms of v3 direct/selected requests match the frozen kernel exactly.

The initial comparison failed three harness assertions. It included expectation
metadata in a package-input equality check and compared Shell001's older output
schema with the current one. Full frozen/current outputs agreed; only the added
entitlement_basis field differed from Shell001. One reviewed repair now compares
every actual request field, every historical Shell field, and full frozen/current
outputs separately. The failed method/results remain retained. No production
repair, second package call, source refetch or test rerun was used.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | What is not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain optional named-period support | Exact fraction/amount and actual consumers pass | Source/method drift, legacy regressions, changed Q1–Q4 and false promotion checks pass | Source interpretation is development-exposed | Continue distinct source/event and convention work through reviewed authority refinement | Complete finance integration or actual entitlement |
| Attribute missing convention locally | Frozen local branch rejects; mapped package executes and agrees | No package execution or variant mismatch found | Finite endpoint coverage; no package-wide audit | Preserve explicit mapping and unsupported aliases | Fundamental QuantLib defect or package-wide suitability |
| Keep original task incomplete | Original broader obligations remain | Independent interpretation, VP rules and actual events still veto completion | Actual payment mechanics and facts absent | Inspect authority continuation routes after record/refresh | Automatic, independent or production settlement acceptance |

## Remaining limits and post-run review

The actual issue is VP Systems dematerialised book entry (final p6), not a global
or definitive note. Printed DKK51,000 regular and DKK12,750 broken amounts are
expressly for definitive notes. They provide an independent numerical check here;
neither is a v1 amount input or proof of VP entitlement. No maturity, complete
perpetual/floating schedule, cancellation, conversion, principal adjustment,
tax, agency rules or actual Copenhagen/VP payment-day rule has been established.
Quantum1 DKK and one unchanged entitled recipient are explicit numerical
hypotheses, not legal rounding or ownership findings. The source graph uses
complete retained page-text derivatives, with original/text/derivative identities
kept separate; no fresh native PDF extraction is claimed.177 units remain
unresolved in the192-unit graph.

The strongest alternative explanation is a mistaken source-role reading despite
correct arithmetic. Independent interpretation or VP/agency evidence showing a
different applicable basis would overturn its payment relevance. Exact agreement
with the contract formula supports the optional numerical branch; package
agreement alone does not resolve that legal question. The weakest evidence is
actual entitlement and form-specific payment mechanics. The initial failure
invalidated three harness assertions, not the candidate or research direction;
the corrected comparison removes that defect without lowering the criteria.

This package uses the original revision102 admission and the single reviewed
local repair. Eight bounded product/control stages, one focused test stage, one
QuantLib call and one official-source retrieval are retained; none is reset.
run-manifest.json records available commands, environments, identities, wall
times, output paths and the limits of shell-command provenance. Broader finance,+automatic capability and independent acceptance remain false.
