# Prospectus adoption and validation program

Status: reviewed implementation/trial specification, **not executed**.
Baseline: `a05e18bbdeefbf278d29a6755e274124f97bda35` on
`feature/prospectus-evidence-master`.
Evidence: [survey](../research/prospectus-adoption-2026-10-07/SURVEY.md).
This program extends the ordered repair; it does not reset historical receipts
or turn the current partial results into acceptance.

## Research intent and pre-execution audit

Question: can explicit source dispositions, better structure, bounded constraint
reasoning and independent checks close the observed prospectus gaps without
introducing silent legal or financial defaults?

Candidate mechanism: retain the current service and add small checked adapters.
Expected failures: missing shared definitions, source-map shifts, omitted remote
exceptions, wrong editions, implicit conventions and undeclared dependencies.
The existing installed-product path is the baseline; current manually corrected
inputs and automatic extraction are separate comparison arms.

Promotion requires the substantive invariants and case-specific expected results
below, followed by independent acceptance for the frozen scope. Zero critical
errors on a finite development set is a necessary engineering check, not an
estimate of population error. Parser scores, test counts, bracket counts,
throughput and reviewer agreement alone are explanatory diagnostics.

Promotion vetoes: an unaccounted governing occurrence; wrong known answer or
silent missing-fact default; broken source identity; unreviewed financial
convention; unsupported priority; input leakage into acceptance labels; or
unresolved actual-event/independence requirements for a release claim.
Continuation vetoes: corrupted sources or comparator, invalid evaluation design,
unexpected paid/model execution, or an exhausted declared resource budget.
Candidate failure normally triggers its named repair or fallback and does not
veto independent later engineering work. Never turn a failed candidate into
rejection of the prospectus program without identifying which premise failed.

Skeptical review: PASS for this implementation sequence after the following
corrections. Individual new benchmarks still need their fully bound run plan.

- Start from the committed repair, not the historical defect assertions or
  broad test count. Preserve the final BASF margin correction.
- Keep reviewed-input and automatic-input arms comparable; do not credit a
  parser for improvements made by manually changing legal labels.
- Check the source-map and complete page scope before comparing downstream
  accuracy. Generic benchmark ignore rules cannot discard governing margins.
- Treat package availability and installed API inspection as feasibility evidence,
  not accuracy. Pin release, model weights, export format and documentation
  together; current INCEpTION code and the v38 guide are different versions.
- Extend Boolean semantics conservatively. Z3 `unknown`, conflicting premises
  and unsupported recursion must not be collapsed to false or to success.
- Observe actual reads before reducing broad invalidation. A narrowed hand-written
  list could hide a dependency and make a stale result look current.
- Do not buy, install or migrate tools solely to make a phase look completed.
  Failure to preserve source meaning sends the work back to the relevant adapter.
- Each phase writes a result, an explicit repair disposition, and a refreshed next
  phase plan. A current receipt never means legal acceptance.

## Defaults and assumptions

| Choice | Provenance and justification | Failure mode | Earliest diagnostic | Status |
|---|---|---|---|---|
| Current Poppler/retained PyMuPDF path | Working baseline and immutable OCR receipts | English OCR misses Portuguese/German or wrong reading order | Compare raw and reviewed words/boxes on the named pages | Baseline |
| Z3 4.16.0.0; Hypothesis 6.151.9 | Already pinned dependencies | New adapter changes conflict/unknown handling; generator misses intended cases | Small truth tables; mandatory named mutants independent of random generation | Reviewed for feasibility only |
| QuantLib v1.38 | Schedule/day-count/calendar code inspected | Old version or convenience fallback appears authoritative | Explicit schedule plus a case whose ISDA/ICMA results differ | Comparator hypothesis |
| Docling | Prior technical report and source inspection | Normalization breaks provenance; layout confidence hides a missed margin | One BASF shared-definition round trip before a larger cohort | Candidate hypothesis |
| INCEpTION release/export | Technical paper, v38 guide and later source slice | Version mismatch, UTF-16 offsets, loss of evidence groups | Pin matched release; supplementary-character and discontinuity round trip | Unresolved version choice before trial |
| Named corner cases | Observed defects and retained documents | Development overfitting and family leakage | Freeze issuer/template/amendment group identities | Development set only |
| Two independent first readings plus adjudication | Practical starting workflow, not a statistical power calculation | Shared explanations or correlated expertise biases labels | Blind protocol and exposure records before opening predictions | Study-design hypothesis |
| Exact dates/amounts; no critical source loss | Legal source and deterministic arithmetic obligations | An approximate tolerance excuses wrong entitlement | Independently derived boundary examples | Primary engineering criterion |

For floating point comparisons, derive an error tolerance from each calculation's
scale and rounding quantum before running; do not inherit an upstream test
tolerance as a legal threshold. For stochastic model comparisons, predeclare
family-level sampling and uncertainty analysis. Until then report paired cases
descriptively without ranking viable parsers or claiming a new default.

