# Rounding defects reproduced; repair execution stopped by evidence-size veto

The pre-edit actual direct and selected consumers reproduce two local defects.
With all supplied holders excluded, zero quantum, unknown HALF_EVEN rule and
zero-denominator quantum 1/0 are accepted as CONDITIONAL with no transfers.
With active holders, zero quantum and unknown rule are refused, while 1/0 leaks
ZeroDivisionError from the exact-rational parser. The retained hypothetical v2
per-holder variant exhibits the same inactive validation bypass. These are our
validation defects; no external package was executed or implicated.

The baseline also retains 16 valid Danske and eight valid Shell full consumer
records, including excluded accounts, with unchanged originals compared against
their sealed answers. Changed selected terms were readmitted with new term
hashes; source graphs, assembly, other terms and law payloads were checked.
These are pre-edit comparators only. No candidate, adverse-after-repair stage,
regression test or post-edit verification ran, and no production file changed.

The once-only baseline completed its calculations but failed its final storage
assertion after 75.558 seconds. It had written 53,957,985 bytes against the
40,000,000-byte limit. Repeating complete P1-P4 graphs in every compressed record
was an evidence-storage design error. The eight Shell records alone occupy
about 29 MB. The limit was checked too late to prevent the overshoot.
The process exited with status 1 and tool session 20368 was polled to completion.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | What is not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain defect reproduction | Actual consumer counterexamples retained | No source corruption detected | Finite malformed-input coverage | Preserve failure and formulate minimal validation repair | Fix is implemented or tested |
| Stop this admitted package | Candidate comparison not executed | Explicit cumulative storage bound exceeded | Post-edit behavior untested | Record FAIL and refresh; review independent authorized routes | Successful package or repaired engine |
| Preserve entitlement limits | All inputs hypothetical | Actual records and independent review absent | Real ownership, events and clearing rules | Obtain authentic evidence separately | Actual entitlement or settlement |

The observed result invalidates this runner's storage plan, not exact rounding
arithmetic or the proposed validation repair. Although one diagnosed changed
repair was allowed, the admitted plan expressly makes exhausted storage a
continuation veto. It cannot be silently waived, reset, or erased by deleting
failed evidence. No further entitlement admission is requested by this result.

A future explicitly reviewed continuation must retain this failure, budget
cumulative existing evidence, reference immutable graph/assembly payloads by
hash, store only actual changed products and answers, and preflight size before
writing. No rerun of this unchanged baseline is justified. The weakest evidence
is the entirely absent repaired candidate; the result supplies no correctness
claim for a patch.
