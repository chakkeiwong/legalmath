# The proposal is part of the unified LegalMath monograph

[Read the unified book](proposal.pdf) · [LaTeX entry point](proposal.tex) ·
[Canonical source and contents](../monograph/README.md)

The former 66-page proposal and 153-page interpretation monograph now form
**one ten-chapter, 232-page work with 76 cited references**. The material is
integrated by subject, from the business problem and two circulars through formal
languages, ensemble interpretation, verified Java, execution and operation.

`proposal.tex` includes `../monograph/monograph.tex`; it is a compatibility entry
point, not a second manuscript. The standard build keeps `proposal.pdf`
byte-identical to the canonical monograph PDF:

```sh
python3 scripts/build_unified_monograph.py
```

Run that command from the repository root. Direct XeLaTeX builds through either
entry point are supported. The [preservation map](../monograph/review/unification/content-map.md)
accounts for all 207 source units from the two works, with explicit corrections
to stale implementation status and API descriptions. The [merge review](../monograph/review/unification/merge-review.md)
records page counts, mathematical and source retention, and review limits.

The numbered TeX fragments and the old bibliography files in this directory are
retained historical inputs; the current entry point does not include them.
Edit the canonical chapter files under `docs/monograph/chapters`.
The [complete original proposal](../../.localresources/unification/baseline/docs/proposal/proposal.pdf)
and its [original review](../../.localresources/unification/baseline/docs/proposal/review.md)
remain frozen. [Current validation](validation.json) describes the unified book.
