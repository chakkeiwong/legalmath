# LegalMath

Turn selected Hong Kong regulatory requirements into reviewable specifications
and generated Java controls.

- [Proposal v0.3 (PDF)](docs/proposal/proposal.pdf) and
  [LaTeX source](docs/proposal/proposal.tex): formal-language tutorial, full
  circular-to-Java worked case, 62-reference literature review and implementation plan.
- [Executable Java example](examples/java-dry-run/README.md): generated source,
  compiled JAR, separate host caller and recorded tests.
- [Implementation entry point](docs/implementation/START-HERE.md): contracts,
  fixtures and work packages, including the required full Java backend.
- [Master implementation plan](docs/implementation/master-plan.md): task order,
  readiness, interfaces and acceptance tests; [Claude review handoff](docs/reviews/claude-review-handoff.md).
- [Paper library](docs/papers/README.md): 38 downloaded PDF editions, technical
  reading notes and an explicit coverage/gap ledger.
- [Validation and review](docs/proposal/review.md): checked evidence and limits.

The Java demonstration implements an individual-client, solicited-transaction,
execution-monitoring profile from circular 23EC35. It passes 32 decision cases,
eleven consent histories and three mutation checks. The larger workbench, complete
RuleIR runtime and actual bank integration remain to be built. Demonstration
results carry no production authority; legal interpretation and data mappings
require the bank's review.

```sh
python3 examples/java-dry-run/build_and_verify.py \
  --jdk .localresources/java-toolchain/jdk-17.0.20.1+1
python3 scripts/check_spec_pack.py
```

The second command checks the separate full-language specification pack; it does
not execute the 35 general RuleIR cases until that runtime is implemented.
