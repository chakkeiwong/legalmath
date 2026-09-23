# Proposal v0.3 review record

Date: 22 September 2026, Hong Kong. The literature/source snapshot remains
21 September. Scope: a self-contained product proposal, implementation contracts,
and a bounded, generated and executed Java demonstration. No bank deployment,
human effectiveness study or published proof reproduction was performed.

## The user's objections and the resulting changes

The user rejected v0.2: formal legal languages were insufficiently explained,
the proposal lacked a complete circular dry run, and Java delivery was missing
from the required implementation path. That verdict is retained. The 45-page
baseline and 27 associated files are protected under
`.localresources/proposal-v02-baseline/`. Its PDF digest is
`3228de141ddd6fc6e4735c4ac0fd7696cbd2a7190dbe45be41047d6df1395b4c`.
The still earlier v0.1 baseline is also preserved. Author review of either
document did not establish human comprehension or product acceptance.

The reconstruction follows
[the pre-execution plan](../plans/proposal-v3-self-contained-java.md). The main
manuscript now contains the explanations and contracts; companion files are
operational copies and executable examples, not substitutes for explaining the
method in the PDF. It has 66 physical pages and 62 cited references.

| Objection | Change in the manuscript | Concrete supporting material |
| --- | --- | --- |
| Formal languages were names without sufficient explanation | Section 2 teaches syntax, types, expression trees, executable semantics, exceptions, parties, states, actions and scheduled events. The consent example distinguishes recording an occurrence from permitting an action. JML/KeY, solver search and proof assumptions are explained in ordinary programming terms. | Source-specific citations and explicit teaching notation; the Stipula-inspired pseudocode is not presented as compilable Stipula. |
| No whole-cycle circular example | Section 3 follows actual circular 23EC35, its main text and both annexes, through a synthetic client's evidence, provision inventory, interpretation, ten rules, review, tests, Java generation, withdrawal, replay and amendment. | A machine-readable circular disposition inventory, 34 verified source anchors, exact input bundles and expected outcomes. |
| No final Java output | Section 6 specifies a plain Java 17 library, immutable facts/results, exact cents, deterministic emission, compilation, a separate caller, release identity and host concurrency requirements. W03J is mandatory. | Generated source, a compiled JAR, a separately compiled host, full reference/result comparisons, fresh binary rebuilding and compiled mutation checks. |

The document distinguishes the delivered SPI-Demo1 subset from full RuleIR 0.1.
The full workbench, complete compiler, reviewer UI, automatic drafting and bank
adapter are implementation work. The existing 35 full-language fixture contracts
are not reported as executed merely because the narrower Java suite passes.

## Substantive source and method checks

The running profile is an individual client, a solicited transaction and
paragraph 8.3(a) execution monitoring. Corporate, unsolicited and designated-
account profiles remain in the circular inventory and return outside-profile
in the demonstration. Imported PI definitions and ownership/FX calculations are
reviewed input mappings, not secretly inferred by the Java rule.

The example explicitly connects HK$35m plus a documented quarter of HK$20m to
HK$40m of qualifying portfolio; HK$120m minus HK$15m liabilities and HK$30m home
value gives HK$75m net assets excluding the residence. Inclusive OR determines
the financial condition. The source's reasonable-satisfaction assessment,
category qualification, non-conservative objectives, explanations, warnings,
documents, prior written acknowledgment and current consent remain separate.
The gross-exposure example includes leverage and evaluates HK$8m plus HK$2m
against HK$10m. Passing the selected conditions is not an order authorization.

The threshold discussion was repaired to attribute the client's choice and the
bank's record-keeping duty precisely. The bank records the setting and client
rationale; the manuscript does not invent a universal percentage or attribute
an extra threshold-appropriateness requirement to the circular. Paragraph 14's
annual duty is distinguished from the proposed bank restriction that suspends
streamlining while the review is not current. Offering documents remain required
when the conditional product-explanation relief applies.

