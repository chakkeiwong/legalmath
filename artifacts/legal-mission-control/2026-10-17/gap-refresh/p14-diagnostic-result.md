# P14 retained invalid-request diagnosis

The exact rejected parameter remains **unknown**. The local diagnostic
authenticated the eleven charged receipts at slots 2335–2345, including the
failed slot 2341. The ten neighbors have complete output; all eleven schemas
pass the current necessary checks. No reproducible local schema failure was
found. This leaves the cause unclassified rather than proving a provider defect.

No successful neighbor has an identical full schema. The closest, slots 2335
and 2336, have the same schema properties; their sole schema difference from
2341 is the maximum of `$defs/ExactCitation/properties/span_id`: 7 and 15 versus
5 in the rejected request. Other neighbors differ in citation bounds,
considered identifiers, source-gap enums or indexed-source availability.
These differences are expected to vary with the legal inputs and do not identify
an invalid parameter. The failed application request is 23,757 bytes; successful
neighbors range from 23,578 to 53,883 bytes. Size alone does not explain the failure.

The error says only that the request could not be processed and its parameters
should be checked. The retained application request and schema are not the raw
HTTP body. CLI framing, actual wire parameters and gateway behavior were not
observed. The next discriminating evidence is a trace naming the rejected
parameter with its actual wire body, or a reproducible local contract violation.
Repeatedly sending the same invalid request would not supply that diagnosis.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain P14's branch blocker | No local invariant failure or parameter-specific diagnostic established | Receipt authentication passed; P14 owner allocation remains exhausted | Which wire parameter was rejected, and at which service boundary | Preserve request and comparisons; obtain a parameter-specific trace or reproduce a defect locally | Provider fault, permanent impossibility, or legal acceptance |
| Continue independent branches | P10 receipt repair is registered; evidence retains its own attempt | Shared global authority, deadlines and budgets still apply | Whether their remaining production requests succeed | Execute the same master and preserve actual results | That these branches depend on P14 success |

This was a deterministic local comparison: zero provider calls, unchanged live
ledger, no task reopening and no stochastic ranking. The actual command,
commit, environment, inputs, hashes and 0.040-second diagnostic runtime are in
`p14-diagnostic-result.json`; `p14-contract-differences.json` preserves complete
recursive differences. The pre-execution review is `p14-diagnostic-plan.md`.

Post-run review: a hidden CLI or gateway parameter remains a stronger alternative
explanation than any particular schema field identified here. A parameter-specific
trace or locally reproducible rejection would overturn the current unknown-cause
classification. Necessary local checks cannot establish provider acceptance.
This diagnostic has reached its evidence limit; it has not rejected the legal
research direction or invalidated the ten neighboring completions.
