# UBS instrument gap-closure increment

All five phases and document delivery passed; see the [execution result](execution-result.md)
and [reset memo](RESET-MEMO.md). The affected regression passed 238 tests with
zero failures, errors or skips.

This increment takes the June 2024 UBS SGD issue, CH1357852636, from a retained
prospectus to executable conditional product premises, notice schedules and share
calculations. The reviewed [plan](../../plans/instrument-gap-closure.md) and
[plan audit](plan-review.md) define its scope. The
[operator guide](operator-guide.md) explains the executable master program and
its repair/refresh mechanism.

The earlier joined public-source report had 37 unknown product observations.
The new dossier supplies five source-dependent premises and derives product
scope for the selected issue. Actual client PI status, notices, market histories
and other external facts remain unknown. The result stays qualified and retains
all fourteen bank obligations.

Implemented distinctions include the higher-trigger capital add-back, strict
seven-percent threshold, ordinary and extraordinary notice rules, restoration
timing, higher-trigger postponement, separate viability deadlines, actual
alternative-loss notice, covered Zurich/Singapore calendars, holder aggregation
and whole-share rounding. Price calculations include a bounded deterministic
subset, successor-price arithmetic and net offer allocations. The
[branch coverage](I2/attempt-003/branch-coverage.json) identifies qualified paths.

The retained PDF prints an unusual extraordinary-distribution formula,
`(A-B)/B`. Its literal result is retained and its intended operational meaning
remains qualified. See the [source review](source-review.md); the program does
not silently change the denominator.

Validation uses independent mathematical relations, counterexamples, source and
scenario tampering, calendar/rounding invariants and both native language
targets. The comparison checks 370 target cases: 350 compiled evaluations and
20 intentional abstentions before execution. This distinction corrects the
earlier summary count; see [repair 002](repair-002.md). Five formal models have
kernel-checked preservation evidence, five independent SMT equivalences and
seven detected formal mutants. These checks do not certify English-law truth or
rank Catala above RuleIR.

The [remaining-gap ledger](remaining-gaps.md) distinguishes absent external
evidence, additional implementable instrument branches and the unproved
generalization claim. No human legal answer labels or live interpretation calls
are used. The source-specific account is in monograph section 2.4.7 and its
new process-guide flowchart. See the final execution and rendered-review records
alongside this file for the accepted snapshot and document hashes.
