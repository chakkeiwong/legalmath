# Coupon anchor preservation: reviewed design pending execution admission

This follows the admitted status/negative-pledge package. It does not modify
the active amount/holder method or authorize concurrent changes to it. Final
admission must name the committed predecessor and verify its retained results.
The reproduced blocker and its immutable input/method record are in
`docs/implementation/prospectus-integration-closure/finance-anchor-diagnostic/`.

## Question and evidence contract

Can a supplied, source-bound coupon anchor reach both the schedule generator
and ICMA reference-period validator without losing the original day after
February? The comparator is the existing 30-August-2023 semiannual regular
schedule, EOM false: 29-February-2024, then 30-August-2024. The existing
validator rejects its second period and their union. For each full regular
reference period, the conditional fraction is exactly days/(2*days)=1/2;
their union is one. These are interface and arithmetic expectations, not a
determination of a real prospectus's convention.

| Role | Criterion |
|---|---|
| Primary engineering pass | The identical declared schedule admits exact regular and short/long-stub fractions through the kernel, selected terms, P5 and installed CLI |
| Primary compatibility pass | Historical fixed-coupon.v1 requests and selected-coupon-terms.v1/v2 retain their meaning and limitations; new anchor semantics require explicit new versions |
| Promotion veto | Inferring a day from a clamped endpoint, silently turning on EOM, accepting inconsistent reference endpoints, replacing an admitted anchor with a calculation premise, or reporting actual entitlement |
| Continuation veto | Corrupt comparator or source, missing diagnostics, unexplained method/runtime drift, or exhausted admitted time/storage bound |
| Repair trigger | Reproduced local version/admission/date-lattice/consumer defect; retain failure and review a bounded repair |
| Explanatory | Runtime, test count, compatibility examples and optional numerical agreement |

No general instrument support, real payable amount, full settlement, legal
correctness, default promotion or package failure follows from an engineering
pass. Missing real convention/entitlement evidence leaves those questions
conditional; it does not prevent fixing the reproduced local mismatch.

## Mechanism and source boundaries

Use one small pure date helper for an explicitly anchored coupon lattice.
From date A and integer month offset m, retain A's day, temporarily clamping
it to the destination month length. With declared EOM true and A itself at
month end, use destination month end. Frequency supplies the integer month
spacing. Both endpoints of each ICMA reference period must lie on this same
lattice, separated by exactly one coupon step. Adjacent reference periods
remain contiguous. Do not recover a missing anchor from any endpoint.

Keep the legacy validator path for requests without the new version. Introduce
an explicit anchor field in a new fixed-coupon profile, with required source
evidence and a matching new selected-term version. Admit an anchor date only
from deterministic date translation of its exact selected occurrence. A
reviewed-convention label cannot supply a fabricated date. The calculator's
premises cannot override selected terms. The anchor must reach the output's
term/source evidence and be protected by the normal source/currentness checks.

The regular schedule also uses this helper. An original anchor may precede
the requested accrual period: require that accrual start is on the lattice
before generating later coupons. Do not silently expand the existing complete
selected-term profile to arbitrary stub schedules. The explicit hypothetical
coupon profile can exercise reference fractions for declared short/long first
and final periods while full real-contract schedule support remains separate.

## Smallest discriminating checks and execution order

1. Verify the committed predecessor and diagnostic hashes; inspect current
   profile/schema consumers and record final admission before implementation.
2. Implement explicit versioned anchor admission and the shared date rule.
   Check the original 30th-day case before broadening. The legacy profile
   must keep its recorded behavior; the new profile must produce 1/2 and one.
3. Test independently listed dates for 28/29/30/31 anchors, leap/nonleap
   February, annual/semiannual/quarterly spacing and EOM true/false. Test
   wrong month, wrong day, wrong frequency, gaps/overlaps, malformed anchor,
   unavailable source, excluded source and field/profile mismatches.
4. Check short/long first/final fractions by independent overlap-day
   enumerations against manually listed quasi-coupon dates. Do not use the
   production date helper to generate expected reference dates. Preserve
   exact rational rounding/aggregation and hypothetical-entitlement limits.
5. Exercise the new selected-term request through real service/P5 and a fresh,
   relocated and offline-restored installed CLI. Compare full result/source
   identities, including a matched changed/missing anchor rejection.
6. Retain focused/consumer/installed evidence; run only justified regression
   and affected phase checks under measured bounds. Update the gap register,
   attribution and next task from actual outcomes. Continue available work.

## Assumptions, resources and skeptical audit

| Choice | Provenance/status | Risk | Earliest check |
|---|---|---|---|
| Original day survives a short month | Existing regular-schedule fixture; regression baseline | Mistakenly presented as a universal financial convention | Preserve explicit profile and inspect date sequence |
| Anchor is supplied and source-bound | Proposed mechanism | Endpoint inference silently changes the instrument | Missing and contradictory anchor controls |
| EOM behavior | Existing schedule implementation; bounded compatibility target | Changing 30 August to 31 August | Paired explicit EOM controls |
| Exact ICMA fractions | Existing overlap-day formula; conditional arithmetic | Right fraction on wrong schedule | Independently listed dates before arithmetic |
| New version | Existing migration policy | Historical replay changes meaning | Reject new fields in old profiles; compare legacy output |
| CPU/offline runtime | Existing .venv and retained wheels | Environment mismatch | Import identity and method hashes |

Provisional budgets: 30 seconds for the initial date diagnostic, 120 seconds
for pure date/admission tests, 600 seconds for a small real service diagnostic,
and the existing installed 1,200-second/200-MB limit. Review measured execution
before the combined suite and phase refresh; do not inherit the preceding R4
bound as a numerical-quality criterion. New repair evidence is capped at 30 MB
outside the separately bounded installed evidence. At most three attempts per
unchanged method; no unchanged failed attempt is rerun without a recorded
diagnosis. No installation, network, model or GPU work is planned.

Skeptical design audit: PASS with final execution admission pending. It targets
the reproduced interface, uses the strongest existing month-end case, preserves
historical versions and exposes the unsupported real-instrument inference.
The strongest false-pass risk is a shared date-helper mistake: independent
date lists and hand-derived overlap fractions are therefore required. A
QuantLib match would be a secondary implementation comparison only. ACTUS/CDM
are not invoked and cannot be blamed for this failure. Actual source-backed
conventions and entitlement events still need separate evidence.

Retain an execution note and manifest naming the baseline commit, exact
commands, imported methods, environment, CPU status, sources, deterministic
seed status, elapsed time, bounds and result paths. Separate engineering
correctness, numerical validity and legal interpretation in the result.
