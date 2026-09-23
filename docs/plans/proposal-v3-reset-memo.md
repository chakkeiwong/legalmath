# Proposal v0.3: self-contained circular-to-Java handoff

Date: 22 September 2026, Asia/Hong_Kong. The user rejected v0.2 for insufficient
method explanation, lack of a complete circular dry run and failure to require
Java output. This turn reconstructs the proposal and supplies a bounded working
Java example. It does not implement the entire proposed product.

## Current material

- `docs/proposal/proposal.pdf`: 66 physical pages, 62 references, version 0.3.
  SHA-256: `c2526cbb521ad43328f3ea3de6915c0803af203bf3524fe85141aa7d30cdbb63`.
- New main-manuscript sources: `01a-language-lesson.tex`,
  `01b-complete-dry-run.tex`, and `03d-java-delivery.tex`. The main manuscript
  contains the grammar, event semantics, API/storage explanation and Java path.
- `examples/java-dry-run/`: source-linked ten-rule SPI-Demo1 bundle, generator,
  separately written Python reference, Java support, generated Java source,
  compiled JAR, separate host caller, inputs and verification results.
- `docs/implementation/START-HERE.md`, `work-packages.md`, `decisions.md`, and
  `docs/specs/v0.1/java-backend.md`: Java is mandatory W03J, before release W04.
- `docs/proposal/review.md`, `render-review.json` and `validation.json`: actual
  checks and rendered reading, with explicit limitations and pending human review.
- Existing paper collection: 38 PDF editions, 37 works, 947 pages. All seven
  requested papers are retained. Technical and citation-coverage notes remain.

The v0.2 PDF and companion material are protected under
`.localresources/proposal-v02-baseline/`; v0.1 remains protected separately.
All nine v0.2 equation labels and the cited bibliography are retained. There is
no Git repository here and no commit was created. Adjacent projects and bank
systems were not modified.

## Decisions and assumptions

| Choice | Provenance and reason | Failure mode and diagnostic | Status |
| --- | --- | --- | --- |
| Plain Java 17 JAR | User requires Java; host framework/version unspecified. A plain library makes the actual delivery boundary inspectable. | Bank target may differ; confirm during real integration, compile with its declared release and rerun conformance. | Explicit integration assumption, not a claimed bank standard. |
| Individual / solicited / 8.3(a) profile | Actual 23EC35 and both annexes; a bounded route reaches a real Java result. | Full-circular coverage could be falsely inferred; inventory every provision and reject other profiles explicitly. | Demonstration scope. |
| Exact BigInteger HK cents and tagged evidence | Avoid threshold changes, overflow and missing-to-false conversion. | Upstream ownership/FX mapping can still be wrong; review dated evidence and boundary cases. | Implemented numerical representation; real normalization unimplemented. |
| Suspend streamlining when annual review is not current | Proposed bank restriction supporting the source's continuing review duty. | Could be falsely described as the automatic legal consequence of paragraph 14. | Separately tagged bank policy, awaiting bank choice. |
| Consent completeness and authoritative sequencing | Absence of an event cannot establish absence without a complete stream. | A fabricated future completeness seal or missing withdrawal produces a misleading result. | Implemented rejection checks; host truth remains an external premise. |
| Twelve-week full prototype | Planning allocation, now including mandatory Java W03J. | Effort may exceed allowance; reduce scope or extend schedule, not semantics or review. | Planning hypothesis, no measured implementation velocity. |

The circular's financial condition is inclusive portfolio >= HK$40m OR net
assets excluding the home >= HK$80m. Qualification, category, objectives,
reasonable satisfaction, agreement, exposure and retained information remain
separate. Client-selected threshold and bank-recorded rationale are attributed
precisely. Offering documents remain required under the relevant explanation
relief. Imported definitions and judgment are named reviewed inputs.

Stipula's 2021 language is type-free and its timed contract semantics is not
bank regulation. Its pseudocode in the tutorial is explicitly illustrative.
Stipula–KeY Java verification models are not assumed to be drop-in production
bank components. MathDevMCP's inspected derivation controller is not MCTS;
DynareMCP's historical UCB use is an investigation-scheduling analogy.

## Executed evidence and decision

The evidence contract was written before implementation in
`proposal-v3-self-contained-java.md`. It requires source-derived expected cases,
reference/Java agreement, meaningful mutations, source identity and an actual
JAR/host call. The baseline is the written semantics and specified expected
outcomes; compilation success alone is insufficient.

