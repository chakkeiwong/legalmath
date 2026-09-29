# Incremental fidelity admission after a measured false capacity stop

The latest UCITS revision preserves 25 claims and nine readings. Its legacy
fidelity check nevertheless performs no model batch: seventeen possible
200,000-byte outputs create a 3,409,937-byte conservative bound above the
2,097,152-byte aggregate ceiling. Smaller batches therefore cause a larger
worst-case preflight bound. This establishes an admission-policy failure for
this workload, not an error in the source interpretation.

Add an explicit opt-in incremental admission setting; keep the existing default
for old callers. Retain the projected bound as an explanatory diagnostic. Keep
pair and minimum-call limits as pre-dispatch vetoes. For each strictly validated
batch, preserve its exact file, then check actual accumulated concerns and a
conservative sum of retained canonical bytes before aggregation. A part that
would exceed either unchanged aggregate ceiling stays retained but unadmitted;
processing remains incomplete and no complete matrix or legal verdict is issued.
Memory is bounded by the admitted aggregate plus one individually bounded
response. No response is shortened, no concern deduplicated and no pair removed.

The primary criterion is complete aggregation of small valid parts whose
projected worst-case responses would have been rejected. Negative criteria are
a late byte/concern overflow, a late invalid/missing batch, duplicate or missing
pairs, or altered quotations; these must retain evidence and reject completion.
Existing default-capacity tests must still pass. This is an optional engineering
capacity repair; no accuracy or independence improvement follows. Stage outside
the active source tree, test, then merge only after S8 attempt eight finishes.
The later continuation must retain original pair expenditure and deadlines.
