# Danske's defined 30/360 first-period calculation

Continue the original finance-conventions task, not the exhausted BASF initial-agent
repair. Revision101 has empty dispatch, but its continuation inspector identifies
local preparation and review routes. Finance attempts001 and002 remain sealed:
Shell's anchored ICMA and distinct initial amounts already work. This package
repairs a different, reproduced unsupported convention under the same obligations.

## Research intent and evidence contract

Question: does the source-defined Danske 30/360 arithmetic survive the existing
direct and selected-term financial consumers for one explicitly hypothetical first
period? The candidate is the optional unambiguous convention name
THIRTY_360_BOND_BASIS in fixed-coupon.v1. No generic 30/360 alias is admitted. V2/V3
remain ICMA-only. No new coupon profile or maturity is needed.

Baseline: freeze the present fixed_coupon.py and the sidecar before editing. Run
the same Danske scenario through the frozen kernel and actual consumer before the
repair: unsupported convention is the expected failure. Post-repair direct and
selected-coupon-terms.v1 consumers use identical dates, rate, principal, numerical
rounding, events and source occurrences. Compare Q1–Q4 and source/construction
payloads under matched requests. Preserve existing supported-convention behavior
against the frozen kernel, including the two sealed Shell scenarios.

Primary engineering pass: exact 90/360 = 1/4 and DKK12,750 on a hypothetical
DKK1,000,000 principal at 5.100%, for 25 August through 25 November2026 (end
exclusive). A separately declared hypothetical DKK1,250,000,000 aggregate yields
DKK15,937,500. This aggregate is a numerical scenario, not proof of a global note
or beneficial ownership. The published DKK12,750 is an independent cross-check,
not an amount consumed by v1. The published regular DKK51,000 is not substituted
for the broken amount. A complete perpetual or floating schedule is not computed.

The source formula, a separate exact hand-declared control table, and QuantLib1.38
BondBasis on identical endpoints must agree. Floating output tolerance is 1e-12
years, only for package agreement; rational local expectations require equality.
Include Jan31, end31 with start below/above30, February-end, leap February-end,
year boundary and a positive interval with zero 30/360 day count. Actual first
coupon agreement cannot distinguish variants: retain at least one endpoint where
USA/European/ISDA differ, without adding those variants to our supported kernel.
Read and retain official QuantLib v1.38 thirty360.cpp and inspect its ISMA/BondBasis
endpoint implementation and variant definitions before interpreting agreement.

Run vetoes: source/hash drift, wrong baseline or imports, missing actual consumer
artifacts, failed rational/comparator checks, unexpected supported legacy changes,
changed Q1–Q4 on matched inputs, or false entitlement/settlement promotion.
Missing independent source interpretation, VP rules/agent agreement, actual events
and broader conventions veto promotion and completion, not this bounded repair.
Runtime and test totals are explanatory only. Expected unsupported convention
aliases, unexpected references/anchors, stale selected terms and actual-event
claims are adverse controls. A failed candidate triggers the one bounded local
repair only if its cause is understood; no unchanged rerun or automatic admission.

## Source and assumption audit

Use the retained classification-holdout-v2 originals and complete page-text JSON:
Danske final21August2026 and base14August2026. Verify their manifest hashes.
Final p3 supplies DKK, issue/calculation amounts and incorporation; p4 supplies
dates, fixed rate, annual November25 coupon, short first period, definitive-form
regular/broken amounts and 30/360; p6 selects VP Systems and Copenhagen. Base p71
defines D1=min(start day,30), D2=30 only if end-exclusive day is31 and D1>29.
There is no February-end correction. Base pp71–72 define other variants separately.
Base pp55–57,66,92–93,109–110,127 explain form, principal adjustment, conditional
interest, cancellation/conversion and VP/fiscal payment rules. Retain exact contexts.

