# Failed source repair must preserve the existing inventory

Actual UCITS investigation retained nine candidates after two initial inventories.
A fidelity timeout opened the provider circuit. Both subsequent source-inventory
repair calls therefore failed, and the engine assigned the empty `revised` map to
its active inventory. `claims.json` became empty. This is an implementation defect:
failed new evidence must not erase already retained source obligations. The old
initial inventories remain on disk, so recovery and a focused reproducer are possible.

Stage a fix in the isolated repair source tree while S8 runs. A replacement is
usable only when both requested independent inventories validate. Otherwise
retain the previous inventory and claims, record the failed proposed revision
with both role statuses, retain its source concern and mark execution incomplete.
Do not substitute a successful single role for two-role evidence or treat the
prior inventory as a successful repair. Keep action reservations and history.

The exact baseline is current engine behavior on a forced source-repair failure.
Run the actual workflow with deterministic providers for both-failed and
one-failed replacement, plus the existing successful-repair path. Acceptance:
old claims survive byte-identically, failures and concern remain visible, no
execution-complete claim follows, and successful two-role repair still works.
No legal conclusion or live accuracy claim follows from this regression.
Merge only after the active S8 phase stops and revalidate current sources.
