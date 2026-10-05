# Handoff to Claude: review the entire legal interpretation program

Prepared 5 October 2026. Review status: **not yet dispatched**.
Workspace: `/home/chakwong/python/legalmath`.

## Assignment

Review the whole proposed program for repairing substantive English legal
interpretation and case-law reasoning. The user requested a monograph treatment,
a detailed implementation program with concrete phases, a thorough program review,
and this handoff. Your task is a skeptical **read-only program review**, not
execution, a further provider campaign or final product approval.

Do not edit the program, application code, source evidence, grants or historical
results. Return your review as text. If the supervising user/agent requests a file,
write only your review to
`docs/implementation/legal-interpretation-program/claude-review.md`.
That file does not exist merely because this memo names it.

Do not launch subagents, model/API calls, dependency installations or long
experiments to produce this review. Inspect retained literature and code. If an
essential question cannot be checked, say NOT_CHECKED and identify the smallest
missing observation. Do not use reviewer agreement as legal quality evidence.

## Context that must survive the handoff

The product's existing orchestration and formal checks do not close the English
interpretation gaps. The current audit records 35 readings in two roles, all
46 original challenge obligations still open, and zero accepted substantive
repairs in the selected package. The 20 mechanical guards / 1,040 synthetic
checks concern declared program behavior. Counts are tied to that audit and must
not be represented as a new experiment.

The pilot concerns the retained **26EC22 circular revised on 20 April 2026**:
paragraph 10's responsibility/supervision/adequacy meanings, paragraph 14's
confirmation and request-qualified demonstration, footnote 5's wording, and the
separate verification/opinion duties in paragraphs 15/16. Case-law methods may
help, but no judgment was established in this review as resolving those disputes.

The controlling product requirement forbids human answer keys, ratings,
adjudication, preferences and approvals as quality evidence. Published legal
texts and formal specifications are premises. A correctly qualified unresolved
result is permitted; blanket abstention that avoids useful supported computation
is inadequate. Current natural-language correctness and unrestricted future
generalization remain NOT_ESTABLISHED.

P0–P8 are **planned, not executed**. The phase manifest is an index, not a new
autonomous runner. The existing
`.venv/bin/python scripts/assurance_evidence_master.py ops-run`
belongs to the old provider campaign and must not be used to run this program.
No fresh call allowance or expiry extension follows from these documents.
The program is not the separate prospectus project.

## Verify the reviewed version

From the workspace root, the following read-only command verifies the final
review package files:

```text
sha256sum --check --quiet docs/implementation/legal-interpretation-program/handoff.sha256
```

If a listed file has changed, identify it and distinguish review of the frozen
version from review of the current file. Do not silently refresh the hashes.
The JSON `handoff-manifest.json` distinguishes authored deliverables,
supporting source/code identities and documentary validation. Historical inputs
must remain unchanged. The baseline snapshot lives under
`.localresources/legal-interpretation-program-2026-10-05/baseline/`.

## Required reading order

1. [Controlling product requirement](../proof-qualified-generalization/product.md)
   and [product gap audit](../assurance-evidence-master/product-gap-audit-2026-10-05.md).
2. [Master program](../../plans/legal-interpretation-master-program.md), completely.
   Inspect background, proposed interfaces, evidence contract, assumptions,
   dependency graph, repair/refresh procedure, commands and closure map.
3. [All nine phase plans](../../plans/legal-interpretation-program/README.md),
   in order, and [phase-manifest.json](phase-manifest.json).
4. Monograph [LaTeX addition](../../monograph/chapters/06m-legal-interpretation.tex)
   and [rendered PDF](../../monograph/monograph.pdf), section **6.40**,
   “What case law can contribute to an interpretation.” Inspect the revised
   title/executive summary as well. Page locations are in documentation-review.md.
5. [Retained research review](../../research/legal-interpretation-reuse-2026-10-05.md)
   and its cited technical sources. Inspect source snapshots for contested
   implementation claims; do not rely only on this author's summary.
6. [Author program review](program-review.md), [documentation review](documentation-review.md)
   and [validation.json](validation.json). Challenge their conclusions rather
   than treating them as independent endorsements.

