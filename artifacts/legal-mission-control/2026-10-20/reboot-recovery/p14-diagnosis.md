# P14 checkpoint at machine recovery

The transport interruption recovered under the existing schedule. Global slot
3404 dispatched at 2026-10-19T19:37:05.984323Z with the same request hash as failed
slot 3403 and became `VALIDATED` at `reduce-p14-2-2`. Slot 3405 completed the last
synthesis, `reduce-p14-3-0`. All 109 P14 dispatch entries now validate. Do not
retry either success or apply the elapsed early-retry schedule to them.

The remaining failure is local. The retained
`live/p14/product/phases/call-candidates-p14/phase.json` under the synthesis
resolution directory records 76,966 bytes and 18,841 local tokens, zero logical
dispatches, and `E_RESOURCE_LIMIT`. Thus there was no service rejection of this
candidate request. Its existing default allows 12,000 local input tokens.

The code trace explains the gap:

1. `BoundedProduct.tools` constructs `GENERATE_SOURCE_WARRANTED_CANDIDATES`
   directly. It bypasses `PhasedProduct.request`, where downstream capacity is
   attached, and the task is absent from `phased/downstream_input.py:TASKS`.
   The reviewed 70,000-token/250,000-byte profile therefore never reaches this
   request. The criticism constructor needs the same audit before another run.
2. `BoundedProduct.answer` calls `tools` before saving a prepared baseline even
   when no tools are selected. Its comment says failed generation cannot block
   the baseline, but `preparation_diagnosis.diagnose` rejects every incomplete
   phase, including this candidate-only phase. The implemented dependency is
   stronger than the intended baseline dependency.
3. P14 attempt 11 is already terminal and is the last allocated owner attempt.
   Re-running a live worker cannot repair the request or silently reopen that
   attempt. A reviewed revision must preserve this result and the 109 successes.

The actual `product/result.json` strengthens the second finding: its P14 answer
is already `PREPARED`, with one complete synthesized finding and an empty tools
list. The acquisition wrapper rejects this prepared result because the optional
candidate phase is incomplete. This discrepancy is not an incomplete P14
synthesis and is not evidence of an invalid synthesized finding. The preserved
failure label says "synthesis not prepared", but the failed stage is candidate
generation and the wrapper's all-phases criterion. A repair must distinguish
required answer preparation from tool-specific prerequisites while retaining
the failed candidate phase and its blocked formal/argument arms. It must not
silently promote this existing prepared finding into a reviewed legal answer.

Next product repair: reproduce the exact candidate packet without dispatch;
apply an explicit bounded transport/capacity contract to candidate and criticism
constructors; test their real schemas and decoders as well as changed-source,
output-bound and oversized-input controls; separate baseline preparation from
optional-tool preparation; then register the reviewed implementation and any
necessary finite owner allocation before live work. Freeze the active campaign
before changing its bound sources. A capacity measurement alone cannot show
that the provider will accept the request or that the candidate is legally valid.

This diagnosis is independent of the reboot recovery. Gatecoin, P10 and evidence
retain their original prerequisites and allocations. No legal question,
obligation, reading or matched tool comparison is marked complete here.
