# Catala integration and teaching-order audit

28 September 2026. The main volume is **294 pages**, the technical companion is
**78 pages**, and the separately exported process guide is **10 pages**. Both
LaTeX entry points compile with the repository's XeLaTeX build. The current
two-volume document check passes. Independent reader acceptance remains pending.

This revision answers the request to incorporate the completed Catala work and
repair the monograph's linear teaching order. It uses the current worktree draft
as its immediate baseline, including work that was already uncommitted. It does
not claim authorship of those earlier additions or rerun their research campaigns.

## What changed

The process guide now introduces RuleIR as the project's small rule language,
Catala as a legal-rule language and compiler, and Stipula as a language for
contracts involving parties, resources and state changes. A consent-withdrawal
example gives Stipula a purpose before its name appears in the verification
discussion. The guide distinguishes the studied Stipula/Java/JML/KeY route from
LegalMath's implemented targets. Its old statements about an uninvoked Catala
compiler and unavailable scanned-text extraction have been corrected.

Chapter 3 now begins with the vocabulary needed by its preservation argument.
It follows a gift provision through a proposed reading, controlled language,
typed shared model and executable target. It introduces JML, KeY, s(CASP),
s(LAW), UCB and MCP by their roles. Chapter 4 introduces stable models before
discussing their implementation, and defines Clingo, DMN and L4 locally. Chapter
5 defines argument extensions before its mutual-attack example and introduces
Carneades and natural-language inference. The assurance sections introduce OCR,
MAPIE and TweetyProject. Chapter 9 defines exchangeability before invoking it.

One substantive error was repaired: when the request flag is true and the
material-query flag is unknown, their combined OR guard is **true**. That is
different from a default with one true sibling guard and an unknown competitor.
The text now explains both cases. It also distinguishes native Catala's checked
coalescing of identical literal consequences from the strict conflict policy
encoded by the compatibility backend and shared version-2 translator. The
RuleIR evaluator's `any` and `default` branches were inspected against this
explanation; no semantics were changed to fit the prose.

Chapter 8 teaches the shared frontend through a holdings calculation. Records,
lists, filtering, summation, options and payload variants are introduced before
the architecture table. Worked examples distinguish exact scaling from explicit
rounding and a known record field from an unresolved inclusion decision. The
chapter records the two Catala routes, versioned input policies, capability
failures, bounded vocabulary/resources, acyclic helpers, per-output evaluation
and the native tracing limitation.

Chapter 9 reports the retained results with their actual comparison targets.
The companion indexes the implementation records and reproduction manifests.
The main entry point now explicitly includes the existing chapter-six extensions
in their previous order. Those sections were already included indirectly;
the repair adds a transition and makes that structure visible, without counting
their prior work as newly written content.

The complete section-by-section review is recorded in
[chapter-audit.json](chapter-audit.json). The executive summary was tightened
to avoid an almost empty extra page. Table 9.1 was kept with its results so it
no longer interrupts the following section's opening paragraph. The README now
uses section names in place of stale physical-page references.

## Results reported, and their limits

| Evidence | What the manuscript says it establishes |
| --- | --- |
| 44 paired common-model cases | Agreement on the declared scalar profile with common model/interpretation identities and retained semantic traces. |
| Seven richer version-1 outputs | Implemented native Catala coverage that the RuleIR target explicitly rejects as unsupported. |
| Seven direct-converter programs, 48 final cases, six changed-program challenges and four forged execution records | Bounded computation and host-integrity evidence. |
| 344 decision comparisons, eight event cases and 202 regression tests | The earlier compatibility and host-behavior checks. |
| Four version-2 builds and 91 exact checks | Declared version-2 behavior checked against retained references and execution routes. |
| 792, 69 and 35 tests at successive checkpoints; 794 distinct identifiers | Regression accounting across checkpoints, not one final full-suite invocation. The later main integration has its own 30 focused tests. |
| Historical source-generation study: 19/24 slots, then a two-slot repair | Limited, exposed-source development observations with format/context and budget differences; no defensible quality ranking. |
| Zero human observations | No measured reviewer benefit, review-time reduction or comprehension improvement. |

The engineering result is a wider optional Catala profile behind a common
frontend. It is not universal Catala superiority, a new default, proof of source
interpretation, a comparative runtime result or approval for bank deployment.
The statistical and prospective-study qualifications remain in the main text.

## Verification

The [build run](build-run.json) records the exact command, Python environment,
commit, wall time and output log. The worktree was dirty; the revision manifest
therefore binds actual source hashes rather than treating the commit alone as
the identity of this edition.

