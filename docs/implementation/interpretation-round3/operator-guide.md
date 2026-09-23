# Automated interpretation assurance

This increment adds an executable source-facing assurance workflow around the
existing BFS/UCT interpretation search and Java verifier. Use it on retained
public sources or explicitly authorized inputs. External legal consultancy is
not a dependency. The workflow produces candidate code, diagnostic evidence and
specific unresolved questions; production release remains a separate operation.

## Run a circular

From the repository root, with the existing Python environment and JDK:

```sh
.venv/bin/legalmath interpretation-assurance \
  --manifest examples/interpretation-assurance/23ec46.json \
  --out artifacts/interpretation/manual-assurance-01 \
  --jdk .localresources/java-toolchain/jdk-17.0.20.1+1 \
  --at 2026-09-23T00:00:00.000000Z \
  --allowance artifacts/interpretation/round2/live-allowance.json \
  --total-calls 100
```

Use a fresh output directory for a new investigation. Repeating the exact same
request on a completed directory verifies and returns its retained report without
more model calls. Changing inputs under the same directory is rejected. An
interrupted run remains retained; make a successor instead of redispatching an
action whose remote result is unknown. The shared allowance counts calls before
dispatch, including failures. Do not reset or increase it without authorization.

The manifest names `roots`, optional `retained` documents and an optional
`authority_catalog`, plus an explicit `selected_slice`. A document contains
`url`, `path` and `media_type`; `path` is relative to the manifest. Optional
`sha256` binds a local snapshot. Without a path the CLI acquires the official URL.
Acquisition accepts only the existing SFC/HKMA HTTPS hosts and validates public
addresses. Gateway circular links are translated to the official document API.
An authority catalog entry can also contain exact `aliases` for incorporated
definitions or source titles. Ambiguous aliases remain unresolved.

Text-only references are found by the semantic inventories. Only an exact
catalog match can automatically acquire a document lacking an explicit link.
The workflow never treats a guessed URL or a similarly named source as resolved.
This is a deliberate, visible limitation of the current acquisition profile.

## What the command actually executes

1. Capture raw documents, follow bounded explicit references and retain failures.
   Compare primary extraction with a second algorithm; check that every retained
   non-whitespace character occurs in the packet. PDF second extraction requires
   Poppler `pdftotext`; its absence is a finding.
2. Obtain two source-only atomic-claim inventories in isolated contexts. They
   identify actor, action, modality, conditions, exceptions, time and authorities,
   accounting for every supplied unit. No candidate or peer answer is supplied.
3. Run the existing independent initial readers and bounded interpretation tree.
   Refinement receives independent source claims and source-inventory findings.
   Boolean output meanings are explicitly proposed as `TRUE_IS_PROHIBITED` or
   `TRUE_IS_COMPLIANT`. Source-dependent judgment remains visible in fact bindings.
   Up to eight distinct proposals in the deferred search queue also receive
   assurance checks. Their queue/registration status is preserved. This avoids
   losing an encodable alternative to a legacy family reservation; any remaining
   queue limit stays explicit.
4. Compare the original English and its qualifications with executable meaning.
   Only used fact definitions enter that meaning; an unused exception declaration
   cannot look like implemented code. Each claim/candidate pair is labelled
   `ENTAILED`, `CONTRADICTED` or `NOT_ESTABLISHED`, with evidence and a failed stage.
   Large matrices are checked in bounded batches (32 pairs by default), with
   exact coverage required across all batches. A failed required inventory stops
   dependent generation; missing checks cannot produce a clean report.
   Unencodable or unformalized candidates remain in the denominator with
   deterministic `NOT_ESTABLISHED` results and encoder diagnostics. They cannot
   acquire an entailment result by quoting a renderer error message. Encodable
   siblings still receive source-facing checks and original Java execution.
   Requests carry an explicit response schema. A malformed response is retained;
   its bounded repair receives located field errors and the required schema.
   At most 64 field diagnostics are transmitted, with their total and truncation
   status. The application does not silently rename fields to accept a judgment.
5. Repair an implicated source inventory or candidate formalization within the
   configured limits, then rerun downstream checks. Exact repeated commitments
   are not progress. Original readings and failed checks remain in the history.
6. Evaluate structured arguments, named premise/inference/conclusion attacks,
   explicit assumptions and exceptions. Optional conditional derived comparisons
   normalize opposite output conventions and replay original generated Java.
   Case constructors use separately sourced target factors and case records.
7. Run bounded source-edit and formula challenges, reuse only exact-bound prior
   diagnostics, and produce deduplicated residual questions with attempted actions.

Model source-support labels are judgments, not formal proofs of English. The
argument engine is a documented bounded adaptation; it does not claim all ASPIC+
rationality theorems or complete Carneades semantics. Case-factor extraction and
the authority of a model-proposed case record remain unverified. No candidate is
deleted or approved because an argument graph accepts it.

## Settings and stopping

