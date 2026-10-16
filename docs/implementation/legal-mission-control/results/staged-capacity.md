# Staged capacity: a repair candidate, not a qualified live method

10 October 2026. The scoped and core constructor screens have completed within
the same admitted offline design package. They establish that the proposed
encoding can carry the measured batches without dropping the qualified source
or assigned pairs. They also reproduce two independent core blockers: the
journal measures expanded requests before compression, and the conservative
32-pair fidelity reservation exceeds its aggregate byte limit. **No production
repair, complete answer, matched tool effect or live method has been admitted.**

The original [design result](evidence-route-design.md) and its source refinement
are unchanged. These measurements use all 55 qualified source units and 78
actual retained partial claims, combined with twelve historical readings whose
quotations map uniquely into that packet. This is a **hybrid engineering
fixture**, not a same-run legal dossier or the completed two-reader inventory.
The original 35 readings remain a separate preserved population.

## Measured boundaries

The scoped constructor was exercised on all 936 claim–candidate pairs at four
batch sizes. Every assignment and quotation reconstructed exactly, including
source qualification. The request screen constructs one perspective; the call
formula counts both required perspectives. Actual tool augmentation, actual
model responses and later rounds are not included.

| Scoped pairs per request | Batches measured | Minimum calls for both perspectives | Maximum encoded request bytes | 82-call stage allocation |
|---:|---:|---:|---:|---|
| 12, current setting | 78 | 156 | 137,870 | Fails |
| 32, hypothesis | 30 | 60 | 141,410 | Fits minimum only |
| 48, hypothesis | 20 | 40 | 142,891 | Fits minimum only |
| 64, hypothesis | 15 | 30 | 145,453 | Fits minimum only |

Each input fits the 200,000-byte screen. This says nothing about whether a model
can supply adequate reasoning for 32–64 pairs, how large the expanded output
will be, or how long the response will take. Schema size is additional to the
reported request bytes. No batch size is selected as a production default.

The core constructor has a different contract. It excludes eleven CONTEXT
claims and retains 67 CONTROL/UNCERTAIN claims. The same pure `bundle` check used
by the core stage accepted the six formalized historical readings; six
unformalized readings produce deterministic NOT_ESTABLISHED rows. The fixture
therefore contains 804 core pairs: 402 deterministic rows plus 402 pending
model-review pairs, assuming no matching cache. Deterministic unsupported rows
are retained, not deleted or promoted to a source judgment. Their aggregate
occupies 160,033 bytes.

| Core pairs per request | Pending batches | Maximum original journal input | Maximum encoded input | Conservative aggregate reservation | 2 MiB aggregate screen |
|---:|---:|---:|---:|---:|---|
| 32, current setting | 13 | 223,605 | 136,175 | 2,760,033 | Fails |
| 64, hypothesis | 7 | 321,233 | 142,459 | 1,560,033 | Fits |

Both policies still fail the **current original-input journal screen**, even
though their encoded inputs fit. The larger batch passes the particular
aggregate reservation formula because there are fewer pending responses, not
because larger responses have been shown to remain small. Core criticism adds
at least one call; inventory, interaction, search and repair work are absent
from these counts. Actual aggregate response volume remains unknown.

A continuation-summary assertion that the core constructor supplied all selected
claims and all candidates in each batch was wrong relative to the inspected
code. `semantics.fidelity_request` filters both lists by `required_pairs`.
This screen exercised that real behavior. It does not establish that narrowed
batch context is sufficient for every legal comparison.

## Workload and method decision

Search permits twelve nodes and can then retain up to eight deferred readings.
Twelve candidates is a scenario, not the maximum retained population. Scoped
review also has an independent 4,096-pair limit. For example, 200 claims and
twenty candidates give 4,000 pairs, requiring 126 scoped calls even at batch 64;
205 claims give 4,100 pairs and fail the pair limit. No candidate or claim may
be dropped to make the envelope fit. CONTEXT claims and unformalized readings
remain in the scoped denominator.

