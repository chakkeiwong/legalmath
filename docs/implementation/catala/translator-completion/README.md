# Shared model version 2

Version 2 represents scoped rich rules, strict defaults, exact scaling, explicit
rounding, reusable typed helpers and named outputs. Interpretation still happens
once, before target selection. Catala performs the calculations and propagates
result states; Python validates observations and decodes the returned records.

The existing version-1 model, scalar compatibility backend and native builds keep
their original representation. Use version 2 deliberately when these extensions
are needed. The `rules` commands accept either version. `catala-convert generate`
selects version 2 for multiple native outputs; `--shared-version 2` also enables
it for a single output. `catala-convert execute --rule NAME` selects an output;
omitting it returns all outputs. `catala-convert verify` checks each named output.

## Interpretation and expressions

A version-2 `RuleInterpretationTask` has `version: "2"`, a fixed `facts`/`types`
interface and `outputs: [{"id": "amount", "result_type": "money_hkd"}, ...]`
instead of a single `result_type`. Choose `complete.v1` or `partial.v1` explicitly.
Generation returns `formalization` with `version`, `facts`, `types`, `helpers`,
and `outputs`. Each output adds `scope` and `result` prefix expressions. A helper
has `name`, typed `parameters`, `result_type` and `body`. It can call acyclic
helpers and use its parameters; facts and rule references must be passed through
parameters. The source critic reviews all outputs and helpers together.
Copyable [task](examples/task.json), [fixture response](examples/reading-fixture.json),
[snapshot](examples/snapshot.json), [task schema](examples/task-schema.json) and
[generation schema](examples/generation-schema.json) are retained. The response
is a handwritten synthetic control, not a live model response or legal rule.

| Expression | Meaning |
| --- | --- |
| `(scale cash 1 2)` | Exact half of integer/money minor units; indivisible values produce `E_INEXACT_SCALE` |
| `(round money_hkd nearest_away (decimal 3 2))` | Two minor units; rounding is a separate source-justified operation |
| `(default BASE (exception NAME GUARD VALUE) ...)` | All guards checked; multiple true guards conflict, including equal consequences |
| `(call helper ARG ...)` | Typed reusable calculation with explicit parameters |
| `(rule output)` | Reference an unconditionally scoped output |
| `(record Entry (active true) (amount (decimal 1 3)))` | Construct a named record |
| `(library numeric.min X Y)` / `numeric.max` | Same-type integer, money or exact decimal minimum/maximum |
| `(library date.add_days DATE N)` | Add integer days |
| `(library date.add_months_clamped DATE N)` | Add months, clamping an invalid day to month end |
| `(library date.month_end DATE)` | Last day of the same month |
| `(library list.sequence BEGIN END)` | Begin inclusive, end exclusive; empty when end is no greater than begin |
| `(library list.length LIST)` | Number of items with complete membership; item values need not all be known |

Rounding modes are `toward_zero`, `floor`, `ceiling` and `nearest_away` (ties away
from zero). Decimal inputs to monetary rounding are in **minor units**. Version-2
money payloads compile as exact integer minor units, avoiding implicit rounding
by Catala's native money conversion. Other existing expressions—including map,
filter, sum, options, payload variants and exhaustive matching—remain available.

Scope is lazy: false returns `OUT_OF_SCOPE`; unknown/conflict/error scope prevents
body evaluation. Defaults prioritize guard errors, then guard conflicts, then
overlap, then unknown guards. Only a selected consequence runs. Boolean operators
use strong Kleene logic after error/conflict precedence. Helper calls evaluate
their explicit argument expressions and propagate unavailable root arguments.

## Partial observations

`complete.v1` still requires every declared input. `partial.v1` permits missing or
conflicting observations and uses dependencies actually evaluated. This differs
from RuleIR's static whole-fact conflict veto, so the RuleIR capability report
rejects this profile. It is not a silent change to existing RuleIR semantics.

Existing `known` snapshots retain their raw values and per-field/item evidence
paths. To provide partial structure, use `status: "structured"` at that node and
make each child a complete observation record. For example, a known amount with
an unknown inclusion flag can be supplied as:

```json
{
  "status": "structured",
  "type": "Entry",
  "complete": true,
  "evidence_ids": ["entry-document"],
  "valid_from": "2026-09-25T00:00:00.000000Z",
  "valid_until": null,
  "recorded_at": "2026-09-25T00:00:00.000000Z",
  "value": {
    "active": {"status": "unknown", "type": "bool", "reason": "MISSING"},
    "amount": {
      "status": "known", "type": "decimal",
      "value": {"numerator": "1", "denominator": "3"},
      "evidence_ids": ["amount-document"],
      "valid_from": "2026-09-25T00:00:00.000000Z",
      "valid_until": null,
      "recorded_at": "2026-09-25T00:00:00.000000Z"
    }
  }
}
```

Projecting `amount` returns one-third. Returning the whole record produces
`PARTIAL`, with explicit child states under `partial_value`; it never substitutes
a placeholder for an unknown value. Filtering on `active` cannot decide whether
the item belongs in the result, so an aggregate becomes unknown. A complete empty
list sums to zero; an incomplete list is unknown, even when no items are observed.
Known optional absence remains a value, distinct from unavailable option evidence.
Each nested observation has its own validity/knowledge time and evidence IDs.
Returned `used_evidence`, missing paths and conflict paths are bound to the
snapshot and actual compiled dependencies.

## Limits and verification

This is a bounded shared vocabulary, not a parser for every Catala program. Helpers
and type declarations must be acyclic. The native interface allows 40 inputs,
40 outputs, 30 generated types, depth 12 and 64 KB candidate source. Encoding
states consumes some of that type/depth budget; capability reports reject models
that exceed it before compiler dispatch. Source expressions retain the 1,000-token
and depth-32 parser limits. Expanded structured types and observation trees are
bounded; list sequence allows at most 10,000 items. Dates stay within years
1–9999. Native process/time/log limits remain active for resource-heavy programs.

Verification compares independent expected values/statuses, replays evidence
encoding, checks plain against instrumented Java, and asks the unmodified Catala
interpreter to assert exact equality. It does not use a Python rule evaluator for
the new operations. Fixture generation checks orchestration, not the accuracy of
live source interpretation. Builds remain drafts and do not grant release approval.
