# Review of the unified LegalMath monograph

22 September 2026. The deliverable is one author draft, **232 pages in ten
chapters**, combining the product proposal and interpretation-assurance
monograph. The canonical sources are [monograph.tex](../../monograph.tex) and
its chapter files; [monograph.pdf](../../monograph.pdf) is the canonical PDF.
The earlier [proposal.tex](../../../proposal/proposal.tex) includes that same
source, and its distributed PDF is a byte-identical copy.

## What was merged and why it has 232 pages

| Measured PDF | Pages |
|---|---:|
| Frozen product proposal | 66 |
| Frozen interpretation monograph | 153 |
| Sum of the two original PDFs | 219 |
| Unified monograph | 232 |
| Difference from the original sum | +13 |

The original proposal used 11-point typography; the unified book keeps the
monograph’s existing 12-point A4 setting, margins and line spacing. Shared front
matter and the bibliography have been consolidated. The expansion also includes
an account of the executed workbench. The earlier 150–200 page estimate was not
used to delete material or shrink the type. Page counts include front matter
and references and are measured by the preservation checker from the actual PDFs.

The argument now proceeds from the bank’s regulatory perimeter to two concrete
circulars, the meaning of a formal specification, the legal-language literature,
alternative interpretations, bounded ensemble investigation, Java verification,
implementation, evaluation and operation. The original proposal is integrated
where each question arises. It is not attached after the monograph or consigned
to an appendix. There is one title, introduction, contents and bibliography.

Chapter 2 teaches the complete 23EC35 SPI transaction before the selected 23EC46
gift restriction. The SPI case exposes data, timing, consent and Java execution;
the marketing example exposes the unresolved interpretation boundary. Chapter 4
combines the language and verification methods by mechanism. Chapter 5 brings
legal argumentation and search together with the bounded assessment of the
adjacent research projects. Chapter 6 retains the full 27-page ensemble design.
Chapters 7–8 connect it to the Java implementation and the complete workbench;
chapters 9–10 retain the manual-workflow comparator, business assumptions,
resources, operating controls and research limitations.

## Source and mathematical preservation

The [protected baseline](../../../../.localresources/unification/baseline/manifest.json)
contains both original PDFs, source trees and their prior review records. The
[content map](content-map.md) accounts for **207 body units**, comprising 67
proposal units and 140 monograph sections. Nested proposal inputs are included.
The [front-matter map](front-matter-map.md) accounts separately for the consolidated
introductions and disclosures.

The checker reconstructs each unit from its frozen source, applies the exact
recorded editorial changes, adjusts its heading and checks the result against
the actual destination block. It checks the declared source line boundaries and
hashes and independently enumerates the original units. It does not accept a
self-reported retention flag as evidence. All 207 comparisons pass.

All **33 original equation environments, 18 code listings and six figures**
remain identical after whitespace normalization. The two other display forms
counted by the broader surface diagnostic are also retained within their source
units. All **119 original labels and 76 cited entries** remain. Tables are
checked within the exact source-unit transformations; specified table changes
correct status and interfaces rather than silently remove rows. The bibliography
has 76 entries, all cited. Existing mathematical illustrations pass their
retained diagnostics, but this merge does not constitute a new independent
proof or source adjudication.

Twenty explicit edits in fourteen units repair stale status, relocated references,
one long filename and the first chapter’s transition. The old wording survives
in the baseline and the exact replacements and reasons appear in
[source-retention.json](source-retention.json). New framing and heading changes
are recorded separately. No original body unit, example, equation, figure or
listing was dropped to meet a page target.

## Execution coverage and current interfaces

The largest substantive addition is
[the executed-workbench account](../../chapters/08a-executed-workbench.tex).
It maps the original W work packages to T00–T24, records completion of T00–T22,
explains T23’s unrun effectiveness study and T24’s pending independent acceptance,
and distinguishes the proposed E01–E14 ensemble tasks. It follows source intake,
coverage review, compilation, tests, meaning review, Java preparation, release,
withdrawal, historical replay, amendment, host checks, export and restoration.
Current reproduction commands and all 22 current API paths are included.

