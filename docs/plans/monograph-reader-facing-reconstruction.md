# Reader-facing reconstruction of the LegalMath monograph

Date: 2026-09-24

Status: whole-volume reconstruction delivered for reader review; human acceptance pending

## Question

Can the monograph teach a senior management and compliance reader why a
regulatory interpretation must preserve scope, exceptions, evidence, time and
review responsibility, while still retaining the mathematical and engineering
record needed by implementers?

## Protected baseline

The current candidate is the 283-page PDF produced on 2026-09-24. Its source
and PDF are copied under
`.localresources/monograph-reader-facing/baseline/` before this rewrite. The
baseline is a comparison point, not a target for preserving its present order.

## Skeptical audit before editing

The current front matter fails the reader question: it spends several
paragraphs on T00--T22, E01--E09, test counts, hashes and source-preservation
machinery before stating the contribution in terms a senior manager can use.
Chapter 2 makes the same error locally. It introduces digests, extraction
offsets and software field names before explaining the business reason for
preserving an exact circular edition. Tables combine source location, legal
meaning, ownership and implementation treatment in one scan. A successful
LaTeX build would therefore be a false pass for the stated goal. The first
diagnostic is a rendered front matter and Chapter 2 review, with text checks
for unexplained identifiers and engineering chronology.

## Narrative spine

The recurring question is: **When a bank turns a circular into a decision, how
can it show that the decision still means what the circular required?**

The reader follows one SPI transaction and one marketing incentive. Each case
starts with a plausible shortcut, shows the fact that defeats it, introduces
one new distinction, and carries that distinction into a reviewable decision.
The formal language, competing interpretations, executable control and
operational record appear when the case needs them. Engineering details remain
available, but they are named as support for a business or legal consequence.

## Whole-volume scope

The user has clarified that Chapter 2 is an example of a volume-wide problem.
The reconstruction therefore covers the front matter and all ten chapters. A
chapter is not accepted merely because its opening is readable if later pages
return to unexplained fields, implementation chronology, or tables that make
the reader reconstruct the argument.

## Reconstruction work

1. Replace the front matter's production history with a short executive
   summary: problem, contribution, evidence completed, present boundary and
   management decisions required.
2. Reframe Chapter 2's source-preservation passage around reproducibility of a
   legal decision. Move digest and offset mechanics into a concise implementation
   note after the reader understands the purpose.
3. Split the two dense Chapter 2 inventories into prose-led explanations and
   smaller tables with plain-language labels. Keep the exhaustive mappings in
   the implementation record where they remain searchable.
4. Remove unexplained task identifiers from reader-facing paragraphs in the
   front matter and chapter openings. Preserve identifiers when they are needed
   to locate an engineering record.

5. Give every chapter a reader-facing opening and a visible question that the
   chapter answers. Audit later sections for the same failure before moving on
   to the next chapter.

6. Recast implementation, verification and evaluation material around the
   decision or risk it addresses. Move exhaustive schemas, endpoint matrices,
   task inventories and raw provenance to a clearly labelled implementation
   record or appendix when they are not needed for the main explanation.

7. Split or replace dense tables throughout the volume. A table remains only
   when the reader needs a direct comparison or lookup after the quantities have
   been taught in prose.

## Checks for the reconstructed candidate

- The first three pages answer what was done, why it matters, what evidence
  exists, and what remains before bank use.
- A reader can explain why an exact source edition and paragraph anchor matter
  before encountering a digest, offset, or validator.
- Every table in the repaired Chapter 2 has a stated comparison purpose, and
  its terms are introduced in prose before the table.
- The prose uses domain actors, decisions, evidence and consequences rather
  than production-history language.
- LaTeX builds and the rendered pages are inspected. Any lost equation,
  citation, source boundary or qualification is recorded before acceptance.
- Each chapter has at least one rendered review note identifying its live
  decision, the concepts introduced before they are used, and any remaining
  engineering material that needs a later appendix move.

## Structure decision after the first build

The first reconstructed candidate built at 290 pages with the former engineering
chapter and detailed tables included as appendices. Skeptical review found a
material flaw: this still made the bound volume partly an implementation report.
The next candidate separates those reproduction records into
`technical-companion.pdf`. All mathematical derivations, assumptions and worked
reasoning stay in the main monograph. Cross-PDF references identify the optional
record explicitly. This is an editorial split, not deletion or evidence of
improved comprehension. Preservation checks must compare the union of both
documents with the protected baseline, and check that all original displayed
equations remain in the main argument.

## Limits of acceptance

This rewrite cannot establish legal correctness, reader acceptance, production
readiness or measured business value. Human review remains pending. The phase
also does not erase the engineering record; it changes where and why that
record appears.

## Delivered candidate

The main volume is 235 pages and the companion is 69 pages. The front matter and
all ten chapters were revised. Every original mathematical display stays in the
main volume. Detailed tables, implementation chronology and reproduction records
are preserved in the companion, with cross-document references. Short tables use
ordinary-language comparisons, body-size type, more row space and placement next
to their explanation.

The skeptical audit was revisited after rendering. It rejected the first
single-volume appendix arrangement, the remaining cramped three-column tables,
tables floating into unrelated explanations, a split executive-summary paragraph
and diagrams retaining unexplained engineering terminology. These were repaired
before delivery. Page count, figure count and a successful build were not used
as evidence of human comprehension.

`python3 scripts/build_reader_facing_monograph.py` and the current document
checker pass. The review records 36 selected main-volume pages across every
chapter and five companion pages, with automated geometry checks on all 304
pages. See `docs/monograph/review/reader-facing/reconstruction-review.md` and
`delivery-manifest.json` for the final disposition and exact file identities.
