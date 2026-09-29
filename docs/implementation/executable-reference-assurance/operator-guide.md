# Executable reference v2

The public Python route is:

```python
from legalmath.interpretation.assurance import executable_references_v2
from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation

runner = CompleteInvestigation(
    root, directory, provider, jdk, assessment_at,
    reference_protocol=executable_references_v2.PROTOCOL,
    scoped_schedule="round-first",
    machine_qualification=True,
)
result = runner.run(sources, selected_slice)
```

Supply the existing provider authorization, source inputs, toolchain, exact
assessment timestamp and bounded settings. This example does not grant calls.
Both existing live grants are exhausted. Use an explicitly offline provider for
simulations; actual live execution still checks the original authorization and
issue limits. The qualified dossier joins this transport to the existing shared
proof/Java route. V2 itself neither generates different Java nor proves the
source interpretation.

Earlier source and question stages use `legalmath.source-spans.v1`. The scoped
correspondence stage uses `legalmath.source-and-executable-spans.v2`. Its table
contains only scope/result expressions parsed from the actual retained reading.
Fact descriptions and runtime explanations remain context. The request must
match the caller-held reading and question; its own hashes cannot authenticate
substituted text. Selections bind those originals and the request/schema.

For a direct scoped call, `scoped_investigation.investigate` accepts the same
`reference_protocol` argument. For a direct transport call, use:

```python
answer = executable_references_v2.complete(
    provider, request, fidelity_schema, settings, directory,
    readings=retained_readings, questions=retained_questions,
)
```

Run `fidelity_v2.validate` on its result using the original source packet,
claims, readings, questions and required pairs. The normal investigation does
this automatically. Transport success means exact evidence selection; it does
not mean the model's judgments passed the semantic contract or are legally true.

Retained files include `executable-original-context.json`, original request and
schema, executable references, source-reference wire request/schema,
`raw-response.json`, both resolution results and both validation records.
Rejected judgments remain unchanged. Unencoded/unsupported readings expose no
selectable expression. NOT_APPLICABLE still requires the separately justified
NOT_APPLICABLE_TO_THIS_QUESTION relation; software does not choose that label.

V1 remains an explicit historical option. Do not point v2 at a v1 journal to
reset reservations or reinterpret evidence. Changed methods require their own
recorded implementation identity and preserve predecessor histories. The scoped
v2 binding also includes parser/renderer dependencies. Whole invalid batches
remain rejected; rows are not counted as extra votes.

The engineering controller uses the exact commands in `allowlist.json`. It
reserves a phase attempt, freezes sources, executes checks, preserves failure,
then refreshes its next plan. Failed retries need the corresponding
`D2-repair-N.json` or `verify-repair-N.json` bound to the previous manifest and a
successful focused-command receipt matching current inputs and actual log.
Three engineering attempts is the limit; these attempts are distinct from and
cannot reset live model or legal-issue budgets.