The immutable original allocation is 187 calls per arm: core 36, exact-question
assignment 3, scoped review 82, dossier review 64, interaction 1, synthesis 1.
Thirteen charged baseline-core calls leave 23 core and 174 total baseline-arm
calls. A matched continuation must limit both arms to equal remaining effort;
the unused candidate allocation is not evidence that the baseline has more
budget. The global grant remains 13/400 used, with the original absolute
deadline at **12 October 2026, 04:28:01 UTC**. Its current pair reservation
ceiling is 374; unused calls outside stage allocations are not automatically
available to a new method.

The staged inventory design needs separate source checks and interaction work.
It cannot in general fit the existing 23-call core remainder. With the first
design's pressure inventories, ten piece reads and twenty-eight claim-view
reviews already require 38 calls before interactions, search or core fidelity.
Larger scoped batches do not fix that stage allocation. Moving those requests
to a different stage name would conceal the problem rather than solve it.

The selected architecture remains one shared exact-evidence store, separate
reader aggregates, bounded claim reviews against the full source, explicit
interaction/omission review, deliberate search reductions, and common resource
admission through the final answer. Core and scoped fidelity remain distinct.
Consolidating them is not included: any future proposal must account explicitly
for every lost or retained assessment dimension. The next implementation has to
repair the entire route together, using the specification below, and must not
dispatch another cap-only live configuration.

## Concrete implementation specification

1. **Separate limits and identities at every boundary.** Introduce finite
   logical request, encoded request, raw response and expanded response limits.
   Integrate them consistently in `JournalProvider`, `CompactProvider`, source
   reference resolution, `ContextProvider`, scoped dispatch and the dossier
   consumer. The diagnostic 16 MiB logical/expanded bound is below canonical
   JSON's 20 MiB ceiling but remains a hypothesis. Count/depth/expansion checks
   must run before allocation. Preserve the 200,000-byte wire caps, source
   qualification, trusted expected hashes, raw response and exact decoded
   identity. Measure after actual tool augmentation and response-schema
   preparation. A codec must not bypass the current qualification check.
2. **Separate inventories from responses.** Keep single-response limits of
   80 claims, 40 authorities and 30 uncertainties. Build a distinct aggregate
   for each independent reader, with complete piece/unit accounts and original
   occurrence identities. Five pieces permit at most 400/200/150 rows per
   reader before cross-review issues. Store cross-review issues separately with
   their evidence and affected claim IDs; do not squeeze them into the response
   uncertainty list. Preserve exactly equal commitment coalescing and reader
   provenance through later claims.
3. **Implement a genuinely staged source-review contract.** Each review gets
   the complete qualified source and exact assigned claims. Its schema records
   assigned claims, source-unit consideration, contrary evidence, qualifications,
   missing authorities and nonlocal dependencies. It cannot attest to reading
   unassigned claim contents. Interaction requests must include the exact
   records at both ends of every nominated dependency. A final omission review
   challenges the claim catalogue and findings against the source. Unknown or
   unfit interactions remain explicit blockers. The old whole-inventory prompt
   used for the earlier size fixture must never be dispatched on a partial view.
4. **Make reductions usable by the actual consumers.** Search/refinement must
   receive reviewed evidence tied to exact raw records, the original question,
   contrary readings and unresolved reductions. A model summary is a fallible
   interpretation, not a lossless codec. Preserve source access and reader
   provenance. The real tool arm must run all selected applicable adapters and
   measure the augmented payload; unsupported profiles must survive. Reuse the
   current `dossier_answer` occurrence accounting, dependency closure,
   interaction and synthesis route, qualifying the actual generated dossier.
   An empty synthetic reduction is not an adequate output-capacity test.
