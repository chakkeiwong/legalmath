# Native Catala gap-closure results

The branch now has an explicit native v2 profile, optional values and payload
enums, five pinned library imports, executed decisions with source positions,
and portable packages with named review and authenticated transaction controls.
The engineering checks pass. The conversion study does **not** establish that
Catala is better than RuleIR. Independent legal adjudication, representative
heldout sources and human reviewer measurements remain outstanding.

The [reviewed plan](../../../plans/catala-gap-closure.md) was executed on
26–27 September 2026 from branch baseline `71633380`. Its skeptical audit revised
the baseline, authentication design, dependency scope and human-evidence claims
before acceptance. Further audits rejected misleading draft evidence and repaired
specific failures. The [post-run repair](post-run-repair.md) preserves the original
study and gives the successor its own commitments.

## Implemented behavior

- Native v2 binds exact arithmetic, money rounding, calendar conventions,
  complete-input abstention and exception behavior into each build. Version 1
  remains the default for tasks without an explicit profile.
- Known optional absence is distinct from unavailable evidence. Optional values,
  payload enums and nested acyclic types round-trip through Python, Java and
  Catala. Declared imports cover `Integer_en`, `Decimal_en`, `Money_en`, `Date_en`
  and `List_en`, including their pinned transitive dependencies.
- An isolated derivative of the pinned compiler records actual conditions,
  branches, option decisions and enum arms with source coordinates, alongside
  scope outputs. The untouched compiler checks invariants and supplies the plain
  comparator. The trace transform does not pass the upstream nested-scope
  inversion check; manifests state `trace_invariant_check=untouched_compiler_only`.
  Standard-library internals are not instrumented. This records execution, not a
  complete legal justification.
- Packages bind source bytes, interface, semantics, builds, cases and reviews to
  an externally supplied hash. Import rejects corrupt inventories and unsafe ZIP
  paths. Local staging reruns retained cases. Distinct named legal and engineering
  reviewers approve a displayed review commitment; multiple tokens for one person
  do not create multiple reviewers. Activation, rollback and transaction commit
  recheck current authority, expiry, revocation, package and subject revision.
  Historical replay verifies the original bytes. Legacy unpackaged releases
  require staging and approval again.

The [API guide](../native-converter/README.md) explains the profile and package
adapter. Recursive types, arbitrary imports and a production institutional
identity/transport integration are outside this implementation.

## Executed semantics

The [conformance report](../../../../artifacts/catala/gap-closure/semantics/conformance.json)
contains four shared controls, four deliberate-difference controls and two
native-feature controls. Catala's original interpreter, plain Java and
instrumented Java execute the native cases; RuleIR's Python and Java engines
execute the representable comparator cases. References use separately specified
exact values. Large integers, signed money, leap dates, nested scopes and a lazy
branch containing an otherwise failing division receive executable checks.

| Case | Native Catala | RuleIR |
| --- | --- | --- |
| Complete Boolean, integer, money-subtraction and date controls | Matches declared values | Matches the same values |
| False AND unknown input | Abstains before execution | False |
| True AND unknown input | Abstains before execution | Unknown |
| False AND conflicting input | Abstains before execution | Conflict |
| Two active exceptions with identical literal consequences | May coalesce to that value | Conflict |
| Two active exceptions with different consequences | Conflict exception in interpreter and both Java variants | Conflict status |
| Half of positive/negative 101 minor units | 51 / -51 minor units | Error for nonintegral exact scaling |
| Known option absence | Valid native value | Outside this declared RuleIR interface |

These observations establish finite conformance and expose policy differences.
They are not a proof of equivalence. The native runtime currently surfaces
conflicting consequences as an execution failure, rather than RuleIR's structured
`CONFLICT` result. Consumers must preserve that distinction.

## Source conversion and repair

The original study froze four tasks, three retained source families and 44 factual
cases. It used real generation in all three arms, the same primitive interfaces,
a two-dispatch cap per arm/task, fresh contexts on the same model route, and hidden
references excluded from prompts and repair feedback. The RuleIR arm measures its
source-generation component, not the full assurance/search system. The reviewed
Catala arm must spend a dispatch on criticism as well as generation; equal call
budgets therefore leave less room for its format repairs.

| Task | RuleIR generation | Minimal native | Source-reviewed native |
| --- | --- | --- | --- |
| Net-assets calculation | Rejected: exact source quotation mismatch | Pass | Rejected: citation in executable source field |
| Gift control | Abstained: missing footnote/effective-date context | Pass | Rejected: citation in executable source field |
| Public network control | Abstained: missing footnote and scope/modal questions | Abstained: missing footnote | Rejected: citation in executable source field |
| Prior consultation | Abstained: missing authorised-product qualifier | Rejected: missing executable fence | Unresolved after generation and source criticism |

The [frozen comparison](../../../../artifacts/catala/gap-closure/study/results.json)
used 19 of its 24 authorized slots. Only the consultation task reached the critic
in the reviewed-native arm. Its other failures are output-format failures and
must not be described as rejected legal reasoning. The two minimal-arm passes
are conditional matches to provisional references, not legal correctness.
Three convenience-sampled families and wide conditional paired intervals support
no ranking. All attempts and failed dispatches remain counted.

