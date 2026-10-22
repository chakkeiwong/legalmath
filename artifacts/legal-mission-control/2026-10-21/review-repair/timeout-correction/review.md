# R4 correction: ended timeout with an empty message

This is a correction within the reviewed R0–R6 repair, governed by
`docs/plans/legal-integration-master-2026-10-13.md`. It preserves the original
four questions, 46 obligations, 35 readings and six applicable tool evaluations.
The exact comparator is P14 attempt 3, charged slot 3591: a local 300-second
timeout, terminated child, no output file or completed turn, and one final-message
event containing a single space. The existing predicate treats every message
event as partial output and raises a global live-consumer veto. The failure
result and every charged call remain evidence.

| Work | Success prerequisites | Independent work / completion evidence |
| --- | --- | --- |
| Diagnose and stage | Exact saved receipt and original sources | Independent of the running supervisor; authenticate all bytes, classify blank versus substantive output, inspect orphan recovery |
| Regressions | Staged implementation | Offline exact-receipt and adversarial tests; zero provider calls |
| Settle and freeze | Verified process identity, no children or reserved dispatch | May proceed while local tests run; acquire all shared locks and preserve both task reservations and failures |
| Adopt | Passing regressions and settled freeze | Transactional program, binding and mission update; unchanged global and service budgets |
| Continue | Valid adopted bindings and original grant | Recover exact ended request with counted five-minute retry; drain original ready work and retained Gatecoin reservation |

The substantive question remains whether the saved answers satisfy the original
source and legal requirements. These tests answer only whether an ended request
with no answer can enter the authorized recovery path. Test counts, transport
success and local fit cannot promote an answer or establish tool usefulness.

Use one shared, conservative output predicate in the current reviewed recovery
profile. Empty or whitespace-only string messages with the recognized event
shape may count as no answer. Nonempty text, missing/nonstring text, unexpected
content fields, refusals, completed turns, output files, authentication or billing
errors, malformed events and unknown dispatch remain ineligible. Reasoning events
are not structured answers. Preserve historical recovery-profile behavior.
The provider's exact process-termination receipt, request/schema hashes,
cumulative replacement counts, five-minute minimum and global deadline still
govern every replacement.

The review also checks the transition from an ended supervisor with a retained
Gatecoin reservation to service recovery. An orphan reservation is not a live
provider process. Recovery may proceed only after exclusive locks and absence
of uncertain dispatch establish that distinction. The answer loop must yield
to bounded recovery after shared deferral; it must not spin on a retained owner
or demand a closed circuit before invoking the mechanism that closes it.

Preserve all completed and malformed review results for both questions. Seed a
new binding's runtime from authenticated settled dispatches, excluding only the
single exact no-output veto dispatch after proving its receipt. Preserve that
excluded result and its identity separately. Do not overwrite it or convert it
into ACCEPT. Recovery probes remain transport evidence; product re-execution
must validate any later answer normally and every new request is charged.

P14 attempt 3 has already been finalized by the old controller. It must remain
immutable. A single explicitly registered continuation of that owner is permitted
within this same consolidated repair; maximum owner attempts becomes four, with
the earlier three retained. This is not a new substantive answer correction,
detour, global call allowance or service reserve. Gatecoin retains attempt 4.
Resolve only the precisely evidenced whitespace veto, retaining the veto and its
resolution in history. Unrelated vetoes and blockers remain effective.

Skeptical audit: PASS for this scoped local correction. The actual comparator
and receipt are available; the test artifact can distinguish the code defect
from a provider outage. The main assumptions are that a whitespace string has
no usable answer and that an authenticated killed child cannot still dispatch.
Adversarial content and process-identity tests challenge those assumptions.
Mutable bindings may not change under an active worker. Historical sources,
phase results, charge prefixes, task attempts and completed owners must survive
adoption. A new unknown receipt, active/uncertain dispatch, changed grant, spent
allowance or expired deadline vetoes live continuation. Branch failures otherwise
trigger refresh and independent work. This correction does not establish that
Sol will complete the next request or that the full matrix fits the remaining
4,509 calls.

Use the existing master command entry points and current environments. Stage
under this directory, test with CPU-only `.venv-context/bin/python`, retain exact
commands, hashes, wall times, receipt reproduction and test results here, then
refresh the mission and master and resume their fixed `live` action. No new
subagent, model, external permission or allowlist prefix is part of this plan.
