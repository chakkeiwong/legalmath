# Preference-dividend adjustment explains the 2008 EPS comparison

The original 2008 and later comparative EPS differ because the later note
adjusts the numerator for preference dividends while retaining the same 2008
weighted outstanding-share count. Both original 2008 editions show
402,284 thousand euros divided by 497,302 thousand shares: exactly 326/403,
or 0.808933... euros per share, displayed as 0.81. The 2009 report's 2008
comparative uses 368,804/497,302, or 0.741609... euros per share, displayed
as 0.74. Its footnote explicitly states that profit is adjusted for preference
dividends. The numerator reduction of 33,480 thousand euros matches the
preference dividend in the retained primary statements.

The same source-backed bridge holds for 2009: Bank-holder profit of 522,114
less 33,480 gives the EPS numerator 488,634. Dividing by 998,174 thousand
outstanding shares gives 0.489527... euros per share, displayed as 0.49.
For 2007, both original editions show 607,069/495,910 = 1.224151..., displayed
as 1.22. All six source ratios match the named two-decimal HALF_UP diagnostic;
all six gross-minus-treasury share calculations agree. This is a display
consistency check, not proof of the reports' unstated rounding policy.

The two 2008 editions agree at all ten numerical EPS-note positions. The
Portuguese note uses decimal commas, unlike the dots printed in its primary
income statement. All three notes state that SIBA plans have no dilutive
effect and therefore diluted EPS equals basic EPS. This does not establish
absence of potential shares or nondilution in future periods. Thousands of
euros divided by thousands of shares gives euros per share with no extra
factor of 1000. The exact unrounded 2008 ratio difference is 540/8021; the
displayed 0.07 difference is rounded, not exact.

All five original images are legible and were inspected. The complete three
Note 14 readings contain 81 occurrences; all 405 page occurrences and 69
earlier statement occurrences are retained. Physical page 112 of the 2009
report is printed page 111. Document identity excludes the unrelated
prospectus page 112. The 2008 note's full numerator and absence of the later
preference footnote remain recorded rather than overwritten.

This closes the previously unanswered source explanation for 0.81 versus
0.74. It does not decide why the reporting treatment changed, compliance with
IAS 33, an official correction, controlling edition or financial validity.
The 5.58% rate relates to BES Finance preference shares, not the prospectus
note coupon. The intangible-asset contradiction, other classification
differences and Note 46 amount conflict remain unresolved. All 14 original
dependencies remain UNRESOLVED and Q3 remains PARTIAL.

The complete prior answer was composed in memory with the new EPS reading;
every earlier field was verified unchanged. `answer-composition.json` records
the exact baseline and small `answer-overlay.json.gz`, their file/content
hashes, the merge rule and the complete composed-answer hash. No large answer
was copied. All 32 freshly pinned adverse readings were actually refused for
their expected semantic reasons. All 441 production files and protected
historical evidence remain unchanged; 005's FAIL/REJECT remains intact.

| Decision | Primary criterion | Veto diagnostics | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain the source-backed EPS explanation | Five inspected images, all 81 note occurrences, both numerator bridges and complete prior answer preservation pass | 32 actual semantic refusals pass; no source/production drift; cumulative limits satisfied | Reporting-change rationale, accounting authority and independent acceptance | Record/refresh and inspect the separate 122,516-thousand-euro asset-classification difference through original Notes 24 and 28 | Automatic discovery/integration, IAS 33 compliance, legal entitlement, package defect or completed source07 |

The seven pre-seal stages consumed 21.11696218093857 seconds, plus
894.5421627317555 historical seconds, giving 915.6591249126941 seconds before
seal. Draft preparation is retained separately in `draft-diagnostic.json`.
After controls, storage measured 167,174,963 bytes combined and 2,085,748 new
bytes, below the original 160 MiB combined ceiling and 2300 KiB new allowance
with the declared reserves. Final seal runtime and inventory are in
`result.json` and `outputs.json`. Five PNG images occupy 1,049,786 bytes and
all 32 compressed adverse inputs occupy 133,624 bytes.

The actual stage commands used `timeout 55 .venv/bin/python -m
scripts.prospectus_2008_eps` followed by prepare, render-en, render-pt,
render-2009, profile, answer, controls and seal. Per-stage manifests retain
the exact command, interpreter, source identities, plan/result paths, time and
commit e8beb52b13399f18bbbff9aecea9636803729d5f. Exactly three bounded pdftoppm
children rendered the five pages. Work was deterministic CPU-only, with GPU
devices intentionally hidden and no applicable random seeds. No text
extraction, OCR, network, model, GPU, installation or production edit occurred.

Post-run review: the explanation is supported by explicit source wording,
independently located primary-statement amounts and exact arithmetic. It
remains an agent-supplied reading; finite controls do not constitute an
independent accounting judgment. A contrary authoritative source or a
demonstrated mapping error could alter the interpretation. The current
evidence supports a numerator explanation for this particular difference and
does not justify normalizing other source disagreements. No package candidate
is rejected or ranked by this source comparison.
