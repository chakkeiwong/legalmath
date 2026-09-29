# Edition-integrity repair: second implementation version

The real-document fault challenge rejected version 1. Replacing the Compass
2025 base with the 2026 base, while updating hashes consistently, still produced
a negative because the newer document mentioned the older edition. Hashes alone
and a whole-document date search cannot establish document identity. Preserve
the frozen run and its rejection; Compass and ING are now development cases.

The repair binds the selected edition's marker to its identified page. The
declaration remains a qualified source premise, but a historical mention on
another page cannot satisfy it. Add controlled examples where an old date
appears only in the body and where it appears on the actual cover. The real
Compass substitution must now abstain with an edition-location error.

This failure invalidates an implementation integrity claim, not the source
clauses for the original bonds or the formal predicate. Continue the planned
repair. A new version starts a new bounded attempt sequence; do not count the
exposed families as fresh evidence. Re-run both source sets, relevant tests and
native targets, then freeze before acquiring different issuer families.

```
.venv/bin/python scripts/build_bond_feature_inventory.py
.venv/bin/python scripts/run_bond_loss_absorption_classification.py --inventory docs/prospectus/classification-additions/issue-inventory.json --output docs/implementation/bond-loss-absorption-classification/execution/development-v2 --checks
.venv/bin/python scripts/run_bond_loss_absorption_classification.py --inventory docs/prospectus/classification-holdout/issue-inventory.json --output docs/implementation/bond-loss-absorption-classification/execution/exposed-v2 --checks
```

No output indexed by issuer or intended answer is introduced. The decision
logic is unchanged; the repaired source acceptance rule is stricter.

The first version-2 corpus attempt correctly rejected an incorrectly assigned
Tesco page-1 date. Inspection located the explicit edition statement on page 2;
the inventory now uses that exact sentence and page. This was input-location
repair, with no classifier rule change. The exposed-source native run also had
one RuleIR `E_SCHEMA` failure at its first case while two native campaigns were
running concurrently. A serial rerun passed both targets. Concurrency as the
cause is unproved; preserve the failed receipt and use serial native campaigns.
The final corrected runs are `development-v2-retry` and `exposed-v2-retry`.
