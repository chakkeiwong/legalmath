# LegalMath

Turn selected Hong Kong regulatory requirements into reviewable specifications
and generated Java controls.

- [Run the application](README.application.md): local workbench, complete SPI
  walkthrough, API console and Java delivery instructions.
- [Implementation results](docs/implementation/execution-report.md): executed
  core tasks, acceptance evidence and remaining human/bank work.
- [Second-circular test and correctness method](docs/implementation/second-circular-verification.md):
  23EC46 paragraph 10, source-based cases and the limits of current verification.
- [Proposal v0.3 (PDF)](docs/proposal/proposal.pdf) and
  [LaTeX source](docs/proposal/proposal.tex): formal-language tutorial, full
  circular-to-Java worked case, 62-reference literature review and implementation plan.
- [Executable Java example](examples/java-dry-run/README.md): generated source,
  compiled JAR, separate host caller and recorded tests.
- [Implementation entry point](docs/implementation/START-HERE.md): contracts,
  fixtures and work packages, including the required full Java backend.
- [Master implementation plan](docs/implementation/master-plan.md): task order,
  interfaces and acceptance tests, with the [current task ledger](docs/implementation/master-plan.tasks.json).
- [Paper library](docs/papers/README.md): 38 downloaded PDF editions, technical
  reading notes and an explicit coverage/gap ledger.
- [Validation and review](docs/proposal/review.md): checked evidence and limits.

The application includes a full RuleIR reference evaluator and Java backend,
dated evidence, consent and duty replay, source review, versioned releases,
amendment analysis, bounded solver comparison and deterministic drafting stub.
The complete example implements an individual-client, solicited-transaction,
execution-monitoring profile from circular 23EC35. Public sources and synthetic
identities exercise the workflow. Bank interpretation approval, production
integration, live-model quality and human usability remain pending.

```sh
.venv/bin/legalmath serve \
  --data-dir artifacts/runs/mvp-accepted/database \
  --identities artifacts/runs/mvp-accepted/local-identities.json \
  --jdk .localresources/java-toolchain/jdk-17.0.20.1+1 \
  --comparison-jar artifacts/runs/mvp-accepted/java-release/policy.jar
```

Open `http://127.0.0.1:8765`. The earlier narrow Java example and proposal remain
preserved as design and regression evidence.