The Stipula tutorial identifies the 2021 language as type-free and distinguishes
its contract semantics from LegalMath's typed decision design. It explains
assets, function guards, event priority and observable behavior without implying
that a client agreement can amend regulation. Java verification models in the
Stipula–KeY work are distinguished from the production library and its real
calendar, evidence and host-transaction boundary. Catala's exception behavior
is separated from the proposed treatment of incomplete bank evidence.

The literature now also explains concolic path exploration, the stable-model
example and ARc's reasoning/translation stages in the manuscript. Existing
technical findings and qualifications remain, including the limited compiler
proof, reachability restrictions, solver consistency checks and the separation
of reported empirical results from formal guarantees. All nine baseline
equation labels are retained; the normative input/output equation now explicitly
defines the previously underexplained G(S).

## What the Java checks establish

The executed command is:

```sh
python3 examples/java-dry-run/build_and_verify.py \
  --jdk .localresources/java-toolchain/jdk-17.0.20.1+1
```

The [verification record](../../examples/java-dry-run/build/verification.json)
binds the source bundle, compiler, reference, Java support, generated source,
fixture inputs and tested binary by hash. It records Python 3.11.15,
jsonschema 4.26.0, javac 17.0.20.1, Java class version 61 and an approximately
eight-second deterministic CPU run. Runtime is descriptive, not a performance
comparison. No Git commit exists in this workspace; no random seed or GPU is
applicable.

- All 32 decision cases match their specified statuses/blocking inputs and the
  independently written Python reference's complete serialized results,
  including traces and hashes.
- All eleven consent histories match. Cases include withdrawal, late evidence,
  incomplete history, duplicate events, conflicting identifiers and unresolved
  ordering. A completeness assertion cannot certify events after its own
  recording instant; that invalid premise is an explicit eleventh case.
- Three modified generated classes were compiled and executed. Strict rather
  than inclusive portfolio comparison, conjunction rather than alternative
  wealth routes, and bypassed consent each change an expected status and are
  detected. Merely observing changed hashes would not count as detection.
- An unsupported, schema-valid scale expression is rejected before generation.
  A fresh Java compilation in a separate directory produces the same JAR bytes.
  A separate host compiles against and calls that JAR before and after withdrawal.
- All 34 used source spans match original PDF, derivative, passage and page
  identities. This establishes identity to retained sources, not legal approval.

The library is a working integration example. Its response says
`DEMONSTRATION_ONLY`; it does not implement production authority. The host's
atomic exposure reservation, consent-version validation, idempotency and real
data mapping are specified but not exercised against a bank system. The full
RuleIR compiler, generic obligation scheduler and a universal compiler proof
remain unimplemented. Independently written evaluators can share a mistaken
interpretation; compliance adjudication is still separate evidence.

## Literature collection and retained limitations

The collection remains 38 PDF editions representing 37 works and 947 source
pages, including all seven requested papers. All recorded PDF hashes and sizes
match. Technical notes preserve inspected methods, theory, evaluation and relevant
appendices; retained page count does not claim every appendix page was read.
Original-code inspections, version-specific limits and the adjacent-project
inspection records from v0.2 remain applicable to their recorded versions.

The two saved forward searches have 65 raw records and 60 individually screened
indexed identifiers: 15 retained technical records, 15 relevant unresolved
follow-ups, 13 background/deferred records and 17 title/metadata exclusions.
Coverage addresses the architectural questions; it is not a claim of exhaustive
citation-network coverage. The L4 paper, later Symboleo journal article and other
named unresolved leads remain retrieval/reading gaps. No published benchmark or
proof was rerun. ResearchAssistant discovery/parsing was exercised locally;
MathDevMCP and DynareMCP reuse remains a proposed bounded integration.

## Rendered reading and repairs

The initial 66-page v0.3 candidate was read as individual 1.35x renderings,
beginning to end, in eleven consecutive groups of at most six pages. This is
author self-review, not an independent reviewer or human acceptance test.

