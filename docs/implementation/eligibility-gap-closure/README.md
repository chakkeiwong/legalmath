# Joined eligibility, executable references and date assurance

All six phases of the [reviewed plan](../../plans/eligibility-gap-closure.md)
passed. The scoped increment joins selected HKMA conditions to the bank
inventory, adds exact executable quotation references and extends preservation
to declared Gregorian date comparisons. It does not establish full legal
interpretation or transaction clearance.

Validation: 338 affected regression tests passed with no skips; 136 native
product-model executions and 98 native date executions completed across
RuleIR/Java and Catala. Eleven Boolean equivalence obligations and twenty-one
mutations passed their checks. All 3,652,059 valid dates in years 1–9999 passed
the finite codec/order check. Eight unchanged encoded UCITS readings received
preservation certificates; the ninth remained unencoded. Earlier focused test
counts overlap and are not added to the regression count.

Run from the repository root:

```sh
.venv/bin/python scripts/run_eligibility_gap_closure.py
```

`--phase G0` through `--phase G5` selects a phase. Successful results are reused
only with matching method, inputs, predecessors and outputs. Failed/interrupted
attempts require an executed causal repair and `--repair-note`. The runner
reserves each attempt before work and refreshes the next-phase plan after every
result. It cannot dispatch live model calls or reset historical allowances.

The joined API is `legalmath.prospectus.eligibility.investigate(request, store)`.
It binds a bank request, product assertion document, prospectus sources,
issuer-basis sources and an optional contract/event document. It recomputes the
bank receipt, derives the broker exception from individual premises, preserves
conflicts and returns no execution permission. `revalidate` recomputes the
result after dependency changes. All three retained prospectus reports remain
qualified, with every bank obligation present.

`legalmath.source-and-executable-spans.v1` is an optional `reference_protocol`
for scoped interpretation. It preserves source quotation handling and the
original semantic validation. References bind reading, question, expression
and request; an unencoded reading has no selectable executable text. Only
deterministic providers were used in this campaign.

The date certificates distinguish constructor preservation, Lean calendar
theorems and executed codec/runtime checks. They do not choose the date intended
by a regulation or prove business-day, whole compiler or English semantics.

See [execution and repairs](execution.md), [remaining limits](remaining-gaps.md),
and [the next-phase record](next-phase-plan.json). Computational attempts remain
immutable; final document build and rendered inspection are recorded separately.
