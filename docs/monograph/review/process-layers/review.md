# The process guide now follows the full transaction investigation

Completed 29 September 2026 under the
[reviewed plan](../../../plans/process-guide-compliance-layers.md).

The [standalone guide](../../process-guide.pdf) now contains **18 pages and
20 flowcharts**. It appears on physical pages 4–21 of the **337-page monograph**.
The technical companion remains **78 pages**. The eight-step overview now leads
from retained documents to a qualified transaction assessment and reassessment.
The source title and exporter agree on “From source documents to transaction
decisions.”

The main additions are the seven-layer assessment on guide page 3, the paired
CoCo walkthrough on pages 4–5, the shared-model/target split on page 9, and
assessment, lifecycle and repair/refresh charts on pages 15–17. Interpretation,
bounded search, source extraction, formal checking and the separate Stipula
research route remain explained in the same guide.

## Implementation and evidence audit

| Guide pages | What the chart explains | Inspected implementation or retained evidence | Boundary retained |
| --- | --- | --- | --- |
| 2–3, 15 | Eight software steps and seven assessment categories; scope, sanctions, bank, client, product, policy, operations | `transaction/catalog.py`, `engine.py`, integrated implementation guide | Fourteen obligations, five conditional rule models, nine missing families/coverage entries; supporting calculations give eleven models. No complete-law discovery claim. |
| 4–5 | Same synthetic purchaser, two dated original CoCo offerings, opposite purchaser conditions, common bank gaps | `prospectus/purchaser_cases.py`, `docs/prospectus/coco-cases/`, retained attempt-002 result and monograph §2.4.5 | Barclays passes only the selected condition; Standard Chartered fails the declared original route. Both bank receipts remain qualified and prohibit execution. The supplementary route result does not close `product.other`. |
| 5–6 | Issuer law, regulatory write-down, sanctions sources, account and booking scope | Monograph §§2.3–2.4, transaction source registry and implementation guide | The Swiss survey is not universal executable issuer-law coverage or a rule for UK issues. Identity, effective dates and capacity require evidence. State ownership and absent name matches do not establish sanctions consequences. |
| 6–8, 18 | Source extraction, alternative interpretations, bounded investigation and complete accounting of declared source units | Existing process source, monograph chapters 5–6 and continuing-investigation records | The paired CoCo campaign uses retained proposals; it did not conduct a fresh whole-prospectus model investigation. Exhausted work and unexamined meaning remain unresolved. |
| 9–11 | Shared frontend and typed model, RuleIR/Java and direct native Catala, same declared input profile | `translation` implementation account, `transaction/native.py`, CoCo runner and retained native results | Native Catala need not lower through RuleIR. Capability failure and unknown/conflicting/expired inputs remain explicit. No backend ranking. |
| 12–14 | Independent formal relation, Z3 comparison, narrow Lean preservation, native execution, mutations and bound evidence | Paired result, formal checker and assurance chapters | 512 Boolean assignments, six detected mutations, 157 executions per target, including 19 abstentions each. Formal/source/runtime checks prove different things; none proves the English interpretation or whole compiler. |
| 16 | Changes invalidate current assessments; distinct sourced duties and bounded calendars | `transaction/lifecycle.py`, implementation guide | Replay records events rather than executing trades, blocking assets or sending reports. A completion record does not prove performance; current qualified receipts never permit settlement. |
| 17 | Failed attempts, executed repair, validated phase reuse and refreshed next-phase plan; frozen future observations | Both master-program descriptions and retained attempt records; transaction observation mechanism | A runner records a repair request; code repair must actually be executed. Engineering success does not clear a transaction. There are no real prospective observations in the bank series. |

Technology prerequisites are introduced before their charts. QIB is explained
as an institutional/account category, Regulation S as a separate offshore
distribution route, and the shared frontend as the stage before target
selection. The previously unexplained STR acronym is spelled out. A bank's
QIB status cannot silently replace its client's status.

## Corrections to the old guide

The old RuleIR-first chart has been replaced by the actual shared model and
separate translators. The Java-only execution picture has been replaced by
the two targets and independent formal consequences. The general interpretation
workflow remains distinct from what the retained CoCo run actually executed.

The old bank-approval and hidden-human-reference quality route is absent from
the current workflow. The controlling requirement is a checked proposition or
explicit qualification, with no human answer labels or model consensus as a
quality authority. Institutional authorizations remain possible business facts.
Historical research proposals in the main chapters are preserved; they were
not silently rewritten as current product requirements.

The narrow Boolean certificate explanation was relocated from the execution
page to the proof page, retaining its exclusions for arithmetic, dates, full
histories and English meaning. The mutation illustration now uses a QIB bank
and a non-QIB client, connecting the test to the running case. The original
gift/discount interpretation example and Stipula reproducibility limitations
remain. No equation, derivation, citation or chapter was removed.

## Build, rendered review and preservation

Executed from the repository root:

```sh
python3 scripts/build_reader_facing_monograph.py
```

The command built both PDFs, settled cross-document references, ran the normal
document checker, refreshed the proposal aliases and exported the standalone
guide. The final checker reports **PASS**, no errors, **133 archived citation
documents**, **288 citation occurrences** and **207 retained original source-unit
labels**. Citation contexts are byte-identical to the immediate baseline.

All 18 final guide pages were rendered and inspected. Three initial paragraph
spills onto almost-empty pages were repaired by tightening repeated prose and
diagram spacing, without reducing the font. The last wording changes on pages
5, 8 and 14 were rebuilt and inspected again. No text or arrow overlaps, clipped
labels, accidental blank pages or unresolved references were found. This is
executor inspection of the document, not a human quality score or a claim that
readability has been independently proved.

The [machine record](document-review.json) verifies:

- all 18 standalone pages match the corresponding monograph pages in extracted
  text and rendered pixels;
- all **32 guide links** have valid destinations: 15 within the guide and 17
  to the monograph or companion;
- the expanded monograph before and after the guide is unchanged from the
  immediate working baseline;
- every prior guide label survives, citation contexts are unchanged, and all
  six protected baseline files still match their recorded hashes.

The baseline is the user's existing dirty checkout, preserved under
[`baseline/`](baseline/), not the much older committed guide. No application
code, source evidence or campaign result was changed. The exporter changed only
its title lookup and PDF title. No new legal inference experiment or compiler
benchmark was run for this documentation task.

The strongest remaining risk is reading the scope diagram as a completed
implementation of every law named in it. The adjacent captions and worked
outcomes explicitly retain the nine unresolved inventory entries, the missing
bank facts and the limited purchaser result. New sources or private bank
documents may change future assessments; these charts do not pre-approve them.
