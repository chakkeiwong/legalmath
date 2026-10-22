# Explain the statement content affected by BASF incorporation ambiguity

The current BASF answer preserves 92-page and 94-page incorporation readings,
but identifies the difference only as annual-report pages 204 and 208. The
implementation in successor/basf_incorporation.py explicitly marks their
financial values unvalidated. The retained original page 204 contains an
18-row, two-year statement of comprehensive income. Its extraction order is
nonmonotone: some numbers precede their labels, and lower-row labels follow
several numeric rows. Adjacent text order is an unsafe cell-association rule.

Question: can an optional, supplied complete-page reading preserve all 36
printed cells, row/column associations, signs, units and qualifications, and
show how the existing two incorporation readings affect this page's inclusion?
This closes a concrete scope-to-content explanation gap for one disputed page.
It does not adjudicate incorporation or claim that the same information is
absent from every other incorporated page.

Baseline: the exact complete candidate answer and products retained by
basf-meanings/attempt-011. Reconstruct its P1/P2 only from its saved common
request, original graph and payload; compare the resulting product headers
with its saved headers before using them. Reuse its sealed P3/P4/P5. Reconsume
the ordinary answer and require exact equality. Do not silently fall back to
the older incorporation001 answer if the current baseline does not reproduce.

Candidate: a separate optional BASF comprehensive-income review. Bind the
original PDF, the retained inspected page204 image, complete source graph and
every page204 occurrence. Supply exact title/entity/unit/year/row/footnote
associations; validate cell-to-row vertical overlap, cell-to-year column overlap
and distinct ordered columns. Retain all 65 visible source occurrences exactly
once across page metadata, headings, labels, values and footnotes. This is
exposed supplied reading with geometric checks, not automatic table discovery
or independent financial validation. Page208 remains explicitly unreviewed.

Parse only the inspected integer-million notation: signed integers, correctly
grouped thousands and the standalone printed dash. Preserve each literal; a
dash stays unknown and must never become zero. Record exact arithmetic
differences between printed subtotals and their supplied constituents. Preserve
the report's page6 rounding warning (complete lines8–10), which may explain a
difference but does not prove a rounding model or justify adjusting a number.
Do not infer fraud, accounting error or extraction error from a one-million
displayed residual. Do not use an assumed rounding tolerance as promotion.

Research intent and evidence contract: the mechanism under test is source-bound
row/column reading attached to the existing unresolved incorporation review.
Primary pass requires exact current baseline reproduction, all36 cells and65
occurrences accounted for, correct2022/2021 association and negative signs,
unknown dash retained, both conditional source scopes shown, and ordinary
Q1–Q6 unchanged. Actual adverse controls must reject swapped years/cells,
cross-row association, sign loss, omitted/duplicated cells, altered unit/source/
image, omitted footnote and claimed legal selection. Arithmetic differences
are explanatory diagnostics only. Corrupt source or comparator, altered-input
acceptance, missing original occurrences or changed ordinary answer veto the
candidate and trigger one bounded local repair. Invalid comparator or exhausted
time/repair/storage bounds stops this package while independent work continues.

Default/assumption audit: the existing original page image and native boxes are
provenance, not independent truth; inspect the image and compare all rows before
promotion. Positive geometric overlap is a necessary consistency check rather
than a learned tolerance. Exposed row names and subtotal groupings are supplied
associations; record them in the profile and never describe arithmetic agreement
as proof of their semantics. Exact decimal-integer arithmetic avoids binary
rounding; no financial default or payment calculation changes. The page6
warning is contextual source evidence outside both proposed incorporated sets,
not a newly incorporated clause. Source authenticity, German-original priority
and governing legal scope remain unresolved.

Skeptical audit: PASS for the narrow conditional statement-content explanation.
It uses the latest retained BASF answer, supplies whole-page rather than selected
positive cells, and distinguishes literal accounting from legal admissibility.
The negative cases address actual row-order and sign/dash failure modes. The
page can pass all checks while its legal incorporation remains unresolved; that
is retained in the result. Missing page208 and independent readings prevent a
whole-statement or task-completion claim. No package limitation can be inferred
from this exposed reading alone.

Use the existing second basf-incorporation admission; no allowance extension.
Stages prepare,profile,baseline,compare,controls,tests, then seal/record/refresh.
At most120seconds per stage and350MiB new evidence, one local implementation
repair, zero native/OCR/HTTP/install/GPU/model calls. Keep native77/source HTTP9
historical lower bounds. Use `.venv/bin/python -m scripts.prospectus_basf_statement`
with one-second yields and retained sessions. The new optional path's installed
evaluation is separate and remains explicit if not performed in this package.

Retain all original supplied profile data, complete full answer/optional result,
all changed adverse inputs and actual errors, source/method identities, focused
tests, exact commands and timing in basf-incorporation/attempt-002. Record the
post-run alternative explanation and next justified source work before refresh.
