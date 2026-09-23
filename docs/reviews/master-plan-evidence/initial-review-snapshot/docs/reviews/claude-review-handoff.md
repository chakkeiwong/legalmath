# Handoff to Claude: independent review of the LegalMath implementation plan

Repository: `/home/chakwong/python/legalmath`.
Date: 22 September 2026. Review target: master plan 1.0, proposal 0.3 and the
associated implementation contracts. **Your task is a thorough independent
review. Do not begin application implementation or assume the author's readiness
verdict is correct.** This memo has been prepared for you; no Claude review has
yet been executed or incorporated.

## What the user needs

The user works in a Hong Kong private bank of a major American bank. Staff read
SFC circulars, interpret requirements and manually change bank systems. They
want an intermediate specification that compliance officers can inspect and
engineers can execute and verify. The final transaction component must be Java.

The user rejected earlier proposals because they named languages without
explaining them, did not run a concrete circular through the complete workflow,
and left Java delivery vague. Proposal v0.3 now teaches the language concepts,
works through actual circular 23EC35 and delivers a bounded generated/compiled
Java example. The latest request is: assess readiness, create and thoroughly
review a **master implementation plan**, and prepare this handoff. The user
explicitly clarified that this is a plan, not a request to write the application
in this turn.

Answer the concrete question: **Can an implementing agent execute this plan into
the specified engineering MVP without silently inventing consequential semantics,
omitting requirements, waiting on circular dependencies or mistaking local tests
for legal/production approval?** Identify what can start now and what must close
before each later stage. A concrete defect and a reproducer are more useful than
general advice to “add tests” or “use a mature framework.”

## Files and starting evidence

Read [the master plan](../implementation/master-plan.md) from start to finish and
[its machine task graph](../implementation/master-plan.tasks.json). These contain
the product boundary, architecture, tasks T00–T24, milestones M0–M7, sixteen
adversarial acceptance families and expected evidence. The
[author audit](master-plan-review.md) contains findings already identified; try
to disprove their resolutions rather than assuming they are settled.

Then inspect:

| Material | Local path | Reason to inspect |
| --- | --- | --- |
| Normative semantics | `docs/specs/v0.1/semantics.md` | Types, eager/conditional/default semantics, conflicts, traces, events and solver fragment. |
| Service/identity/release contract | `docs/specs/v0.1/contracts.md` | Exact hashes, evidence normalization, review state, transactions and HTTP boundaries. |
| Required Java output | `docs/specs/v0.1/java-backend.md` | Operator mappings, Java API, native engine identities and build/release records. |
| Original work packages | `docs/implementation/work-packages.md` | Concrete modules, future commands and estimates; master task order takes precedence. |
| Schemas and database sketch | `docs/specs/v0.1/*.schema.json`, `storage.sql` | Check actual representability; prose describing a field does not create storage or validation. |
| Expected cases | `docs/specs/v0.1/fixtures/` | 35 full decision cases, six invalid variants, eight event histories and four release examples. |
| Fixture generator/checker | `scripts/build_spec_examples.py`, `scripts/check_spec_pack.py` | Existing checks are incomplete and generated templates can overwrite manual schema edits. |
| Actual demonstration | `examples/java-dry-run/` | Ten-rule bundle, emitter, Python reference, Java runtime/events and separately compiled callers. |
| Original and isolated evidence | `docs/reviews/master-plan-evidence/` | Exact input/source/JAR hashes, replay results and targeted contract probes. |
| Explanatory manuscript | `docs/proposal/proposal.pdf`; LaTeX below | Source and method explanations from the rejected-document reconstruction. |

The most relevant manuscript sources are `01a-language-lesson.tex`,
`01b-complete-dry-run.tex`, `03-product.tex`, `03a-rule-contract.tex`,
`03b-event-contract.tex`, `03c-storage-review.tex`, `03d-java-delivery.tex` and
`04-prototype.tex` under `docs/proposal`. The PDF is 66 physical pages. The
planning task did not rewrite it; dated implementation clarifications may resolve
ambiguities in its older wording. Do not silently use the older ambiguity instead
of examining the new resolution.

