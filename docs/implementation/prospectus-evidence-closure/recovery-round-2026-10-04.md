# Public recovery round, 4 October 2026

The additional request allowance enabled recovery of 31 PDF candidates from exact issuer and exchange routes. The strongest acquisition result is BASF's 9 September 2022 base prospectus and 27 February 2023 supplement, both named in the selected bond's final terms. The source-intake refresh registered every recovered PDF as an unreviewed candidate and preserved the existing assessment.

Fifty of the 100 additional requests were used: 62 cumulative receipts against the 112-request ceiling. Fifty remain authorised. There is no need for another request-budget approval for work within that remainder. No request ledger was reset.

## Acquired sources and limits

| Issuer | New PDFs | What was recovered | Work still needed |
| --- | ---: | --- | --- |
| BASF | 3 | Exact 2022 base, February 2023 supplement, and 2022 annual report | German Option I and all final-term selections, page fidelity, incorporated sections and amendment coverage. Six additional financial-report candidates have exact exchange records in request040. |
| SEB | 7 | June 2024 programme, July/October supplements, 2022/2023 annual reports, Q3 2024 report and factbook | Exact fiscal agency agreement of 6 July 2023, three 2024 agency supplements and deed of covenant of 18 June 2014; scoped incorporation review. |
| LVMH | 8 | French 2022/2023/2024 registration documents, 2024 half-year report, two 2024 financial documents, October 2024 and April 2025 releases | Apply the latest supplement's cross-reference table, exclude second-level incorporation, recover the July 2024 agency agreement and establish amendment coverage. |
| BBVA | 12 | English and Spanish consolidated 2023/2024, standalone 2023/2024 and June/September 2025 reports | Spanish precedence, scanned auditor/title pages, printed-page mapping, scoped sections, 2024 Form 20-F and November 2025 agency agreement. |
| Enel | 1 | EFI deed of covenant dated 20 December 2024 | Execution and amendment evidence. Blank extracted signature fields cannot establish absence of image signatures. |

Unilever's source-linked issuer route and Lloyds' SEC accession-index route returned HTTP 403. Exact-ISIN LuxSE searches for Unilever and SEB returned no match. These failed routes do not prove that the documents do not exist. Other years' agreements and unauthenticated mirrors cannot replace the required evidence.

All 31 PDFs have retained source bytes, acquisition receipts, source and derivative hashes, and physical-page extraction counts. Text observations are recorded separately from admission in recovery-identity-review-2026-10-04.json. Source metadata is in docs/prospectus/evidence-closure/source-inputs.json, with no changed issue selections.

BASF final terms pages 2 and 7 select fixed-rate Option I and German control; the recovered base identifies its German Option I at pages 108-133. The third LVMH supplement replaces the incorporation section and specifies French sources. BBVA's offering circular says Spanish originals prevail over the English translations. These observations guide review; they do not establish complete source fidelity or absence of later amendments.

## Engineering repairs and validation

The recovery helper distinguishes real PDF bytes from HTML landing pages, extracts pages with bounded Poppler commands, validates retained bytes and cached derivatives, and publishes complete caches atomically. Interrupted extraction cannot publish a partial cache. A fixed Apollo preflight header is restricted to the official LuxSE public API host. No credentials, paid model calls, dependency installation or arbitrary-shell capability were added.

The current code passed 906 prospectus/compliance tests, including ten recovery cases covering misleading PDF labels, malformed PDF bytes, changed source/receipt/derivative evidence, interruption/resume and the host-specific request header.

The master refreshed S1-S7 after the candidate intake. It preserves the 18 qualified yes / 17 qualified no / BASF unknown classification. All 36 bank investigations retained exactly 14 obligation identities and false transaction permission. Source admission remains zero; 4,990 candidate references remain open. Clause review has 1,467 unresolved issue records across 1,307 unique source spans. The Deutsche, BBVA and SEB calculations remain conditional illustrations.

Verification passed: all 3,775 protected files and all 47 attempt records, including retained external evidence, were intact. No phase was stale and no current execution failure remained. A subsequent master run was a no-op: the state was identical, the attempt count remained 47, cumulative phase time remained 2072.796809328487 seconds, and the request count remained 62. See recovery-round-verification-2026-10-04.json.

