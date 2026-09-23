# Proposal v0.2 review record

Date: 21 September 2026. Scope: research, product design and implementation
specification. No application benchmark, bank deployment or published proof replay.

## The repair and its evidence

The user rejected v0.1 as rushed, incomplete in its literature survey and not
sufficiently concrete for implementation. That verdict is retained. Its 34-page
PDF and 22 companion files are protected in
`.localresources/proposal-v01-baseline/`; every recorded digest remains unchanged.
The reconstruction plan is `../plans/proposal-v2-reconstruction.md`; the complete
baseline reading and unit/equation map is
`../plans/proposal-v2-reader-diagnosis.md`.

The revised proposal is 45 physical pages with 62 cited references. The important
change is a startable design: fixed types/operators, unknown/conflict/default
semantics, an event profile, source identity, review transitions, database layout,
API behavior, exact decision cases and eleven implementation work packages.
These settle routine engineering choices while leaving legal interpretation and
bank data meanings with their owners. The runtime has not been implemented.

## Literature and source review

The library contains 38 usable PDF editions representing 37 works and 947 pages,
including all seven user-supplied sources. Thirteen editions were added in this
revision. Technical reading is documented in the original and expanded notes;
page count measures retained material, not a claim that every appendix page was
read. Methods, definitions, relevant theory/evaluation and relevant appendices
were inspected for the mechanisms adopted. The expanded review covers defeasible
logic, input/output logic, strong and weak permission, violations/reparation,
obligation taxonomies, eFLINT's original and stable-model semantics, Symboleo,
LegalRuleML/process compliance, Stipula amendment/liquidity and LegalBench.

The saved Catala and Stipula forward searches contain 65 raw records and 60
distinct indexed identifiers. Every one has a disposition in `coverage.md` and
`citation-screening.json`: 15 retained technical records, 15 relevant unresolved
follow-ups, 13 background/deferred records and 17 title/metadata exclusions.
Indexed identifiers are not distinct works. Broader search captures are not all
claimed as screened or read. The stop criterion is coverage of eight architectural
families, not an exhaustive review or citation-network saturation.

ResearchAssistant supplied isolated discovery and PDF parsing. Provider errors,
failed publisher retrievals and narrower official/author alternatives are
recorded. L4's paper and the later Symboleo journal paper remain retrieval gaps;
claims use inspected official documentation and the retained Symboleo preprint.
The 2023 Stipula amendment manuscript is distinguished from the unretrieved 2024
chapter. Unread recent comparators remain visible follow-ups.

Original software inspection includes the earlier Catala, Stipula–KeY and
neurosymbolic code checks, plus eFLINT's published Clingo source artifact and L4
and Symboleo repository documentation. The eFLINT release's expected interpreter
differences and excluded cyclic-aggregation/unsatisfied cases are retained as
limits. No published benchmark, compiler proof or model-checker experiment was
rerun. The three adjacent MCP projects were inspected at the recorded revisions;
their environments were not changed. ResearchAssistant parsing/discovery is the
specific executed local reuse, not evidence that all three integrations work.

## Substantive consistency checks and repairs

- The financial condition remains an inclusive alternative, distinct from full
  SPI classification and transaction permission. HK dollars in exposition map
  explicitly to integer HK cents in the fixtures.
- The paragraph 3.1 anchor covers the complete source paragraph. Raw PDF,
  derivative text, span digest and physical page are checked. Synthetic validity
  intervals are marked as test settings; wealth definitions, applicability and
  legal effectiveness remain open review issues in the financial bundle.
- Unknown is distinct from zero, false, conflict and out-of-scope. Static conflict
  checking includes skipped branches; known Boolean outcomes have no blocking
  unknowns. Sibling exceptions conflict even if their values agree.
- Consent absence requires a complete history or a reviewed initial snapshot
  followed by complete history. Fixtures now state their completeness premise.
  Obligation breach requires an evidenced observation window. Late performance
  preserves a supported breach; late-arriving timely evidence creates a corrected
  replay without erasing the earlier assessment.
- A changed bundle always needs approval and an evidence report for its new
  hash. Dependency-based reuse of individual tests cannot reuse release authority.
- The pure evaluator receives an explicit mode; service/export checks enforce
  production authority. The response schema includes mode and deterministic
  diagnostics. The future runtime checker validates the full response before
  comparing expected projections.
