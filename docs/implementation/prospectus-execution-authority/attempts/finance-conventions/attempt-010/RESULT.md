# Exact coupon premises preserved through complete answers

Revision359's finance-conventions repair passes its declared deterministic
checks. Coupon results now retain the complete validated scenario, including
calendar edition/coverage/weekends/holidays, exact rates and reference periods,
rounding, original event order, holdings and their evidence. Returned events and
source evidence are detached from the caller's mutable input. Arithmetic and
admission rules are unchanged.

Before implementation, seven actual P5/full-consumer results exactly matched
their sealed Shell002 and Danske008 answers. Every one reproduced missing
calculation_inputs and input/output aliases. This is a demonstrated local
reporting/ownership defect, not a QuantLib package defect.

The candidate passes388 focused tests. Seven ordinary complete answers retain
all22 exact coupon scenarios. Removing only the named additive field preserves
every old answer field apart from independently checked P5/report hashes.
Input/output mutation controls pass in both directions. Invalid calendars,
rounding and event dates still refuse. Rehashed corrupt output controls fail
the complete-answer check. Independently enumerated source dates and integer
arithmetic preserve Danske amounts12750 plus five51000, total267750DKK on the
declared hypothetical1m principal; the excluded scenario has no transfers.

The fresh offline wheel contains534 source-matched files. Isolated installed
execution imports all48 legalmath modules from that installation and matches
the complete ordinary answers and P5 products for all seven cases. The same
adverse and mutation controls pass there. These are new P5/full-consumer runs
over authenticated retained P1-P4 evidence, not fresh extraction or a new
QuantLib trial. The successful matched QuantLib009 evidence remains unchanged.

| Decision | Primary criterion | Veto diagnostics | Main uncertainty | Next justified action | Limit |
| --- | --- | --- | --- | --- | --- |
| Retain exact-premise and mutation-isolation repair | All22 exact scenarios visible; whole prior-answer projection preserved; ordinary/installed equality | No accepted invalid/corrupt control, source drift or wrong import | Supplied hypothetical premises can still differ from actual facts | Record/refresh and reconcile next original finance coverage | No actual entitlement/payment/settlement or whole-task acceptance |
| Keep current event-order restriction | Existing refusal rules preserved | No unreviewed early-payment rule introduced | Broader preceding-payment domain has no source-backed trial here | Review only if supported original source requires it | No conclusion about every possible fixed-rate instrument |

Measured stages and actual commands are retained under stages/ and commands/.
The run manifest gives exact costs; all earlier finance admissions/costs remain
in the preparation history. Older unmeasured runtime is UNKNOWN. The120-second
authoring charge is conservative accounting, not measurement. No network,
registry installation, OCR, GPU, model calls, subagents, commit or push occurred.

The strongest alternative explanation for apparently reproducible results is
that a supplied interpretation or hypothetical premise is wrong. Exact retention
does not establish its truth; it makes the conditional calculation inspectable.
A lost optional field, valid scenario whose old answer changes, or surviving
input/output alias would overturn the corresponding engineering claim. Source
interpretation completeness remains the weakest evidence and original task
acceptance remains open. Actual holdings and reader acceptance follow the build;
external-adviser opinion is not a prerequisite.
