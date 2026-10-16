# Capacity diagnosis and remaining-work resolution, 12 October 2026

The immediate capacity refusal comes from our application's request policy and
repeated evidence, not a demonstrated model-service or machine-memory limit.
Exact sharing helps, but the tested representations do not carry even the
partial original input within 200,000 bytes. The [reviewed resolution
design](../../../plans/legal-mission-capacity-resolution-2026-10-12.md) therefore
covers request preparation, final review, provider qualification, bounded review,
source acquisition and per-tool answer evaluation together.

This work executed only a bounded local diagnosis and wrote the design. No
production files or defaults changed; no provider calls, native-tool reruns,
network or GPU operations occurred. Detour 17 remains settled and the historical
grant remains expired with 41/400 calls charged. All four legal questions,
46 obligations, 35 readings and six original-answer tool evaluations remain
open. The 224 premise records and 407 subparts remain retained.

## What was reproduced

| Request or diagnostic | Bytes | Interpretation |
|---|---:|---|
| Original indexed regulatory context, literal compact v2 | 353,561 | Partial original context, before complete dossier |
| Existing shared profile, original runtime construction | 252,475 | Reproduces the previous retained result |
| Same logical request, retained JSON reload | 252,110 | Same evidence; insertion order changes table layout |
| Global repeated strings, compact markers | 239,994 | Exact local prototype; exceeds the application cap |
| Global strings and substring references, compact markers | 224,388 | Exact local prototype; exceeds the application cap |
| Current final-review reservation, runtime construction | 368,972 | Conservative bound using trial output limits |
| Current final-review reservation, retained JSON reload | 368,696 | Same trial limits, order-normalized baseline |
| Substring prototype's fixed final-review context | 232,121 | Already too large before answer/catalog/binding |

The final prototype plus the current 16,000-byte answer and 92,032-byte catalog
reservations yields a **340,153-byte subtotal**, excluding variable binding and
outer framing. It is not an admitted total bound. The trial 16,000 answer bytes
and 128 fields have not demonstrated adequate room for the original legal
analysis. A rejected conservative reservation does not show that every actual
answer is that large.

The initial verbose-tag prototypes measured 289,212 and 266,856 bytes. They
wrapped scalars and arrays in extra tags, unlike the current codec. The final
comparison removes that avoidable overhead. All candidates reconstruct the exact
compact-v2 request. No candidate is a product transport or a demonstrated format
the model can interpret reliably. This is neither an optimization search nor
proof that no other exact representation can fit.

The baseline discrepancy is fully reproduced. The initial diagnostic assumed
the previous runtime measurement would equal a canonical JSON reload and stopped
before producing a result. Reconstructing the previous builder in memory yields
52 column shapes and 252,475 bytes. Reloading canonical JSON yields 51 shapes and
252,110 bytes; normalizing the construction reproduces the reload's exact wire
hash. The source hash is unchanged. The codec uses object insertion order for
shapes and traversal order for IDs, while persistence sorts object keys.
The 365-byte difference does not explain the major overload, but must be removed
from any deterministic admission contract. Prior evidence was not rewritten.
Diagnostic-script assertion/serialization corrections are retained in
`capacity-diagnosis/attempts.md`; they are not production defects or repair
attempts. The bounded computations took seconds, below the five-minute budget.

## Causes and their consequences

| Code or retained evidence | Finding | Required response |
|---|---|---|
| `search/models.py:Settings`, `search/providers.py:CodexProvider.complete` | The application rejects request JSON above 200,000 bytes before reserving a provider call. The separately supplied schema/instructions are outside that byte check. | Distinguish application bytes from service tokens; qualify full prompt, output, latency and useful response behavior on the actual route. |
| `dossier_answer.py:COMMON`, `partition` | Complete common source and acceptance material is repeated; an empty group fails before record batching helps. | Remove duplicate representation and qualify an appropriately sized full context, or change common-context assignment through reviewed bounded materialization. |
| `interaction_request`, `synthesis_request`, `capacity_budget` | Complete-raw interaction/synthesis reattach the full dossier; the shared profile currently requires this method. | Review the downstream method explicitly; smaller initial groups alone do not fix it. |
| `answer_evidence.catalog`, `answer_transport.final_review_budget` | Final review contains answer text twice plus per-field metadata. | Version and validate path-based catalog resolution, retaining actual answer text and useful output room. |
| `evidence_tables.encode` | Equal logical inputs can produce different wire layouts after persistence. | Canonical preparation and the same measured object at dispatch. |
| `route_admission.workload/admission/check` | Separate pair, candidate, action, group, time and grant limits remain; live execution is explicitly refused by the current guard. | Qualify all stage resources and a reviewed live-authority binding, not just one byte limit. |
| Incomplete current inventories | Actual complete claim/candidate populations and route cost remain unknown. | Bounded acquisition-only stage, then freeze actual counts and re-budget before downstream dispatch. |

