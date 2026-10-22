# Identity admission result

The finance consumer previously accepted JSON holder IDs `true` and `1`, then
silently merged their GBP60,000 and GBP40,000 holdings because Python treats
those keys as equal. Both the retained v2 scenario and the ordinary v3 consumer
reproduced one conditional GBP1,249 payment. This was our input-validation bug;
no external package was involved.

Holder, account and event identifiers now require nonblank strings before they
enter aggregation or event indexing. Values retain their original spelling;
there is no string coercion, trimming or case conversion. Existing uniqueness,
entitlement, principal, form and chronology checks remain in place.

All four direct/selected GLOBAL/DEFINITIVE comparisons preserve the complete
pre-edit P5 and Q1-Q6 answers exactly. Their hypothetical global payment remains
`31215847/5` and definitive payment `1249`. The two definitive positive controls
retain three accounts, aggregate the two accounts belonging to string holder
`true`, and keep string holder `1` distinct. The resulting payments are `3747/5`
and `2498/5`, respectively.

All 120 malformed-input controls reject at their actual consumer boundary:
typed UNSUPPORTED for direct scenarios, with Q1-Q4/Q6 preserved, and ValueError
for selected terms. The original v2 counterexample now also returns
UNSUPPORTED. All 154 focused tests pass; collection through the existing R5
register selects all 32 new regression cases. Eight stages completed without a
failed stage, changed repair or duplicate launch.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Limit |
| --- | --- | --- | --- | --- | --- |
| Retain identity validation | Complete valid P5/answer equality; malformed IDs rejected before use | No accepted invalid ID, changed valid answer or source/method drift | Finite input coverage | Seal, record and refresh | Engineering correctness for these inputs |
| Keep entitlement partial | Conditional amounts and declared accounts retained | Actual entitlement and independent source review absent | Real form, ownership and events | Obtain and review authentic records separately | No settlement or legal-right determination |

The original P1-P4 products were explicitly frozen and reused. Selected adverse
cases reseal parent identities only to change hypothetical calculation premises;
their extraction, construction, interpretation and law payloads remain equal.
No fresh extraction or independent interpretation is established. Correct
arithmetic can coexist with an incorrect source/form interpretation; that is the
strongest remaining alternative explanation for the Shell legal reading.

This package uses the task's second and final existing admission. Historical
evidence remains immutable. Commands, tool sessions, source/method identities,
exact comparisons and CPU-only environment are retained in the run manifest.
The wider financial engine, actual clearing/settlement, independent acceptance
and whole-program completion remain unestablished. No stochastic comparison or
package ranking was performed.
