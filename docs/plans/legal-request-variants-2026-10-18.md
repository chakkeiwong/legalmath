# P14 and Gatecoin request-format diagnostic

This is a bounded diagnostic under the current integration master and admitted
`product-contribution` task, authorized by the user's request to test both
failures in different ways. It does not reopen exhausted acquisition owners,
replace the master, change acceptance criteria, or alter the active P10 worker.

The question is whether the two actual failures recur on an unchanged replay
and on equivalent representations. The baseline is P14 slot 2341 and Gatecoin
slot 2285, authenticated against their receipts and original global charges.
The registered model and route remain `gpt-6.1-sol`. No source, instruction,
question, citation bound, required field or legal qualification is removed.

| Item | Success dependencies | Result and continuation |
| --- | --- | --- |
| Authenticate and prepare | Original receipts, global grant, current binding and shared service scope | Freeze all six arms, authorization, baseline ledger and source hashes; reject any mismatch before calls. |
| P14 original, inline schema, pretty JSON | Preparation; original precedes variants | Record each outcome independently. An invalid request does not block the other forms or Gatecoin. |
| Gatecoin original, inline schema, pretty JSON | Preparation; original precedes variants | If any arm receives an explicit safety block/refusal, stop this branch's later variants. Do not attempt to defeat the refusal. |
| Review and refresh | Completion of attempted or blocked arms, not successful answers | Preserve results, update mission history under its existing lock, refresh the mission and report remaining uncertainty. |

The branches are substantively independent but serialize on the existing
`service-worker.lock`, global ledger lock and service circuit. The P10 process
remains running. A diagnostic must wait until every live master owner has
settled; lock availability between two P10 calls is not enough, because the
existing owner acquires this lock nonblocking and could otherwise fail when the
diagnostic temporarily owns it. The runner checks recorded worker identities
and the master task register before it tries the service lock. If the circuit
remains open after P10 settles, it stops without dispatch; it cannot take over
the master-owned delayed probe. Each diagnostic call has its own immutable stage identity in
the same global ledger; it is never charged to P10's stage or dispatched by
overwriting `current-stage.json`. The user's new instruction permits at most six
diagnostic calls, three per question, within the existing 8,100-call ceiling and
18 October UTC grant deadline. There are no replacement calls, new owner
attempts, repairs, extra global calls or renewed deadlines. A crash consumes its
reservation; the runner refuses automatic restart or redispatch.

The three arms are:

1. Exact saved request and schema bytes, with current identical provider command
   construction and route. The original unretained HTTP envelope cannot be replayed.
2. Exact request bytes with local `$ref` definitions expanded in the schema.
   Expansion accepts only acyclic local definitions with no reference siblings;
   it preserves every validation constraint. Validate responses against both
   this schema and the original schema.
3. Original schema bytes and the same JSON request with indentation. Parse and
   compare the complete request before dispatch. Only whitespace changes.

The primary observation is terminal completion with output satisfying the
original schema, or an authenticated terminal error/refusal. A completed turn,
exit zero, or a present file alone does not pass this screen. Tool use, an
unended subprocess, altered inputs, invalid authority, an expired grant or
exhausted allowance veto execution. Original-schema failure vetoes acceptance
of that response, without blocking independent forms. An open/half-open shared
service circuit defers all calls; a terminal transport failure opens that same
circuit and stops this diagnostic without borrowing its scheduled retry.
The wait for active master owners is bounded only by the original campaign
deadline. Call execution is bounded to 300 seconds and the six-call batch to
3,600 seconds, with no application or CLI retries. Once owners settle, the
service lock must be immediately available; a lock held by an unknown worker is
a stop condition. Lock contention is a scheduling result, not a provider
failure.

The research intent is persistence and representation sensitivity, not legal
correctness or model ranking. Counts, sizes, usage, runtime and warnings are
explanatory only. A success after a failure shows that the failure is not
universal over these observed calls. With one call per form, time variation
confounds format variation; no format can be declared a causal fix or superior.
A repeated generic invalid request still does not name the offending parameter.
A repeated safety block is a limitation requiring legitimate provider review,
not an invitation to split, reword or reroute around the block. Successful
diagnostic responses remain outside production checkpoints pending normal
citation, decoding, source and legal review.

Material assumptions and defaults: original fixture identity comes from retained
manifests and charged request hashes (early check: authenticate every file).
Schema equivalence follows from exact reference substitution, checked with
original and expanded validators including adverse boundary cases. The route
comes from the current approved route hash, checked before reservation; no
provider/model change is allowed. The 300-second timeout is the existing live
policy, not a model-capacity claim. The three-arm design is a convenience
diagnostic within the user's request, not a statistically powered comparison.
CLI-generated HTTP framing remains unobserved and cannot support a claim about
the exact gateway parameter or underlying OpenAI policy implementation.

Initial skeptical audit: **REVISE**. It checked call ceilings and branch stops
but missed the active P10 owner holding a nonblocking shared lock. The first
runner invocation waited for that lock and was stopped before reserving a call;
the global ledger contains no diagnostic charge. This was a scheduling
conflict, not a provider response. The revised gate waits for all recorded
master owners to settle and refuses an open circuit or unknown lock holder.
No active P10 file, task state or checkpoint is changed by this diagnostic.

Revised skeptical audit: **PASS with the owner gate**. Earlier ten P14 owner
attempts are not ten reproductions of this exact failure. Different neighboring
payloads are not matched controls. This plan uses the actual rejected inputs,
preserves source coverage and validation, separates the two failure classes,
does not infer legal progress from transport, and has explicit branch, owner,
and shared-service stop conditions. The strongest alternative explanation for
any changed outcome is intermittent service behavior. A full acquisition
continuation is not authorized by these diagnostic results alone. P10 and all
historical evidence remain protected from edits.

Run from the repository root:

```text
.venv/bin/python artifacts/legal-mission-control/2026-10-18/request-variants/probe.py prepare
.venv/bin/python artifacts/legal-mission-control/2026-10-18/request-variants/probe.py run
```

The runner retains its authorization, exact inputs, command manifests, original
and new receipt hashes, events, stderr, validation outcomes, reservation slots,
timings and result under that artifact directory. The final result note is
`docs/implementation/legal-mission-control/results/request-variants-2026-10-18.md`.
Environment is `.venv/bin/python`; no GPU initialization is needed and GPU
devices are intentionally hidden. Model sampling seeds are unavailable, and no
statistical ranking or default-policy change is permitted.