| Initial physical pages | Material inspected and relevant findings |
| --- | --- |
| 1–6 | Title, investment case, contents and regulatory perimeter; public/synthetic scope and required Java output are visible. |
| 7–12 | Financial/category failures, language fundamentals, Catala exceptions and Stipula tutorial; consent arrow labels needed more space. |
| 13–18 | Verification/search lesson and actual circular intake, whole-source disposition and evidence mapping; threshold duty attribution and FAQ numbering needed correction. |
| 19–24 | Ten-rule evaluation, distinguishing cases, generated host path, withdrawal/replay and literature foundations; eleven-history count and future-completeness premise were added after code review. |
| 25–30 | Dates/testing, normative engines, stable models, Stipula theory and neural-symbolic methods; clarified that absence of a stable model can indicate inconsistent constraints. |
| 31–36 | Method comparisons, software choices, literature reuse, reviewer views and expression grammar; kept the short JSON listing together. |
| 37–42 | Unknown/conflict semantics, event duties, proof targets, counterexamples and authoring architecture; generated Java is the required bank runtime. |
| 43–48 | Storage, service APIs, drafting, release and Java API/compiler; kept the API signature together. |
| 49–54 | Java host race, release contract, work packages and local-project reuse; distinction between specified and executed integration remains explicit. |
| 55–60 | Evaluation, mutation tests, economics, business cases and research limits; deterministic checks are not empirical business benefits. |
| 61–66 | Complete bibliography, source editions and URLs; citations are legible and within page bounds. |

After those repairs, the next 66-page PDF was compared page by page with the
first render. Every changed rendering was reread in ascending order:
2, 3, 12, 16, 17, 21, 26, 27 and 35–60. Unchanged pages were byte-identical PNGs.
That reading caught one newly split two-line Java build command. Keeping the
command together changed only pages 48–52; all five were then rendered and read
again. The remaining 61 pages are byte-identical to the preceding checked render.
The resulting PDF digest is
`c2526cbb521ad43328f3ea3de6915c0803af203bf3524fe85141aa7d30cdbb63`.
[The render record](render-review.json) retains per-page hashes and comparison
stages. Temporary images are under `/tmp/legalmath-proposal-v3-release-review/`.

The repaired diagram labels are distinct from boxes; short code listings remain
together; table headings repeat; formulas, captions, API paths and bibliography
URLs are legible. The short closing page before references is an ordinary section
ending. XeTeX retains five nonfatal `ignored: Infinite glue shrinkage found in
box being split` notices at multipage tables. Corresponding tables and
continuations were inspected with no clipping or lost rows. These are diagnosed
layout notices, not a claimed warning-free build. There are no undefined
citations/references, overfull/underfull boxes or words outside PDF page bounds.

## Reproducible checks and remaining acceptance

From `docs/proposal`:

```sh
latexmk -xelatex -interaction=nonstopmode -halt-on-error proposal.tex
```

From the repository root:

```sh
python3 scripts/check_spec_pack.py
python3 scripts/check_proposal.py
```

The proposal check verifies 62 unique used bibliography keys, reference targets,
nine preserved equation labels, protected baseline digests, 38 paper PDFs, Java
evidence hashes and PDF page bounds. The specification check validates three
schemas, 35 decision fixture contracts, six negative contract variants, eight
event structures, source identities and SQLite DDL. It executes zero decisions
for the full RuleIR runtime; that result is separate from the executed Java suite.
The Markdown link check found no broken local targets after decoding URL-escaped
paper filenames. Current checks are preserved in [validation.json](validation.json).

The revision supplies the requested teaching narrative, concrete whole-cycle
example and actual Java output. It also names the remaining engineering tasks.
It does not certify the proposal as accepted by its reader. Human comprehension,
product acceptance, independent legal adjudication, full-runtime conformance,
host integration and measured business value remain pending.
