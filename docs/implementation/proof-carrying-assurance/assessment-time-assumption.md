# Assessment clock used by the replay

The manifest uses `2023-12-09T00:00:00.000000Z` as a fixed replay clock. This is a
convenience value for repeatable bundle/snapshot eligibility checks. It is not a
source-backed effective date and is not evidence that the retained circular was
applicable to a bank transaction on that date. The source itself carries edition
and supersession questions. Those require authority/edition evidence before any
legal conclusion.

The early diagnostic checked the timestamp through the repository's strict UTC
format and reaudited the retained packet against source bytes. That exposed and
repaired the missing six fractional digits. This checks engineering syntax and
source anchoring; it does not establish legal applicability. Runtime comparisons
hold the declared clock fixed across Python, Java and Catala. Their finite
agreement is conditional on that shared clock and does not compare effective
editions or historical business transactions.
