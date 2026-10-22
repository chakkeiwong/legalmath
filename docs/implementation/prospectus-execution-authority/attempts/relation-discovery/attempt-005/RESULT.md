# Japanese programme edition review

The correction published on 6 August 2026 explicitly identifies the programme
dated 7 August 2025. The acquired 2025 original confirms that publication date,
issuer and the original issuance period, 8 August 2025 to 7 August 2027. The
correction prints an amended end date of 6 August 2026. The adjacent programme
published on 6 August 2026 is a different edition. Catalogue adjacency and the
correction's own publication date cannot identify its target.

The new optional `legalmath.prospectus.programme_editions` consumer binds the
supplied field associations to exact source occurrences, original PDF hashes,
cover images and a pinned profile. It retains the complete printed target
paragraph, including the instruction to consider the correction together with
the programme, and the before/after issuance periods. It nominates the 2025
edition for review and marks the 2026 candidate incompatible. Removing the
2025 candidate gives `MISSING_TARGET`; repeating it gives `AMBIGUOUS_TARGET`.
None of these cases accepts a legal relation or establishes amendment effect.

Actual extraction of all three documents produced 5,075 source units. The
prior 2,550 units remain exactly equal; the 2025 original contributes 2,525.
The three-document full answer is unchanged by all three optional review
cases. The earlier two-document full answer also reproduces exactly. Both
existing default discovery profiles produce zero candidates on this family;
there is no evidence that the default engine previously applied a wrong
amendment. Its reproduced gap is the absence of this edition-specific review.

Ten focused semantic tests pass. Nine actual controls refuse changed image,
original hash, quote, date label, omitted joint-reading context, reversed period
roles, the correction's publication date used as its target, fabricated legal
acceptance and a stale profile pin. The first eight controls use newly computed
pins, so refusal is not merely a stale-hash check.

| Decision | Primary criterion | Veto checks | Main uncertainty | Next justified action | What is not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain the optional local review; task remains incomplete | Actual correct/wrong editions, missing/duplicate targets and unchanged full answers pass | Nine altered controls refuse; source bytes, native receipts and method bindings verify | Field associations are exposed supplied readings; the legal effect and independent reading remain unchecked | Replay this API from an isolated installed wheel with exact comparison and adverse inputs | Automatic Japanese interpretation, independent legal acceptance, full amendment scope or delivery completion |

This is deterministic engineering evidence, with no stochastic ranking. It
identifies a missing application feature and supplies a bounded optional path;
it does not establish a fundamental limitation of the PDF packages. Native
inspection and source extraction succeeded without an additional repair.

One exact HTTP fetch returned 200 with no redirect. Four native reservations
were used: one original inspection and three actual source extractions. The
historical visible lower bounds are now nine source HTTP starts and 77 native
reservations. No OCR, installation, GPU, model/API call or local repair was
used. Per-stage commands and times are retained under `invocations`; sources,
methods, products, full answers and controls are included in `outputs.json`.

Post-run review: date and issuer compatibility can nominate a candidate while
other legally material distinctions remain unresolved. A different controlling
edition or a source-bound contradictory paragraph would require renewed review.
The weakest evidence is the supplied Japanese field association, which has no
independent reviewer. The current outcome supports this optional screen only.

Continuation: execute a reviewed installed-package replay, preserving this
attempt as the comparator. Broader relation discovery still requires complete
endpoint/scope inventories, independent readings and unseen source families.
