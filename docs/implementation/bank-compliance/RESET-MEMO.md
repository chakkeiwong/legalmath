# Bank-compliance reset memo

The instrument-independent foundation is implemented and conditionally checked;
full bank compliance and live transaction permission are not established.
See `report.md`, `run-manifest.json`, `document-review.json` and
`docs/plans/bank-compliance-layers.md`.

- 107 tests pass: 44 new compliance checks and 63 existing checks. The finite
  specifications cover 2,187 layer combinations and 512 ownership graph/seed cases.
- The shared context preserves legal entity, establishment, client, instrument,
  service, action, effective/knowledge time and content references to facts,
  route and policy. Missing policy or required findings prevent permission.
- Selected CMIC principal/support and holding/divestment distinctions and
  exact blocking ownership propagation are conditional Python functions.
  Native RuleIR/Catala lowering and live data/policy integration are outstanding.
- Source records: 12 retained primary documents; four eCFR access responses
  rejected. Historical 2025 CFR editions are labeled; complete currentness is
  not established.
- Monograph section 2.4 is added. The 327-page main PDF and 78-page companion
  compile; all 269 earlier citation contexts are preserved, with 13 additions.
  The excerpt occupies PDF pages 57--61, printed pages 35--39.
- Next: source-bound jurisdiction/activity inventory, live sanctions identity
  and ownership inputs, separately versioned bank/AML/conduct/reporting rules,
  actual bank policy, common native lowering, and future unseen-source evaluation.

Reproduce with `.venv/bin/python scripts/check_bank_compliance.py`; rebuild with
`python3 scripts/build_reader_facing_monograph.py`. Preserve existing unrelated
dirty work. No human quality labels, actual trade decisions, filings or external
publication were used.