The relevant actual code interfaces are:
`src/legalmath/interpretation/contracts.py`,
`src/legalmath/interpretation/search/models.py`,
`src/legalmath/interpretation/assurance/source_references.py`,
`qualification_adapter.py`, `complete_investigation.py`,
`investigation_observations.py` in the same assurance directory, and
`src/legalmath/translation/model.py`.
The proposed `interpretation/semantics/` package and its tests do not yet exist.
Verify proposed compatibility against these actual interfaces.
Their reviewed worktree versions are preserved under
`.localresources/legal-interpretation-program-2026-10-05/reviewed-interfaces/`,
using the same `src/` paths. Start with those frozen copies: the documentation
commit intentionally does not publish the unrelated application edits.
Each manifest entry names both the snapshot and the original worktree path.
Current checkout code may differ; identify that difference instead of silently
assuming the reviewed worktree was identical to the committed application.

## Required substantive challenges

- Is any part merely a new representation of supplied judgments, with no actual
  plan to justify source-to-predicate or source-to-rule steps?
- Can the pilot distinguish retained authority, exercised supervision and achieved
  adequacy? Does it keep confirmation, demonstration, verification and legal
  opinion separate, including the unresolved footnote?
- Does every material assumption have provenance, a failure mode, an early check
  and an honest status? Examine graph semantics, ordering, negation, types,
  partial dates, proof standards and resource caps.
- Does case reasoning preserve findings versus allegations, submissions versus
  holdings, majority versus dissent, material facts, procedural posture,
  jurisdiction, date and later treatment? Does “no contrary case found” remain
  limited to search coverage?
- Is the proposed reference independent at both argument construction and
  extension evaluation? Can the plan detect a wrong graph as well as a wrong
  extension?
- Are phased interfaces feasible without breaking strict legacy schemas,
  changing historical evidence or creating an import cycle? Notice the
  16-node legacy search limit versus the distinct proposed prototype bounds.
- Are incomplete/unsupported branches counted? Can an empty result or
  always-abstaining implementation pass? Can a missing compiled target be
  presented as completed execution?
- Does the actual complete investigator call the new machinery and verify its
  outputs? Do explanations and summaries retain the qualifications?
- Are any formal theorems, synthetic tests, citation metrics, model votes or
  externally human-labelled benchmarks promoted beyond their evidence?
- Does every phase have concrete inputs, deliverables, checks, failure decisions
  and an actual next-phase refresh? Are there hidden dependency cycles or
  legal-uncertainty conditions that accidentally stop repair work?
- Is future evidence genuinely prospective and separated from later repairs?
  Does the program distinguish preparing a window from observing it?
- Are licence findings and version claims accurate? In particular, do not treat
  SARA-IE as licensed for reuse or a nested CLERC licence as covering all code.
- Is the new monograph argument technically faithful, self-contained and
  readable? Does it preserve the meaning of the disputed source instead of
  making an attractive but unsupported promise?

## Response format

Lead with **PASS_FOR_BOUNDED_IMPLEMENTATION**, **REVISE_BEFORE_IMPLEMENTATION**,
or **NOT_CHECKED**, and explain exactly what that verdict covers. It is a verdict
about this program's readiness for the next implementation step, not legal
correctness or product release.

Give severity-ranked findings. For each finding provide:
identifier; blocking/nonblocking status; exact path and line/section; mechanism of
failure; a concrete counterexample or source/code evidence; affected phases;
smallest proposed repair; and the check that would establish the repair.

Then give a phase-by-phase verdict for P0–P8, list material assumptions still
unexamined, and state which files/source sections you actually inspected.
Separate program defects from legal questions expected to remain unresolved.
If no blocking finding remains, give at least the strongest alternative
explanation and weakest remaining evidence; do not return a generic agreement.

Finish with the next executable development step and any genuinely required input.
Do not request fresh approval for authorized local editing on the future
executor's behalf, and do not treat old campaign allowances as new permission.

## What has and has not been done

The author added the literature argument to the canonical monograph, created the
master and nine phase plans, repaired issues found during author review, built
the PDFs and checked the changed pages and source/citation preservation.
The detailed results and final hashes accompany this memo.

Claude has not reviewed the program yet. No product phase, new dependency
installation, prospective observation or provider assessment was executed as
part of this documentation task. Your review should therefore focus on whether
the proposed implementation would answer the substantive questions honestly.