| Decision | Primary criterion | Veto checks | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain SPI-Demo1 as the proposal's working Java demonstration | PASS: all 32 decisions and 11 consent histories match expected results and the reference; complete decision traces/hashes agree. | PASS: all three compiled rule mutants detected by wrong statuses; unsupported operator rejected; 34 source spans intact; separate host and reproducible fresh JAR pass. | Shared legal interpretation can be wrong; fixture coverage is finite and author-written. | Extend to full RuleIR in W03/W03J and obtain independent source adjudication. | Universal compiler correctness, complete regulatory scope or production readiness. |
| Deliver revised manuscript for user review | Built PDF, resolved references, retained equations, checked paper/source hashes, complete rendered reading and rereading of changed pages. | No missing references, page-bound errors or changed protected baseline. Five diagnosed nonfatal table-layout notices remain. | Human understanding and acceptance are not established by author checks. | User reading and review of the concrete implementation proposal. | Human acceptance or measured reduction in compliance errors. |

These are deterministic engineering observations. There was no stochastic
comparison, no statistical ranking, no human pilot and no performance claim.
The approximately eight-second run is descriptive only.

Run manifest:

- Command: `python3 examples/java-dry-run/build_and_verify.py --jdk .localresources/java-toolchain/jdk-17.0.20.1+1`.
- Recorded run: 2026-09-21T16:19:01.530111+00:00, which is 22 September in Hong Kong.
- Python 3.11.15, jsonschema 4.26.0, javac 17.0.20.1, target Java 17/class 61.
- CPU-only; no TensorFlow/JAX/PyTorch or GPU was used. Seed N/A: deterministic.
- Commit N/A: workspace is not a Git repository.
- Data: immutable 23EC35 public snapshots/anchors and synthetic versioned JSON.
- Result: `examples/java-dry-run/build/verification.json`, with exact source,
  generator, reference, runtime, generated-code, fixture and JAR digests.
- JAR SHA-256: `1377ee0b1a5ef53d5e5af4b464b66e5899c2f0378e92d44696e810965465d27c`.
- Document build: `latexmk -xelatex -interaction=nonstopmode -halt-on-error proposal.tex`
  in `docs/proposal`; checks: `python3 scripts/check_proposal.py` (also runs the
  specification check) and the recorded direct `check_spec_pack.py` command.

The machine initially had Java 11 runtime but no javac. The project-local
Temurin 17 archive was downloaded and verified against the official checksum:
`3808d1d15e3ec6bd5b84057fb5d84c33d8a1536a258146bcea2e603fc726e08e`.
Use `.localresources/java-toolchain/jdk17-clean.tar.gz` and the extracted
`jdk-17.0.20.1+1/`. The earlier `jdk17.tar.gz` is a failed partial/resumed
download, failed validation, and was not used. No default Java or adjacent
environment was changed.

## Review findings and repairs

The Java review exposed an invalid event-history premise: a completeness record
was allowed to certify a future interval. Both evaluators now reject that
premise, fixtures use realistic completeness recording times, and the eleventh
consent case exercises it. This repaired the fixture/runtime assumptions; it
did not invalidate the product direction. Monetary boundaries, knownness,
conflict handling and source-linked rules passed the final checks.

The manuscript was read as all 66 individual rendered pages, in order. Then
every changed page after repairs was reread, with raster identity checking for
unchanged pages. A final command-listing repair changed pages 48–52 only; those
were reread. The review record preserves exact hashes, page groups, diagram and
listing repairs, five diagnosed table notices, and remaining human review.

The strongest alternative explanation for agreement is a shared interpretation
mistake in both evaluators and examples. Independent legal adjudication and
held-out source-derived scenarios would challenge that explanation. The weakest
part of the current evidence is real bank data and operating integration: none
has been connected. A correct Boolean formula alone does not prevent concurrent
orders exceeding a threshold or an order consuming stale consent.

## Next implementation step

Follow START-HERE. W00 establishes an isolated authoring environment; W01–W03
implement full source/typing/reference contracts; W03J expands the demonstrated
emitter to the full language and result contract. W04 must bind approval and
verification to both bundle and actual JAR hashes. W05 implements the full
event/duty profile. W06 builds the reviewer UI. Host reservation/version races,
idempotency, stale releases and real mappings need explicit integration checks.

The existing 35 general RuleIR cases are fixture contracts, not executed runtime
results. The implemented 32/11 cases are a separate suite. Legal approval,
complete source imports, automatic prose translation, proof adapters and the
comparative pilot remain future work. Do not silently change a demonstration
authority field to promote this example into a bank release.