5. **Admit the complete remaining workload at each transition.** Use actual
   claim and candidate counts, both fidelity stages, both scoped perspectives,
   unresolved dependencies and final dossier packing. Preserve the original
   grant, ledger prefix and failed reservations. Any stage reallocation needs
   an explicit reviewed successor allocation and matching enforcement; never
   edit the old authorization or misclassify a request. Equal arm effort and
   the original deadline must survive. Known insufficient workload capacity
   refuses before dispatch rather than spending calls on a doomed prefix.
6. **Qualify one candidate before a further live comparison.** Use the retained
   rejected full-unit response as a regression case; exercise every constructor
   through a local no-network responder, both arms, actual tool feedback and
   the final consumer. Test changed sources, ambiguous spans, expansion overflow,
   missing/foreign pair IDs, lost authorities/uncertainties, false completion,
   interrupted journal reservations and over-budget dispatch. Source-derived
   cases must preserve P10/P11 distinctions, actor/activity/time applicability,
   assessed conduct versus effective mitigation, shared-error reconciliation,
   secondary records, unknown facts and unformalized fulfillment. Then conduct
   bounded actual response qualification on the selected model before the full
   matched trial, within whatever method is separately admitted. Input byte fit
   alone cannot justify that trial.

Offline implementation qualification and live legal qualification are different
stages. Requiring future real model answers before implementing a candidate
would be circular. A candidate can be implemented against exact retained data
and labeled fixtures after a reviewed repair admission; its unmeasured output
and semantic risks then require bounded live qualification before promotion.
The current offline task has **zero production repair attempts**, so this
specification does not itself admit that implementation or alter its allowance.

## Review and acceptance decision

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Retain both constructor screens | Full measured pair accounting, exact reconstruction and qualified source retention pass | No fixture identity/coverage veto fired | Hybrid partial inputs cannot represent the completed target | Use these measured boundaries in one coherent candidate repair | Full-target feasibility or legal fidelity |
| Reject the current full-route dispatch | Actual journal and conservative core reservation fail; full inventory/search pressures also fail | Capacity veto supported before any new call | Actual complete claim/candidate counts and model outputs | Implement only after a separately reviewed bounded repair admission | Failure of the legal tools or underlying legal research |
| Keep larger batches as hypotheses | All measured encoded inputs fit | Output, latency and substantive reasoning remain unqualified | Compression may merely shift the failure to response or reasoning limits | Test real response adequacy before selecting a batch policy | That 64 is better than 32 or production-ready |
| Keep the mission open | No complete original-question answer pair exists | Legal standards, faithful reduction and matched contribution remain open | Whether any selected tool changes a supported inference | Return to the P10/evidence comparison after qualifying the entire route | Closure of any original obligation or full evaluation of a tool |

This is deterministic engineering evidence. There is no stochastic candidate
ranking, statistical superiority or default promotion. Byte differences and
minimum call counts explain resource pressure only. The strongest alternative
explanation of apparent success is that small syntactically exact envelopes
are harder for the model to understand or cannot contain adequate response
reasoning. Actual source-grounded outputs would distinguish that explanation.
The weakest evidence remains the missing complete answer and downstream use.
The results reject current dispatch eligibility, not the research direction;
the specified consolidated repair addresses the observed failure.

Execution records:

- `.venv/bin/python scripts/legal_mission_staged_capacity_screen.py`:
  `staged-capacity.json`, 23.671 seconds; reviewed in `staged-method-review.md`.
- `.venv/bin/python scripts/legal_mission_core_fidelity_screen.py`:
  `core-fidelity-capacity.json`, 3.776 seconds; reviewed in
  `core-fidelity-review.md`.

Both artifacts are under
`artifacts/legal-mission-control/2026-10-10/evidence-route-design/` and bind
their scripts, plans and input hashes. Python 3.11.15 ran on CPU with no GPU
imports/detection. Seeds are inapplicable to these deterministic measurements.
The core artifact records commit `cde11a610cbd1e90eafecfa0cbda6efd51f9bef2`
and the relevant dirty source hashes. No provider, Java/tool worker, installation,
network, production edit, commit or push was used in these two screens.
