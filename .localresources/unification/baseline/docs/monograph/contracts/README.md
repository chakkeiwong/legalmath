# Proposed interpretation.v1 contracts

These ten JSON Schemas describe the ensemble extension in chapters 6–8 of the
monograph. They do not replace RuleIR 0.1 or implement the new service.

- `policy`: explicit limits, mandatory roles/checks and paid-provider requirements.
- `run`: source/profile/policy identity, phase, counters and linked records.
- `candidate`: immutable revisions, assumptions, arguments and scheduling priority.
- `issue`: root identity, discrepancy, materiality, processing and resolution states.
- `action`: a counted reservation, dispatch state, lease and result identity.
- `coverage`: source-unit dispositions, dependencies and interpretation families.
- `evidence`: typed source, repair, comparison and adjudication evidence.
- `report`: complete terminal reporting, including unresolved and missing items.
- `issue-decision`: adjudication of an issue revision before the terminal report.
- `review-decision`: post-report candidate/report/source identities and attributed judgment.

`reference-policy.json` is for deterministic fixtures. Its limits are convenient
engineering choices, not selected production defaults. Paid runs require explicit
positive token/cost caps and billing currency. Actual provider reservations must
bound usage; the schema alone cannot establish that capability.

`examples/blocked-investigation.json` is entirely synthetic. Four initial actions
are followed by one explicit-omission repair and three unsuccessful attempts to
settle a definition. The resulting report remains blocked. It is not a new legal
adjudication of 23EC46 and does not alter its retained oracle.

Run from the repository root:

```bash
python3 scripts/build_interpretation_contracts.py
python3 scripts/build_interpretation_examples.py
.venv/bin/python scripts/check_interpretation_contracts.py
```

The checker validates the example, cross-record identity and accounting, sixteen
negative mutations, the task dependency order, an eight-state finite budget model
and the sixteen-row release predicate. It does not test real concurrency, leases,
a provider, authentication, an API or the legal sufficiency of evidence.

The application must enforce these rules transactionally:

1. Reserve an action and increment global/root counters with the outbox entry.
   Dispatch requires that committed reservation. Issued counts never refund after
   an ambiguous dispatch, crash, timeout or candidate revision.
2. Child issues retain root accounting. New roots remain under the global cap.
   Initial roles use the initial account and also consume the global cap.
3. Bound waiting by the earlier of action timeout and run deadline. Preserve late
   results as observations; never mutate a closed report implicitly.
4. Resolve an issue only using the matching evidence kind. Equivalence requires a
   feasible checked domain, a completed comparison and disposition of distinct
   source commitments. Adjudication requires authenticated review authority.
5. Reconcile every discrepancy. Unknown materiality blocks; an immaterial
   disposition requires its own reason and authority. Every issue remains in the
   report, including resolved issues and processing failures.
6. `READY_FOR_REVIEW` requires mandatory roles/checks and coverage. Every report
   has `release_eligible=false`: the separate release service must validate exact
   approvals, applicability, integrity and absence of unresolved material issues.
7. Treat the schemas as structural validation. Review identity comes from the
   authenticated service context, never from a submitted principal or role field.
   Production evidence authenticity cannot be established by these fixture files.

The terminal-state precedence is integrity failure, cancellation, deadline/action/
round limits, no-progress limit, unavailable permitted action, then readiness.
When several limits coincide, retain all applicable diagnostics and a deterministic
primary stop reason. An initial-phase failure must create an issue; the final
mandatory-evidence check independently prevents false readiness if that issue
creation path is defective.