| Choice | Provenance and justification | Failure mode / early diagnostic | Status |
| --- | --- | --- | --- |
| BondBasis endpoint rules | Base p71, checked against official package code | A generic label selects USA/European; discriminating endpoint table | Source interpretation awaiting independent review |
| 5.100%, Aug25–Nov25, annual | Final p4 | Wrong floating phase or inclusivity; exact quoted anchors | Source-bound development reading |
| Unchanged principal / hypothetical recipient | Separate explicit premise text | AT1 conversion/reduction or lack of entitlement; retain assumption in final evidence | Hypothesis only |
| Unadjusted Nov25 and ordered intraday events | Separate hypothetical payment-day premise | Copenhagen/VP calendar not actually established; no actual-date conclusion | Convenience for named-period arithmetic |
| Quantum1 DKK / HALF_UP / one recipient | Explicit numerical premise, integral amounts are unchanged | Could imply actual DKK/VP rounding; compare unrounded amount and retain qualification | Convenience, not legal currency default |
| EOM false, no reference schedule | No date lattice is generated; exact endpoints supplied | Accidental ICMA references or anchor; reject controls | Reviewed numerical scope bound |
| Complete retained page text as P1 input | Existing pinned PDF extraction, every original page preserved as a form-feed page | Derivative text mistaken for fresh native evidence; retain original/text/derivative identities | Historical text input, not new extraction validation |
| QuantLib1.38 | Existing isolated CPU sidecar | Wrong variant/version; official source + metadata + variant controls | Independent numerical comparator only |

No paper-based scientific or legal claim is made here. Official implementation
inspection supports package mapping; the controlling contract defines our target.
All sources are development-exposed. Independent legal acceptance remains false.

## Reviewed execution

1. Explicitly extend only finance-conventions' cumulative admission maximum2→3,
   retaining001/002 and the59 obligations/44 tasks. Freeze pre-edit methods in003.
2. Build complete-page text derivatives from the pinned retained text, retaining
   original/text/page identities. Use ordinary text P1 intake; no ad hoc source
   graph injection or fake original-PDF extraction. Select relevant contexts only;
   leave all other source units unresolved. Retain exact source/premise distinction.
3. Reproduce the frozen unsupported result. Obtain and read the single official
   source file. Implement only the explicit endpoint convention and comparator
   mapping. Meaningful tests cover discriminating endpoints and adverse consumers.
4. Freeze current methods, execute source-bound direct/selected consumers and the
   same-input package comparison. Retain actual P1–P5 and final answers, checks,
   environment, git identity, command, wall time and data hashes. Check no-entitled
   and unsupported alias controls without inferring cancellation semantics.
5. Seal RESULT.md, result.json and outputs.json with a decision table, strongest
   alternative explanation, package-vs-local attribution and exact remaining gaps.
   Record and refresh. Review independent continuation routes; no checkpoint stop.

Each command uses a one-second tool yield and at most120seconds; native child
timeouts are unnecessary because no new extraction, rendering or OCR is planned.
At most one20second HTTP retrieval (official source), one30second QuantLib run,
eight120second product/control stages and one120second focused test stage. New
files are under60MB. Historical attempts and all their counts remain retained;
one additional admission is explicit, not a reset. No installation, model/GPU,
external messaging, branch change or approval-list modification is needed. Pin
imports to this worktree and hide GPUs before importing product/package modules.
One understood local repair maximum, without extending deadlines/call caps.

## Skeptical audit: PASS for the narrowed package

The first draft would have called a perpetual AT1 a fixed-maturity bond, used
definitive printed amounts for VP notes, and treated an actual-case match as proof
of a 30/360 variant. Those are material flaws; this plan removes each inference.
V1 selected terms deliberately omit a schedule and distinct published broken
amount. Retain these interface gaps explicitly instead of reporting full finance
integration. Complete source-page derivatives avoid repeating native extraction
for an arithmetic question, while their provenance and incomplete coverage remain
visible. Correct arithmetic can still rest on a mistaken source-role reading;
independent reading, VP procedures and event facts remain necessary for payment.
No test total, successful command or QuantLib match becomes legal acceptance.
This repair addresses our unsupported convention, not a demonstrated package bug.
