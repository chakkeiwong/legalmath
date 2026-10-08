# Executable offline program

The reviewed revision-2 plans and hashes remain historical specifications.
Actual results are selected by execution-current.json and immutable per-phase
attempts under artifacts/legal-interpretation-program/2026-10-06-offline-v1.

Run from the repository root using the already approved command form:

```text
python3 -m scripts.run_legal_interpretation_program resume
python3 -m scripts.run_legal_interpretation_program status
```

The fixed resume action validates all semantic tests and the declared regression
groups, checks the reviewed program manifest, verifies existing output hashes,
and executes missing or stale phases in order. Each phase consumes the preceding
result and refreshed next-phase plan. A changed owner module or predecessor
invalidates the affected phase; shared package changes invalidate P6 onward.
The driver, offline demo and fixed operations script are also hashed. Changing
any of them requires new validation and new phase receipts.
An implementation failure is retained and stops that attempt. Repair requires
a new attempt and validation; no generic shell execution or automatic model
repair worker is exposed.

The runner deliberately re-executes the project virtual environment, hides GPU,
and uses retained inputs or declared offline fixtures. It dispatches no live
provider, sends no messages, changes no external grant, and requires no new
allowlist form. Local Java/Lean execution is part of fixed phase work.

Validation records exact commands, logs, source/test hashes, commit/environment,
elapsed time and qualifications. The current pointer is issued only after all
phases execute. OPEN_QUALIFIED legal obligations, unsupported constructs and
pending real authority/future observations are retained; phase execution is not
a claim that the product's English interpretation problems are solved.

Final resource audit repaired repeated-path cycle checking and repeated subtree
expansion in P3. The finite adapter now checks cycles without enumerating paths,
memoizes subargument sets, caps input profiles, checks generation/attack deadlines
and bounds derived identifiers. The 30-level shared-DAG challenge passes.
P6 receipts made before this repair remain historical; the resumed execution
creates new P3 and dependent attempts.