| Phase | Current attempt | Result |
| --- | --- | --- |
| S0 | 008 | PASS: 906 tests and saved command forms |
| S1 | 006 | QUALIFIED: 31 unselected candidate additions; zero classification changes or admissions |
| S2 | 016 | WAITING_EVIDENCE: 31 PDFs, 62 total requests, 50 remaining |
| S3 | 003 | WAITING_EVIDENCE: 36 bank investigations; facts and authority applicability still missing |
| S4 | 003 | WAITING_EVIDENCE: semantic reviews still open |
| S5 | 003 | QUALIFIED: three conditional profiles; full adjustments, timing and settlement unfinished |
| S6 | 004 | WAITING_PROTOCOL: eligible fresh cases, independent adjudicator and method freeze absent |
| S7 | 004 | WAITING_HUMAN: exact-version qualified legal acceptance absent |

## Decision and next execution

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain recovered sources for review | Exact source-linked bytes retained; key edition/title text checked to the recorded extent | No integrity or budget veto | Some scanned identities, selected scope and amendment chains unchecked | Follow the reviewed source plan | Download does not admit a source |
| Preserve existing assessment | Zero issue-selection or classification changes | Admission veto remains: unverified pages, dates and incomplete coverage | New observations postdate the assessment's 00:00 UTC knowledge cutoff | Perform actual reviews, then deliberately version a later assessment | No backdated knowledge or corrected BASF classification |
| Keep master resumable | Protected-file verification and no-op resume pass | No current infrastructure failure in the runner | Image viewer still fails at sandbox startup | Repair the viewer environment and perform real rendered checks | Rendered-page fidelity is not certified |
| Continue evidence and implementation work | Recovery improved document availability | No scientific-direction rejection | Missing agreements, source semantics and actual facts | Use the remaining authorised budget and complete scoped repairs | Full gap closure or human acceptance |

The image viewer failed at sandbox startup because the host mount at /mnt/wslg/distro is unsupported. Rendered PNGs exist, but no rendered-page fidelity review has been performed. This is a verification limitation, not evidence about signatures or document contents.

The reviewed follow-up plan is docs/plans/prospectus-recovered-source-review-2026-10-04.md. It orders the work by source dependencies and records the exact master commands. Next acquisition candidates and the admission reviews remain executable work; this note completes the present recovery round, not the entire prospectus programme. Independent adjudication, human acceptance and private facts are not supplied by a public-request allowance.

Post-run red-team: the strongest misleading interpretation would be to count downloads as closed legal dependencies. The weakest evidence is page fidelity and complete amendment coverage. A wrong edition, wrong controlling language, conflicting amendment or failed extraction comparison would overturn a candidate's usefulness. The harness passed its integrity checks; the remaining open results concern evidence and substantive implementation.

## Run manifest

- Recorded: 2026-10-04T06:17:16Z.
- Checkout: /home/chakwong/python/legalmath/.worktrees/bond-gap-closure.
- Branch / comparator: feature/prospectus-evidence-master / 2d6b737b; changes remain uncommitted.
- Environment: checkout .venv/bin/python; per-phase manifests retain Python version and method hashes. CPU only; GPU devices intentionally hidden. Seeds: N/A, deterministic acquisition and validation.
- Data version: exact receipt/source hashes in each recovered inspection and the identity review; source-inputs.json records the candidate metadata. Existing assessment effective/known time remains 2026-10-04T00:00:00Z.
- Commands: .venv/bin/python scripts/run_prospectus_evidence_master.py close phase S2 for bounded queues; close inspect for selected pages; close run, close verify, then close run for refresh and resume verification. Local edits used scripts/edit_workspace_files.py with reviewed JSON edits.
- Timing: per-attempt manifests preserve actual start times and wall times; cumulative phase wall time 2072.796809328487 seconds, unchanged by the no-op. S0 test subprocess took 94.66695199999958 seconds; S3 rebuild took 266.77495693205856 seconds.
- Plans: docs/plans/prospectus-public-recovery-2026-10-04.md and docs/plans/prospectus-recovered-source-review-2026-10-04.md.
- Outputs: docs/prospectus/evidence-closure/requests, recovered, and source-inputs.json; docs/implementation/prospectus-evidence-closure/phases; recovery-identity-review-2026-10-04.json; recovery-round-verification-2026-10-04.json; this result note.