The [review input manifest](master-plan-evidence/review-inputs.json) identifies
the exact files being reviewed. If hashes differ, report the difference and
review the current coherent set rather than presenting stale evidence as current.
This workspace has no Git repository. Adjacent projects are read-only.

## What actually runs and what does not

The preserved SPI-Demo1 Java demonstration implements an individual client,
solicited transaction and Annex 1 paragraph 8.3(a) execution-monitoring profile.
It uses exact integer HK cents, known/unknown/conflicting facts, a Boolean rule
graph, source-linked rule traces and simple consent replay. It generates Java,
compiles with `javac --release 17 -Xlint:all -Werror`, packages a JAR, recompiles
a separate host against it and compares complete demo responses with a separately
written Python evaluator. Its reported results are 32 decision cases, eleven
consent histories and three outcome-changing compiled mutations. An isolated
rerun reproduced the original inputs, generated source and JAR hashes.

It does **not** implement the full RuleIR response, dates/arithmetic/defaults,
general duties, production validator, reviewer application, legal approval,
automatic source-to-rule translation or bank adapter. Its `DEMONSTRATION_ONLY`
result cannot be promoted by changing an input flag. The existing 35 full-language
cases are contracts; the checker reports zero full-runtime decisions. The
release examples are simplified predicates, not a tested release database.

Three targeted probes confirm that the current fixture helper accepts duplicate
source-span IDs, duplicate interpretation IDs and an interpretation referencing
a missing source span. The input bundles used by the demo are unaffected. The
master plan makes the production rejection behavior a T00/T05 acceptance target;
it does not claim the helper was fixed during this planning task.

## The circular example you must preserve

Actual source: SFC–HKMA circular 23EC35, 28 July 2023, streamlined suitability
treatment for sophisticated professional investors. Local sources:

- `.localresources/sfc/23EC35.json` and `.txt`: main circular.
- `.localresources/sfc/23EC35-annex1.pdf` and `.txt`: guidance.
- `.localresources/sfc/23EC35-annex2.pdf` and `.txt`: FAQs.
- `examples/java-dry-run/spec/circular-disposition.json`: provision dispositions.
- `examples/java-dry-run/spec/spi-control.bundle.json`: ten interpreted rules and
  34 used, hash-verified source anchors.

The synthetic Ms Lee example has a HK$40m portfolio: HK$35m own plus a documented
quarter of a HK$20m non-associate joint portfolio. Assets HK$120m less liabilities
HK$15m and home HK$30m yield HK$75m net assets excluding the residence. The
financial test is portfolio **at least** HK$40m **or** net assets excluding home
at least HK$80m; it is only one subcondition. Five qualifying category transactions
provide one sophistication route alongside the separately evidenced reasonable-
satisfaction assessment. Conservative objectives, category mismatch, missing
acknowledgment or withdrawal can defeat the selected streamlining route.

The client chooses a threshold; the bank records the setting and rationale.
Gross exposure includes leverage. HK$8m plus HK$2m reaches the HK$10m limit.
Offering documents and applicable requests for explanations/material queries and
warnings remain relevant. Paragraph 14 creates continuing review duties; automatic
suspension when the review is not current is labelled an additional proposed bank
restriction. Verify this separation in the rules and explanations.

Corporate, unsolicited and designated-account profiles stay outside the demo.
Annex 1 paragraph 8.3(b)/FAQ 6 has different monitoring logic; exceeding a threshold
must not automatically become a forced-unwind requirement. Imported definitions,
current applicability and bank data calculations remain review dependencies.
No test establishes the authenticity of real documents or the bank's entire
regulatory perimeter.

## Review in five bounded passes

Make notes after each pass, then reconcile findings across passes. You may use
read-only searches and small isolated diagnostics. Do not replace the source
question with a broad literature survey or defer a concrete engineering choice
merely because several frameworks exist.

### Pass 1: product and source-to-control completeness

Reconstruct the Ms Lee path without guessing a missing step: source intake,
provision inventory, imported definitions, interpretation issue, typed fact,
decision, explanation, review, Java build, export, host use, withdrawal, amendment
and historical replay. Identify every Boolean that actually represents an owned
assessment. Is authority (source, bank policy, synthetic choice) retained?