`answer_acceptance` consumes 217,270 logical bytes, compared with 62,013 for the
source packet, 40,753 for legal indexes and 30,410 for source qualification.
Acceptance includes both substantive distinctions and repeated metadata/text.
Removing fields was measured only for attribution: deleting the obligations
would make this partial request appear to fit at 188,496 bytes but would change
the target and is explicitly rejected. Marginal savings are non-additive.

Catalog duplication is also not the whole problem. The small retained product
answer is 4,414 bytes and its catalog 7,127 bytes; removing copied field text
leaves 5,995 bytes. Its separately supplied response schema adds 3,424 bytes to
the 72,375-byte request, before CLI instructions. The small scripted product
does not establish full-input feasibility or realistic output requirements.

## Proposed implementation and evaluation

The design starts with one deterministic prepared request and explicit limits
for logical evidence, wire bytes, full prompt/output tokens, decoded output,
structural populations, actions, calls and time. Internal source storage can
share exact content, while occurrence identity and legal/source qualifications
remain distinct. Each model must receive the actual text it needs: the current
provider cannot read a local path or dereference a hash.

Next qualify a larger ordinary context on the actual service before treating
200,000 as immutable or requiring complex compression. A finite canary must
exercise meaningful source/citation handling, separated exceptions and rivals,
real schemas and adequate output. It cannot certify a yet-unseen full dossier.
Once complete inventory exists, repeat admission using the actual whole-route
population and final-review reservations.

Where that route fails, the proposed alternative divides work by original
question and necessary evidence dependencies. All source units, readings,
requirements and occurrences receive explicit review assignments. Independent
source omission checks, source-supported interaction reviews and a final
cross-question review must catch misplaced footnotes, exceptions, temporal
conditions and common assumptions. Unresolved dependencies remain unresolved.
This is a changed legal-review method requiring evidence, not a smaller version
of the existing all-raw-context method.

Source qualification and legal warrant work remain independent: P10's discharge
standard and applicable source/version chain; P14/FN5's attachments and separate
P15/P16 requests; the inference from observations to adequate supervision and
ownership records; and Gatecoin's relationships, later treatment and transfer.
Uninspected authority is our unfinished research. Client terms, roles, requests,
dates and operational facts are external inputs; their absence still permits
conditional answers. No inspected evidence establishes an impossible gap.

Each eligible tool then gets a separate matched answer trial. Retrieval needs
source relevance and downstream effect; formal adapters need supported original
representations; argument engines need legally justified premises and attacks.
A valid case result can show help, harm, no observed change or a limited supported
use. An invalid review cannot show no benefit. Keep deferred and conceptual
tools separate from the six selected integrations, and keep those integrations
separate from full evaluation of their answer contribution.

The plan records success dependencies, completion-only assessment, alternatives
and bounded recovery. Failed capacity does not cancel source research; one tool's
failed review does not cancel another valid arm. New live work needs an actual
runnable qualification packet and fresh authority because the old deadline has
expired. No speculative approval request or allow-list change was necessary for
this diagnosis. The design is complete; its implementation is not executed or
admitted by this result.

## Decision and post-review

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not established |
|---|---|---|---|---|---|
| Accept diagnosis | Same source hash; runtime/reload difference reproduced; exact screens and attribution retained | No evidence mismatch remains | Unknown complete dossier and model behavior | Use one coherent capacity method and explicit stage budgets | Capacity repaired |
| Reject tested prototypes for this cap | Each partial input exceeds 200,000 bytes | Input-size screen fails | Untested better representations and service envelope | Qualify readable larger input; implement bounded review only where needed | Compression impossible or service inherently too small |
| Accept resolution design | Dependencies cover sources, outputs, review, authority and individual tools | Not a live/implementation admission | Actual inventory, applicable legal standards, empirical quality | Prepare reviewed execution and finite qualification packet | Product completion or new repair/live authority |
| Keep legal/tool results open | No new source-supported answer or matched tool effect | Missing substantive evidence | Authority, factual premises and observed product handling | Continue independent warrants and later valid comparisons | Solved English interpretation or tools helping the full target |

There is no stochastic comparison here. Byte differences and exact reconstruction
are deterministic engineering facts. No tool/model ranking or default-readiness
claim follows. The strongest alternative explanation is that a sufficiently
qualified larger ordinary context could solve much of the operational problem
without elaborate new partitioning. That option is included explicitly. The
weakest evidence is still the absent complete inventory and provider behavior
on the full original workload; valid source-reviewed complete answers would be
needed to overturn the remaining product and legal limitations.

Measurements, scripts, snapshots, manifests and command outcomes are retained in
`artifacts/legal-mission-control/2026-10-12/capacity-diagnosis/`. The mission
history records `product_evaluation/no_advance`; no engineering attempt or live
allowance is reset.
