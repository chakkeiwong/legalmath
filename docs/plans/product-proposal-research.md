# Regulatory specification translator: proposal and literature review

## Intended decision and reader

Produce an extensive, cited LaTeX product proposal and compiled PDF for a Hong Kong
private-bank compliance sponsor and technical lead. Explain actual source clauses,
plausible implementation errors, the representational choices, the limits of proof,
and a bounded prototype with an independent evaluation. Synthetic cases must be
identified as such. Preserve the existing feasibility note and example.

The narrative follows a client decision from source text through interpretation,
facts, executable rules, operational events, and later amendments. Literature is
organized by the problems it solves, with an annotated source index for lookup.

## Skeptical preflight

The principal risk is a convincing proposal built on wrongly identified papers,
abstract-only reading, an incomplete legal dependency set, or proofs of the wrong
interpretation. The review will therefore retain full texts, record versions and
technical reading anchors, distinguish recommendations from measured results, and
inspect relevant official implementations. Citation counts do not establish
quality or applicability. The Catala compiler and local proof-search capabilities
must be described at their inspected scope, not promoted into legal correctness.

This is a document and source review, not a scientific benchmark. No performance,
cost-saving, extraction-accuracy, or production-readiness result will be invented.
Prototype acceptance criteria are proposals to be agreed, not observed results.
Use only public regulatory and research material. No bank/client records are needed.
The plan passes preflight on these terms. If a source is inaccessible, seek a lawful
author/preprint copy and explicitly record any remaining coverage gap.

## Work and evidence

1. Resolve the seven user-specified scholarly links, download the full texts, and
   preserve title/author/year/version/DOI/URL/SHA-256 metadata. Paper filenames use
   `Title, FirstAuthorSurname(year).pdf`, with filesystem-unsafe punctuation replaced.
2. Expand backward and forward references around Catala and Stipula and search the
   adjacent topics: legal default/deontic/temporal logic, Rules as Code, controlled
   language, decision models, LLM formalization, testing and verified compilation.
   Use ResearchAssistant discovery and parsing where available; record provider
   limitations. Read technical sections and relevant appendices before borrowing.
3. Build a source review ledger, SFC worked cases, and a literature-to-design mapping.
   Preserve distinctions among source findings, local deductions, and untested ideas.
4. Author the complete argument in LaTeX with a bibliographic database and build
   instructions. Introduce formal notation through the running case and interpret
   each important equation. Keep source-audit machinery outside the main narrative.
5. Compile, resolve references, inspect all rendered pages and detailed pages with
   figures/equations/tables, and audit source fidelity and bibliographic identity.

## Deliverables and completion

`docs/proposal/` contains the LaTeX source, bibliography, compiled PDF and build
instructions. `docs/papers/` contains full-text papers, a human-readable index and
machine-readable manifest. Research notes preserve checked sections, limitations,
search coverage, and proposal review. Completion requires a useful, substantial
proposal and verified local paper files, not a claim of exhaustive literature
coverage or human acceptance of prose. Human reader feedback remains pending.

## Completion note

The authored proposal and PDF are in `docs/proposal/`, with chapter sources,
46 bibliography entries, build instructions and a review record. The paper library
contains 25 valid PDF editions representing 24 works (530 pages), including all
seven requested sources. ResearchAssistant discovery and parsing records, citation
queries and inspected implementation material are retained under
`.localresources/literature-review/`. No adjacent repository was modified and no
bank integration or prototype benchmark was run. Document-validation details are
recorded in `docs/proposal/validation.json` and `docs/proposal/review.md`.
