# BASF source-order repair

Baseline: `bada667759a7d9f87ffc01235ff3a012601f5b75`, with the completed,
uncommitted INCEpTION integration preserved. The source comparator is the retained
BASF September 2022 base prospectus, SHA256
`aac3da33755fae327f7542a9be08008d53d1dbcdfa3b01596e48d97debe1cfef`,
German Option I, file/printed pages 108–133. The historical construction comparator
is adoption A1 attempt-004. Its output and source graph remain immutable.

## Question and evidence contract

Does the construction's top-edge sort reorder fragments on the same printed line,
and can source-reviewed occurrence permutations correct that order without
changing, deleting or inventing any source character? On page 120 the retained
graph puts `[Falls` at y=605.6506 and preceding words at y=607.42336, while their
bottom edges differ by only 0.02844 points. The current constructor moves the
opening bracket before `des betreffenden Clearing Systems ausgewählt.`. An intact
character inventory therefore does not establish faithful reading order.

The primary criterion is agreement of every changed occurrence order with its
rendered original row, plus unchanged raw unit bytes and complete occurrence
coverage. Independent source quotations anchor the regression expectations.
An unreviewed changed row, stale edition/text/geometry, duplicated/missing unit,
overlapping ambiguous fragments, altered source character or broken downstream
source map vetoes promotion of this repair. Corrupt originals/comparator or an
exceeded runtime/storage budget stops the affected run. A failed ordering candidate
triggers the next bounded repair; pending legal review does not stop source work.
Interval/bracket counts and runtime are explanatory, never completeness criteria.

No complete German contract, resolved incorporation, legal interpretation,
independent human reading, corpus accuracy or production readiness follows.
Results, image review, commands, code/input hashes and refreshed next steps go in
`docs/implementation/prospectus-basf-source-order/`.

## Skeptical audit before execution

The next-program instruction to review all unresolved clauses assumes that the
candidate already preserves printed reading order. Inspection disproves that
assumption, so ordering is repaired first. The comparator is the original PDF,
not the existing candidate, OCR score or another parser's prose. The source slice
and exact characters stay fixed. The existing Poppler source graph remains the
baseline; the rejected Docling trial is not reopened.

The first diagnostic only nominates rows whose fragment bottom edges are within
0.25 PDF points. This is a convenience hypothesis motivated by the observed
0.02844-point difference, not a universal reading-order rule. It must also reject
horizontal overlap; rendered inspection determines every admitted permutation.
Do not deploy that tolerance as a new unreviewed extractor default. Prefer a
small edition-bound list of checked occurrence orders if that fully repairs the
observed cases. If the diagnostic exposes whole-column interleaving or cannot
preserve source maps, revise this plan before implementation.

The application environment is the existing `.venv/bin/python`, with worktree
`src` on PYTHONPATH and `CUDA_VISIBLE_DEVICES=-1`. No models, downloads or external
communications are required. Diagnostic, render and focused-test commands each
have a 180-second bound. The adoption verification retains its existing
1800-second per-command bound and immutable attempts. Stop after three attempts
with unchanged method/input; all failures remain visible. New evidence is bounded
to 200 MB. No historical repair verifier is run.

Audit verdict: PASS for the diagnostic and source-review-first sequence. The
hidden default, comparator, environment, stop conditions and downstream check
are explicit. A green test count cannot discharge unresolved legal/source work.

## Execution and refresh

1. Inventory all changed-row candidates over pages 108–133, binding the historical
   graph, construction and original PDF. Render and inspect each affected source
   row; record exact unit order and why top-edge order is wrong.
2. Implement only the source-reviewed ordering correction in the existing BASF
   constructor, with strict stale-source and geometry guards. Preserve raw units,
   occurrence identities and source/character maps. Add regressions for real
   source wording, stale/ambiguous records, and exact interval conservation.
3. Run focused source checks, then the existing adoption verification when the
   correction passes. Current code invalidates historical receipts; create new
   attempts, preserving earlier results. Do not rerun the unchanged INCEpTION
   server exchange.
4. Record the engineering decision and the strongest alternative explanation.
   Refresh NEXT-PROGRAM.md with the next unresolved source obligation. Missing
   independent legal acceptance is a promotion veto, not a reason to abandon
   remaining source reconstruction.

Pre-mortem: a geometrically plausible order can still be wrong in tables or
multiple columns. Every admitted changed row therefore needs the original image,
exact source identities and a specific implementer judgment. A zero-gap interval
account can coexist with wrong word order; test explicit source sentences and
map replay as separate obligations. Human legal acceptance remains separate.

## Source inspection and plan correction

The first diagnostic nominated four rows on pages 111, 120, 121 and 124, with no
horizontal overlap. Direct inspection of all four original page images confirms
the three prose corrections: the final-coupon field follows `belaufen sich auf`
on page 111; `[Falls die` follows the complete clearing-system sentence on both
pages 120 and 121. Page 124 is a two-column label/address block: exchanging just
the nominated row would still interleave the columns. The current text even
leaves `Zahlstelle:` behind after the Canadian branch is excluded.

Revised implementation unit: five explicit occurrence permutations, covering the
three prose rows and both complete Fiscal Agent label/address blocks on page 124.
Each table block reads its complete left label, then the right address/field.
The calculation-agent block already follows that order. Bind every affected
unit's exact text, page and box, require a contiguous complete old span, and apply
only a permutation. No geometric tolerance enters the constructor. Preserve this
review in a packaged Python data constant so installed behavior does not depend
on external documentation or a new packaging rule. Record the applied ordering
decisions in the construction result.

Re-audit: PASS for implementation of these five source-inspected permutations.
This repairs the observed whole-column issue before branch parsing; it does not
certify all table attachment, margins, legal scope or remaining construction.
