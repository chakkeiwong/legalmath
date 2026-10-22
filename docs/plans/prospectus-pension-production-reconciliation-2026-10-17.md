# Production pension reconciliation and scoped build evidence

This is a continuation of `basf-references`, not a new task or source finding.
The sole authority remains the prospectus program. The user's general-build
direction from revision205 remains controlling. Apply a reviewed revision before
admission; preserve all seven original admissions and sealed evidence.

## Question, baseline and intended effect

Does the normal source-bound pension consumer explain which rounding hypotheses
can and cannot account for the printed differences, without inventing a missing
amount, selecting an incorporation reading or attributing a source error?

The comparator is the entire `basf-references/attempt-005/pension-consumer.json.gz`
with its original products and statement/equity/OCI/hedge/pension profiles.
Attempt007 contains a correctly qualified, agent-written rounding supplement.
It is evidence of the source reading and arithmetic, not an integrated product
feature. The actual omission is reproducible by reading the production `consume`
entry: it returns the pension review and explanation without that analysis.

Retain the original return value when no reconciliation profile is supplied.
When explicitly supplied through that same consumer, validate a separately pinned
profile, original policy PDF/image and all policy occurrences24--28 on page209.
The ordinary return must then contain the source-bound rounding analysis and its
answer. All preceding output must remain equal. Merely writing a supplement or
calling a private arithmetic helper is insufficient.

## Mathematical target and assumptions

Let `d_i` be a displayed amount, `x_i` its unknown underlying amount, and `a_i`
its signed integer coefficient in a proposed relation. If
`abs(x_i-d_i) <= epsilon_i`, then the true residual lies in
`[sum(a_i*d_i)-B, sum(a_i*d_i)+B]`, where
`B=sum(abs(a_i)*epsilon_i)`. This follows by substituting
`x_i=d_i+(x_i-d_i)` and applying the triangle inequality. Thus a zero outside
the interval excludes a rounding-only reconciliation under those assumptions.
A zero inside the enclosure does not prove actual rounding, source equality or
common accounting scope. No independence assumption is needed for an enclosure.

The reusable enclosure accepts general integer/rational inputs. The BASF prose
reader is specific to the four identified original amount configurations and
refuses a different configuration: its fixed source explanation must never be
reused for new numbers. A new issuer/report needs its own source review and
answer construction. This is a supported-domain restriction, not evidence that
the general extraction problem has been solved.

Use exact integer/rational arithmetic. Reject floats, booleans, negative error
bounds, malformed vectors and mixed units. A printed dash remains an unknown;
return an explicit symbolic residual and no numeric rounding conclusion. Never
replace it with zero. This is a reusable finite calculation, not an accounting
materiality threshold or an implementation of an IFRS recognition rule.

The report says amounts are in millions and totals may differ due to rounding;
it does not state a rounding algorithm. The half-million and one-million bounds
are explicit hypotheses inherited from007, not reported facts. Compare the four
2022 quantities3,758,6,800,-2,641,-431: residual30; maximum error2 or4. Both
exclude zero, conditional on a common complete scope. The separate2022 after-tax
subtotal residual1 is not excluded. The2021 candidate residual remains
`45 - unknown signed ceiling`; the displayed acquisitions/divestitures45 is
not an attribution. Source cause and incorporation remain unresolved.

## Repair the build projection without changing original verdicts

Revision205 projects current build solely from original task completion. That
cannot express a verified conditional capability while the historical source
resolution remains partial. Add optional named build criteria inside the same
authority. A recorded partial attempt may carry validated build-criterion IDs,
bound to its active task, methods, inputs and sealed output. The historical state
must remain `RESULT_RECORDED`, and original obligations remain incomplete.

For this task declare both `pension-rounding` (a named substantive validator)
and `remaining-reference-coverage` (the original acceptance still required).
Passing the first is one verified component, not completion of BASF references
or the build. Other tasks retain their original criterion until a substantive
review declares a complete conditional replacement. No unreviewed blanket waiver,
external-handler conversion, second dispatcher or automatic new budget.

Stale methods, altered output, arbitrary PASS JSON, another task's validator,
an omitted criterion and an unchanged partial attempt must not create current
build acceptance. Changes to shared authority and production methods stale the
previous finite acceptance; retain it and plan one final current revalidation
after substantive changes, instead of replaying it after each edit.

