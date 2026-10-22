# BES English/Portuguese OCR diagnostic, 12 October 2026

## Intent and evidence contract

Question: does a pinned Portuguese model recover the observed accent/code
failures of the English-only profile on the four retained report pages, without
losing any previously matching critical span or changing native extraction?
Candidate profiles are `eng+por` and `por+eng`. Their exact comparator is the
current `eng` model and the retained four-page worker output from
`coverage-expansion/attempt-001/ocr/`. The fixed oracle is retrospective v2 in
`coverage-expansion/review-repair-001/prepare/oracle-v2.json`; v1 and its original
20/25 result remain preserved. No oracle is adapted to these new outputs.

All three profiles use the existing product worker and the real
`service.source_product` interface, 300 dpi, identical PDF bytes, original page
numbers, rendering, runtime, language-model bytes and native extraction. The
source consumer covers the two full original PDFs, adding OCR only at 2009
176–177 and 2010 88–89. It is P1 evidence, not a repeat of the legal-answer
consumer or a replacement of its supplied corrections.

A candidate passes the local nomination screen only if (a) the 21 known raw
matching v2 spans remain matched in worker text and source-product units, (b)
at least one of the three identified transcription failures (issuer accent,
committee-member accent or AA1000APS) is recovered, (c) native units are
identical and (d) every original source/page/model/image binding is verified.
The negative-assurance reading-order failure is measured separately. It cannot
be hidden by ignoring punctuation, accent-folding or silently dropping sidebar
words. Unicode NFC and whitespace normalization are the only matching changes.

Source/method/model drift, wrong baseline reproduction, changed native units,
invalid product or missing image verification are continuation vetoes. A
candidate's lost critical span or lack of recovered mismatch blocks nomination
but does not stop the other predeclared profile. Raw span match counts, false
footer text, wall time and page unit counts are explanatory diagnostics. No
profile ranking, new default, multilingual accuracy, whole-report completeness,
source authenticity, native confinement or legal acceptance follows. Results
are deterministic case diagnostics; no stochastic superiority claim applies.

## Defaults, provenance and skeptical audit

The current English model SHA is
`7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2`.
The Portuguese fast model comes from the official `tesseract-ocr/tessdata_fast`
repository at commit `923915d4ced2a7235221788285785a29c4a42d4a`; SHA is
`c4932b937207a9514b7514d518b931a99938c02a28a5a5a553f8599ed58b7deb`.
The API response, response headers, exact URL, fetched bytes and repository
README are retained in `language-profile/acquisition-001/`. The README calls
these integer trained models; it does not prove suitability or comparative
quality for this source. This is an optional configuration experiment, not a
package installation or new production default.

The Portuguese model is a plausible language hypothesis because the inspected
source includes Portuguese names. It can also harm English text. Retain both
language orders rather than assume order is immaterial; neither is promoted
in advance. The first cheap check must reproduce the original English worker
pages exactly before a model-comparison verdict is interpreted. Baseline
native extraction is the actual product mode, not a mock. Image, model and
source identities are checked through the existing retained-hybrid consumer.
Every candidate must preserve matched critical facts, not merely raise an
average score. Sidebars and footer artifacts may remain even if accents improve.

Audit verdict: PASS for three bounded diagnostic arms. The thresholds nominate
an optional profile on known pages only. They do not certify a default, legal
answer or package. Our previous oracle mistake is a reason for preserving v1
and binding enlarged-image-reviewed v2, not for scoring against changing text.
All inherited settings are comparator hypotheses and remain unchanged.

## Execution, stop and refresh

Run once from the prospectus worktree:

```text
timeout 600 .venv/bin/python docs/implementation/prospectus-integration-closure/bes-original-acquisition/compare_language_profiles.py
```

`CUDA_VISIBLE_DEVICES=-1` and `OMP_THREAD_LIMIT=1` are set before imports.
The existing `/home/chakwong/miniconda3/envs/tfgpu/bin/python` executes the OCR
worker deliberately on CPU. A private tessdata folder copies the pinned English
and Portuguese bytes; no global environment changes. Each arm retains fresh
worker JSON, raw text, product summary, all span matches/mismatches and hashes.
The top-level start/manifest records baseline commit, actual dirty method bytes,
exact command/environment, source data, deterministic seed status, elapsed
time and output paths at `language-profile/attempt-001/`.

After each arm, retain its result and refresh the next-profile reason; a
candidate rejection continues to the next predeclared language order. An invalid
harness stops and retains the failure. After all arms, review losses and gains
by exact span, distinguish configuration from layout errors, update the result
and next plan, and retain the no-default/no-legal-promotion boundary. If neither
candidate passes, keep the English baseline with supplied corrections and
identify the next discriminating crop/layout or model-family experiment.
