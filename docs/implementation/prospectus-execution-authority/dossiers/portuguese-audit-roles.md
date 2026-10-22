# Continue Portuguese2008: audit roles and materiality

Read `docs/plans/prospectus-portuguese-audit-roles-2026-10-16.md`, the107 audit
and source-review.json, complete retained Portuguese readings, and sealed001/002
results. Follow that plan, preserving G01/G10, all history and independent-reader
requirements. This is a separately reviewed third admission, not a reset.

The first actual current consumer must reproduce board duties being accepted
as a conclusion under the existing optional profile. No implementation follows
if that check fails. The positive v1 baseline must survive. After the candidate
is frozen, actual matched consumers test both statutory reports, omission and
role controls, plus the unchanged committee/date/NCA behavior. Retain actual
answers before checks. v1 remains an explicit comparator; v2 is opt-in.

Run local stages from this worktree, one at a time, with a one-second tool yield:

    timeout 120 .venv/bin/python -m scripts.prospectus_portuguese_audit prepare
    timeout 120 .venv/bin/python -m scripts.prospectus_portuguese_audit baseline
    timeout 120 .venv/bin/python -m scripts.prospectus_portuguese_audit candidate
    timeout 120 .venv/bin/python -m scripts.prospectus_portuguese_audit cases
    timeout 120 .venv/bin/python -m scripts.prospectus_portuguese_audit compare
    timeout 120 .venv/bin/python -m scripts.prospectus_portuguese_audit seal

Read the actual stage result before the dependent stage. Tests run once after
their fixture dependencies are inspected, and their exact command is retained.
The cases stage may be split into named cases without resetting any bound.
The stage runner is an execution aid; program.json remains the sole authority.
No stage grants network/native/model permissions or independent acceptance.