## Evidence contract and intent ledger

| Evidence | Role | Decision |
| --- | --- | --- |
| Normal consumer reaches independently checked source-bound analysis | Primary pass | Required, with full old output equal |
| Exact independently calculated interval and dash handling | Primary pass | Required for all four dated relations |
| Changed source/profile, guessed scope/algorithm, lost unknown, false rounding cause | Promotion veto and repair trigger | Every declared alteration must refuse |
| Corrupt original source/comparator; methods change during execution | Continuation veto for affected run | Retain failure, repair evidence before another admission |
| Scoped criterion leaks into original or whole-build completion | Promotion veto and repair trigger | Reject the scoped acceptance mechanism |
| Time, test totals, mutation totals and file size | Explanatory/resource checks | Never source truth or legal progress |

Passing establishes the implemented conditional arithmetic and its downstream
effect for these identified sources and declared hypotheses. It establishes no
source authenticity, actual rounding algorithm, cause of30million, complete
legal interpretation, independent adviser acceptance, general extraction
accuracy or unrestricted future-case correctness. Candidate rejection does not
reject the mathematical direction; an implementation failure triggers one
changed reviewed repair under the same cumulative lineage.

## Defaults, cheap checks and pre-mortem

| Choice | Provenance / justification | Failure / earliest diagnostic | Status |
| --- | --- | --- | --- |
| Original005 profiles and whole consumer | Retained source-complete baseline | Wrong path/import could test main tree; pin imports and compare whole JSON | Baseline |
| Bounds1/2 and1 million |007's nominated hypotheses | Reader might infer reported algorithm; require explicit false establishment flags | Hypotheses |
| Common complete accounting scope | Candidate bridge, not source-established | An interval pass might imply reconciliation; preserve scope false in every answer | Hypothesis |
| Closed interval enclosure | Triangle inequality, sufficient for exclusion | Endpoint/correlation mistaken for cause; test both endpoints and only claim nonexclusion | Reviewed calculation |
| Optional pinned profile | Existing source-reader convention | Detached supplement mistaken for integration; invoke normal consume and prove on/off difference | Reviewed interface |
| Named scoped validator | Needed to distinguish engineering from source resolution | PASS laundering; actual recomputation, seal and stale-binding adverse checks | Reviewed mechanism |

Pre-mortem: the command could succeed while merely echoing007, checking a helper,
using the wrong worktree, or silently treating half a million as a source fact.
The earliest checks are full comparator identity, public consumer dispatch,
independent integer-scaled interval calculation, policy occurrence matching and
adverse claims with hashes deliberately rebased. A permissive acceptor must be
detected. No external adviser, network, model, GPU or new installation is needed.

Skeptical audit: the baseline and intended product omission are identified;
smoke/test totals are not promotion criteria; rounding assumptions are explicit;
source resolution and conditional correctness are separate; unknown values and
accounting scopes are retained. Proceed with the bounded implementation, then
freeze exact methods and commands in the reviewed proposal before admission.

## Execution and refresh

Prepare focused tests and an admitted deterministic runner with a named
task-specific build validator. Freeze all changed code, source inputs, prior
outputs, profile, plan and test paths. Request one cumulative admission7->8,
retaining all earlier costs (unknown historical elapsed time stays unknown).
New command budget180seconds; additional artifacts32MiB including failure
outputs, with8MiB reserved for authority/doc overhead. No unchanged retry.

Exact planned command:

```
.venv/bin/python -m scripts.prospectus_pension_reconciliation --attempt docs/implementation/prospectus-execution-authority/attempts/basf-references/attempt-008
```

Run CPU only (`CUDA_VISIBLE_DEVICES=-1`), imports pinned to this worktree.
Use one-second tool yields and poll the original session. Retain the command,
commit, environment, data/method identities, deterministic seed disposition,
wall time, controls, consumer, independent verification, JUnit and result note.
Record, refresh and inspect actual authority status; continue the next source
work without treating this package as a checkpoint stop.

Next substantive checks are BES printed units, bilingual investing discrepancy
and property comparative treatment through their actual consumers. Reuse sealed
source evidence. New public retrieval requires a distinct reviewed lead;
unchanged RGICSF retrieval remains excluded. Final current-method revalidation
comes after the substantive batch. The eventual whole reference criterion still
needs the complete original mapping and conditional source limits.
