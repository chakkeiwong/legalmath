# Candidate responses in ordinary investigations

The candidate-specific response constraints used by the completed coverage
runner are now available in the product's `CompleteInvestigation` and scoped
investigation APIs. Select the profile explicitly:

```python
from legalmath.interpretation.assurance import candidate_responses
from legalmath.interpretation.assurance import executable_references_v2
from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation

runner = CompleteInvestigation(
    root, directory, provider, jdk, at,
    reference_protocol=executable_references_v2.PROTOCOL,
    response_profile=candidate_responses.PROFILE,
    input_profile="literal",
)
```

The profile binds each requested claim/candidate pair to that candidate's exact
question and selectable executable expressions. Unformalized candidates retain
unavailable meaning; uncertainty and blocked judgments remain available. The
caller expands the short response identities before the existing source,
executable and legal-judgment validators run. Raw responses, the expansion and
the binding are retained in the scoped action's `source-references` directory.

The response option is part of the investigation revision, scoped journal and
whole-investigation observation method. Changing it cannot silently reuse the
previous journal. It requires executable references v2 and literal input;
readable input tables are currently incompatible and are rejected before
dispatch. Omitting the option preserves the existing literal response default.
Normal live-grant checks and call limits still apply to live providers.

The [reviewed plan](../../plans/legal-candidate-response-product-integration.md)
defines this repair's scope. Its offline replay preserved all 984 retained
assessments over 492 pairs and all 473 concerns, with zero live calls. Replay
checks deterministic content preservation; it supplies no new legal judgments.
The completed coverage scripts remain frozen for historical verification. The
product implementation imports no script modules, and regression checks compare
its codec with the retained runner.

See [execution-result.md](execution-result.md) and [reset-memo.md](reset-memo.md)
for validation, limits and the next substantive work.
