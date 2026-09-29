# Running and extending the prospectus program

Use the exact approved prefix, without an environment assignment or shell wrapper:

```
/home/chakwong/python/legalmath/.venv/bin/python /home/chakwong/python/legalmath/scripts/prospectus_master.py run
/home/chakwong/python/legalmath/.venv/bin/python /home/chakwong/python/legalmath/scripts/prospectus_master.py verify
```

`run` completes seven phases and resumes current evidence. Changed sources,
methods or upstream results invalidate affected downstream phases. Each attempt
retains results or failure, a review and a refreshed next-phase plan. Derivative
corruption triggers reconstruction from unchanged originals and an automatic retry.
Changed originals or unrepaired mathematical mismatches stop execution. Known
download failures remain qualified after bounded attempts; separately identified
mirrors can repair coverage. `status` distinguishes current, stale and failed work.

The complete plan is `docs/plans/prospectus-master-program.md`. `report.md`,
`summary.json` and `next-program.json` give the latest conclusions and next work.
The immutable evidence is in `artifacts/prospectus-master/P*/attempt-*`. `state.json`
identifies the current attempts. The project rule is in `allow.rules`; its installed
copy is `/home/chakwong/.codex/rules/legalmath-prospectus.rules`.

For a genuinely later publication, add a separately identified source to
`docs/prospectus/catalog.json` and preserve it with `phase P0` (group `supplied`).
Do not run the whole campaign before testing that new source: doing so makes it
development evidence in a new freeze. Create `future-intake.json` here with a list
of objects containing only `document`, `task_id`, `family`, `published_at` and
`first_seen_at`. Dates must be UTC ISO timestamps. Families are `new_issuer`,
`new_contract_template` and `later_rule_edition`. Then run:

```
/home/chakwong/python/legalmath/.venv/bin/python /home/chakwong/python/legalmath/scripts/prospectus_master.py future
```

This uses the retained P6 freeze and a separate prospective ledger. It checks the
full unchanged method, original hash, chronology, quotations and conditional
candidate results. Publication dates are recorded premises, not independently
authenticated facts. The source inventory is bounded at 32 URLs in this campaign;
changing that budget changes the frozen method and requires a new campaign.

An observed qualification is evidence about those checked properties. It is not
a legal accuracy score. No human or model answer label, rating or acceptance can
enter the input. A repaired method needs a later untouched window. Current
documents and synthetic future tests never count as real prospective observations.
