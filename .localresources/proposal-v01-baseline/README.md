# LegalMath product proposal

[Read the proposal (PDF)](proposal.pdf) · [LaTeX entry point](proposal.tex)

The 34-page proposal contains 46 references, detailed SFC worked cases, a technical
literature and software review, the proposed rule representation and verification
approach, and a twelve-week prototype plan. It also assesses reuse of MathDevMCP,
DynareMCP and ResearchAssistant. The financial flowchart and client scenarios are
design illustrations; an executable translator has not been implemented.

The [paper library](../papers/README.md) contains 25 PDF editions representing 24
works, including all seven papers requested. The [technical reading notes](../papers/reading-notes.md)
record the relevant methods, limitations and proposed borrowings. The
[manifest](../papers/manifest.json) records versions, source URLs, page counts and
file hashes. Papers follow `Title, FirstAuthorSurname(year).pdf`, with unsafe title
punctuation normalized for portable filenames.

## Source organization

- [01-problem.tex](01-problem.tex): business problem, SPI examples, tokenisation
  replacement, marketing rules and common failure cases.
- [02-literature.tex](02-literature.tex): statutes and exceptions, dates and testing,
  normative languages, Stipula, process compliance, neurosymbolic methods, software
  and an approach to continued literature reuse.
- [03-product.tex](03-product.tex): reviewer workflow, typed rules, unknown evidence,
  obligations, verification targets, counterexamples and amendment management.
- [04-prototype.tex](04-prototype.tex): scope, staffing assumptions, sequence, local
  project reuse, independent evaluation, economics and implementation risks.
- [05-evidence.tex](05-evidence.tex): 15 initial acceptance cases, the source library
  and decisions needed when starting a bank prototype.
- [papers.bib](papers.bib) and [sources.bib](sources.bib): papers, regulatory sources,
  standards, software documentation and local inspection records.

## Build

Run from this directory:

```sh
latexmk -xelatex -interaction=nonstopmode -halt-on-error proposal.tex
```

The build uses XeLaTeX, BibTeX and latexmk; TeX Gyre Pagella, TeX Gyre Heros and
DejaVu Sans Mono fonts; and the LaTeX packages named in the preamble. It was built
with the existing TeX Live 2026 installation without installing extra packages.

[Review record](review.md) describes the document, citation and PDF checks. The
research snapshot is 21 September 2026. Regulatory examples use selected public
sources and synthetic facts; adopting them in bank systems requires the bank's
interpretation and implementation review.