Pass `--settings PATH` for a JSON `AssuranceSettings` object. Omitted fields use
the reviewed prototype defaults: 18 total model calls, 3,000-second deadline,
one output-contract repair, two semantic repair rounds, at most two repairs per
issue, 20 documents and three reference levels. The embedded `search` object uses
the existing `Settings` contract (six calls and one refinement round by default).
The final acceptance pilot uses its separately recorded smaller settings.

`action_cost_budget` uses relative scheduling units, not currency. Calls and wall
time have separate hard bounds. `max_derived_comparisons` caps optional common-fact
mapping proposals; only the documented Boolean profile gets an automatic domain.
Dates and numbers require a declared finite domain. A domain cap never becomes
an equivalence result. `reuse_machine_diagnostics` reuses a prior model judgment
only for matching source, claim set, candidate, code, provider route and settings.
It does not create another independent vote.

Possible report states are `NO_ISSUE_DETECTED_IN_PROFILE`, `UNRESOLVED` and
`FAILED_INTEGRITY`. The first describes the checks that ran within this profile;
it does not establish legal correctness. `execution_complete` distinguishes a
completed diagnostic from missing checks. Every report has `release_eligible:
false`. A source-supported replacement may supersede its parent for the current
automatic proposal while preserving both in the candidate archive.

## Continuing checks

```sh
.venv/bin/legalmath assurance-monitor \
  --config examples/interpretation-assurance/monitor.json \
  --out artifacts/interpretation/monitor-01 \
  --jdk .localresources/java-toolchain/jdk-17.0.20.1+1 \
  --at 2026-09-23T00:00:00.000000Z \
  --allowance artifacts/interpretation/round2/live-allowance.json \
  --total-calls 100
```

This executes one bounded tick and can be called by an institution's scheduler.
The example deliberately uses retained local documents. Remove their `path`
fields only when actual public refresh is wanted. The control registry specifies
each source and incorporated dependencies; discovered new control families need
an explicit scope configuration. The command does not install a background job.

Source or dependency versions, control configuration, actual implementation,
provider/settings and fact-schema changes create successor investigations.
The explicit `--at` evaluation date is also part of the revision: moving across
a commencement or expiry date rechecks the control even if source bytes agree.
Keep that date current in a scheduler; `--now` is the scheduler's clock and does
not replace the rule evaluation date.
Unchanged controls reuse their retained result. Unavailable dependencies block
dependent controls, and explicit failed investigations use bounded retries.
Old results are never overwritten. The example daily cadence and two-attempt
limit are tested settings, not a validated bank service-level commitment.

Retries are charged before dispatch. An invocation's timeout is reduced to its
remaining run deadline. A cached or recovered response never becomes an
additional independent model vote. The repaired acceptance pilot explicitly
reuses one already-counted, exact request/schema response from its interrupted
predecessor; that recovery is confined to the pilot's retained evidence.

For subsequent integration repairs, the fixed pilot also verifies the completed
predecessor's manifest and replays only identical request/schema pairs. Original
slot numbers and failures remain explicit. Only the reviewed fidelity/criticism
checks on the expanded candidate sets can issue new calls; an unexpected replay miss stops. In these
repair reports `model_calls` counts journaled actions, including retained ones.
Use `new_live_invocations`, per-response provenance and the persistent allowance
for actual newly dispatched calls. Replay adds no independent evidence.

The final continuation also uses an explicit source/task replay plan. For 23EC46,
source and fidelity responses come from attempt 07 and the exact criticism
response from attempt 06; all manifests verify and the route forbids live calls.
The disconnected attempt-07 invocation remains recorded and counted. An overridden
task is not replayed from its base directory; all base file hashes still verify.
Independent circular and challenge checks continue after an ordinary source
execution failure, but overall pilot acceptance requires all of them to pass.

## Evidence to inspect

* `report.json`: findings, source versions, journaled-action count, repairs, candidate
  dispositions, structured arguments and residual questions.
* `source-context.json`, `sources/`, `packet.json`: acquisition, dual extraction,
  original bytes, missing dependencies and exact evidence spans.
* `inventories-initial.json`, `inventories.json`, `claims.json`: original and
  current source-only interpretations.
* `calls/`: every request, requested schema, response/provenance or failure.
* `stage-history.json`: retained checks and downstream invalidations.
* `search-state.json`, `candidates.json`, `java/`: tree lineage, readings and
  compiled code/check evidence. Java artifacts are research candidates.
* `criticism.json`, `derived-comparisons.json`, `challenges.json`: structured
  criticism, explicitly conditional mappings and labelled engineering probes.
* `manifest.json`: hashes checked on reopening the completed investigation.

The sibling `assurance-answers` directory contains version-bound diagnostic
answers. A cached answer is explicitly labelled `MACHINE_DIAGNOSTIC`; the cache
does not confer human or institutional approval.

The master supervisor and repair records are under
`artifacts/interpretation/round3`. Start with its `state.json`, the phase
`next-plan.json`, review note and each attempt's `run-manifest.json`. Failed
attempts are part of the evidence, not disposable scratch files.
