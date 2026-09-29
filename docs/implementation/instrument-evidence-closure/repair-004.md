# Development repair: typed constants

The first independent-relation diagnostic stopped before comparison because
bare numeric atoms are not legal expression identifiers. The common frontend
requires `(integer 30)`, rather than `30`, for an integer literal. Corrected
the three declared constants; no parser relaxation or expected-result change.
Lean had already checked the arithmetic propositions. The rerun must build
the actual model before attempting either SMT or native comparisons.
