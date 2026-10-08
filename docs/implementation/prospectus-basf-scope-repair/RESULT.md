# BASF source-scope repair result

The constructor now applies 62 operations checked against the original BASF
prospectus and final terms. It corrects a substantive notice-selection error,
selects the supported issuer/clearing/currency/agent alternatives, and copies
twelve scalar occurrences from exact source substrings. All 1,578 original body
occurrences and every copied character are preserved. The selected text remains
a partial contract awaiting further source and independent legal review.

The final focused run is [run-003](run-003/manifest.json): 35 checks pass.
[Adoption verification attempt-006](../prospectus-adoption/verification/attempt-006/manifest.json)
passes 148 checks, verifies all seven current phases, and reuses all seven on
identical replay. A0 is attempt-009; A1–A6 are attempt-007. The installed package
loads the packaged review data outside the checkout and produces the exact A1
construction. The installed full-product digest is
`481bb13df030ba17de0ff6b555ed32a77221254fa62c103125376a04d50a3827`.

## What was wrong and what changed

The old notice rule matched “Clearing System” and selected the unlisted-securities
alternative alongside the Luxembourg-listed alternative. Base page 132 provides
a separate clearing-system paragraph **inside the listed alternative**, subject
to exchange rules. Final pages 7 and 13 select that configuration. The new
construction excludes the unlisted clause and preserves the listed clause's
qualification. This was our clause-selection error, not a package defect or a
failure to extract the printed words.

The review also distinguishes BASF SE from BASF Finance. It retains BASF SE's
successor guarantee condition while excluding the Finance-specific alternatives.
It retains the change-of-control right while excluding references to the
unselected specified-price holder put. NGN instructions disappear but their
partial-redemption provisions survive. The common ICMA definition and temporary
global-note certification remain intact.

Of the 62 rules, 23 select printed alternatives, five remove an inline instruction
while preserving its body, 22 exclude inapplicable alternatives, and twelve copy
values. Admission, raw text, source edition, occurrence, page membership,
geometry, visibility and instrument identity are checked before those operations
can be used. Changed or missing premises reject construction. These guards make
this particular reviewed construction reproducible; they do not generalize the
readings to other prospectuses.

| Decision | Primary criterion | Veto checks | Main uncertainty | Next action and limit |
|---|---|---|---|---|
| Apply the reviewed operations | Exact source/premise bindings and source-character conservation pass | Wrong issuer/instrument, changed text/geometry, missing/duplicate/added units and altered selections reject | Implementer reading has no independent adjudication | Keep this source-specific construction; do not claim a complete German contract |
| Correct the notice branch | Listed configuration retains exchange-rule condition; unlisted alternative removed | Wrong-scope wording absent; exact printed governing margin retained in evidence | Actual current listing and delivered notices are unobserved | Use the issue configuration only; obtain event facts for an actual-notice question |
| Use packaged data | Installed constructor equals A1 exactly | Import location and every packaged source/resource hash checked | Native reads remain outside capability enforcement | Retain broad hashes; no hermetic-execution claim |
| Continue source completion | Every original body interval remains accounted for | No silent deletion or legal acceptance | Numbering, office, margins, prose and incorporated documents remain open | Follow the specific repairs below; counts do not establish completeness |

No stochastic method ranking is claimed. These are deterministic construction
and mutation checks on an exposed development instrument. The 83-to-19 bracket
change and 1,008-to-545 interval change explain the effect of the operations;
they are not acceptance thresholds.

## Remaining work

The 19 brackets comprise 14 numbering/cross-reference occurrences, four spare
call-table cells and the combined calculation-agent name/office field. The final
terms name NatWest Markets N.V. but do not provide the designated office. The
545 unresolved interval records comprise 23 retained-branch spans and 522
margin/header spans (496 margins and 26 headers). Reviewed governing relations
are recorded with operations; this run does not mark the entire margin inventory
reviewed.

A prose diagnostic also finds two successive `jeweils ein "Zinszahlungstag"`
phrases near the interest clause. Original base page 111 places the second phrase
beside the different-rate table. Its exact scope/order needs a separate repair;
it falls outside the retained-bracket count. The conflicting 195–209 and 209–290
incorporation ranges also remain unresolved. [NEXT-PROGRAM.md](NEXT-PROGRAM.md)
sets out the next discriminating work.

## Failures, limits and preserved evidence

Run-001 had 32 passes and two wrong test expectations. The original page says
`vom`, not `ab dem`; the spare call-table cells are empty brackets, not repeated
named placeholders. Correcting the oracle produced run-002's 34 passes. A final
code review then added the graph-level instrument guard; run-003 passes 35.
All failed and successful attempts remain intact.

The strongest alternative explanation for apparent completeness is shared
implementer assumptions about scope. A source-backed counterexample can still
overturn one of these readings. The known duplicate phrase already demonstrates
why bracket counts alone are insufficient. Nothing here rejects the research
direction or establishes a fundamental Docling, INCEpTION, ACTUS or CDM defect.
The previous integration trials remain historical after this source change;
the affected adoption checks were refreshed, while unchanged live authoring was
not repeated.

The [plan](../../plans/prospectus-basf-scope-repair-2026-10-08.md),
[page review](source-review-001/REVIEW.md), manifests, exact commands, original
images, source maps, candidate text and refreshed next-phase records preserve
the result. Runs were local and CPU only, with GPU devices intentionally hidden
in relevant subprocesses. No new install, network call or permission prompt was
needed. The LaTeX account was rebuilt and visually reviewed; its source and PDF
hashes are in [the document record](document-review/build-manifest.json).
