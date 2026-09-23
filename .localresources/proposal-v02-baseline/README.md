# LegalMath product proposal

[Read the proposal (PDF)](proposal.pdf) · [LaTeX entry point](proposal.tex)

Version 0.2 is a 45-page proposal with 62 references, detailed SFC worked cases,
an expanded technical literature review, fixed RuleIR semantics, and an
implementation plan with eleven dependency-ordered work packages. It assesses
MathDevMCP, DynareMCP and ResearchAssistant against inspected local code. The
runtime remains to be implemented; the supplied specification pack is checked.

An implementing agent should begin at [START-HERE](../implementation/START-HERE.md).
The [work packages](../implementation/work-packages.md) name modules, interfaces,
commands, failure conditions and completion evidence. The [semantics](../specs/v0.1/semantics.md),
[storage/API contracts](../specs/v0.1/contracts.md), three JSON schemas, SQLite
definition and [fixtures](../specs/v0.1/fixtures/decision-cases.json) settle the
first runtime's behavior. Cases include 35 decision inputs, six invalid variants,
eight event histories and four release-guard examples.

The [paper library](../papers/README.md) contains 38 PDF editions representing 37
works and 947 source pages, including all seven papers requested. The
[original technical notes](../papers/reading-notes.md) and
[expanded notes](../papers/reading-notes-v2.md) record inspected methods,
limitations, code and proposed borrowings. The [coverage ledger](../papers/coverage.md)
gives individual dispositions for 60 indexed records from two forward-citation
searches and lists unresolved retrieval and reading gaps. This is a bounded
technical survey of the prototype's design questions, not an exhaustive census.
The
[manifest](../papers/manifest.json) records versions, source URLs, page counts and
file hashes. Papers follow `Title, FirstAuthorSurname(year).pdf`, with unsafe title
punctuation normalized for portable filenames.

## Source organization

- [01-problem.tex](01-problem.tex): business problem, SPI examples, tokenisation
  replacement, marketing rules and common failure cases.
- [02-literature.tex](02-literature.tex): statutes, defeasible/deontic foundations,
  dates and testing, eFLINT, Symboleo, Stipula and amendments, process compliance,
  neurosymbolic methods, L4, software and continued literature reuse.
- [03-product.tex](03-product.tex): reviewer workflow, fixed typed rules, unknown
  and conflicting evidence, obligation/event semantics, verification targets,
  counterexamples, storage, APIs, source-to-decision walkthrough and amendments.
- [04-prototype.tex](04-prototype.tex): scope, staffing assumptions, sequence, local
  project reuse, independent evaluation, economics and implementation risks.
- [05-evidence.tex](05-evidence.tex): 15 source-based business scenarios, their
  distinction from language conformance cases, current checks and pilot decisions.
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

From the repository root, `python3 scripts/check_spec_pack.py` validates the
specification material; `python3 scripts/check_proposal.py` checks the built PDF,
bibliography, references, paper hashes and protected baseline. These use the
existing `jsonschema` and PyMuPDF installations. The latter writes
[validation.json](validation.json). The generator
`scripts/build_spec_examples.py` reproduces the schemas and supplied fixtures;
it is not a rule interpreter.

[Review record](review.md) records complete rendered-page reading, consistency
repairs, document/PDF checks and their limits. The
research snapshot is 21 September 2026. Regulatory examples use selected public
sources and synthetic facts; adopting them in bank systems requires the bank's
interpretation and implementation review.
