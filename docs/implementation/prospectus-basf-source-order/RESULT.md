# BASF source-order repair result

Five source-reviewed ordering corrections pass against the retained BASF base
prospectus. The constructor now preserves the printed order of three prose rows
and two Fiscal Agent label/address blocks. Every one of the 1,578 body occurrences
retains its exact source text. The Canadian-agent exclusion consumes its entire
label and placeholder; the German-agent address remains in the candidate.

The source review and original page images are in
[source-review-001/review.json](source-review-001/review.json). The plan and
skeptical audits preceded implementation; the failed first tests remain in
`focused-001/`. [run-001/manifest.json](run-001/manifest.json) binds the command,
method, source edition, original images, interpreter, CPU mode and comparison.

| Decision | Primary criterion | Veto diagnostics | Main uncertainty | Next justified action | Not established |
|---|---|---|---|---|---|
| Accept five ordering corrections in the pinned constructor | Exact source-reviewed order; all body occurrences and raw characters preserved | 12 focused tests pass, including stale text/geometry/edition, missing/duplicated/intruding occurrences, complete table exclusion and source-map replay | Other rows retain the previous unreviewed geometry order | Continue full source and margin review, beginning with issuer-specific branches and nested instructions | General PDF reading-order accuracy or a complete German contract |
| Accept downstream engineering verification | 125 regressions, installed checks, all seven phases and identical replay pass | No failed test, stale phase or accepted legal release; common Actual/Actual definition retained | Source-derived meaning, incorporation and authentic legal review remain absent | Admit changed source-backed decisions and rerun affected phases | Legal interpretation or permission to transact |
| Keep Docling rejected | Existing exact-map criterion remains binding | 14 of 53 critical lines still fail exact mapping in current A3 | Two exposed development pages | Retain existing extractor and repair specific evidenced source defects | Parser superiority or population performance |

The defect arose before bracket parsing. Bold words can have a higher top edge
than adjacent regular words on the same printed baseline. On pages 120 and 121,
the old sort moved `[Falls` ahead of `des betreffenden Clearing Systems
ausgewählt.`. On page 111, it similarly moved the closing-coupon placeholder.
Page 124 required complete label/address-cell order; a row-only exchange would
still interleave the columns. The initial diagnostic's 0.25-point bottom-edge
tolerance only nominated rows for inspection and is not an extractor default.
The runtime applies explicit permutations after checking the complete old spans'
text, edition, geometry and occurrence identities.

The first tests found two follow-on issues. The source repeats the NGN sentence
outside the two corrected pages, so the regression now checks exact page
occurrences. Correcting the German Fiscal Agent label also made the old Canadian
deletion regex ambiguous. The constructor retained that ambiguity; the repair
qualifies the rule with the full Canadian placeholder. No match-count criterion
was weakened, and no unseen source occurrence is treated as reviewed.

Current A1 reports 1,008 unresolved intervals and 83 brackets, compared with
1,018/83 in historical A1 attempt-004. The interval-count change reflects
ordering and branch boundaries; it is not ten new legal decisions. Zero
unaccounted intervals was already true of the defective baseline. Exact coverage
and faithful reading order therefore remain separate checks.

`python3 -m scripts.prospectus_basf_source_order` completed in 8.51 seconds and
passed 12 deterministic source regressions. The full
`python3 -m scripts.verify_prospectus_adoption` result is
[verification attempt-003](../prospectus-adoption/verification/attempt-003/manifest.json):
125 tests passed, A0 attempt-007 and A1–A6 attempt-005 executed, all seven receipts
were reused on identical replay, and all were current afterward. Its execution,
regression, replay and status took 108.93, 9.28, 35.43 and 5.29 seconds respectively.
These timings are descriptive. CPU mode was deliberate; no GPU, download or paid
service was used. The passed INCEpTION server trial was not repeated.

Post-run red-team judgment: the repair is correct for the five inspected spans,
but other geometry choices or legal attachments could still be wrong. The
strongest alternative explanation for broader apparent success is shared
implementer assumptions. A source image contradicting a permutation, or a lost
occurrence in the installed result, would reopen this repair. A passing suite
cannot resolve the remaining 1,008 intervals, 83 brackets, 289 printed-page
labels, incorporated agreements, financial conventions or independent readings.
The engineering correction remains viable; legal release remains unaccepted.

The refreshed [next program](../prospectus-adoption/NEXT-PROGRAM.md) continues
source completeness, faithful interpretation, actual coupon premises, annotation
authoring/authentication, independent evaluation and dated event facts. The
controller's new next-phase and repair records bind the current receipts.
Historical attempts and the 250 existing snapshot reconstruction records remain
unchanged; no new ignored snapshot or stale reconstruction source was found.

The LaTeX chapter and PDFs now explain this correction. Build-003 passed with
390 monograph pages, 90 companion pages and 319 checked citation occurrences.
[DOCUMENT-REVIEW.md](DOCUMENT-REVIEW.md) records the final inspection of physical
pages 95–98 and its four separate findings on comprehension, mathematics, source
fidelity and rendering. Human readability acceptance remains pending.