Check whether user-facing views can explain why a rule applies and where evidence
is missing. Is the first milestone genuinely executable? Does T00 have bounded
outputs and enough decisions to complete, or merely postpone crucial design?
Are source completeness and human usability accounted for without making them
unnecessary blockers to independent engineering? If another circular fragment
cannot fit this IR, identify the precise unsupported construct and disposition.

### Pass 2: language, evidence, Java and verification

Read the written semantics, schemas, checker, generator, Java emitter and runtime.
Try at least these thought experiments or focused probes:

1. Unknown OR a sufficient alternative; unknown AND false; conflict in a branch
   that would otherwise be skipped; an unrelated conflict.
2. Two true exception guards returning the same value; one true and one unknown;
   empty exception list; error in an eager sibling; identical branches under an
   unknown conditional. Is error/conflict precedence implementable and deterministic?
3. Exact/inexact scale, negative values, large integers, valid leap dates,
   interval endpoint and Unicode canonicalization. Can the Java encoding change
   cents, dates or hash bytes?
4. Duplicate IDs outside expressions; unresolved interpretation source; false
   source pointer; invalid input without a valid hash; shared rule-node trace.
5. A correction known today but valid tomorrow, and a late correction to a past
   decision. Does interval-local supersession preserve both intended histories?
6. Python and Java have different actual `engine_version` values. Do semantic
   comparison and independently verified execution hashes avoid both false
   failures and forged common identities? Are all other fields compared?
7. Can an accepted operator, generated identifier or large AST create unsupported
   Java, code injection, exponential traversal or an unreported limit?

A reference/interpreter pair sharing a mistaken interpretation can agree. Ask
which expectations are independently specified and which traces have independent
invariants. Do not equate the demo's three mutations with complete fault coverage.

### Pass 3: temporal events, release and bank integration

Follow consent/duty evidence across `valid_at` and `known_at`. Test withdrawal
received late, unknown completeness, a future completeness seal, duplicate IDs,
sequence collision, wrong stream/actor/category, timely/late performance and a
late-arriving record proving on-time satisfaction. Does the data contract carry
the evidence the replay claims to use? Does the Java event component arrive in
the plan before event-dependent acceptance?

Inspect the new record order: BuildManifest -> VerificationReport ->
JavaReleaseManifest -> ReleaseRecord. The build identifies the JAR; the report
identifies the build; approval comes later. No manifest is embedded in a JAR
whose hash it contains. Find any remaining self-reference or build-before-review
cycle. A draft candidate may build; only a reviewed release may export for use.

Force two HK$1.5m orders to read HK$8m exposure under HK$10m. At most one may
reserve the streamlined route. Force consent withdrawal or release activation
between read and commit. Does the adapter validate all versions in one atomic
protocol? Is retry idempotency separate from event duplicate handling? What
happens when retries exhaust or a process crashes? A deterministic evaluator
alone does not prove this host property.

Check unique effective releases, retirement, actual deployment history, original
evidence replay and existing obligation versions. Restoring old software must
not automatically revive superseded law. Check every needed relation against
the SQL sketch and T00/T02 storage work; do not assume payload JSON solves unique
selection or transactions without a query/constraint.

### Pass 4: execution graph, API, security and feasibility

Check every task's dependencies, planned module, acceptance command and output.
The graph has 25 tasks; T00–T22 form the engineering MVP, T23 is optional research,
and T24 is the separate comparative pilot. No core task may depend on optional
proof search or live model access. T21's semantic comparisons require T18.

Commands labelled planned must not be reported as available. Is environment
creation/locking reproducible without touching adjacent or `tfgpu` environments?
Are mutable build directories, unbounded compiler/solver work, missing request
limits and stale binary reuse addressed? Are state creation, draft submission,
job retrieval/cancellation and restart recovery actually scheduled?

Check role spoofing from request bodies, source/HTML injection, untrusted model
output, path traversal and private-network redirects. Ask whether declared
LOCAL_SYNTHETIC authority is unmistakable without intruding on ordinary reviewer
flows. Enterprise deployment is outside scope, but the local prototype cannot
silently grant itself a stronger authority.

