# Legal interpretation program: phase plans

The [master program](../legal-interpretation-master-program.md) states the
background, architecture, evidence contract and repair/refresh protocol.
All phases below are planned; this documentation task has not executed them.
A phase can complete its engineering work with explicit legal qualifications.
It cannot declare a legal premise resolved merely because its software works.

| Phase | Implementation plan | Prerequisites |
|---|---|---|
| P0 | [Bind the baseline and repair contradictory operative wording](P0-baseline-and-operative-repair.md) | documentation package |
| P1 | [Represent source meaning and evidence without losing uncertainty](P1-typed-meaning-and-evidence.md) | P0 |
| P2 | [Make the disputed duties explicit](P2-clause-scope-and-pilot-readings.md) | P1 |
| P3 | [Evaluate competing arguments under declared semantics](P3-arguments-and-explicit-priorities.md) | P2 |
| P4 | [Interpret precedents and justify their transfer](P4-precedent-and-factor-transfer.md) | P1, P2, P3 |
| P5 | [Derive scoped facts from evidence](P5-evidence-applicability-and-consequences.md) | P2, P3, P4 |
| P6 | [Run the same meaning through explanation and execution](P6-lowering-explanations-and-product-integration.md) | P3, P4, P5 |
| P7 | [Verify scoped invariants and expose silent failures](P7-independent-checks-and-formal-claims.md) | P6 |
| P8 | [Extend coverage and prepare honest future observation](P8-coverage-and-prospective-observation.md) | P7 |

Each plan identifies concrete new modules, actual existing integration points,
future test commands, discriminating cases, acceptance, repair/veto conditions
and what the next plan must change in response to the result. All proposed source
and test paths are marked as future work. The phase manifest records dependencies
and initial statuses; it does not run code or replace observed results.

Use the [Claude handoff](../../implementation/legal-interpretation-program/claude-handoff.md)
for the independent program review and the
[author review](../../implementation/legal-interpretation-program/program-review.md)
for issues already repaired in this specification.
