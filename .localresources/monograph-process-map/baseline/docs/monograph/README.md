# From SFC Circulars to Reviewable Bank Controls

[Read the monograph](monograph.pdf) · [Technical companion](technical-companion.pdf) ·
[LaTeX source](monograph.tex) · [Revision review](review/round4/integration-review.md)

The 24 September 2026 reader-review edition contains a **244-page monograph**
and a **76-page technical companion**. The monograph opens with a two-page
executive summary and develops the argument through ten chapters. It follows
two circulars from the bank's practical questions to interpretation, evidence,
mathematics, reliable execution and supervised operation.

The latest revision integrates the interpretation work through round four.
Source editions, competing readings, separately scoped duties, useful comparison
cases and continuing source review enter through worked explanations. The
companion begins with a current reference organised by implementation task,
followed by provision inventories, detailed tables, interfaces and clearly dated
historical records. Keep both PDFs together for links between them. Mathematical
derivations needed for the main argument remain in the monograph.

## Contents

1. A correct program can enforce the wrong rule.
2. Two circulars, from business meaning to executable controls.
3. What can be proved, and under which assumptions.
4. Languages that make interpretation inspectable.
5. Constructing and comparing competing interpretations.
6. Using disagreement to improve a review.
7. From an accepted interpretation to verified Java behavior.
8. What the bank would own and operate.
9. Measuring error, uncertainty and the value of redundancy.
10. Operating the product without losing its evidence.

The examples use public sources and synthetic facts. Earlier live development
observations and later controlled or replayed checks retain their different
meanings. They do not establish independent legal validation, comparative
live-model interpretation performance, reviewer savings or production readiness.
Subsequent implementation rounds are separate continuations, not evidence
silently incorporated into this edition.

## Build

From the repository root:

```sh
python3 scripts/build_reader_facing_monograph.py
```

The build uses XeLaTeX through `latexmk` and Python with PyMuPDF. It
settles references in both directions, runs the current document checks and
copies the main PDF to the historical `docs/proposal/proposal.pdf` location.
The companion and a `monograph.pdf` return-link target are copied beside it.

The current checker is `scripts/check_reader_facing_monograph.py`. It verifies
the protected source checkpoint, exact mathematical displays and listings,
labels, citation archives and existing citation judgments, reference resolution,
LaTeX diagnostics and the geometry of every page. It does not assign new citation
support judgments or certify comprehension. A changed citation context needs
explicit author review; moving an unchanged context may retain its judgment.

## Preservation and review

The [current check](review/reader-facing/document-check.json) compares the two
documents with the protected 282-page checkpoint and verifies its 243 retained
files. The immediate 235/69-page pair is also protected in a 253-file checkpoint.
All 35 original mathematical display groups, containing 37 equation labels,
remain in the main volume. The revision adds two displays in a derived,
conditional uncertainty argument. All 21 original listings remain across the
pair, with three new companion command examples. All 207 original source-unit
labels survive; label retention is a navigation check, not proof that every
rewritten sentence has the same meaning.

The pair now cites 85 archived documents in 216 citation occurrences. All 211
contexts from the immediate baseline are unchanged; five added occurrences
have explicit scoped author judgments. The new sources are two Code editions,
the retained gift FAQ and the settlement-readiness circular. The
[citation review](review/reader-facing/citation-occurrence-review.json),
[source archive](../papers/monograph-citation-archive.json) and technical reading
notes retain their support and historical limits.

The [revision review](review/round4/integration-review.md) records the changes
across every chapter, the new mathematical argument, 44 selected rendered main
pages and 15 companion pages inspected, and the remaining limits. The
[delivery manifest](review/round4/delivery-manifest.json) identifies the exact
PDFs. Naturalness and comprehension still need target-reader acceptance.
Automated checks and author/model inspection cannot supply it.

The earlier [unification](review/unification/merge-review.md),
[eight-part assessment](review/revision/final-assessment.md) and
[whole-volume reconstruction](review/reader-facing/reconstruction-review.md)
describe historical editions. Their page counts do not describe this revision.
Use the build and review record above; the historical master program is not
the current delivery command.

[The implementation entry point](../implementation/START-HERE.md),
[ensemble contracts](contracts/README.md) and
[product-risk review](review/revision/product-risk-review.md) retain the separate
engineering and adoption records. This editorial revision did not rerun or
promote concurrent implementation work.
