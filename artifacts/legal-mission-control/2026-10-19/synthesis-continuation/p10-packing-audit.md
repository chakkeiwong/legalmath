# Settled P10 packing diagnostic

The detached supervisor finished at 2026-10-18T23:41:11.502585+00:00.
All 85 account roots validate. The complete synthesis populations are
105, 19, 7, 4 and 3; no phase is incomplete. The returned failure is
`E_RESOURCE_LIMIT: Synthesis cannot contract without losing support`.
The cumulative ledger contains 3311 charges out of 8100. No worker owns a run.

Question: does the final P10 frontier contain a pair that fits the exact
existing production request and capacity rules, as the evidence frontier does?
Comparator: the three unchanged rows in reduction-p10-4.json. Measure all
three singletons and all three pairs through the production request builder,
source selection, downstream instructions, encoding, tokenizer and limits.
No provider call or allowance reservation is permitted. Retain every original
row, hash and charge. A fitting nonadjacent pair reproduces a grouping defect;
no fitting pair means that repair alone cannot resolve P10 at these limits.
Neither result decides legal completeness or validates a new capacity default.

Skeptical audit: PASS for this local diagnostic. The latest settled production
rows are the comparator. A 250k-byte/70k-token account capacity does not imply
the downstream synthesis profile uses those bounds; record the actual bounds.
The pair screen is an engineering diagnostic, not a promotion criterion for
answers. Stop on changed ledger, missing evidence, unexpected errors or altered
inputs. Preserve the measurements in p10-capacity-diagnosis.json and use them
to review the same-master continuation before editing production code.
