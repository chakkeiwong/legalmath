# Reset memo — prospectus corner cases, 4 October 2026

## Current outcome

User authorised 100 additional public requests to find corner cases. This extension
used 58 (cumulative receipts 170/212); 42 remain. Public retrieval is stopped at a
useful evidence boundary. Do not spend the remainder simply to exhaust the allowance.

Worktree: `/home/chakwong/python/legalmath/.worktrees/bond-gap-closure`.
Branch: `feature/prospectus-evidence-master`.
HEAD: `2d6b737b27aa6f028d8b37ccac17cbd5816d4488`.
The dirty tree includes substantial previous work; preserve it. No commit was made.

Saved: 24 PDFs plus six official readable CJEU judgments; 30 distinct specifications,
51 checked passages. Seven new offering PDFs all abstain, with 29 unresolved clause
records and zero runtime errors. Three extra probes also abstain but each incorrectly
classifies unpaid cancellation as ordinary post-payment cancellation.
`check_prospectus_corner_findings` deliberately exits 1 and reports three failures.
No reader fix, legal accuracy claim, legal-label promotion or transaction permission.

## Frozen files

Do not edit the 293 reader files identified by
`docs/prospectus/difficulty-2026-10-04/freeze.json`.
Preserve the original 24 PDFs/run and historical master/continuation campaigns.

The extension run binds these inputs:
- `scripts/run_prospectus_corner_tests.py`
- `docs/prospectus/corner-cases-2026-10-04/reader-selection.json`
- `docs/prospectus/corner-cases-2026-10-04/source-index.json`
- `docs/prospectus/corner-cases-2026-10-04/manual-transcriptions.json`
- `docs/implementation/prospectus-corner-cases-2026-10-04/reviewed-catalogue.json`
- `docs/implementation/prospectus-corner-cases-2026-10-04/test-specifications.json`
- `docs/plans/prospectus-corner-cases-2026-10-04.md`

Do not rerun extraction or change these inputs to accommodate a new candidate.
A repair must use a separate method snapshot, runner and result directory.
All reader outputs remain in `run-001/`.

## Completed documentation and checks

The two difficulty LaTeX files include the new narrative, source catalogue and
30-case matrix. PDFs built: monograph 365 pages, companion 89, guide 24.
Affected monograph pages 81–87 and companion pages 12–22 inspected; page 22 is the
adjacent appendix transition. Source images inspected include both six-page BES
scans, Adriano Lease pp140/144/145, Adriatica pp44/121 and Adriano Finance p65.
Human prose review and independent legal adjudication remain pending.

Read `REPORT.md`, `rendered-review.json` and `archive-verification.json` here.
The combined verifier checks the old 24 PDFs/run, historical campaigns, all new
receipt/source/policy bindings, unchanged method, frozen extension outputs,
manuscript source/link preservation and built PDFs. It does not re-adjudicate law.

## Important source boundaries

- BES Series 23 PTBEQBOM0010 matches the coupon/maturity in C-500/22, but the judgment
  does not print the ISIN; original Portuguese Annex 2B is still required.
- BES 2010 base plus six supplements and 2013 base plus four supplements are saved.
  Series 35 and Series 36 have different dependencies. Financial reports and final
  applicability/precedence review remain open.
- The HETA April notice is 11 April 2016 about 10 April decree; TO 46.02%, not BY 46.02%.
  Original FMA decree and exact debt/guarantee list remain missing.
- Hypo search keys for the Italian documents do not make them HETA debt.
- Dana Gas assumed the UAE illegality premise without deciding it. Lloyds is a call
  case with a separate conversion provision and a dissent. Ukraine is a procedural
  outcome, not a final duress finding or discharge.
- Kotnik, Kuhn, Popular and Snoras cannot be generalized to unrelated issuers,
  governing laws, security classes or unconditional compensation.
- No automatic OCR was claimed; scan transcriptions were kept out of the raw runs.

## Next work

The reviewed follow-up plan is
`docs/plans/prospectus-corner-repair-2026-10-04.md`.
Start with unpaid-cancellation action binding and segmentation; keep actual
post-payment cancellation and paid amortisation controls. Add exception/condition
checks, extraction status, dated dependency and identity binding, then integrated
external-law interpretation and independent adjudication.
The candidate failed; the research direction remains viable.

Exact local commands:

```text
python3 -m scripts.run_prospectus_corner_tests verify
python3 -m scripts.check_prospectus_corner_findings
python3 -m scripts.verify_prospectus_corner_archive
```

Only the middle command should fail, with `GAPS_REPRODUCED`.
Master/jurisdiction actions share one lock: run sequentially.
The existing Python3 environment is the tfgpu environment but no GPU/framework
was used. No installations or paid-model calls are needed for these checks.
Use ordinary sandboxed edits in the worktree/tmp; current approvals already cover
the resource budget and local work. No agent delegation was used.