## Ordered work and acceptance obligations

### A0 — Freeze the development slice and the question

Create a new input manifest under `docs/implementation/prospectus-adoption/` with
source hashes, PDF indices versus printed page labels, raw units, reviewed
evidence groups, instrument identifiers, effective/knowledge dates and question
scope. Use the BASF p112 shared Actual/Actual definition and supplement p12 ranges;
the Deutsche pages 52–55/62, BBVA pages 96/104/108/116–117/129/131 and SEB pages
39–40/43–44/59–60/65 already listed in `closure_mechanisms.PROFILES`; and the four
BES extractions in `reviewed-extractions.json`. Verify page numbering against the
retained PDFs rather than assuming printed and file indices coincide.

Keep all of these as development evidence. Freeze a genuinely unexposed family
cohort separately before independent acceptance. If a source quotation or gold
disposition is disputed, record alternatives; do not score an automatic reader
against an invented definitive label.

First artifact: input and question manifests plus a comparison of existing
reviewed versus automatic inputs. An invalid source or mislabeled comparison
blocks dependent evaluation until repaired.

### A1 — Complete occurrence and construction accounting

Extend `anchors.bind`, `construction_ast.render/assemble` and the BASF adapter.
Add source-bound interval dispositions for copied text, selected/unselected
branches, replaced templates, superseded text and unresolved material. Bind every
exclusion to its choice and every override to its target, authority and time.
Keep accounting separate from the output map so excluded material need not be
printed as operative text. Shared leaves may support several uses; excluding one
use cannot erase another. Version the representation and its admission schema.

Acceptance: every relevant occurrence has a compatible disposition or an explicit
unresolved reason; no material disappears because it lacks an AST node; the
rendered source maps recover all quotations exactly. Exercise nested/correlated
choices, shared definitions, fields, renumbering, repeated quotations, indirect
references, amendment chains, boundary dates and contradictory overrides. Preserve
the BASF all-options margin. The 195–209/209–290 discrepancy stays unresolved until
there is an admitted source-backed interpretation. Zero bracket count is not a
completion criterion.

Add focused regressions to `tests/prospectus_successor/`; implement an independent
interval-accounting checker. If the source does not justify a choice, expose that
gap and continue unrelated constructions rather than inventing punctuation or
selection rules. Output: selected text, disposition map, unresolved report and
immutable review packet.

### A2 — Constrain choices and close question-specific references

Keep the finite enumerator in `predicates.py` as the comparator. Add a bounded Z3
Boolean adapter only after the source-bound constraint language is frozen.
Translate constants/names/not/all/any recursively; preserve explicit conflicts;
check consistency before entailment. Store named constraints and witnesses.
Keep solver timeout/unknown distinct in the reason field from missing legal facts.

For the declared expression corpus, enumerate all assignments up to the existing
twelve-fact limit and compare results. Separately exhaust a small expression
grammar over a few facts. Do not claim exhaustive testing of every possible
twelve-variable formula. Beyond the enumerator's limit, check named satisfiable,
unsatisfiable, conflicting and unknown-premise examples; report solver bounds.
The Boolean argument in the survey applies only if translation preserves truth
tables and constraints faithfully represent admitted premises.

Extend `source_graph`, `clause_graph` and `contract_assembly` with typed reference
edges and question-root reachability. An evidence group must include governing
definitions, conditions, negation, exceptions and justified priorities. Reject or
retain unsupported cycles as unresolved. Compare reviewed evidence and automatic
evidence through the same evaluator. Missing material must not produce a supported
negative answer. First failure repair: identify extraction, scope/translation or
execution before changing the rule language.

### A3 — Trial layout and annotation adapters

Implement a Docling sidecar adapter that preserves raw extraction and supplies
structure/reading-order/attachment relations. Start with BASF p112 and one
bilingual page. If the candidate cannot map a governing span back exactly, repair
the map before expanding to A0's remaining pages. Both baseline and candidate use
the same frozen questions and reviewed target evidence.

Primary trial criterion: every designated governing span, margin attachment,
reference, numeric/negation token and selected-contract conclusion is correct on
the frozen slice; a previously failing declared case must be resolved to justify
added complexity. Record baseline failures too. Edit distance, layout IoU and
speed explain outcomes but cannot override a failed governing-span check. The
trial can establish a viable optional path; default promotion requires broader
family-separated independent evidence.

In parallel as a workstream, prepare an INCEpTION bridge using a matched release
and guide. Export grouped spans/relations and exact source editions; explicitly
convert UTF-16 and code-point offsets. Test supplementary characters, combining
marks, duplicate paragraphs, hyphenation, multiline and discontinuous groups,
relation identifiers, edits and reimports. Disable recommendations and pre-merge
for blind annotation. Preserve individual exports before adjudication. Fallback:
use existing local review forms if group or source fidelity fails. A successful
round trip does not establish reader independence.

