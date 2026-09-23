# Continue developing LegalMath

Current increment: the [bounded interpretation master program](interpretation-round1/master-plan.md)
has been executed. Start with its [execution report](interpretation-round1/execution-report.md),
[operator guide](interpretation-round1/operator-guide.md) and
[next-round plan](interpretation-round1/next-round-plan.md). The original MVP
contracts and instructions below remain available as historical implementation context.


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
has been run, and no comparative accuracy or time-saving claim is made.

Bank deployment needs actual legal perimeter, interpretations, data freshness,
ownership/FX mapping, calendars, identity, retention and transaction integration
decisions. Synthetic approvals demonstrate version binding and separation of
roles; they do not answer those questions. Keep adjacent repositories read-only
and preserve the original proposal, source snapshots and narrow Java demonstration.
