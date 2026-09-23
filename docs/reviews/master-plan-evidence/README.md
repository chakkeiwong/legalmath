# Evidence for master-plan preparation and review

Date: 22 September 2026. This directory records a deterministic planning audit,
not an application release, legal opinion or effectiveness experiment.

- [Starting file hashes](baseline-files.json): 31 inspected starting files.
- [Original Java verification](java-original-verification.json): copied before review.
- [Isolated Java verification](java-isolated-verification.json): actual temporary-workspace run.
- [Original/replay comparison](java-replay-comparison.json): all fifteen input,
  runtime, generator, generated-source and JAR hashes match.
- [Host output](java-isolated-host-output.txt): separate Java caller before/after withdrawal.
- [Contract probes](contract-probes.json): observed validator omissions and
  consequence of real backend identity on execution hashes.
- [Specification check](spec-check.json): current fixture/schema/source/SQL checks;
  zero full-runtime decisions.
- [Review input manifest](review-inputs.json): current plan/contracts/example
  file identities for Claude; excludes itself to avoid self-reference.
- [Plan consistency check](plan-check.json): task graph, core dependencies,
  links and protected baseline checks.

The Java command, executed in an isolated copy of the example and its inputs:

```sh
python3 examples/java-dry-run/build_and_verify.py \
  --jdk /home/chakwong/python/legalmath/.localresources/java-toolchain/jdk-17.0.20.1+1
```

Its working directory is in [replay-location.json](replay-location.json). It may
be removed by temporary-directory maintenance later; the results needed for the
review are preserved here. The original example and manuscript PDF were not
modified. No private source data was introduced.

The run has 32 decision cases, eleven consent histories, three detected compiled
mutations, one unsupported-operation rejection, 34 checked source spans, separate
host invocation and a reproducible fresh Java build. This evidence covers
SPI-Demo1 only. The full RuleIR, events, lifecycle and host protocol remain tasks.

Read [the author audit](../master-plan-review.md) for interpretation and
[the Claude handoff](../claude-review-handoff.md) for the independent review
request. A prepared handoff is not a completed Claude review.
