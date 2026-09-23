# Running and reviewing source-driven interpretation search

This increment adds a generator and an investigation tree to the existing
interpretation service. A retained source packet is the input. Fresh Codex
contexts propose readings; the program validates their citations, constructs
executable rules where possible, investigates alternatives, and produces a
blocked review package. It does not select a legally correct reading by vote.

## The execution sequence

1. Import the source bytes into the existing source store and create a packet
   whose units resolve to those bytes. Include footnotes and referenced material
   that is actually available. Mark missing authorities as missing dependencies.
   The packet declares `scope`, `definitions`, `exceptions`, `modality`, `time`
   and `dependencies` as its six interpretation dimensions.
2. Freeze the packet and settings when creating the investigation. For an
   evaluation intended to use independent annotations, assign distinct reviewers
   before any generation request. Their packet contains the source and no model
   proposals. Assignment and submitted annotations are immutable.
3. Generate initial readings in three fresh contexts. The normative role parses
   actors, triggers, obligations and exceptions; the controlled-language role
   rewrites the control as explicit conditions and checks for lost qualifiers;
   the alternatives role looks for the strongest supported rival reading. Each
   accounts for every supplied unit and all six dimensions. No initial role sees
   another role's response.
4. Validate the complete response. Quotes must occur exactly once in the cited
   unit, every reference must resolve, and unknown fields or authority claims
   are rejected. Persist the raw response before validation. A malformed response
   may receive a separately charged correction request carrying the exact error
   and allowed source identifiers. The original failure remains in the history.
5. Keep each distinct commitment, including its assumptions and fact meanings.
   Compile supported expressions into RuleIR and Java; retain unsupported
   readings with their encoding errors. Run boundary probes against Python and
   generated Java. Compare candidates with identical fact definitions; exact
   aliases with identical metadata can be renamed explicitly. Changed meanings
   remain incomparable until a separate conditional correspondence is proposed.
6. Investigate a tree branch using breadth-first selection or the optional UCT
   scheduler. Retrieve uncited units from the retained packet, supply executable
   counterexamples and prior reconstruction diagnostics, and request supported
   refinements. Preserve parents, children, visits, rewards and unexpanded
   branches. Replayed behavioral differences guide investigation priority.
7. Render a compiled rule into controlled English and ask a fresh context to
   reconstruct it without the original formula or interpretation. Compare the
   result; keep drift and unresolved differences visible. This check concerns
   the formal rule and its rendering. It does not prove fidelity to the circular.
8. Finish on a call, time, depth, candidate, root-action or round limit; no
   progress; cancellation; an unavailable provider; or exhausted search. The
   report retains unsuccessful actions, unsupported readings, incompatible fact
   definitions, missing authorities, distinguishing questions and the frontier.
   Every generated candidate remains bound to the existing release guard.

## Inputs and command line

`Settings` in `src/legalmath/interpretation/search/models.py` is the strict input
contract. A small complete case uses three initial calls, one refinement, one
possible output-repair call and one reconstruction: up to six invocations.
These are resource bounds, not a claim that six calls find every interpretation.
The P8 pilot uses three investigation rounds and a twelve-call ceiling per
source; it requires at least two actual rounds. Multiple rounds can still all
expand initial roots. Inspect recorded parent links and depth before describing
a run as multi-level descent.
The shared allowance is consumed before dispatch. Failures and interrupted
dispatches do not refund it. A repeated run cannot resume an unknown dispatch.

The executable entry point is:

```text
.venv/bin/legalmath interpretation-search \
  --data-dir WORK_DIRECTORY \
  --identities LOCAL_IDENTITY_REGISTRY.json --caller AUTHOR_ID \
  --packet FROZEN_PACKET.json --settings SEARCH_SETTINGS.json \
  --jdk .localresources/java-toolchain/jdk-17.0.20.1+1 \
  --at 2026-09-23T00:00:00.000000Z \
  --allowance AUTHORIZED_SHARED_ALLOWANCE.json --total-calls AUTHORIZED_CEILING \
  --key UNIQUE_INVESTIGATION_KEY --output INVESTIGATION.json
```

The capitalized arguments identify files or values the operator must provide.
Public packets created by the executed pilot are under
`artifacts/interpretation/round2/P8/attempt-01/pilot/24EC50/packet.json`.
Retained-source packets need their source bytes imported into the chosen store;
copying a packet JSON into an empty store is insufficient. The pilot's
`source_packet` function shows the existing source importer and span builder in
use. Do not substitute synthetic authority for a missing retained source.