The older three-week foundation estimate was corrected. Challenge the revised
planning allowance using actual task content, including T00, full Java semantics,
host integration and reviewer time. Recommend a narrower first milestone if
necessary; do not remove required Java delivery or semantic rejection behavior.

### Pass 5: literature transfer and final readiness verdict

The manuscript borrows concepts, not whole tool guarantees. If you challenge a
method claim, read the relevant technical section and official code where local
copies exist. Papers are in `docs/papers/`, with manifest/reading notes. Especially
check any proposed use of Catala defaults, Stipula state semantics/Java verification
models, knownness encoding and normative duty/violation distinctions.

Stipula's 2021 language is type-free; the tutorial pseudocode is illustrative.
Stipula–KeY verifies a restricted translated model, not this production Java code.
MathDevMCP's inspected controller is not MCTS; DynareMCP's historical UCB work is
an investigation-scheduling analogy. No local adapter is already a legal theorem
prover. A solver result or checked code property cannot certify source meaning
or evidence authenticity. Optional research failure must not derail the useful
reference/Java product.

Give separate verdicts for starting foundations, entering semantic/runtime work,
engineering MVP, comparative pilot and bank production. If you say a stage is
blocked, name the exact missing contract or evidence and the earliest task that
must repair it. State what may proceed independently.

## Permitted review work and evidence discipline

Keep existing application, schema, source, paper and manuscript files read-only.
You may create your review report and diagnostic outputs in a new
`docs/reviews/claude-master-plan-review/` directory, and temporary diagnostics in
`/tmp`. Do not edit the plan to make a test pass; propose a patch in the report.
Do not send messages, deploy, connect to bank systems, install into shared
environments or start live paid model/pilot jobs. Record NOT_CHECKED if a tool,
source or exact version is unavailable; do not fabricate a review result.

The ordinary fixture checker is:

```sh
python3 scripts/check_spec_pack.py
```

It executes no full-runtime decisions. The existing isolated replay at
`/tmp/legalmath-plan-audit-uo5a7fe0` may still be available; its evidence is copied
under the review evidence directory. If rerunning Java, use a new temporary
workspace with `examples/java-dry-run`, `docs/specs/v0.1`,
`scripts/check_spec_pack.py` and `.localresources/sfc` copied to the same relative
paths. Create `examples/java-dry-run/build` there, then run from that root:

```sh
python3 examples/java-dry-run/build_and_verify.py \
  --jdk /home/chakwong/python/legalmath/.localresources/java-toolchain/jdk-17.0.20.1+1
```

This may run only local CPU subprocesses. Do not overwrite the original demo
evidence. The checker uses assertions: ensure Python optimization is disabled.
The production checker must not be made reliable merely by trusting those
assertions under arbitrary launch flags; flag its limitations explicitly.

## Required review deliverables

Write `docs/reviews/claude-master-plan-review/report.md` and, preferably,
`findings.json`. Each finding must contain:

- ID and severity: P0 (wrong authority/correctness with broad impact), P1
  (blocks a stated milestone), P2 (bounded defect or missing clarity), or P3
  (optional improvement).
- Exact current file/section or line, supported by what you actually inspected.
- Expected behavior and a concrete failing/ambiguous example.
- Evidence class: observed by command, derived from the contract, or not checked.
- Consequence for the product and the tasks affected.
- Smallest proposed repair and a distinguishing acceptance check.
- Whether it blocks starting foundations, a later milestone or only production.

Also include a coverage table for all five passes, commands actually run, source/
code versions, uninspected material, author-audit findings confirmed or disputed,
and a readiness decision table. A recommendation of READY must list residual
assumptions and the stages they constrain. A BLOCKED recommendation must preserve
useful independent work. Do not supply a ceremonial “looks comprehensive” verdict
without adversarial cases and source/code checks.

Return the report location and highest-priority findings to the user. This
review is an independent engineering assessment; human acceptance of the prose
and compliance adjudication remain separate.
