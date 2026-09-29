# A measured shared response-construction failure

In initial batch 9 of C6 attempt 2, both source-first and qualification-first
contexts assessed an executable omission for the unencoded candidate
`node.8eb374ffa546ddd2ba291e37`. The relevant source claim was
`claim.9393beb42f3f951c0d910e5a`. Both responses were rejected because the
candidate has no executable representation to assess. The existing contract
requires executable correspondence to remain unassessed in that situation.

This is not proof that both proposed English readings are wrong. It is an
observed shared failure to distinguish an unencoded interpretation from an
executable program. The preserved responses and row-specific diagnostics show
why agreement between contexts is insufficient evidence of correctness.

The current scoped validator accepts a batch only when every required row
passes. Therefore one malformed row keeps the batch incomplete, even if other
rows might pass separately. Their complete raw responses remain available;
they are not silently deleted. The report must not count either rejected batch
as a second validated perspective or silently repair a label on the model's
behalf.

A future general response protocol can expose each candidate's mechanically
known representation availability and restrict structurally impossible fields
without selecting a legal judgment. If row-level recovery is introduced, each
accepted row must be independently validated against the same original full
source, question and candidate; failed rows and cross-row concerns must remain
in the denominator. Recovered rows reuse the original reservation and context,
never constitute additional independent votes. This requires a reviewed
protocol and mutation tests; it is not part of the current batch-completion
claim.
