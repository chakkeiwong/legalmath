# One bounded successor to the batch 36 timeout

9 October 2026, Hong Kong. Batch 36 source-first exhausted its reviewed
300-second call cap. The provider wrapper terminated and waited for its local
process group before retaining transport files. Its role journal records
`E_RESOURCE_LIMIT: Codex call deadline`; the receipt records 300.78 seconds.
The manifest records no complete output, and events contain only thread and
turn starts. The runner exited and a process inspection found no survivor.
There are 432/492 complete pairs, 39/200 new calls and 4/100 repair entries used.

This is a known locally terminated timeout. It is not an interrupted journal
with unknown dispatch state or a returned legal response. The remote provider's
internal work is not observable; the failed call remains charged. No local
output exists to recover or adjudicate.

## Evidence contract

Question: can this unchanged twelve-pair assessment finish under a single,
explicitly bounded 450-second recovery attempt? The comparator is the same
request and schema under the 300-second cap. The pass criterion is validation
under the original source, candidate, typed-question and fidelity rules. It
does not measure comparative legal accuracy, explain the latency or establish
that 450 seconds is a suitable general default.

Vetoes: unknown local dispatch state, changed request/schema/route, changed
historical evidence, missing timeout journal/transport, any complete or partial
returned model output, or exhausted grant/deadline. Runtime and request size
are explanatory diagnostics. Another failure consumes this single reviewed
successor and triggers an exact review; it is not automatically retried. The
timeout invalidates this attempt's completion, not the legal target or research
direction. Continue the planned remaining batches after a valid replacement.

## Assumptions, remedy and skeptical audit

The recent target calls took up to 273 seconds, 219 seconds and 258 seconds;
one 300-second timeout is insufficient evidence about its cause. A 450-second
cap is a bounded operational hypothesis giving this one unchanged task another
150 seconds. It changes no source, prompt, representation, model or route. The
normal per-call cap stays 300 seconds. The original absolute expiry still takes
precedence. Ten calls remain at minimum, projecting 49 calls for the new grant;
450 + 9 × 300 seconds is 52.5 minutes before overhead, within the roughly ten
hours remaining. No new allowance or time window is inferred.

Reuse the already verified tool context so request and schema hashes remain
identical. Save the replacement under `roles/36/source-first/attempt-01/` with
its own journal, counted reservation and repair entry. Preserve the old receipt,
failure and transport. Qualification-first for batch 36 has never been issued
and will run normally after recovery. Do not claim a reused peer here.

The skeptical audit passes conditional on tests of the distinct timeout
eligibility, unchanged normal cap, original-deadline precedence and request
binding. The 502-specific review must continue to reject a timeout. The new
review must reject auth/schema/output-size errors and incomplete journals,
even if their text includes the word timeout. A complete output or completed
turn vetoes this empty-output remedy and requires examination instead.

Record the implementation as repair entry 5 and the live successor as entry 6.
Seal review v3 and a fresh source snapshot and tests; preserve reviews v1/v2.
Use the existing closed wrapper actions `resume-test`, `resume-repair`,
`resume-verify`, and `resume-execute`, sequentially. Live calls use the already
approved trusted prefix; no new policy change is needed.

Artifacts: the original and successor receipts, `service-recovery-02.json`,
review v3, its test receipt, provider transport, refreshed plan history and the
final execution report. Independent legal adjudication and the 46 substantive
obligations remain outside the engineering pass criterion.
