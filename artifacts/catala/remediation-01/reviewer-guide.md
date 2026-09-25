# Reviewing the generated backend

The authored rules are in each comparison's corpus.json. source-map.json maps
every RuleIR node to its rule, source spans, execution layer, and generated
Catala scope/line numbers. Lowered.catala_en contains the generated calculations.
verification-results.json places complete Python and Catala/Java results beside
one another, including skipped branches and evidence IDs. The JAR retains those
generated sources and the pinned runtime sources under META-INF/legalmath.

A lawyer should assess the canonical rule and retained source interpretation.
An engineer can follow node IDs into generated code and the executed trace.
No human reviewer has yet compared accuracy, time, or comprehension using this
backend. A counterbalanced study with the same source, rules and questions is
required before claiming that either presentation is easier to review.
