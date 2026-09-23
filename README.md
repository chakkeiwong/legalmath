# LegalMath

Turn selected Hong Kong regulatory requirements into reviewable specifications
and generated Java controls.

- [Bounded interpretation workbench](docs/implementation/interpretation-round1/operator-guide.md):
  source inventories, competing readings, bounded scripted repairs and exact-evidence review.
- [Executed next-round master program](docs/implementation/interpretation-round1/execution-report.md):
  205 passing tests, retained repairs, Java/browser/package evidence and the next implementation plan.
- [Run the application](README.application.md): local workbench, complete SPI
  walkthrough, API console and Java delivery instructions.
- [Implementation results](docs/implementation/execution-report.md): executed
  core tasks, acceptance evidence and remaining human/bank work.
- [Second-circular test and correctness method](docs/implementation/second-circular-verification.md):
  23EC46 paragraph 10, source-based cases and the limits of current verification.
- [Five additional circulars](docs/implementation/interpretation-round1/multi-circular-result.md):
  75 scoped Python/Java scenarios, ten detected compiled mutations, bounded repairs
  and blocked releases; 113 integration/interpretation regression tests passed.
- [Unified monograph (PDF)](docs/monograph/monograph.pdf) and
  [LaTeX source](docs/monograph/monograph.tex): ten chapters, 232 pages and 76
  references, integrating both circulars, formal languages, the ensemble design,
  Java delivery and complete implementation. The [preservation map](docs/monograph/review/unification/content-map.md)
  accounts for the original proposal and monograph.
- [Executable Java example](examples/java-dry-run/README.md): generated source,
  compiled JAR, separate host caller and recorded tests.
- [Implementation entry point](docs/implementation/START-HERE.md): contracts,
  fixtures and work packages, including the required full Java backend.
- [Master implementation plan](docs/implementation/master-plan.md): task order,
  interfaces and acceptance tests, with the [current task ledger](docs/implementation/master-plan.tasks.json).
- [Paper library](docs/papers/README.md): 50 downloaded PDF editions, technical
  reading notes and an explicit coverage/gap ledger.
- [Validation and review](docs/monograph/review/unification/merge-review.md):
  preservation checks, page counts, execution coverage and review limits.

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

Open `http://127.0.0.1:8765`. The earlier narrow Java example remains preserved
as design and regression evidence. The former proposal entry point now builds
the unified monograph; both original documents remain frozen for comparison.
