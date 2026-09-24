# LegalMath

Turn selected Hong Kong regulatory requirements into reviewable specifications
and generated Java controls.

- [Smaller interpretation tasks and retained replay](docs/implementation/interpretation-round6/operator-guide.md):
  complete inventories from two readers, cross-piece qualification checks,
  exact citation preservation, bounded service failures and smaller fidelity tasks.
  [Current execution](docs/implementation/interpretation-round6/execution-report.md),
  [reset memo](docs/implementation/interpretation-round6/reset-memo.md), and
  [remaining checks](docs/implementation/interpretation-round6/next-phase-plan.md).
- [Public-reference study and live feasibility](docs/implementation/interpretation-round5/operator-guide.md):
  checked reference answers, four new SFC source families, Java mutation witnesses,
  and the [provider-blocked live result](docs/implementation/interpretation-round5/live-result.md).
  [Round5 execution](docs/implementation/interpretation-round5/execution-report.md),
  [reset memo](docs/implementation/interpretation-round5/reset-memo.md), and
  [next work](docs/implementation/interpretation-round5/next-phase-plan.md).
- [Interpretation reliability and continuing assurance](docs/implementation/interpretation-round4/operator-guide.md):
  source editions, scoped Java composition, executed question partitions, official examples,
  paired evaluation and bounded monitoring, with [execution evidence](docs/implementation/interpretation-round4/execution-report.md)
  and [implemented limits](docs/implementation/interpretation-round4/method-boundaries.md).
  [Round4 reset memo](docs/implementation/interpretation-round4/reset-memo.md) and
  [historical successor plan](docs/implementation/interpretation-round4/next-phase-plan.md).
- [Automated source and interpretation assurance](docs/implementation/interpretation-round3/operator-guide.md):
  source-only inventories, executable-meaning checks, bounded repairs and continuing change detection.
  [Execution evidence](docs/implementation/interpretation-round3/execution-report.md),
  [A7 reset memo](docs/implementation/interpretation-round3/reset-memo.md),
  [implemented method boundaries](docs/implementation/interpretation-round3/method-profile.md), and
  [next implementation work](docs/implementation/interpretation-round3/next-phase-plan.md).
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
- [Monograph (PDF)](docs/monograph/monograph.pdf) and
  [technical companion](docs/monograph/technical-companion.pdf): a 252-page
  teaching narrative with a management summary and a 76-page implementation
  reference. The revision integrates interpretation work through round four
  across all ten chapters, with 85 archived cited sources. See the
  [LaTeX source](docs/monograph/monograph.tex) and
  [seven-page illustrated process guide](docs/monograph/process-guide.pdf) and
  [revision review](docs/monograph/review/process-map/review.md).
- [Executable Java example](examples/java-dry-run/README.md): generated source,
  compiled JAR, separate host caller and recorded tests.
- [Implementation entry point](docs/implementation/START-HERE.md): contracts,
  fixtures and work packages, including the required full Java backend.
- [Master implementation plan](docs/implementation/master-plan.md): task order,
  interfaces and acceptance tests, with the [current task ledger](docs/implementation/master-plan.tasks.json).
- [Paper library](docs/papers/README.md): 50 downloaded PDF editions, technical
  reading notes and an explicit coverage/gap ledger.
- [Document validation and review](docs/monograph/review/process-map/review.md):
  preservation, citation support, mathematical checks, rendered inspection and
  the remaining reader, empirical and institutional acceptance conditions.

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
as design and regression evidence. The historical proposal PDF location now
holds the revised monograph, with its linked companion beside it. Earlier
editions remain protected for comparison.