| Check | Result and scope |
| --- | --- |
| `build_reader_facing_monograph.py` | PASS. Builds both volumes, settles cross-volume references, runs the current checker, refreshes proposal aliases and exports the process guide. |
| `check_reader_facing_monograph.py` | PASS. Ten main chapters; 100 archived documents; 240 citation occurrences bound to existing scoped judgments; 207 original source-unit labels. No undefined references/citations, missing characters, overfull boxes or clipped/empty pages. |
| Immediate-baseline preservation | PASS. All 42 mathematical display groups, all listings, all labels and all 240 citation occurrences remain. No citation key was added or removed. |
| `check_monograph.py` | PASS for its main-volume structural and source checks. |
| `check_monograph_mathematics.py` | Sixteen selected symbolic/example obligations give their expected outcomes, including the deliberately different old comparator; the Lean `MonographLogic` record is verified. This is not a proof of every statement in the book. |
| `check_monograph_prose_math.py` | Records 15 applicability reviews; proposed transfers to the product remain unreviewed, rather than being promoted by algebra alone. |
| Source-update check | Trusted rerun captured metadata for 38 DOI records; 14 records have no registered DOI in the manifest. Registration metadata is not an exhaustive correction/retraction search. |
| Rendered review | Whole-volume contact-sheet scan for layout, page geometry on every final page, and readable-resolution inspection of changed teaching, Catala and companion pages. The summary spill and comparison-table interruption were repaired and rechecked. |

There are 18 underfull-box notices in the main-volume log and 29 in the
companion, the same counts as the pre-edit draft. These are spacing diagnostics,
not compilation failures. The checked pages have readable text and no clipped
labels. A successful build and a layout inspection do not certify natural prose
or comprehension.

Three citation-context hashes changed because an introductory paragraph
separated an unchanged cited paragraph from a preceding figure input or section
label. Each exact difference was inspected. The source identities, substantive
cited wording and support judgments were retained; no new human review judgment
was manufactured. See [citation-context-review.json](citation-context-review.json).

The old one-volume citation, evidence-artifact and unification checkers were
also tried. They do not pass against the current edition: their line-based
occurrence sets, page/hash expectations and transformation baselines describe
earlier editions. Their observed failures are preserved under
[legacy-diagnostics](legacy-diagnostics/record.json); the pre-turn historical
reports were restored to their original locations. The temporary compatibility
edit to the old citation checker was reverted. The current checker was not
weakened to obtain a pass. Initial publisher-metadata failures were subsequently
resolved by the trusted metadata rerun, with the limitations above retained.

## Policy review and remaining judgment

The skeptical plan audit checked the immediate dirty baseline, the actual input
graph, comparison-policy differences, checkpoint accounting, historical/current
implementation boundaries, and the risk of treating compiler/test success as
interpretation quality. It passed after correcting the assumption that the
chapter-six extension files were not included. No new research run was needed
to write this edition.

The review applied the local scientific-coding, scholarly-literature and
humanizer policies together with the linear-narrative, scholarly-readability and
natural-analytical-prose skills. The changes keep necessary definitions and
mechanisms in the main narrative, preserve source and mathematical qualifications,
and reserve manifests and operational details for the companion or review files.
Words such as “artifact,” “interface” and “gate” were inspected in context;
their remaining uses principally describe actual software and control decisions.
Search counts were not treated as prose verdicts.

| Decision | Criterion status | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Deliver this manuscript revision | Requested Catala account and teaching repairs are present; current build and preservation checks pass | No unresolved build, citation-binding or clipping failure | A target reader may still find the long assurance discussion difficult | Read the revised PDF from the guide through Chapters 3–4, then the implementation/results sections | Independent human acceptance or complete policy certification |
| Retain the stated Catala conclusion | Claims match retained campaign records and explicit semantic policies | No unsupported superiority/default claim added | Finite engineering coverage and exposed-source study limitations | Use the declared profile; plan a fair quality study separately | Legal correctness, production readiness or a statistically supported language ranking |

The strongest alternative explanation for an apparent readability improvement
is that definitions have been added without sufficiently reducing the reader's
total conceptual burden. The remaining long chapter-six sequence is the clearest
place for target-reader feedback. If a reader cannot explain why RuleIR and
Catala can agree on one model yet implement different partial policies, or still
mistakes Stipula for an installed LegalMath backend, that is a repair trigger.
Author/model review cannot supply the missing human observation.

## Resume note

Start with this review, [manifest.json](manifest.json), the current
[two-volume check](../reader-facing/document-check.json) and
[preservation.json](preservation.json). The immediate baseline has also been
archived under `.localresources/monograph-catala-revision/` with hashes.
Use `python3 scripts/build_reader_facing_monograph.py` for later changes.
Preserve unrelated dirty worktree changes. Historical campaign and manuscript
reports keep their original dates, evidence scope and page counts.
