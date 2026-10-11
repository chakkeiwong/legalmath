# Coupon anchor preservation: admitted execution

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

## Consumer trace and version decisions

Code inspection located a second necessary routing change:
`financial_profiles.assess` recognizes only `fixed-coupon.v1`. A kernel-only
repair would therefore fail the direct scenario service path. Include it in
the new-profile tests as well as `contract_terms.scenario` and P5. The request
container already admits `term_interpretations` and `contract_calculation`;
those outer fields need no unrelated refactor.

Use `coupon_anchor` as the explicit ISO date. The proposed new direct profile
is `fixed-coupon.v2`, limited here to anchored ACT/ACT ICMA calculations.
Its required evidence includes `coupon_anchor`. Old profile v1 rejects that
additional field and retains its original endpoint-based validation. For
source-selected terms, introduce `selected-coupon-terms.v3` with all current
v2 terms plus the anchor. Its admitted representation is separately versioned.
The anchor uses the existing deterministic `english-date` rule; merely calling
it a reviewed convention cannot bypass a mismatched source date. Require the
new calculation profile when the new term set is supplied, and reject a
calculation-premise override even if it happens to equal the selected value.

The regular schedule's optional explicit anchor selects the new lattice; its
omission retains the historical accrual-start anchor. Check both month spacing
and the actual start day before continuing the schedule. A new accrual period
starting on 29 February can legitimately use the original 30-August anchor,
but 29 August and 31 August are different supplied conventions. Do not infer
which is legally required from a numerical match. Direct reference periods
and selected regular schedules must share the rule without broadening full
selected-contract support to first/final stubs.

The current rounding fixture exercises annual 1-January dates and would miss
the reproduced defect. Retain it as compatibility evidence and add a distinct
source-bound synthetic 30-August case. The installed checker must execute
both direct and selected-term paths and compare exact fraction, due dates,
payments and source identity, alongside the existing Compass/BASF cases.
These synthetic inputs test implementation; they cannot supply missing real
instrument conventions or actual ownership/entitlement facts.

Follow-up skeptical audit: PASS for the design. It now names both service
routes, the source translation and the version boundary. Final admission and
all actual execution remain pending the preceding substantive package.

## Additional pre-implementation review

The inspected service routes are `financial_product` to
`financial_profiles.assess` for a direct scenario, and `financial_product` to
`contract_terms.scenario` for selected terms. The latter must retain the anchor
in `contract_terms` and the calculation's `source_evidence`. Use
`admitted-coupon-terms.v2` only for the new selected v3 packet. Old admitted v1
and new admitted v2 require their respective fixed-coupon v1/v2 profiles; a
hash-valid packet must not erase this pairing.

The new direct profile also checks the anchor's quoted English date against
the declared ISO value. Its hypothetical status does not justify unrelated
evidence for that value. Selected terms additionally require an operative
occurrence and the existing deterministic `english-date` translation. Direct
premises remain hypothetical and do not establish selected-contract authority.

A second false-pass risk is accepting an interval labelled REGULAR merely
because its fraction happens to equal one coupon: an interval crossing two
equal-length periods can do that. In the new profile, require a regular
accrual to be exactly one lattice period; a first stub ends at a lattice date
and a final stub starts at one. Keep the existing explicit short/long fraction
check. These are consistency checks for supplied hypothetical classifications;
the complete selected-contract path remains regular-only. Old v1 behavior is
preserved. This revision prevents a stronger classification claim than the
new checks establish.

Independent arithmetic examples use the manually listed lattice
30-Aug-2023, 29-Feb-2024, 30-Aug-2024, 28-Feb-2025, with respective lengths
183, 183 and 182 days. A short first period 30-Dec-2023 to 29-Feb-2024 has
61 days and fraction 61/366 = 1/6. A long first period 30-Nov-2023 to
30-Aug-2024 has fraction 91/366 + 183/366 = 137/183. A short final period
29-Feb-2024 to 30-May-2024 has fraction 91/366. A long final period
29-Feb-2024 to 30-Nov-2024 has fraction 183/366 + 92/364 = 137/182.
Expected dates and these fractions must appear independently in the tests;
production date helpers must not generate them. A further date-only check
should verify the day enumerations before using this table as an oracle.

Skeptical trace review: the missing direct-service route, version pairing,
anchor evidence and possible false REGULAR classification are now explicit.
These changes address local interfaces and conditional arithmetic. No package
trial or real-instrument convention decision is inferred. Final execution
admission still follows completion and commit of the status/pledge package.

## Isolated candidate preparation

While the pledge validations run, candidate files may be prepared under
`/tmp/prospectus-coupon-anchor-candidate/`. This is a reviewed scheduling
revision: the reproduced finance defect and its three production consumers
are independent of the pledge interpretations. Snapshot the current finance
files and installation wiring, name baseline commit `0705bb22a`, and bind
their hashes before drafting. Do not edit any bound worktree source, test,
packet or pledge execution-plan file. Integration must reject a changed
snapshot and await the committed, verified pledge result. No candidate may
be reported as integrated or validated from this preparation alone.

