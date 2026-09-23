# Proposal review record

Date: 21 September 2026. Scope: authored proposal and source library, not an
implementation benchmark, legal opinion, or replay of published proofs.

## Source and technical review

The proposal is based on inspected SFC circular bodies and SPI annexes, 24 scholarly
works in 25 editions, standards, official software documentation and selected code,
and local inspection of the three adjacent projects. Paper-specific technical
anchors and adoption limits are in `../papers/reading-notes.md`. Retrieval coverage
and inaccessible secondary leads are in `../papers/README.md`. All seven explicitly
requested papers have valid local full texts.

The skeptical preflight is in `../plans/product-proposal-research.md`. The main
risks were abstract-only recommendations, proofs of a mistranslation, source-version
confusion, and importing benchmark results into a different domain. The draft
addresses these by separating interpretation, computation and factual evidence;
recording editions; and describing proposed evaluation rather than claiming bank
accuracy or savings.

Specific findings preserved in the draft:

- The SPI financial test is an alternative with inclusive boundaries, distinct
  from the complete SPI assessment or a transaction permission.
- Product-category experience, client identity, consent and the two monitoring
  approaches remain separate conditions or event rules.
- Tokenisation examples preserve actors, SFC-request triggers and the distinction
  between consultation and approval; source replacement does not supply all
  effective-date or transition details.
- Catala's core translation result is not an end-to-end verified legal compiler;
  the inspected formalization notes disclose an admitted supporting lemma.
- Stipula's reachability DI restriction differs from the Java/JML paper's
  disjoint-cycle construction. Bounded trace results retain their bounds.
- ARc's reported soundness is an empirical metric, not a semantic theorem. Its
  precision, recall and repeated-item denominator are identified.
- Reviewed tax rules and annotated examples alter the information and human-work
  budget of a benchmark. Its cost model is not a Hong Kong compliance cost model.
- The current MathDevMCP controller is not described as MCTS; DynareMCP's historical
  UCB scheduling is an investigation pattern, not a legal truth criterion.

The money expression and truth table were checked against their stated definitions.
The numerical boundary witnesses were checked by direct substitution. The
implementation-equality statement is explicitly a future verification objective;
the event transition is a proposed model; the break-even relation is derived from
the costs defined immediately before it. No unperformed solver check is reported.

## Document checks

The build uses `latexmk -xelatex -interaction=nonstopmode -halt-on-error proposal.tex`
in this directory. XeLaTeX and BibTeX resolve the citations and internal references.
The final build log is retained locally. A citation-key audit checks that the 46
referenced entries exist and are unique. The paper integrity audit checks PDF
signatures, PDF readability, page counts and SHA-256 values for all 25 PDFs, totaling
530 source pages.

Rendered-page review covers page layout throughout and detailed inspection of the
cover, contents, diagrams, financial equations and truth table, verification
equations, implementation sketch, software comparison, prototype schedule,
evaluation table, acceptance cases and bibliography. Layout repairs removed an
overlong inline filename, a duplicated page destination, title hyphenation and an
unnecessarily split contents page. All substantive qualifications and equations
were retained.

The scholarly surface audit is a structural diagnostic only. It checks labels,
references, equation labels, repeated words and placeholder candidates; it cannot
certify human readability. Its long-sentence candidate was revised in the
literature-synthesis passage. Source and build findings are preserved in
`validation.json`; temporary page renders and the full diagnostic output are under
`/tmp/legalmath-proposal-review/`.

## Remaining review

This is an authorized research/design draft. Human acceptance of its prose and
bank compliance adjudication of the examples remain pending; neither is claimed
by a clean document build. No third-party software performance, extraction accuracy,
production integration, or savings result has been measured. A selected-source
study does not establish that every applicable requirement has been collected.

The next justified step is the bounded discovery phase in the proposal, beginning
with the bank's business perimeter, interpretation owners and independent cases.
