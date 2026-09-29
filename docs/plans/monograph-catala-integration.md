# Monograph update: Catala results and linear teaching order

28 September 2026. User authorization: update the monograph with the completed
Catala implementation and results, audit the whole `monograph.tex` teaching
sequence against the local scholarly-writing policies, repair concepts that are
used before they are introduced, and compile and inspect the resulting LaTeX/PDF.

## Human contract

The primary reader is a compliance, legal-technology or engineering reviewer who
can follow basic logic and software examples but should not need repository
history to understand the argument. The reader must be able to explain, in order:

1. why a circular cannot be treated as a single Boolean rule;
2. how source evidence becomes a reviewed interpretation and typed shared model;
3. what RuleIR and Catala each execute, and where their policies differ;
4. why Stipula is a stateful contract-language comparison rather than a LegalMath
   backend;
5. what the retained tests establish about implementation behavior; and
6. why none of those tests establishes legal correctness, universal Catala
   superiority or production approval.

The main volume must teach these relations where they first become necessary.
The technical companion may retain exact manifests, schemas and reproduction
details, but it cannot carry a premise required by the main argument.

## Baseline and source boundary

The baseline is the current main worktree at `aa20a84b`, including its existing
uncommitted monograph draft. A complete copy and status/diff snapshot is retained
outside the source tree at `/tmp/legalmath-monograph-catala-20260928/` before
editing. Unrelated assurance code, source files, papers and artifacts remain
untouched. The revision owns the canonical monograph sources, its companion
sources, the relevant build/review records, and the new plan/result note.

Catala claims are bound to the committed records under
`docs/implementation/catala/` and `artifacts/catala/`. The manuscript may report
implementation evidence, exact comparisons, resource limits and explicit
nonclaims. It must not turn finite conformance into a legal or statistical
superiority claim.

## Initial audit and skeptical review

The audit found four material problems:

- `frontmatter/process-map.tex` still says that the emitter does not invoke the
  Catala compiler and describes only the old restricted adapter;
- the final Catala campaign is documented in Markdown but has no reader-facing
  implementation/results section in the main volume;
- the newer `06a`--`06g` assurance sections exist as TeX files and are already
  included indirectly at the end of `06-ensemble.tex`, but they begin without
  a transition that explains how they continue the ensemble argument;
- the process map and early chapters use RuleIR, Catala, Stipula, KeY and other
  names before a common vocabulary tells the reader what kind of object each is.

The skeptical plan audit **passes with repairs required before compilation**.
The main risks are duplicated assurance material, an inflated chapter-six burden,
and a false impression that Stipula or Catala supplies LegalMath's legal meaning.
The repair is to add one early vocabulary bridge, state the shared frontend before
the target languages, introduce the Stipula state-machine distinction before its
examples, add a transition before the existing `06a`--`06g` sections, and repeat
the target/nonclaim boundary in the Catala results section. The independent
references, source citations, exact counts and historical dates are inherited
from the retained result records; no new experiment is required.

## Execution sequence

1. Freeze and inventory the baseline TeX/PDF, chapter inputs, citations, labels,
   displayed equations and the current rendered text. Write a confusion map for
   premature terminology, stale implementation claims and missing Catala results.
2. Repair the frontmatter process map so it introduces the vocabulary and current
   architecture: source and review, shared frontend, `LegalRuleModel`, RuleIR,
   Catala targets, and the separate Stipula contract-language route.
3. Add an early chapter-three bridge before the proof chain uses Catala or Stipula.
   Define each language/tool by its object and scope, then defer detailed examples
   to Chapter 4 and implementation results to Chapters 8--9.
4. Add a reader-facing Catala implementation section to Chapter 8. Explain the
   two Catala routes, the versioned shared model, explicit partial policy, native
   limits and the retained engineering evidence. Add the exact nonclaims.
5. Add a Chapter 9 evaluation section that distinguishes common-fragment
   agreement, Catala-only richer coverage, and the absence of a performance or
   conversion-quality ranking. Use the 44 paired cases, seven rich outputs, 91
   exact checks, 344 earlier backend comparisons, and 794 distinct regression
   IDs only with their documented scope.
6. Add a short transition after the original ensemble chapter. Keep the existing
   `06a`--`06g` inputs in their argument order, and repair their opening
   references where required so the reader sees source inventory, comparison,
   execution, input meaning and proof-carrying integration as one continuation.
7. Add the Catala evidence and reproduction boundary to the technical companion
   appendix. Preserve exact source paths and keep raw manifests out of the main
   narrative.
8. Compile with the repository's XeLaTeX/`latexmk` route. Run structural,
   citation, mathematics, source-update and reader-facing checks; inspect the
   rendered PDF in ordered page segments and inspect the changed Catala and
   terminology passages at normal resolution. Record warnings and repairs.

## Acceptance contract

The result must compile without fatal LaTeX errors, undefined references,
undefined citations, missing characters or off-page text. `monograph.tex` must
include every intended chapter-six section, all terminology used before detailed
discussion must have a local definition or a clearly signposted forward route,
and the old “does not invoke the Catala compiler” claim must be absent from the
current account. The PDF must contain the Catala architecture, evidence counts,
comparison limits and Stipula boundary. Structural and rendering checks are
engineering evidence only; independent reader acceptance remains pending.

The result note will include the actual commands, source/PDF hashes, page count,
diagnostic status, changed files, strongest alternative explanation for any
readability conclusion, and the remaining human-review boundary.

## Completion: 28 September 2026

All eight execution steps are complete. The delivered pair contains a 294-page
main volume and 78-page technical companion, with a ten-page exported process
guide. The result and resume note are
`docs/monograph/review/catala-update/review.md`; source/PDF identities, commands
and the dirty-worktree boundary are in its `manifest.json` and `build-run.json`.

The immediate baseline is also archived under
`.localresources/monograph-catala-revision/`. Its 42 mathematical display groups,
listings, labels and 240 citation occurrences are preserved. The current
two-volume checker, main-volume checker and selected mathematics checks pass.
Three unchanged cited paragraphs received explicit editorial context rebinding
after definitions separated them from preceding figure inputs or labels.

The input-graph audit corrected the initial suspicion that sections 06a–06g
were missing: they were already included at the end of `06-ensemble.tex`.
Their inputs now appear explicitly in `monograph.tex` in the same order, after
the added transition. No duplicate section was introduced.

The final skeptical review confirms that the Catala counts retain their separate
targets and checkpoint dates, different partial policies are not compared as
identical semantics, and deterministic conformance has not become a claim about
legal quality, runtime superiority or human benefit. The corrected OR example
and native/shared conflict distinction resolve substantive issues found during
the teaching review. Rendered inspection repaired the summary spill and a table
that interrupted the following section.

Independent target-reader acceptance remains pending, as required by the writing
policies. It does not prevent delivering this explicitly provisional draft.
