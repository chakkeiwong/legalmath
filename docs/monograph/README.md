# From SFC Circulars to Reviewable Bank Controls

[Read the monograph](monograph.pdf) · [Technical companion](technical-companion.pdf) ·
[Illustrated process guide](process-guide.pdf) · [LaTeX source](monograph.tex) ·
[Revision review](review/process-map/review.md)

The 24 September 2026 reader-review edition contains a **252-page monograph**
and a **76-page technical companion**. The monograph opens with a two-page
executive summary, a seven-page illustrated process guide and ten chapters. It follows
two circulars from the bank's practical questions to interpretation, evidence,
mathematics, reliable execution and supervised operation.

The content integrates the interpretation work through round four.
Source editions, competing readings, separately scoped duties, useful comparison
cases and continuing source review enter through worked explanations. The
companion begins with a current reference organised by implementation task,
followed by provision inventories, detailed tables, interfaces and clearly dated
historical records. Keep both PDFs together for links between them. Mathematical
derivations needed for the main argument remain in the monograph.

The process guide occupies PDF pages 4–10, directly after the executive summary.
Fourteen flowcharts expand every step from source collection to Java and bank
use. They locate breadth-first/UCT search, RuleIR, Java/Python checks, Z3,
selected Lean proofs and the separate Stipula/JML/KeY research route. The
standalone guide contains the same pages; keep it beside the main book and
companion for its links to fuller explanations.

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
The build also exports `process-guide.pdf` with working links inside the guide
and back to the full books. The export can be repeated independently with
`python3 scripts/export_monograph_process_guide.py` after a successful build.

The current checker is `scripts/check_reader_facing_monograph.py`. It verifies
the protected source checkpoint, exact mathematical displays and listings,
labels, citation archives and existing citation judgments, reference resolution,
LaTeX diagnostics and the geometry of every page. It does not assign new citation
support judgments or certify comprehension. A changed citation context needs
explicit author review; moving an unchanged context may retain its judgment.

## Preservation and review

The [current check](review/reader-facing/document-check.json) compares the two
documents with the protected 282-page checkpoint and verifies its 243 retained
files. The 235/69-page pair is protected in a 253-file checkpoint; the immediate
244/76-page pair and build entry point are protected in a 247-file checkpoint.
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

The [process-guide review](review/process-map/review.md) records the technology
mapping and inspection of all seven new pages. The existing 236 main-body and
bibliography pages retain identical extracted text and rendered appearance
against the immediate baseline. The earlier
[evidence-integration review](review/round4/integration-review.md) records the
chapter changes and their scoped inspection. The current
[delivery manifest](review/process-map/delivery-manifest.json) identifies the
exact PDFs. Naturalness and comprehension still need target-reader acceptance.
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