Three stages of evidence are kept distinct. SPI-Demo1 is the earlier narrow Java
demonstration with its own interface and eleven consent histories. The later
MVP implements the wider RuleIR subset and its actual String/Map Java overloads,
with the retained 154-test and 35-case execution results. The interpretation
ensemble is specified, not implemented. The old proposal’s future-tense
statements about the review application, default expressions and full fixture
execution were corrected where they occurred; their earlier experimental limits
remain explicit.

The old service table is marked as design history. The current release flow
prepares build and verification identities before activation; the request uses
the implemented release-manifest identity and revision fields. Caller-supplied
roles cannot grant authority. The prototype’s local trust assumptions, fixture
provider, unsigned records and absence of bank integration are stated. The merge
checks **119 accepted runtime input identities** against the retained acceptance
record and its previously recorded browser-harness repair. These inputs remain
unchanged. No application test suite was rerun for this document task.

## Checks and rendered review

The standard command is:

```sh
python3 scripts/build_unified_monograph.py
```

It builds the canonical document, synchronizes the proposal PDF and runs the
manuscript and preservation checks through the compatibility validator. Individual
checks remain available as `check_monograph.py`, `check_unified_monograph.py`
and `check_proposal.py` under `scripts/`.

The proposal entry point was also built independently with:

```sh
latexmk -xelatex -interaction=nonstopmode -halt-on-error -cd docs/proposal/proposal.tex
```

All 232 pages match the canonical PDF in extracted text and rendered pixels.
[The entry-point check](entry-point-check.json) records both independent build
hashes before final byte-for-byte synchronization. Build metadata can differ
between independently produced PDFs; the standard build then distributes the
exact canonical bytes at both paths.

The document check inventories every rendered page, resolves citations and
references, verifies paper hashes, and checks text bounds. No undefined citation
or reference, missing character or overfull box remains. XeTeX retains eleven
nonfatal longtable-related “Infinite glue shrinkage” notices and 36 underfull
box notices. The affected source-inventory, software and execution tables were
inspected at normal resolution; no clipping or lost rows was observed in those
inspected tables. The build is not described as warning-free.

Targeted author reading covers **29 physical pages** of the final edition,
including the unified preface, both-case transition, chapter boundaries, diagrams,
long tables, actual Java interface, implementation table, conclusion and bibliography.
[The visual record](../visual-review.json) identifies exact pages and image hashes.
Twenty-one of those pages were read at the preceding checkpoint and have
byte-identical final renderings; eight were read in the final rendering. The first
chapter’s stale single-case transition was repaired and reread. The review also
removed real overflows in a long filename and the execution hash listing.
This is targeted integration review, not a continuous reading of all 232 pages.

The expanded-source surface diagnostic has no duplicate labels, missing targets
or unlabeled displayed equations. Its five repeated-word candidates are TeX
preamble names, a state transition followed by its state label, a heading followed
by its subject, and a Java type/variable pair. All six punctuation candidates are
formal grammar or shell commands. Those are retained deliberately. Four long
prose candidates are explicit scope, controller-test or execution enumerations;
the fifth concatenates code with prose during stripping. Length alone was not a
reason to alter their meaning. Unreferenced labels include the added retention
anchors and are not unresolved references. These counts are diagnostics, not a
readability score.

## Four separate judgments

| Question | Evidence and status | Remaining limit |
|---|---|---|
| Does the book provide one path through the problem and full execution? | Integrated chapter order, repaired transitions, complete two-case narrative and new execution account; targeted author inspection completed. | Independent whole-book reader acceptance is pending. |
| Has mathematical content survived? | Original displays, listings and figures retained; existing illustration checks pass. | No new independent mathematical verification of every source theorem occurred. |
| Has source content survived? | All 207 exact transformations, 76 cited entries and 119 labels pass; frozen originals and explicit edit reasons remain. | Preservation does not establish current legal authority or a correct English interpretation. |
| Is the built document usable? | 232-page build, all-page text/bounds checks, both-entry-point rendering comparison and 29-page targeted visual review pass. | Nonfatal layout notices remain; the whole book was not continuously reread visually. |

Independent legal, technical and reader acceptance remain pending. No live-model
study, production-bank deployment, new legal adjudication or Claude review was
performed. The strongest remaining risk is a shared interpretation error that
both the retained examples and the proposed ensemble would miss; the book
preserves that distinction and specifies how unresolved uncertainty blocks release.
