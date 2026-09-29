# Round 11 operator guide

Run from `/home/chakwong/python/legalmath` with the repository virtualenv.
First run `audit` and `preflight`. The substantive author audit is retained in
`design-review.json`; each execution binds it to a freshly generated input plan.
The master creates immutable attempt directories. If it exits with a repair
request, inspect the log, make the smallest justified code or fixture repair,
write a note containing `summary`, `findings`, `changes`, and `regression`, run
`repair`, which executes fixed focused regression, and retry. Do not delete an attempt or edit its
manifest.

Use the absolute allowlisted runtime vector, with trusted execution in Codex:

```text
/home/chakwong/python/legalmath/.venv/bin/python /home/chakwong/python/legalmath/scripts/run_assurance_master.py execute
```

The sandbox can stall the existing Starlette/AnyIO API tests at startup. A
stalled run must be preserved and repaired before retrying in the already
approved trusted context. Do not treat a quiet console as evidence of progress;
inspect the active attempt's command log when it exceeds its usual duration.

The installation phase accepts only the exact `install M1` master command.
It creates a separate CPU virtualenv, extracts downloaded Ubuntu OCR packages
under `.localresources/assurance-tools/ocr`, caches layout weights and downloads
fixed Maven jars. No sudo is used. It records package versions and failed
installs. Missing required tools block the phase. Proposed prefix rules are in
`allow.rules`; they do not themselves install global Codex policy.

The final report is an engineering decision record. `PASSED` means that the
declared local checks passed under their scope. It does not mean that the SFC
English interpretation is correct or that the resulting Java may be deployed.
The completed `artifacts/interpretation/round11/final-report.json` binds all six
phase manifests, including M5. Its `next-phase-plan.json` is generated only after
that binding succeeds. The summary inside the M5 attempt records predecessor
evidence while M5 is running; the post-completion report adds M5 without a
circular hash. Changes to material inputs mark accepted phases and the current
final report stale while preserving the immutable attempt history.
