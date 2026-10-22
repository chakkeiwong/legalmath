# Prepare the economic reference for the gated ACTUS trial

This is a continuation of `actus-prerequisites`, under the sole prospectus
authority. It prepares missing trial inputs and an economic comparator; it does
not run ACTUS or satisfy the prerequisite or numerical-comparison task. Preserve
attempts001/002, all59 obligations and44 tasks, and the existing dependency of
`actus-comparison` on accepted prerequisites.

## Question and evidence contract

Can the already nominated synthetic principal-at-maturity case be made precise
enough to expose wrong cash-flow allocation, principal state, currency, chronology
or implicit conventions when an authorized core is eventually supplied? The
baseline is attempt002's `CORE-REQUEST.md`, not a newly chosen bond. It specifies
a lender's GBP1000 outflow on15January2025, annual5% interest, one annual coupon
and principal repayment on15January2026, 30E/360, unadjusted dates, no EOM, fees,
scaling, optionality, FX, default or resets. A1050 terminal total alone is
insufficient: changing interest and principal in opposite directions preserves
that total while computing the wrong obligations.

Prepare an executable economic reference, source/premise provenance, exact
rational arithmetic, complete date-grouped cash flows and before/after principal
and accrued-interest states. At maturity retain separate50 interest and1000
principal legs. The date group is atomic: no ACTUS equal-time event order or
internal state-transition semantics is claimed. No exact package request will be
invented. Retain the13 required attributes and conditional/optional groups from
the pinned official PAM guide; record which semantic values are known, which
additional hypothetical values are explicitly nominated, and which encodings and
behaviors require inspected implementation/tests.

Primary engineering criterion: the explicit economic reference equals the
independent declared table (initial -1000, maturity +50/+1000, final principal
and accrued interest zero), and the comparison rejects altered legs even when
the terminal total is unchanged. Compare every field and state, not only total
payoff. Fixture controls test this comparator; they are never ACTUS observations.
The actual-core execution gate must refuse both the valid synthetic fixture and
every altered fixture while prerequisites remain missing.

Promotion vetoes: absent authorized exact core1.1.0, matching implementation and
official tests, applicable version/use terms, audited enum/timestamp/cycle/state
mapping and equal-time order, genuine core trace or downstream financial answer.
These veto package promotion and completion. They do not veto this explicitly
bounded preparation. Continuation vetoes: source/method/lineage corruption,
missing required preparation diagnostics, accidental core/network/subprocess
execution, changing production files or spending the retained allowance. A
defective comparator triggers at most one understood local repair within the
same command/time/storage envelope; no unchanged rerun is authorized.

Runtime, counts and source-search hits are explanatory only. Even a complete
preparation PASS cannot establish ACTUS conformance, integration, legal
interpretation, entitlement, settlement or a package defect. Preserve actual
commands, environment, git identity, source/method hashes, CPU-only status,
wall time, decision table, result, manifest and controls in the admitted attempt.

## Default and assumption audit

| Choice | Provenance and purpose | Failure mode and early check | Status |
| --- | --- | --- | --- |
| Synthetic plain PAM and its economic amounts/dates | Retained002 request; smallest nominated trial | Substitute a convenient real bond; compare exact retained text and explicit terms | Existing baseline, not a client fact |
|30E/360 means clamp both endpoint days31 to30 | Inspected retained QuantLib1.38 `EU_Impl` and switch mapping; explicit mathematical definition for the reference | Annual case hides variant errors; use independently declared endpoint probes | Economic-reference hypothesis; ACTUS enum mapping unverified |
| Status before initial exchange | Retained request gives an inequality only | Silently choose a package timestamp/timezone; preserve the inequality and mark exact encoding unresolved | Required unresolved input |
| Deal date, identifiers and party codes | Guide requires them, retained request does not supply them | Invent client facts or backend defaults; keep unresolved rather than emit a runnable request | Missing input |
| Atomic date-group state | Economic principal/accrual accounting for the explicit scenario | Pretend it is the core's intraday order; preserve separate legs and unresolved package order | Deliberate economic scope |
| No adjustment, EOM, FX, fees or optionality | Explicit synthetic terms | Absence selects an engine default; require audited mapping before any execution | Scenario assumptions, not package defaults |
| Existing local coupon kernel as inspected component | Current worktree `fixed_coupon.py` | Interpret a supported-scope refusal as ACTUS defect; reproduce unsupported30E/360 without modifying code | Explanatory limitation only |
| Retained PAM guide | Pinned60234c1e official userguide | Treat generic guide as core1.1.0 implementation or full dictionary; preserve source boundary | Preparation evidence, not version-specific acceptance |

The endpoint probes distinguish European from BondBasis and February-end variants;
they are mathematical comparator checks, not execution of the later stub ladder.
No package ranking or stochastic comparison is attempted.

## Ordered execution and bounds

1. Review a single extra prerequisite admission2→3. Bind both prior complete
   output manifests, retained guide/provenance, request, official QuantLib source,
   plan, review and preparer. Preserve all441 production files by exact hashes.
2. `prepare`: verify admission and retained identities, freeze the sources and
   local methods, read complete guide, emit explicit semantic input/provenance
   and a version-specific mapping checklist. Do not output a core request.
3. `reference`: calculate the economic schedule independently and compare it to
   a hand-declared exact table; retain source-level endpoint probes and reproduce
   the local kernel's explicit unsupported-convention result.
4. `controls`: use clearly labelled synthetic observations to challenge missing
   and extra events/fields, amounts, dates, signs, units/currency, states,
   equal-total reallocation, implicit conventions and false integration labels.
   Retain each actual refusal and demonstrate that the core gate stays closed.
5. `seal`: verify every protected source and all441 production hashes again;
   retain the actual partial result, request additions, manifest and outputs;
   record and refresh. Inspect remaining independent routes after recording.

Exact worker form: `.venv/bin/python -m scripts.prospectus_actus_preparation`
followed by one of `prepare`, `reference`, `controls`, `seal`. Each stage has an
internal30second alarm and is launched under `timeout40`; use one-second tool
yields and poll the same session through exit. Four ordinary stages and at most
one understood repair-stage invocation; cumulative new worker time≤150seconds,
new evidence≤10MiB including admission and seal reserve. Original600second focused
command and200MB evidence rules remain upper bounds; prior admissions and
historical work are not reset. Prior001 records115.393336seconds;002 does not
record a duration, so no exact combined historical runtime is claimed. Count and
retain existing storage before admission. No extraction/render/OCR, package/core
invocation, network, install, model/GPU, external message, production edit,
branch switch or license agreement is included.

Recorded stage-body intervals end before final seal artifact writing. They are
not an exact total worker runtime. The30second alarm also covers finalization,
so the four normal worker bodies have a120second hard envelope, including seal
writing. Failed stages stop for reviewed repair and cannot be retried unchanged;
started-stage records, including failures, count toward the invocation bound.

## Skeptical audit: PASS after scope correction

The initial interpretation would have treated unsupported30E/360 as authority to
change product behavior using BASF's unselected option. That is wrong for this
case: the selected final terms use a different convention. This plan therefore
retains the local limitation and prepares only the existing explicit synthetic
baseline. It does not substitute BondBasis for30E/360, invent an ACTUS role or
calendar enum, manufacture official events, or count fixture success as a real
numerical trial. Atomic economic states leave implementation order unresolved.
The comparator must reject conserved-total reallocations and the execution gate
must refuse even its positive fixture. These diagnostics answer the preparation
question while preserving the missing-core decision boundary. The prior access
search is not rerun, and no new admission or phase erases the original limits.