`--domain` optionally supplies the bounded SMT comparison domain. With identical
all-Boolean fact definitions and no caller domain, the comparator records and
checks the complete declared `{T,F,U}` state space. This avoids missing
interacting exceptions and scope conditions through truncated probes. It covers
valid non-conflicting Boolean inputs to the encoded rules; empirical feasibility
of every assignment remains a separate question. Numeric bounds are never
invented. Without a supplied domain, numerical/date boundary probes can exhibit
a replayable difference or report no difference among the finite probes. They
cannot establish equivalence. If a **caller-declared** domain is unsupported or
the solver cannot finish, the result preserves `UNSUPPORTED` or `UNKNOWN`, with
zero unconstrained fallback probes. Testing a value outside that domain would
answer a different question. An inconsistent domain stays inconsistent.
Dates are supported by the executable rule fragment but have limited solver
support; the report records the method actually used.

The Codex adapter preserves the configured provider route and model while
excluding inherited conversation, project instructions, hooks and tools. It
uses structured output in a fresh temporary directory. The output records
request and response hashes, provider route hash, CLI version, reported usage
and events. A persistent allowance is mandatory before dispatch. The three
contexts can share one model's errors; the software does not call them
statistically independent experts.

## Service integration and reference annotations

`create_app(..., jdk=..., search_provider=...)` accepts an operator-configured
provider. The ordinary server starts with no live provider. Request bodies
cannot install model adapters or shell commands. The available operations are:

| Operation | Route |
|---|---|
| Create an investigation | `POST /v1/interpretation-search` |
| Start its bounded worker | `POST /v1/interpretation-search/{run_id}/execute` |
| Read persisted evidence | `GET /v1/interpretations/{run_id}` |
| Cancel | `POST /v1/interpretations/{run_id}/cancel` |
| Assign source-first reviewers | `POST /v1/interpretation-search/{run_id}/annotation-assignment` |
| Read an assigned source packet | `GET /v1/interpretation-search/{run_id}/annotation-packet` |
| Submit independent annotations | `POST /v1/interpretation-search/{run_id}/annotations` |
| Freeze adjudication | `POST /v1/interpretation-search/{run_id}/reference-freeze` |

Authenticated write requests use the existing `Idempotency-Key` mechanism.
Changing settings under an existing creation key is rejected. The service
retains the same identity, immutable history, source invalidation and archive
rules as the earlier workbench. The local identity registry and an independence
attestation cannot establish that its entries are actual independent people.

Annotation freezing requires all assigned reviewers, a different adjudicator,
the original source version, and a disposition for every unit. A disposition
contains one or more accepted readings or explicit uncertainty.
`evaluation.compare_frozen` loads these records for paired evaluation.
Unresolved dispositions remain unadjudicated, even when they name provisional
readings. The lower-level `compare_runs` function is accounting machinery for
already supplied labels; it does not authenticate those labels.

## Reading the evidence and using Java

### Comparing different fact vocabularies

A fact is its declared meaning, type, unit, source references and judgment flag,
as well as its name. The automatic correspondence path ignores only names and
declaration order. It anchors identical same-name declarations, then requires a
unique metadata match for each remaining fact. Ambiguous permutations and
unmatched declarations remain `INCOMPARABLE_FACT_BINDINGS`. An exact alias
changes AST fact leaves simultaneously, so swapped names cannot overwrite each
other. A differing witness is translated back into each original vocabulary and
executed in both original Java classes. Their bundle hashes and separate input
snapshots remain in the result.

When definitions differ, use the separate post-search workflow below. It
requires a completed, current-source investigation. It leaves the original
search report, issue list and tree unchanged.

| Operation | Route under `/v1/interpretation-search/{run_id}` | Who may call |
|---|---|---|
| Read full definitions, source and review questions | `GET /fact-correspondence?left_node_id=LEFT&right_node_id=RIGHT` | Owner or distinct meaning reviewer |
| Store a correspondence hypothesis | `POST /alignments` | Owner |
| Inspect proposal, analyses and decisions | `GET /alignments/{alignment_id}` | Owner or distinct meaning reviewer |
| Compare under the recorded assumptions | `POST /alignments/{alignment_id}/analyze` | Owner; server JDK required |
| Append a review decision | `POST /alignments/{alignment_id}/review` | Distinct meaning reviewer |

The proposal request contains `left_node_id`, `right_node_id`, and `proposal`.
The proposal itself must contain all of these fields:

| Field | Meaning |
|---|---|
| `source_packet_hash`, `left_commitment`, `right_commitment` | Exact hashes returned in the correspondence packet; changing source or readings invalidates the proposal |
| `links` | Complete one-to-one list of `{left, right, assumption}`; no dropped inputs, many-to-one matches or hidden conversions |
| `rationale` | Why this correspondence deserves examination |
| `output_meaning_assumption` | What matching result values would mean in both readings, including compliance versus prohibited-action polarity |
| `citations` | `{unit_id, quote}` entries copied exactly from retained source; a valid quote is evidence to inspect, not approval of the mapping |

Every changed declaration needs a nonblank per-link assumption. For identical
metadata, the required `assumption` field may be null. Types must match;
numeric/date units must match literally. This version cannot convert units,
decompose one fact into several, negate an output convention, or synthesize a
missing exception. Such differences require a revised interpretation and a
separate investigation.

