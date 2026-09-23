# From SFC Circulars to Reviewed Specifications and Verified Java Controls

[Read the unified monograph](monograph.pdf) · [Canonical LaTeX](monograph.tex) ·
[Preservation map](review/unification/content-map.md) ·
[Merge review](review/unification/merge-review.md)

One author draft, ten chapters, **232 PDF pages and 76 cited references**.
The 66-page product proposal and 153-page interpretation monograph are now
integrated by subject into this book. There is one introduction, contents and
bibliography. The former [proposal entry point](../proposal/proposal.tex)
builds this same manuscript; its distributed PDF is an identical copy.

The book follows regulatory scope through two concrete circulars, formal meaning,
competing interpretations, bounded ensemble investigation, Java generation,
review, release, evaluation and continuing operation. The complete SPI example
from circular 23EC35 precedes the 23EC46 marketing example. Both source inventories,
worked cases, language explanations, implementation contracts and research
qualifications are retained. Chapter 8 now connects the earlier work packages to
the executed T00–T22 MVP and the proposed E01–E14 interpretation extension.

## Contents

1. A correct program can enforce the wrong rule.
2. Two circulars, from business meaning to executable controls.
3. What can be proved, and under which assumptions.
4. Languages that make interpretation inspectable.
5. Constructing and comparing competing interpretations.
6. An accountable ensemble with bounded resolution.
7. From an accepted interpretation to verified Java behavior.
8. The complete workbench and its interpretation extension.
9. Measuring error, uncertainty and the value of redundancy.
10. Operating the product without losing its evidence.

Chapter 6 retains the full 27-page ensemble design. Initial proposals are blind;
source coverage is checked separately; every discrepancy receives a disposition;
actions are charged before dispatch; retries have explicit limits; dissent and
unresolved uncertainty remain in the final report. Material unresolved issues
block release. Search scores and repeated model agreement are not calibrated
probabilities of legal correctness.

## Preservation and execution

The original PDFs contain **66 + 153 = 219 pages**; the unified PDF contains
**232 pages**, including front matter and bibliography. The existing 12-point
A4 typography is unchanged. The original proposal used different typography, so
page arithmetic alone cannot establish preservation.

The [automated preservation check](review/unification/preservation-check.json)
accounts for all **207 original source units**: 67 from the proposal and 140
from the monograph. It reconstructs each unit from a frozen original and explicit
editorial changes. All 33 original equation environments, 18 code listings,
six figures, cited sources and labels survive. Tables are checked as part of
those exact transformations. Original files, including both PDFs, remain in
[the protected baseline](../../.localresources/unification/baseline/manifest.json).

Chapter 8 describes the actual source-to-release workflow, withdrawal, replay,
amendment, host checks, export and restoration. It gives the current API and
maps the original W work packages to T execution tasks. The earlier SPI-Demo1,
completed local MVP and proposed ensemble use distinct interfaces and evidence;
the text identifies each at its point of use. Prior engineering results are
reported from their retained records, not claimed as newly rerun for this merge.

## Implementation companions

[The implementation guide](implementation-guide.md), [task graph](implementation-plan.json)
and [ten JSON Schemas](contracts/README.md) specify the ensemble extension.
Its fourteen tasks remain proposed. They supplement the book with machine-readable
contracts and a synthetic blocked example. The [existing execution report](../implementation/execution-report.md)
records the implemented MVP; [START-HERE](../implementation/START-HERE.md) remains
its operational entry point.

The [paper library](../papers/README.md) retains 50 PDF editions representing
49 works, with 1,298 source pages and recorded hashes. The combined bibliography
also includes regulatory sources, standards, software and local evidence.

## Build and review

From the repository root:

```sh
python3 scripts/build_unified_monograph.py
```

This builds the canonical PDF with XeLaTeX, synchronizes the proposal PDF and
runs document, source-preservation and compatibility checks. The existing system
Python requires PyMuPDF. Individual checks are `scripts/check_monograph.py`,
`scripts/check_unified_monograph.py` and the compatibility wrapper
`scripts/check_proposal.py`. For changes to the ensemble contracts, also run
`.venv/bin/python scripts/check_interpretation_contracts.py`.

[The delivery manifest](review/delivery-manifest.json) binds this edition and its
checks. [The author review](review/author-review.md) distinguishes automated checks
and targeted rendered-page inspection from independent acceptance. No new legal
adjudication, live-model evaluation or bank deployment occurred. Independent legal,
technical and reader acceptance remain pending.