- JSON Schema structure checks are separated from cross-reference, typing and
  cycle checks. The written semantics defines runtime behavior; the interpreter
  must implement it rather than silently becoming the specification.
- The solver's knownness encoding follows the stated three-valued tables. Its
  initial fragment excludes dates, scale, defaults, events and conflicting input
  evidence. Empty domains, timeout and unsupported constructs cannot pass as
  equivalence. No solver or proof result is claimed from the delivered fixtures.
- Fifteen source-based business scenarios remain distinct from 35 language cases.
  Release examples state their other guard premises. Work packages require more
  normalization, event, concurrency, mutation and source-derived tests.
- W01 imports the SPI source/annexes; W08 adds the other pilot sources and general
  pagination. The implementation entry point now links to the actual fixture
  file. All six original numbered equations and their qualifications are retained;
  three new equations explain normative outputs, duty timing and solver knownness.

## Ordered reading of the rendered manuscript

Every page was read as an individual rendering at 1.35x PDF resolution, in order,
in the segments below. This was author self-review, not a fresh independent or
human review. The baseline was also read completely before reconstruction.

| Physical pages | Reader's dependency and inspected material | Assessment/repair |
| --- | --- | --- |
| 1–6 | Investment, contents, perimeter, financial/ownership/category examples | Scope and units precede formalization; title/contents readable; synthetic status clear |
| 7–12 | Event and amendment cases, pain points, review protocol, Catala, normative foundations and dates | Source actors/triggers retained; literature progresses from decisions to duties; equation 1 explained |
| 13–18 | Stable-model eFLINT, Symboleo, Stipula, amendment/liquidity, processes, LLM studies, software table | Mechanism and inspected limits remain connected; adjacent citation spacing repaired; table columns fit |
| 19–24 | Software continuation, reuse method, product views, RuleIR, unknowns and financial flowchart | Complete table headings repeat; valid JSON and HK-cent units visible; conflict precondition in flowchart caption |
| 25–30 | Events, proof target, counterexamples, knownness, architecture, walkthrough and amendments | Completeness wording and explicit evaluation mode repaired; equations and API listing fit; approval reuse corrected |
| 31–36 | Work packages, local projects, evaluation, tests, economics and risks | Future commands distinguished from executed checks; comparison counts/uncertainty explicit; cost derivation retained |
| 37–42 | Fifteen business cases, conformance/library boundaries, pilot decisions and bibliography | No runtime-success claim; source mapping retained; URLs, editions and retrieval notes readable |
| 43–45 | Remaining bibliography | Long URLs wrap within page; source editions and author names preserved |

After the last small text repairs, pages 16, 25 and 29 were rendered and read
again. Other pages' extracted text was unchanged; the final PDF retains 45 pages.
All diagrams, numbered equations, listings, table continuations and references
were included in the full reading. The remaining short closing page before the
bibliography is an ordinary section ending, not missing content.

## Reproducible checks

Build from `docs/proposal`:

```sh
latexmk -xelatex -interaction=nonstopmode -halt-on-error proposal.tex
```

Run from the repository root:

```sh
python3 scripts/check_spec_pack.py
python3 scripts/check_proposal.py
```

Both checks passed. The latter verifies all 38 paper PDFs and recorded hashes,
62 unique bibliography entries and 62 used citation keys, reference targets,
protected baseline digests and six retained equation labels. No words extend
outside a PDF page. `validation.json` preserves current PDF/source hashes and
check results. The specification check validates three schemas, 35 decision
fixture contracts, six negative contract cases, eight event structures, source
hashes and SQLite DDL. It executes zero runtime decisions and no event/release
outcomes. It does not certify all possible schemas or a legally correct rule set.

The build exits successfully. XeTeX emits two nonfatal `ignored: Infinite glue
shrinkage found in box being split` notices at the two multipage tables. The
corresponding rendered pages (18–19 and 31–32 physically) were inspected: headings
repeat, rows remain legible, no text is clipped, and the page-bound check passes.
They are retained as diagnosed layout notices, not hidden as a warning-free build.
There are no undefined references/citations or overfull/underfull-box warnings.

## Verdict and remaining review

The revised design and checked specification are ready to begin W00–W03. This is
an engineering handoff judgment, not approval of the eventual software or legal
interpretations. Human acceptance of the revised prose and product direction,
independent compliance adjudication, runtime conformance, installed-adapter tests
and measured business benefits remain pending. A complete inventory of the bank's
applicable regulations has not been established by the selected-source study.