Staging audit: PASS. It preserves the active method and separates proposed
code from executed evidence. The reviewed mechanism, explicit versioning,
independent dates, source translations, compatibility constraints and finite
execution budgets above remain the admission criteria. Integration and
validation of the actual worktree still require final admission against the
completed predecessor.

A single bounded candidate diagnostic may also run in a separate temporary
copy of the source, with the staged files overlaid and imports verified there.
Use only the new deterministic test file, no retained large prospectus runs,
no network, no GPU and a 120-second limit. Its question is whether the draft
computes the independently listed dates/fractions and enforces its proposed
service boundaries. The comparator is the retained August/February failure;
the pass criterion is the listed exact examples and rejection controls.
Wrong imports, changed worktree/candidate hashes, a missing diagnostic or a
bound overrun veto the run. Test counts and runtime are explanatory only.
Retain the command, copied-source identity, baseline commit, environment,
actual results and elapsed time under a separate candidate-diagnostic attempt.
A pass is preliminary implementation evidence, not completed integration,
installed behavior, a real-instrument convention or legal acceptance.

This diagnostic is justified before the predecessor finishes because the
finance boundary is independent and the temporary copy cannot change the
active validation method. A failure triggers a documented candidate repair;
an unchanged failed method is not repeated. The full worktree and installed
checks still follow final admission. Reviewed staging-diagnostic audit: PASS
under these exact isolation, comparison and finite-resource conditions.

## Regression scheduling review for final integration

The preceding packages ran the entire successor suite and then reran the
long R4 subset to obtain current phase receipts. For this repair, run each
required phase once and use a retained collection inventory to execute the
remaining tests separately. This avoids repeating the same lengthy BASF
controls while still requiring every declared test and all current receipts.
Do not alter the closure controller or manufacture phase execution evidence.

Before implementation, the exact test universe is the successor directory
plus `tests/prospectus/test_closure_mechanisms.py`, extended by this candidate's
new file. After integration, retain a collection of every node identity and
the current method. Run R0–R7 in dependency order through the existing closure
dispatcher, which records their actual test output. Map each JUnit case to
exactly one collected node; an ambiguous or unmapped case vetoes coverage.
Run every as-yet-uncovered node through `closure check` using positional node
arguments. Include R8's small unit tests in that remainder, then update the
actual gap/attribution record and run R8 to validate the changed attribution.
Assert that the union of successful, current cases equals the frozen universe,
with no failures, errors or skips. Retain the inventory, commands, mappings,
JUnit hashes and unique denominator in a coverage index. Report this as
partitioned regression, not as a single aggregate process.

This schedule changes process grouping, which could conceal a test-order
dependency. The new date helper is pure; profile routing adds no global mutable
state; fixtures create separate requests; and tests do not mutate shared module
state. The installed exercise additionally runs old and new finance cases,
Compass and BASF in one interpreter sequence and compares fresh, relocated
and restored answers. These facts justify the partition for this bounded
change. Evidence of state leakage, missing coverage or incompatible grouping
requires a diagnosed revision, including a full aggregate if needed.

Use the existing phase bounds (R4 4,500 seconds, others 600), 600 seconds for
the remainder, and the installed 1,200-second/200-MB limit. Freeze bound source
and plans before these runs; update only unbound actual-result records between
phases. A tested phase is not repeated merely because another capability is
partial. Skeptical scheduling audit: PASS for exact coverage plus current
phase evidence, with process-grouping limitations explicitly retained.

## Final execution admission

The completed status/pledge comparator is committed as `e814e99ad6db96e9530bdb318a3c630d36c85fdb`. Its nine
phase receipts are current, valid engineering PASS; consumer and installed
manifests were freshly verified without rerunning their passing checks.
The protected coupon candidate and its exact source snapshot match the
admitted worktree. Integration copied precisely the nine reviewed files.
`coupon-anchor/execution-admission.json` retains the predecessor receipts,
candidate identities, actual baseline and scope.

The isolated 59-control diagnostic is preliminary, historical evidence under
its recorded plan. The later regression-scheduling revision changes execution
grouping, not its tested implementation. Now verify the actual worktree with
the new coupon file and the existing finance controls under 120 seconds,
then run the installed application with `--basf-status-pledge --coupon-anchor`
under the existing 1,200-second/200-MB limit. Complete the partitioned
regression and serial phase refresh described above. Retain every actual
result and stop only for the declared validity or resource vetoes.

Skeptical admission audit: PASS. Original-anchor evidence, both service routes,
profile pairing, actual date/classification boundaries, independent fractions,
legacy restrictions and conditional entitlement are checked in the candidate.
Worktree and installed execution remain required. Neither independent legal
acceptance nor real-instrument convention support is inferred.
