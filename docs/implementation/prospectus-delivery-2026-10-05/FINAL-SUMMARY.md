# Prospectus master program: final campaign summary

5 October 2026. The reviewed OCR, source-refresh and BASF-selection engineering
campaign is complete. Each continuation reached its final verification phase,
and the latest runner reports `BOUNDED_PHASES_VERIFIED`. This closes the
specified engineering work. Complete legal dossiers, general semantic accuracy,
independent validation and production readiness remain open.

This delivery adds the previously uncommitted 5 October work to
`feature/prospectus-evidence-master` and integrates it with `main`.
The earlier evidence-master campaigns and their immutable results remain part
of the same history. Their original claims and run baselines are preserved.

## Completed work and evidence

| Continuation | Completed result | Final evidence |
| --- | --- | --- |
| OCR and source admission | 17 BES scan pages processed, 18 source-page images inspected, 23 corrections recorded; seven offering inputs now have text. Two source-bound financial profiles and 25 unassigned review forms retained. | [OCR report](../prospectus-closure-2026-10-05/REPORT.md), [verification](../prospectus-closure-2026-10-05/verification.json) |
| Source refresh | Correct BASF 2022 base and February 2023 supplement admitted with 21 initial choices. Deutsche pages 36–38 separated by language, retaining all 2,012 extracted words and conversion alternatives. | [Refresh report](../prospectus-closure-refresh-2026-10-05/REPORT.md), [final verification](../prospectus-closure-refresh-2026-10-05/phases/015-verify/verification.json) |
| BASF continuation | All 55 checkboxes and eight bilingual Yes/No provisions accounted for; 37 source pages visually reviewed. Detailed incorporation ranges identify 92 annual-report pages. | [BASF report](../prospectus-basf-continuation-2026-10-05/REPORT.md), [final manifest](../prospectus-basf-continuation-2026-10-05/phases/014-verify/run-manifest.json), [reviewed PDF](../prospectus-basf-continuation-2026-10-05/phases/013-document/addendum.pdf) |

The latest suite passed **186 tests**, with zero failures, errors or skips.
It includes the earlier 123 refresh/OCR tests; the earlier rounds' counts must
not be added to 186. Final verification checks current methods, source identities,
review records, prerequisite receipts and historical evidence. The BASF entry
baseline protects 8,923 files.

The source review preserves distinctions that a broad label match could erase:
the scheduled holder put is excluded while the change-of-control right remains;
the initial BASF Finance guarantee is excluded for BASF SE while the successor
guarantee condition survives; the clean-up call requires both the 75% acquisition
threshold and global-note reduction. The annual-report table's conflicting
195–209 and 209–290 ranges remain explicit, as does the authoritative-German
qualification in the English auditor's report.

These checks establish selected facts, source identity, extraction integrity and
bounded arithmetic. The seven offering inputs still yield five abstentions and
two conditional positives. They are not certified legal answers. The original
production reader and frozen 4 October candidate were preserved.

## Master-program operation

The runners retain numbered attempts, failed receipts, method/input snapshots,
source bindings and refreshed next-phase instructions. Supported deterministic
repairs execute through the relevant phase. New semantic or source-review repairs
are implemented and reviewed by the supervising coding agent; the driver then
invalidates and reruns dependent phases. It does not synthesize arbitrary repairs
from data or automatically close the remaining legal programme.

Use these read-only status commands from the repository checkout:

```text
python3 -m scripts.prospectus_basf status
python3 -m scripts.prospectus_refresh status
```

The current BASF continuation can resume stale phases with
`python3 -m scripts.prospectus_basf run`. Source and rendered-page review are
required when their bound inputs change. The next full German contract phase is
specified in [next-work-orders.json](../prospectus-basf-continuation-2026-10-05/next-work-orders.json);
it still requires implementation.

The source-retrieval ledger is 188 of 212 authorized requests, leaving 24.
The OCR round used the existing CPU PyMuPDF/MuPDF runtime and one official English
language-data download. The refresh and BASF rounds made no further source
requests. No additional executable or Python package was installed, and no paid
model or GPU run was used. Git fetch/push is separate from that retrieval ledger.

## Remaining programme

| Remaining gap | Next justified action |
| --- | --- |
| BASF operative contract | Construct continuous controlling German text, resolve nested options and filled fields, check cross-references, complete agreement/amendment and earlier/interim report scope, and resolve the incorporation discrepancy. |
| Deutsche and general semantics | Qualify remaining bilingual operative pages; repair actor, modality, antecedents, scope, negation, exceptions and conversion alternatives against independently checked source meanings. |
| Other issue dossiers and BES | Complete the retained Enel/Unilever/Lloyds/SEB/LVMH/BBVA work orders; resolve 29 BES dependencies and the duplicate risk-factor 1.17 precedence question. |
| Jurisdictions and actual facts | Admit exact dated primary sources and actual issuer, event, client, bank, calendar, rounding and settlement inputs. |
| Independent evaluation | Adjudicate the original 1,467 records/1,307 unique spans, assign the 25 review forms, freeze a genuinely unexposed cohort, and run paired evaluation. |
| Integration and acceptance | Integrate qualified inputs into an isolated successor reader, run end-to-end regression, and obtain scoped intended-use and human manuscript acceptance. |

The complete current list is [remaining-gaps.json](../prospectus-basf-continuation-2026-10-05/remaining-gaps.json).
Missing independent evidence blocks promotion; it does not invalidate the
completed engineering work or the next planned repairs.

## Delivery and preservation

The [reviewed delivery plan](../../plans/prospectus-delivery-2026-10-05.md)
requires ordinary commits and merges, incorporation of remote changes, normal
pushes and equal local/remote branch heads. Historical phase reports may say that
their work was uncommitted at execution time; those are preserved run records,
not the current Git delivery status.

The feature worktree must finish clean. The separate main worktree contains
pre-existing assurance work which remains outside this campaign's commit scope.
Its contents are checked before and after integration. Receipt-bound logs and
LaTeX support files are included even when global ignore rules would normally
hide them; unbound runtime locks and caches are excluded.

Engineering completion and Git delivery do not establish a complete contract,
general legal accuracy or production readiness.