The observed failures triggered a bounded repair. The candidate schema, generation
request and error feedback now explicitly require executable code in `source`.
A [separate two-call probe](../../../../artifacts/catala/gap-closure/schema-repair-probe/result.json)
on the exposed net-assets task produced executable Catala, received a SUPPORTED
critic verdict and passed all four exact hidden cases. This demonstrates that
the revised request worked on this attempt; it does not establish a causal or
general improvement. Together the study and repair used 21/24 slots; the shared
ledger advanced from 466 to 487 without increasing its 500-call global maximum
or this investigation's ceiling of 490.

The [successor source packet](../../../../artifacts/catala/gap-closure/source-review-successor/packet.json)
adds the exact omitted footnotes and makes the SFC-authorised qualification
explicit in the material-change input. The original packet and results remain
unchanged. Referenced FAQ and Tokenised Securities Circular provisions still need
source review; neither self-review nor model criticism resolves that legal work.
Both packets remain pending independent adjudication. Admission requires a
trusted independent reviewer attestation bound to the exact task, cases and
witness; source-family exposure blocks a heldout claim even if row labels change.
All these source families have prior project exposure.

## Reviewer study

The [current reviewer packet](../../../../artifacts/catala/gap-closure/reviewer-study/current.json)
contains matched handwritten RuleIR and Catala controls with compiled seeded
defects. These controls are experimental materials, not successful model outputs.
Eight unfilled participant slots each contain four different tasks, two per
language. Every task/language/defect combination occurs twice, and each display
position receives four assignments in each language. Defect labels and compiled
answer keys are separated from participant files. Language syntax remains visible.

Thirty-two deliberately synthetic responses exercise scoring and are excluded
from human evidence: 16 correct, 8 omissions and 8 false alarms. Duplicate
responses, invalid time, altered assignments and unenrolled human claims are
rejected. There are **zero human observations**. Source adjudication and a
prospective sample-size/inference design are prerequisites to a meaningful human
comparison; the dry run establishes neither readability nor reviewer speed.

## Validation and decision

All **725 collected tests** are covered and passed across focused and regression
runs: 88 focused tests, 31 remaining Catala tests, 78 conformance tests, 522 other
repository tests and 6 new source/repair tests. This is combined coverage, not a
single final full-suite invocation. The broader run initially had two archive
protection failures. Ten ignored files were missing from the isolated worktree;
main held identical bytes matching the protected hashes. Restoring only those
copies made both checks pass. No historical commitment was altered. The existing
Python environment was linked into the worktree for scripts requiring `.venv`.

The [validation ledger](../../../../artifacts/catala/gap-closure/validation.json)
records test selections, outcomes, timings, environment and log hashes. Semantic,
reviewer and conversion runs each retain their own command, baseline commit,
input/code commitments, environment, time and results. The conversion's frozen
code archives still match their hashes; current code includes the explicitly
separate post-run repair.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Optional v2 engineering | Exact execution, replay, package/auth tests pass | No observed engineering veto | Finite construct and threat coverage; trace-transform limitation | Use the explicit profile and retain regression checks | Production readiness |
| Shared semantics | Four complete-input controls agree | Deliberate divergences recorded | No general equivalence proof | Add source-driven cases within the declared fragment | RuleIR replacement |
| Original conversion candidates | 2/4 minimal; 0/4 reviewed; 0/4 RuleIR under frozen cap | Rejections and abstentions retained | Format defects, missing context, small exposed corpus | Preserve failures; use successor packet for reviewed development | Language superiority |
| Format repair | One generation, critic and four cases pass | No probe veto | One exposed attempt | Replicate only under a separately justified study | General converter improvement |
| Legal interpretation | Exact bytes and spans validate | Independent adjudication absent | Meaning, cross-references, applicability and references | Qualified independent review; retain unresolved questions | Legally correct automation |
| Reviewer comparison | Matched controls and collector checks pass | Human evidence absent | Comprehension, time, omissions and assistance | Adjudicate sources, then finalize and run a human study | Readability or speed advantage |
| Default promotion | Heldout and independent evidence required | Promotion blocked | Representativeness and external validity | Keep native path optional | New default or deployed authority |

| Inference status | Finding |
| --- | --- |
| Hard veto evidence | Candidate format failures and unresolved source choices veto those candidates. Missing human/heldout evidence vetoes promotion. |
| Statistically supported ranking | None. |
| Descriptive-only differences | Original task passes: minimal native 2/4, reviewed native 0/4, RuleIR generation 0/4. Repair probe 1/1 exposed task. |
| Default readiness | Not established. |
| Next evidence needed | Independently adjudicated unexposed source families, a budget suited to each declared workflow, repeated paired measurements and qualified human observations. |

Post-run red-team assessment: format compliance and source completeness explain
much of the observed conversion difference, so attributing it to Catala's semantic
advantages would be unsupported. The smallest successful repair rescued one
candidate; it did not validate the full research direction. A representative,
adjudicated paired study could overturn the descriptive ordering. Provisional
legal references and the three-family convenience sample are the weakest parts
of the current evidence. Expected candidate failures triggered repairs, while the
promotion veto remained in force.

Earlier prose-only checks, handwritten “conversion” controls, invalid boundary
schemas and confounded reviewer drafts are excluded. Their hashes and reasons
are recorded in [invalidated-drafts.json](../../../../artifacts/catala/gap-closure/invalidated-drafts.json);
the superseded bytes are retained locally under the ignored `drafts/` directory.
Only the conformance report and reviewer `current.json` identify accepted runs.
