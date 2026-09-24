# From SFC Circulars to Reviewable Bank Controls

[Read the monograph](monograph.pdf) · [Technical companion](technical-companion.pdf) ·
[LaTeX source](monograph.tex) · [Reconstruction review](review/reader-facing/reconstruction-review.md)

The 24 September 2026 reader-review edition contains a **235-page monograph**
and a **69-page technical companion**. The monograph opens with a two-page
executive summary and develops the argument through ten chapters. It follows
two circulars from the bank's practical questions to interpretation, evidence,
mathematics, reliable execution and supervised operation.

The companion retains full provision inventories, detailed comparison tables,
software interfaces, implementation history and reproduction commands. Keep
both PDFs together for links between them. All mathematical derivations needed
for the main argument remain in the monograph.

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

The examples use public sources and synthetic facts. Demonstrated engineering
behaviour, proposed empirical evaluation and the requirements for bank adoption
remain distinct. The edition does not establish independent legal validation,
live-model interpretation performance or production readiness.

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
files. All 35 mathematical display groups, containing 37 equation labels,
remain in the main volume. All 21 original listings remain across the pair.
All 207 original source-unit labels survive; label retention is a navigation
check, not proof that every rewritten sentence has the same meaning.

The pair retains 81 cited documents and 211 citation occurrences. The
[citation review](review/reader-facing/citation-occurrence-review.json) carries
204 exact contexts from the earlier scoped author review and records explicit
judgments for seven changed occurrences. The [source archive](../papers/monograph-citation-archive.json)
and earlier technical reading notes remain available.

The [reconstruction review](review/reader-facing/reconstruction-review.md)
records the changes across every chapter, the disposition of moved material,
36 selected rendered main-volume pages and five companion pages inspected, and
remaining limits. Naturalness and comprehension still need target-reader
acceptance. Automated checks and author/model inspection cannot supply it.

The earlier [unification](review/unification/merge-review.md) and
[eight-part assessment](review/revision/final-assessment.md) describe historical
232-, 282- and 283-page editions. Their page counts and exact-transform checks
do not describe this reconstructed edition. Use the new build and review record
above; the historical master program is not the current delivery command.

[The implementation entry point](../implementation/START-HERE.md),
[ensemble contracts](contracts/README.md) and
[product-risk review](review/revision/product-risk-review.md) retain the separate
engineering and adoption records. This editorial revision did not rerun or
promote concurrent implementation work.
