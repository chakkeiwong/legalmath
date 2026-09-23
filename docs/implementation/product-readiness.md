# Product-build readiness assessment

Subsequent execution: the proposed E01–E09 increment has now passed its scoped
engineering acceptance. See the [205-test execution report](interpretation-round1/execution-report.md)
and [refreshed next-round plan](interpretation-round1/next-round-plan.md). The
assessment below is preserved as the pre-implementation baseline.


23 September 2026. **The unified document package is sufficient to begin the next
engineering increment: E01–E09, the bounded interpretation workbench using scripted
members.** The implemented T00–T22 product is the starting point. English-to-rule
accuracy, independent reviewer effectiveness and bank deployment remain unvalidated.
This assessment is an execution brief for the existing design, not another master
plan. The controlling specification remains chapters 6–9 of the
[232-page monograph](../monograph/monograph.pdf), with its
[implementation guide](../monograph/implementation-guide.md),
[task graph](../monograph/implementation-plan.json) and
[ten schemas](../monograph/contracts/README.md).

## Why an implementation agent can start

The design identifies the records to persist, their relationships and immutable
identities, the issue lifecycle, action accounting, terminal-state precedence,
transaction boundaries, proposed HTTP operations, integration modules and required
failure behavior. It defines what a repair must establish and what remains
unresolved after the budget is exhausted. The E task graph records dependencies,
planned files, acceptance identifiers and evidence directories. Those are the
necessary boundaries for implementing and reviewing the next prototype.

Normal engineering work remains: write migrations and request models, implement
the transactions and controller, generate OpenAPI, add the interface and implement
concurrency/recovery tests. The book specifies their observable behavior without
pretending that the implementations already exist. As of this assessment,
`src/legalmath/interpretation` does not exist; the current drafting service uses a
deterministic fixture provider. The proposed ensemble is not running behind the
existing UI.

A workbench that follows these contracts can preserve competing hypotheses and
make errors inspectable. Whether it discovers the right alternatives on unfamiliar
circulars is a separate empirical question. A successful controller test cannot
answer that question.

## Previous execution and testing are documented

Chapter 8’s “What the complete local execution actually established” starts on
**PDF page 170** (printed page 161). The ordered next-build tasks start on PDF
page 187; whole-cycle acceptance scenarios start on page 188, and the first
complete increment on page 189. Chapter 9 specifies evaluation from page 191.

| Evidence set | Recorded result | What it establishes |
|---|---|---|
| T00–T22 MVP | 154 passing tests; all 35 RuleIR cases executed; 32 SPI decision cases and eight attributed event histories verified in the generated candidate JAR; three compiled mutants detected. | Tested behavior of the selected language and local workbench, including Java delivery and review/release controls. |
| Complete 23EC35 execution | Source/annex intake, 51 provision dispositions, generated Java, synthetic separate reviewers, release, withdrawal, one-cent synthetic amendment, separate host and exact historical replay after export/restore. | A complete selected source-to-Java change and retained history under local synthetic authority. |
| Earlier SPI-Demo1 | 32 decision examples and eleven consent histories for its narrower interface. | Earlier demonstration evidence; its event denominator and API must not be conflated with the later MVP. |
| Second circular 23EC46 | 22 named cases, all 729 T/F/U assignments in the selected six-input abstraction, and four compiled incorrect candidates detected. | Correct execution of the manually authored paragraph-10 interpretation and supplied classifications. |
| Ensemble design checks | Ten schemas, one blocked fixture, sixteen rejected negative mutations, fourteen ordered tasks, eight abstract budget states and sixteen release-predicate rows. | Internal consistency of those design examples and finite abstractions; no live controller, provider, concurrency or legal-accuracy test. |

The full records are [the execution report](execution-report.md),
[its task ledger](master-plan.tasks.json),
[JUnit](../../artifacts/runs/acceptance/tests.xml),
[the walkthrough](../../artifacts/runs/mvp-accepted/walkthrough.json),
[the second-circular verification note](second-circular-verification.md) and
[its result](../../artifacts/runs/second-circular-23ec46-final/result.json).
The book includes the substantive results and limitations; these files supply
machine-checkable identities and reproduction detail.

The 23EC46 candidate is still DRAFT with **five unresolved issues and two missing
source dependencies**. The candidate and source-based oracle share an author, and
no language model translated the circular in that run. Passing 751 deterministic
cases does not establish independently correct English interpretation. The four
other pilot circulars primarily supplied source/metadata coverage rather than four
more independently validated executable translations.

## The concrete next product increment

Implement E01–E09 on the current source, review, solver and Java services. Start
with the public/synthetic 23EC46 packet and separate explicitly synthetic resolved
fixtures. Keep the original oracle and unresolved source dependencies unchanged.

| Milestone | Existing tasks | Inspectable deliverable and completion condition |
|---|---|---|
| Persist evidence and alternatives | E01–E04 | Validated models and policy; independent provision inventory; immutable candidate families, assumptions and revisions; issue records with stable root identities. Source omissions produce issues even when every candidate agrees. |
| Investigate within finite limits | E05–E07 | Atomic action reservations and outbox, deterministic scheduler, scripted members, targeted repair and supported formal comparisons. Concurrent workers cannot overspend the last action; crashes retain charges; unsupported comparisons remain explicit; distinguishing inputs replay in Python and Java. |
| Review and control release | E08–E09 | Complete immutable report, comparison UI, authenticated issue decisions and existing Java/release integration. Every material unresolved issue blocks release, and changes invalidate the exact prior review. A separate fully resolved fixture exercises the positive path with synthetic identities. |

