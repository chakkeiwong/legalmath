# Investigate a source clause through the product command

`legalmath assurance-interpret-issue` accepts a retained source and a declared
question. It proposes rival interpretations, executes their consequences in
Python and Java, seeks omitted readings, criticizes the proposals against the
source, and performs one further reconsideration when discrepancies remain.
The result preserves every unresolved question and every rejected response.

This command implements the bounded `declared-predicate-methods.v2` profile.
The earlier sixteen-job comparison used version 1. Version 2 also propagates
questions attached to individual readings and triggers reconsideration when
critics support incompatible executable behaviors. Rejected generation proposals
are supplied unchanged to the semantic reviser, so a structural repair cannot
silently remove an earlier reading from its consideration. It validates the public
packet, unique source identifiers, assessment time and Java toolchain before
paid dispatch.

## Supply the question

The JSON input has exactly three fields: `packet`, `issue` and `at`.
`examples/interpretation-assurance/declared-issue.json` is a complete example.
Its source is the retained SFC Family Offices FAQ and its question concerns the
antecedent of the ordinary-course guidance. The example's three input facts are
supplied classifications; their adequacy remains open to criticism.

The packet contains complete retained source units and their identities. The
issue contains the question, exact target quotes, one to four Boolean fact
definitions, abstraction assumptions and qualifications. Its
`source_packet_hash` must equal the canonical hash of the packet. Use
`legalmath.canonical.digest(packet)` to calculate it after a deliberate source
change. The timestamp uses UTC and six decimal places, for example
`2026-09-24T00:00:00.000000Z`.

A supplied fact must describe an input to the disputed interpretation. Defining
one as “the legally correct answer” would assume away the task. Readers may
report missing vocabulary or leave a proposal without executable code. Such a
proposal remains visible and prevents a no-discrepancy result.

## Execute and resume

The allowance file must already exist under the user's authorization. This
command cannot create a larger grant. Schedule runs serially on a shared grant
so run-level call accounting is unambiguous.

```sh
.venv/bin/legalmath assurance-interpret-issue \
  --public examples/interpretation-assurance/declared-issue.json \
  --out artifacts/interpretation/my-issue \
  --allowance artifacts/interpretation/round7/live-allowance.json \
  --jdk .localresources/java-toolchain/jdk-17.0.20.1+1 \
  --method assurance
```

A run reserves an absolute ceiling of 24 further calls and requires at least that
many calls to remain available. A generation request returns at most two
readings; a criticism request addresses at most four proposals while retaining
all proposals as context. Each task has at most three attempts. The complete
run has a one-hour execution bound by default. Two successive transport failures
stop dependent processing. Output-validation failures retain their response and
receive bounded repairs. Neither failure refunds a call.

The ordinary assurance method begins with two separate reader contexts. The
second reader receives no first-reader proposals. A challenger then looks for
missing alternatives. Java execution supplies cases in which proposals differ;
critics see those cases and the source. A remaining question, deferred or
non-executable proposal, challenge, or behavioral disagreement triggers one
reconsideration and another criticism. Supporting two inconsistent programs does
not settle their disagreement. The smaller `single-reader`, `isolated-readers`
and `search` methods are available for diagnostics; they omit stages explicitly.

Use the same command with `--resume` to reuse completed work. A completed resume
checks source and method identity, implementation hashes (Python, Java, JSON schemas and SQL sources), the provider route,
Java version, the final allowance checkpoint, manifests and every task receipt.
It returns the saved result without dispatching another model request.

An interrupted dispatch requires the same command with `--recover` first, then
`--resume`. Recovery retains the consumed reservation. After a hard interruption,
unknown elapsed runtime is conservatively charged through recovery. A changed
source, question, method or implementation requires a new output directory;
the prior interpretation and its uncertainty remain in the record.

## Read the result and Java evidence

`result/report.json` states the question, actual method, limits, model calls,
status and path of the final executed comparison. Its `output_descriptors` map
each executable candidate to the exact issue question and proposed result meaning;
this may be narrower than the packet's original selected source scope. `UNCERTAINTY_RETAINED` means
that questions or competing outcomes remain. `NO_DISCREPANCY_REPORTED` means
only that this bounded procedure reported none. Both have
`release_eligible: false`, `legal_accuracy_evaluated: false` and no asserted
probability of legal correctness.

`work/result.json` retains all candidates, their originating roles, generation
concerns, deferred candidates, criticism history and rejected proposal history.
Each proposal carries exact quotations, its reading assumptions and the supplied
qualifications. An unsupported formalization receives no invented Java answer.

The final comparison is under `work/java-initial/` or
`work/java-reconsidered/`, as named in the report. It contains:

- `issue-distinction-report.json`: all combinations of true, false, unknown and
  conflicting evidence for the supplied Boolean facts, the Python and Java
  outcomes, distinct behavior groups and counterexample scenarios;
- a generated Java source, compiled JAR and build manifest for each encoded
  candidate, organized by the compiled bundle hash;
- ranked distinguishing scenarios. Their score counts separated behavior-group
  pairs, so multiple prose descriptions of one formula cannot inflate it. This
  score is not a legal probability or evidence that a factual scenario can occur.

The Java output means whether a selected predicate holds under supplied facts.
It is not automatically a compliance verdict, an exemption or licence possession.
The question and candidate must accompany the Java artifact. Existing
`legalmath.java.host_package.prepare_interpretation` creates draft Java 17 host
packages with an output descriptor, source bytes and verification. That older
packaging API uses `packet.selected_slice` as its question: ensure that it is
the intended question before preparing a package for a narrower issue. Compare
the resulting descriptor against the command's issue question before delivery. Round eight
contains two such executed packages. A bank adapter still needs the institution's
actual host API, fact mappings, evidence requirements and release controls.

## Retained execution and remaining uncertainty

See `execution-report.md` for the current accepted phases, exact calls and tests.
The fixed supervisor is `scripts/run_public_issue_plan.py`; `status` and
`preflight` show the recorded state and protected evidence. Every failed phase
requires an executed repair, refreshed successor plan and current-source review.
The command investigates interpretations but does not replace the earlier source
inventory, dependency acquisition and change-monitoring components.

Fresh contexts from one provider can share an error. Exhaustive evaluation of a
small Boolean vocabulary proves only what the encoded formulas do on that
vocabulary. It cannot prove that the source meaning or vocabulary is complete.
These limitations guide targeted further investigation; they do not impose a
blanket requirement to purchase an external legal opinion for every clause.

The accepted live example preceded the final H3 identity repair. Its exact
implementation is archived in `.localresources/interpretation-round10/pre-h3-implementation/`.
Use the reproduction command in `execution-report.md` to audit that existing
run. The current entry point intentionally rejects its older implementation
binding; new investigations use the stronger identity automatically.
