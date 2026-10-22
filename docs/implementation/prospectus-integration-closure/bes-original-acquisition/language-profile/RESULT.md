# Pinned bilingual OCR diagnostics, 12 October 2026

Both official-model language orders, `eng+por` and `por+eng`, passed two bounded
**known-case** source-product screens. On the four newly recovered pages each
matched 24/25 strict critical spans, compared with English 21/25. Both recovered
the inspected issuer accent, committee-member accent and AA1000APS identifier,
with no loss among the 21 English matches. On six earlier audit pages each
matched 16/18, compared with English 15/18. Both recovered the 2009 consolidated
opinion span and lost none of the 15 prior matches. The source-product results
match the worker's span results, preserve native units and verify source/page/
image/model identities. Neither bilingual order is ranked above the other.

The negative-assurance body phrase remains broken by sidebar reading order under
all profiles. The English model reads the 2009 printed footer as “§ 176”; both
bilingual orders read “5 176”, which removes that exact false-reference trigger
but does not establish general footer safety. The retained one-occurrence HEADER
disposition remains necessary for the current English-source consumer. The
current eleven-document consumer and default English model were not changed.

The legacy-audit attempt's `prior_2009_raw_pages_unchanged: false` field compares
whole page dictionaries. The old staged page includes `image`, `printed_page`
and `status`, while the fresh worker adds `disposition`; that is why the field
is false even for the English baseline. The attempt independently required
exact equality of source page, image SHA, raw text and OCR words, and passed it
for English. The field must **not** be read as evidence that English old raw
occurrences changed. It does not prove that bilingual word occurrences are
identical; they are expected to differ. Preserve the original output and use
this review to correct the interpretation. A future metric should compare
the canonical raw fields by identity rather than wrapper metadata.

## Evidence and decisions

| Decision | Primary screen | Veto diagnostics | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| English comparator valid | Exact raw worker reproduction; four-page 21/25 and legacy 15/18 reproduced | Original/image/model identity and native extraction pass | Known-case oracle limitations | Keep current consumer as baseline | English is optimal |
| `eng+por` locally viable | Four-page 24/25 and legacy 16/18; no prior span lost | Actual P1 source product, native and image checks pass | Other page/language families and source-specific readings | Test on a broader frozen mixed-layout cohort before optional adoption | New default or package superiority |
| `por+eng` locally viable | Same strict outcomes | Same | Relative model order has no discriminating evidence here | Treat as statistically/empirically indistinguishable on current cases | Preferred order |
| Keep automatic reading order open | Negative assurance remains unmatched in raw text | No hidden accent/whitespace relaxation | Sidebar and multi-column layouts | Run bounded layout diagnostic; retain assisted ordered source anchors | Automatic legal reading |
| Preserve historical eleven-document result | All prior units and legal statuses remain bound to English OCR | New profiles were not silently injected into prior request | A production bilingual selection could change old raw units/hashes | Design per-page profile and rebind/review downstream packets if wider evidence justifies it | Source-complete legal answer |

These are deterministic known-case diagnostics, not a stochastic ranking. The
hard validity screens passed for all three profiles. Continuous match-count
differences are descriptive and have no uncertainty interval or independent
holdout. Both bilingual candidates remain viable under their declared local
screens; no ranking or default-readiness is established. A larger frozen cohort
with multilingual names, numbers, tables, sidebars and negative controls, then
actual full downstream service validation, would be needed for a default claim.

The official Portuguese model is retained at `acquisition-001/por.traineddata`
with an official repository commit, original URL, response headers, README,
SHA-256 and manifest. No system-wide model or package was installed. The two
plans are `docs/plans/prospectus-bes-language-profile-2026-10-12.md` and
`docs/plans/prospectus-bes-legacy-audit-language-check-2026-10-12.md`.
The exact commands, CPU environment, baseline commit, dirty method hashes,
source/model identities, deterministic seed status, wall times, complete raw
worker outputs, actual P1 products, per-span results and manifests are in
`attempt-001/` and `legacy-audit-001/`. The three four-page arms took 18.229,
19.671 and 20.622 seconds; the six-page arms took 27.016, 30.615 and 31.099
seconds. Both programs left the default and legal answer unchanged.

The strongest alternative explanation is source-specific overfitting: adding
Portuguese helps these BES names but may harm other English pages or codes.
No losses among the 36 previously matching spans across these two known
families weakens, but does not rule out, that explanation. A broader
predeclared test could overturn the local nomination. The current evidence
does not establish a fundamental defect in Tesseract. Language configuration
accounts for the three recovered four-page checks and the recovered 2009
opinion. The 2008 p246/p248 opinion failures remain accent-only (“Espírito”
read as “Espirito”) under both bilingual orders.