The first runnable demonstration must expose the original passages, alternative
readings and their assumptions; show the consequential disagreement; perform
bounded automatic investigation; retain every attempt and the surviving
uncertainty; and bind review to the actual candidate/report/build. Finishing with
an unexplained highest-scoring interpretation is a failure of the design.

Acceptance requires all six chapter-8 scenarios:

1. Repair an explicit omitted product-type route and recheck all affected results.
2. Preserve an unresolved classification through the configured budget,
   then produce a blocked report with alternatives and a precise reviewer question.
3. Detect an uncovered source provision despite unanimous candidate agreement.
4. Enforce the last available action under a worker race, dispatch crash and stale
   returning worker, without resetting or refunding issued counts.
5. Invalidate an earlier approval after a relevant source or footnote changes,
   even if the Boolean expression appears unchanged.
6. Recover a complete terminal report after cancellation or provider failure.

Also exercise the separately specified positive review path. These checks must
invoke the new service and the existing release/Java boundary; merely validating
prewritten JSON records is insufficient. Record exact commands, code/data hashes,
policy, results and departures in the E task’s declared evidence directory.

## How the surveyed methods shape subsequent work

The immediate design already combines typed executable specifications, explicit
exceptions and uncertainty, alternative assumptions, source-linked arguments,
distinguishing counterexamples and a finite investigation controller. Reuse the
existing event and Java semantics. Catala- and contract-language lessons inform
those boundaries; implementing every surveyed language is not a prerequisite.

After the scripted controller and release checks work, E10 adds restricted live
retrieval/model adapters behind the same interface. Initial proposals must remain
blind and independently inventoried; member/provider identity and common sources
must remain visible. Variation in prompts alone is not evidence of independent
errors. The existing fixture caps are engineering examples, not selected live
model budgets.

E11 establishes a reference corpus independently of candidate outputs. Reviewers
can prepare scope, sources and cases while engineering proceeds; the task’s
formal freeze and exported records follow its existing dependencies. E12 compares
the declared baselines with comparable source access and resource budgets,
reporting omitted duties, wrong scope, lost exceptions, unsafe clean results,
unnecessary blocks, abstentions, review effort and uncertainty. Model selection,
corpus size, operational thresholds and cost limits require a registered study;
none has been selected by the current engineering tests.

E13 adds optional argumentation and tree-search machinery after the simpler
scheduler’s limitations can be measured. This is where a bounded DynareMCP-style
search adapter can be assessed against the deterministic baseline. Search priority
is a scheduling heuristic, not a probability that the legal interpretation is
correct. E14 connects the reviewed system to enterprise identity, real data and
host transactions, followed by shadow operation and incident/amendment rehearsals.
T23’s optional research adapters and T24’s pending human/model pilot remain
historical task dispositions; they are not already completed by proposing E13
or E12.

## Remaining decisions and limits

| Decision | Readiness now | Evidence or authority still needed |
|---|---|---|
| Begin E01–E09 implementation | Ready within the stated public/synthetic scope. | Actual service implementation and the specified integration/concurrency tests. |
| Claim better English interpretation | Unsupported by current results. | Independent adjudication, frozen unseen circular families, real provider outputs and a fair comparative study. |
| Select an ensemble or search method as the default | Not selected. | Predeclared downstream error/abstention criteria, resource accounting and uncertainty evidence. |
| Deploy to the bank | Pending. | Bank-owned scope and interpretations, actual data definitions, enterprise identity, operational policy, security and host integration. |

Engineering can proceed without waiting for another general literature survey.
Independent legal-reference preparation should begin alongside it. The strongest
remaining uncertainty is a shared source misunderstanding that survives every
candidate and test. The independent inventory, adversarial cases and adjudication
process address different parts of that risk; no finite ensemble eliminates it.

## Checks performed for this assessment

The retained JUnit record was inspected; the 154 application tests were **not
rerun**. The current evidence audit checks 119 runtime inputs, 36 final evidence
files, 24 protected baseline files and 67 original review files. It initially
failed because the merged proposal PDF occupies the former original-PDF path.
The checker now verifies the frozen original against its original digest. The
current audit passes. Two in-memory corruption probes still reject a changed
archived proposal and a changed runtime input, without modifying those files.

The ensemble contract check was rerun and passes all sixteen negative examples
and its finite diagnostics. The book source and both identical 232-page PDFs
remain unchanged. A review-note sentence confusing T23 and T24 was corrected;
the task table in the book was already correct.

The second-circular audit confirms all **27 recorded output files** and the
**nine executable/data inputs**. Its README differs from the tenth input digest
recorded in the run manifest. The verification script inventories every file in
that directory, including documentation; it does not consume the README in rule
evaluation. The former README bytes have not been recovered, so complete identity
of all ten original files is not claimed and the original manifest is not rewritten.
This documentation discrepancy remains recorded separately from the matching rule,
oracle, source and execution results. Future run capture should retain immutable
copies of all declared inputs as well as their hashes.

The [assessment evidence](../../.localresources/readiness-2026-09-23/assessment.json)
binds the commands, findings and preserved before/after records. Its initial
second-circular diagnostic used the wrong base directory for relative artifact
paths; the corrected diagnostic resolves paths against the run directory and
records that diagnostic error explicitly. No missing output was inferred from
that first failed lookup.
