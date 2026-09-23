# Reset memo: interpretation assurance monograph

22 September 2026. The requested deliverable is a self-contained, implementation-ready
book on competing interpretations, ensemble redundancy, bounded automatic resolution
and complete uncertainty reporting. The author draft is complete.

## Current state

- `docs/monograph/monograph.pdf`: ten chapters, 153 pages, 46 cited references.
- `docs/monograph/chapters/06-ensemble.tex`: the 27-page central synthesis.
- `docs/monograph/implementation-guide.md` and `implementation-plan.json`: concrete
  integration contracts and fourteen ordered extension tasks, E01–E14.
- `docs/monograph/contracts`: ten proposed schemas, explicit fixture policy and a
  complete synthetic blocked investigation. The ensemble service is **not implemented**.
- `docs/papers`: 50 PDF editions of 49 works, 1,298 pages. Three newly inspected
  uncertainty/ensemble papers and official code observations are documented in
  `reading-notes-ensemble.md`.

The final identities are bound in `docs/monograph/review/delivery-manifest.json`.
The full author-draft baseline is protected under
`.localresources/monograph/baseline/full-author-draft`; the earlier proposal,
second-circular source/oracle, semantic contracts and research notes are separately
bound by `baseline/input-manifest.json`. All thirteen protected inputs are unchanged.
All 119 accepted runtime inputs match the prior acceptance record, with its already
documented browser-harness repair accounted for. This task did not change the runtime.

## Decisions not to rediscover

Use blind, frozen initial interpretations and an independently constructed source
inventory. Agreement cannot establish completeness. Generate consequential alternative
readings, preserve their assumptions and use scenarios to expose different outcomes.
Search scores and repeated model answers are not calibrated probabilities of law.

Every discrepancy enters reconciliation. A typed, validated reason may close a
cosmetic difference; unknown materiality blocks. Use immutable issue roots, global
and per-root action limits, round limits, enforced deadlines and no-progress checks.
Charge actions atomically before dispatch, retain timeout/crash charges, disable or
separately account for hidden provider retries, and retain complete terminal reports.
Reopening an investigation requires a linked, explicitly authorized successor run.

The first scheduler is deterministic and specified in chapter 6. Optional argumentation
and search in E13 must obey the same budget and reporting rules. Initial parameter
values are fixture choices, not empirically justified production defaults. The
proposal explains a limited termination argument, conditional on accounting and
infrastructure assumptions; it does not prove natural-language interpretation.

Keep pre-report issue adjudication separate from post-report final review; otherwise
report and approval hashes become circular. Preserve the existing bundle/build/
verification/release chain and actual Java String/Map APIs. Reports never authorize
release on their own. A bank operating policy is distinct from an accepted reading
of the regulator's rule.

## Verification and review

Commands actually run from the repository root:

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error -cd docs/monograph/monograph.tex
.venv/bin/python scripts/check_interpretation_contracts.py
python3 scripts/check_monograph.py
```

XeTeX/TeX Live 2026, latexmk 4.88, Python 3.11.15; the existing project environment
provides jsonschema 4.26.0. These are CPU document/schema checks, with no accelerator,
paid model, bank operation or Claude invocation. No full application test suite was
rerun; the retained 154-test acceptance remains earlier engineering evidence.

| Decision | Primary criterion | Veto checks | Main uncertainty | Next justified action | What is not concluded |
|---|---|---|---|---|---|
| Deliver completed author draft | Requested chapter/page range and substantive method/design present | Build, references, source hashes and contract diagnostics pass | Independent legal, technical and reader judgments remain pending | Begin bounded engineering implementation from E01, with task-specific audit | Correctness of unrestricted English interpretation or bank readiness |
| Retain ensemble as proposed extension | Explicit contracts, controller and acceptance scenarios specified | Sixteen invalid contract examples rejected; finite budget/release diagnostic passes | Real concurrency, providers, reference judgments and error reduction are unevaluated | E01–E09 scripted vertical slice before live providers | An implemented or empirically superior ensemble |

All 153 PDF pages were text-extracted and inventoried. Selected normal-resolution
pages were inspected and repaired; exact review stages are in
`docs/monograph/review/visual-review.json`. This is author review, not continuous
visual reading of the whole book or independent scholarly acceptance.

The strongest alternative explanation for apparent ensemble success is shared
omission or a reference corpus written by the same model. A passing fixture cannot
exclude it. Chapter 9 specifies independent references, held-out circular families,
fair budget comparisons, risk/coverage and uncertainty evidence before a performance
claim. The weakest present evidence is the absence of that live independent study.

## Next action

The first implementation task is E01, contract models and policy. Read chapters 6–8,
the integration guide, current v0.1 implementation closure and the task graph before
editing. Implement validated records and explicit policy rejection; preserve the
existing accepted runtime and frozen oracle. Pass its negative contract checks and
record task evidence before E02–E06 depend on the models.

E01–E09 form a scripted vertical slice. Its six end-to-end fixtures cover a repaired
omission, persistent ambiguity, unanimous omission, budget/crash boundary, amendment
invalidation and recovered failure reporting. E10 introduces restricted providers;
E11–E12 require independent reference/evaluation work. The existing 23EC46 packet
remains DRAFT with unresolved dependencies; this book does not adjudicate them.
