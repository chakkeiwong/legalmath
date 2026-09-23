# Interpreting Regulation with Accountable Ensembles

[Read the monograph](monograph.pdf) · [LaTeX source](monograph.tex) ·
[Implementation guide](implementation-guide.md) · [Task graph](implementation-plan.json)

A complete author draft in ten chapters, 153 PDF pages, with 46 cited references.
The central ensemble chapter occupies 27 pages. Page counts include front matter
and bibliography and are checked by `scripts/check_monograph.py`; ordinary A4,
12-point typography is fixed rather than expanded to manufacture the length.

The book develops the second-circular 23EC46 example, its 22-case oracle and 729
abstract inputs into a proposal for source-grounded competing interpretations,
independent coverage, structured arguments, bounded discrepancy resolution,
uncertainty reporting and delivery through the existing Java path. It teaches
formal languages and proofs through examples, including a complete miniature
state contract and explicit differences between component and whole-offer rules.

The proposed ensemble preserves blind initial proposals, investigates every
discrepancy, charges actions before dispatch, retains dissent and stops within
explicit round/root/global/deadline limits. Unresolved material questions block
release. Search priority and model agreement are never labelled calibrated legal
probabilities. Chapters 9–10 explain independent evaluation and bank operation.

## Contents

1. A correct program can enforce the wrong rule.
2. The second circular, from source to an unreleased control.
3. What can be proved, and under which assumptions.
4. Languages that make interpretation inspectable.
5. Constructing and comparing competing interpretations.
6. An accountable ensemble with bounded resolution.
7. From an accepted interpretation to verified Java behavior.
8. An implementation contract for the interpretation workbench.
9. Measuring error, uncertainty and the value of redundancy.
10. Operating the product without losing its evidence.

## Implementation companion

[Ten JSON Schemas and their guide](contracts/README.md) define runs, policies,
candidates, discrepancies, actions, coverage, evidence, reports, issue adjudications
and final reviews. A complete synthetic blocked example and an explicit fixture
policy accompany fourteen ordered extension tasks. The [implementation guide](implementation-guide.md)
names current code integration points, transactions, endpoints and acceptance
commands. These describe the new extension; they do not claim it is implemented.

The [paper library](../papers/README.md) now retains 50 PDF editions representing
49 works, with 1,298 pages and source hashes. [Additional reading notes](../papers/reading-notes-ensemble.md)
cover self-consistency, semantic uncertainty and conformal prediction, including a
paper/code difference found in the inspected semantic-clustering implementation.

## Build and checks

From the repository root, with the existing XeLaTeX/latexmk installation:

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error -cd docs/monograph/monograph.tex
.venv/bin/python scripts/check_interpretation_contracts.py
python3 scripts/check_monograph.py
```

The contract check uses the project's existing `jsonschema` environment. The
manuscript check uses the system Python's installed PyMuPDF (`fitz`). It follows
all ten chapter files, verifies citations/references, counts pages, checks paper
hashes and protected prior inputs, and checks selected mathematical illustrations.

[Review and limitations](review/author-review.md), [document check](review/document-check.json)
and [contract check](review/contract-check.json) record validation. The original
proposal, runtime, accepted evidence and second-circular oracle are preserved.

This is an implementation-ready design draft, not an independently approved legal
specification or a claim of zero interpretation error. The new ensemble has not
undergone a live-model study or bank deployment. Independent legal, technical and
reader acceptance remain pending; those boundaries are stated in the manuscript.
