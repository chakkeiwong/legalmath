# Continue developing LegalMath

The current executed increment is the [round-15 assurance
program](../plans/assurance-round15-execution.md). Read its
[execution result](interpretation-round15/execution-result.md),
[operator guide](interpretation-round15/operator-guide.md),
[reset memo](interpretation-round15/reset-memo.md) and
[next specification](../plans/assurance-after-round15.md).
It completed the deterministic phases and 140 of 231 restored executable
source checks, with 91 pending and one separately unencoded pair. The shared
500-call allowance is exhausted. All accepted source judgments are
NOT_ESTABLISHED; these are scoped model findings, not 140 proven errors.
Three child rules and the fractional-exposure/mutation cases have actual
Java/Python/cvc5/Catala comparisons. All eight parents, six authority questions
and 330 unresolved PDF materiality questions remain visible. The unified
monograph is 273 pages with a 76-page technical companion.
The final repaired code passed 789 tests, with no failures or skips.
The [final delivery record](../../artifacts/interpretation/round15/post-execution-review.json)
binds the full regression, executed repairs and retained uncertainty.

Previous increment: the [round-14 interpretation-assurance
program](../plans/assurance-round14-execution.md). Its accepted result is
[here](interpretation-round14/execution-result.md), with the [operator
guide](interpretation-round14/operator-guide.md), [post-execution
review](interpretation-round14/post-execution-review.md), and [refreshed
successor plan](../plans/assurance-after-round14.md). It completed 765
repository tests, cvc5 and Catala checks on 22 executable cases, two blind
proposals for an official 23EC52 question, and a 270-page unified monograph.
These are conditional engineering results. They do not establish English legal
accuracy, source completeness, statistical independence, or production release
authority. The eight original unencoded parents, 337 material PDF questions and
five authority dependencies remain visible.

Previous increment: the [round-13 typed-control program](../plans/assurance-round13-execution.md)
has executed all six reviewed phases. Start with its
[execution result](interpretation-round13/execution-result.md),
[operator guide](interpretation-round13/operator-guide.md) and
[next plan](../plans/assurance-after-round13.md). It passed 741 tests and accounted
for all required STR/gifts comparison outcomes; legal interpretation remains
unresolved. The earlier bounded-interpretation and MVP contracts below remain
available as historical implementation context.


The application is implemented under `src/legalmath`. Start with the
[run instructions](../../README.application.md), [execution record](execution-report.md)
and [current task ledger](master-plan.tasks.json). The user's instruction was to
execute the master plan and skip another Claude review. No further Claude review
was requested or run during implementation.

The controlling technical references are the [master plan](master-plan.md),
[semantics](../specs/v0.1/semantics.md), [contracts](../specs/v0.1/contracts.md),
[Java contract](../specs/v0.1/java-backend.md) and the dated
[implementation clarifications](../specs/v0.1/implementation-closure.md).
[OpenAPI](../specs/v0.1/openapi.json) includes the actual service and domain schemas.
The original [proposal](../proposal/proposal.pdf) explains the languages,
literature and complete 23EC35 worked example.

## Reproduce and inspect

Use the isolated Python 3.11 environment and retained JDK 17. The run instructions
show installation and the named offline acceptance scenario in a fresh directory.
The prepared workbench opens retained sources beside interpretations, typed rules,
examples and historical decisions. `/docs` is a local API console; local synthetic
tokens and caller-scoped idempotency keys protect mutations. The exported JAR and
separately compiled `BankHost.java` demonstrate the Java integration boundary.

```sh
.venv/bin/python -m pytest -q
.venv/bin/python scripts/check_contracts.py
.venv/bin/python scripts/check_spec_pack.py --runtime legalmath.conformance:evaluate_case
python3 scripts/check_execution.py
```

API and browser tests need working host thread/process facilities. In the Codex
sandbox, a minimal TestClient probe blocks on a thread wakeup; the same probe and
tests pass in the trusted host context. This is recorded in the acceptance notes.

`scripts/check_master_plan.py` remains the protected checker of the **initial
planning packet**. It intentionally assumes no implementation. Its input files
are preserved under `docs/reviews/master-plan-evidence/initial-review-snapshot`.
It is not a checker of the current executable product; use `check_execution.py`.

## Work after the engineering prototype

T23 research adapters have explicit NOT_RUN dispositions. The core service does
not require MathDevMCP, DynareMCP or ResearchAssistant. Their possible uses and
licensing/interface conditions remain documented in the proposal. Any adapter
needs a bounded real invocation and its own evidence before relying on it.

T24 requires independent compliance readers, adjudicated tasks and an approved
human/model study protocol. Model quality and human understanding cannot be
established by the deterministic stub or engineering tests. No live-model study
with independently adjudicated references has been run, and no comparative
accuracy or time-saving claim is made. Later live development exercises are
recorded in the round-specific results above.

Bank deployment needs actual legal perimeter, interpretations, data freshness,
ownership/FX mapping, calendars, identity, retention and transaction integration
decisions. Synthetic approvals demonstrate version binding and separation of
roles; they do not answer those questions. Keep adjacent repositories read-only
and preserve the original proposal, source snapshots and narrow Java demonstration.