No new parser/platform install has been performed by this survey. Before either
trial, bind package/model versions, license terms, CPU/memory requirements,
network/model-download behavior and exact bounded command in its run manifest.
Use isolated environments rather than changing the application/OCR environment.

### A4 — Complete financial conventions and event traces

Extend `financial_profiles.validate_scenario/assess` and the relevant exact
profile kernels. Require contract-backed calendar edition, calculation and
payment dates, day count, reference periods, stubs, EOM rule, adjustment and
rounding rules, entitled holder and currency. Model notices, observation,
determination, record/ex-coupon and payment events separately. Equal-time event
order and timezone are explicit premises if the case requires them.

Begin with a source-complete fixed-rate coupon slice. Use QuantLib v1.38 in an
isolated comparator environment with all conventions supplied; forbid evaluation
date and missing-reference-period fallbacks. Independently derive dates/fractions
for regular and short/long first/final periods, leap-year and EOM boundaries,
holiday shifts and missing-calendar cases. Vary individual contractual premises
to demonstrate their downstream effect. Introduce entitlement, event ordering,
FX or taxation only with their exact contract/law inputs; unsupported branches
must remain explicit.

Primary criterion: correct dates, exact final contractual allocations/rounding,
and a complete in-scope event/transfer trace. A numerical difference is a repair
trigger until its convention/arithmetic source is understood, not a majority
vote between libraries. Keep the existing distinct-holder and whole-share tests.
Defer ACTUS/CDM runtime adoption unless this phase exposes a specific requirement
that a bounded local model cannot serve or a bank demands their exchange format.

### A5 — Bind actual dependencies and test recovery

Extend the existing phase controller rather than adding a second scheduler.
Implement a `ReadContext`-style capability for phase files, environment values,
clock inputs and tool invocations. Freeze immutable input snapshots and bind
tool/model/language data versions. Instrument native/subprocess reads or state
the unenforced boundary; passing Python-level tests cannot certify native isolation.
Reduce broad method hashes only after observed inputs and mutation tests agree.

Use Hypothesis state machines against a simple fresh-recomputation model. Mandatory
cases include relevant and irrelevant changes, missing/new files, source bytes
changed under an old hash, changed tool identity, corrupt products, interrupted
publication, retry, repair admission and identical replay. Primary criterion:
incremental results equal fresh recomputation for declared deterministic inputs;
undeclared inputs cannot silently change an accepted result. Exact invalidation
sets are a separate efficiency criterion. Preserve crash/minimized examples.

### A6 — Obtain real evidence and accept only the declared scope

Admit dated statutes, regulator/court decisions and issuer/client/event records
through existing source and fact interfaces. Preserve superseded versions,
applicability and alternative readings. Do not relabel development scenarios as
observations. Actual event evidence is needed only for questions claiming actual
exercise or settlement, but is mandatory for those questions.

Freeze method, questions, support scope and a family-separated cohort; obtain
independent readings before exposing predictions. Use a distinct adjudicator
and preserve disagreements. Bind labels, exposure history, identities and
sign-offs through P0/P7/P8. If humans or actual facts are missing, release remains
blocked while independent engineering phases continue. Determine sample size and
uncertainty analysis from the intended coverage claim; the earlier request for
20–30 difficult cases is development coverage, not a statistical guarantee.

## Execution, repair and refresh mechanism

Use the existing `scripts.prospectus_delivery` commands for status, checking,
admitting reviewed repairs and running the amended phase jobs. Put new trial
receipts under the new adoption directory, with links to the source-bound P1–P6
products; never rerun historical extraction workers over frozen evidence.

Existing commands, from `.worktrees/bond-gap-closure`:

```text
python3 -m scripts.prospectus_delivery status
python3 -m scripts.prospectus_delivery check
python3 -m scripts.verify_prospectus_repairs --focused
```

The focused verifier is a regression/integration check after implementation;
it is not a substitute for A1–A6's new acceptance evidence. New adapter and trial
commands do not yet exist. Each phase must implement and review its bounded
command before execution, including timeout, environment, explicit inputs,
output directory and any stochastic seed policy. Reuse already authorized
command forms; local edits need no separate confirmation. Downloads/installations
and external actions remain subject to the actual sandbox rules, with any
necessary narrowly scoped approvals grouped before a trial.

After each phase, write `result.json` and `RESULT.md` with primary/veto diagnostics,
source/code/tool hashes, actual command, environment, wall time, evidence class,
and decision. Classify a failure as invalid harness/input, implementation failure,
candidate failure, unresolved legal premise or missing independent evidence.
Execute the bounded repair where authorized, preserve the failed attempt, and
recheck. Refresh the next phase's inputs, assumptions and acceptance tests against
the new result, recording a skeptical audit before proceeding. Stop automatic
retries at a declared limit and preserve unresolved work; do not make acceptance
easier to obtain a green run.

No new methods have passed local comparison yet. The first next action is A0/A1
source accounting, with the final BASF source regressions as protected evidence.