`POST /analyze` accepts `{"at":"2026-09-23T00:00:00.000000Z","domain":null}`,
or a declared domain in the **left** fact vocabulary. It takes no executable,
JDK path or model configuration. It checks the original Java candidates, then
returns `CONDITIONAL_ANALYSIS` with the actual comparison under
`encoded_comparison`. An inner `EQUIVALENT_WITHIN_DOMAIN` is still conditional
on every mapping and output assumption. The result cannot merge unconditional
behavioral groups, resolve a legal issue or authorize release.

A review request contains the saved `proposal_hash`, `decision`, `rationale`
and nonempty `evidence_refs` of source unit IDs. Decisions are
`ACCEPT_FOR_CONDITIONAL_ANALYSIS`, `REJECT` and `UNRESOLVED`. Reviews append to
history. A latest rejection blocks new analyses, including a rejection arriving
while compilation runs; earlier analyses remain readable. Acceptance permits
examination under the assumptions and does not certify their legal truth.
Local roles attest who submitted a decision; human qualifications and
organizational authority are established outside this local registry.

The frozen circular review packets and a concrete hypothetical proposal are
under `artifacts/interpretation/round2/P12/attempt-01/replay/`. Each circular has
`review-packets/index.md`, full machine-readable packets and matching readable
versions. The 24EC50 `hypothetical-correspondence.json` supplies a complete
proposal, and `conditional-analysis.json` preserves its actual result. These
packets expose generated candidates, so they must not be passed off as blind
reference annotation. The source-first annotation workflow above remains the
route for an independent legal reference.

### Inspecting compiled candidates

`search-state` retains the candidate tree, every failed action, pairwise
comparison, reconstruction and Java verification. `search-report` records the
terminal reason and unresolved material. Its verifier recomputes every report
field, including call counts, release eligibility and the absence of a legal
correctness probability. Historical reports remain tied to their generating
implementation; do not overwrite them using a later format.

Each successfully compiled reading has a `bundle_hash`. `search-java` (or the
pilot's `java` directory) contains its generated source, JAR and build manifest.
Per-candidate Python/Java probes check the implementation of that RuleIR.
Pairwise counterexamples are replayed in both generated classes. This separates
three questions: what the circular means, whether the chosen RuleIR expresses
that meaning, and whether Java executes that RuleIR correctly.

These JARs are draft review material. They enter bank software only through the
existing exact-artifact meaning review, engineering verification, applicability
and release process. Search scores, citation checks, reconstruction agreement,
argument extensions and model consensus supply no release authorization.

The current report always has `release_eligible=false` and
`probability_of_legal_correctness=null`. A high UCT reward means that a branch
has exposed executable differences worth investigating. It is not a confidence
estimate. An abstract argument extension states a property of the supplied
attack graph; the current graph uses behavioral incompatibility and does not
encode a court's priorities, precedent or burdens of proof.

## Repairing and continuing the master program

Use the absolute fixed command in `allow.rules`:

```text
/home/chakwong/python/legalmath/.venv/bin/python /home/chakwong/python/legalmath/scripts/run_interpretation_search_plan.py status
```

The sequence for a failed phase is `repair Pn --note PROJECT_LOCAL_JSON`,
`review Pn --note PROJECT_LOCAL_JSON`, and `run Pn`. The repair note records the
actual fix and discriminating regression. `repair` refreshes the phase plan;
successful phases refresh the next one. Changed source hashes invalidate a
review. A completed attempt is retained and cannot be overwritten. `recover`
records an interrupted attempt as a failure before any retry.

P6 can run after P0–P4 while live P5 is blocked. P6 never promotes P5. P7 and P8
retain the live-discovered comparison repair, full regression, frozen-output
replay and multi-round live reacceptance without overwriting the earlier phases. Live
allowance changes require the authorized plan ceiling and ledger ceiling to
match, with all prior reservations preserved. The next-phase plan records the
exact outstanding live and human-evidence requirements.

P9 retains the earlier traversal regression. It runs the focused
`test_bounded_search_descends_to_a_grandchild_and_keeps_frontier` test for both
BFS and UCT, then the full suite. The deterministic fixture verifies depth-two
lineage, bounded calls, Java checks and frontier retention. It uses no live
provider calls and cannot establish search completeness or legal accuracy.
The accepted manifests are under `artifacts/interpretation/round2/P9/attempt-01/`.

P10–P12 add fact correspondence. P10 checks exact aliases, total bijections,
semantic-change rejection and original Java replay. P11 checks stored proposals,
reviews, source changes, archives and authority separation. P12 runs the complete
suite and every frozen P8 comparison, exporting unresolved review packets. The
pre-run contract and audit are `docs/plans/interpretation-fact-alignment.md`.
No live provider is involved in these phases.
