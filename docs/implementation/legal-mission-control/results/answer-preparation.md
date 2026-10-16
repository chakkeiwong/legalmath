# Complete-answer preparation: partial implementation, qualification blocked

9 October 2026. One bounded engineering attempt under
[`legal-mission-answer-preparation.md`](../../../plans/legal-mission-answer-preparation.md),
returning to `product-contribution`. **No new legal answer or tool-benefit result
was produced.** The source preparation and fresh-fixture tests passed. The
tool-enabled historical qualification was rejected before dispatch because its
nested replay references older implementation files. This is a continuation veto
under the reviewed plan; no qualification retry was made.

## What changed and why

The inspected `CompleteInvestigation.run` path ends with a dossier. Its
candidate-specific question assignments and scoped assessments are not a complete
answer to the original user question. The direct answer experiment in
`scripts/legal_tool_live.py` bypasses that dossier, while its `product_trial`
returns the dossier without consuming it. These are the relevant missing links;
the inspection does not establish that no other answer-related code exists.

The new optional module
[`investigation_answer.py`](../../../../src/legalmath/interpretation/assurance/investigation_answer.py)
accepts the active, verified dossier and an explicit expected revision. It binds
the original questions, source packet, candidates, source qualifications and
consumer version. It retains source criticism, scoped judgments, residual
questions, method inputs and tool reports. Only the flat evidence inventory and
component file references stay outside the model view, in the hash-bound dossier.
Exact source-context duplicates use reversible references to packet units;
unselected text, whitespace and disagreeing secondary extraction remain retained.

One answer proposal must give prose for each original question, claims with exact
support and inference, contrary passages, assumptions, conditional alternatives
and unresolved dependencies. Every supplied reading, including an unformalized
reading, and every tool check needs an explicit disposition and explanation.
Stale or incompletely bound tool evidence cannot be labelled used as current
corroboration. Missing or duplicated references, altered questions, fabricated
quotes and legal-certification flags are rejected. A single bounded call is
permitted; failed validation retains the raw response and does not retry.

This validates accounting and source references, not entailment, the adequacy of
the prose, or genuine consideration of tool feedback. The scripted positive
test intentionally passes those structural checks without answering a real legal
question. The new module is optional and has not been promoted to a product
default or exercised in a live complete-answer trial.

The closed offline runner is
[`scripts/legal_mission_answer.py`](../../../../scripts/legal_mission_answer.py).
Its `prepare` action was executed once; its `qualify` action was attempted once.
Both check the admitted task and the recorded 09:33 UTC local deadline. Their
exclusive output directories prevent silently replacing a previous result. The
runner is an execution record for this attempt, not permission to rerun it.

## Source preparation result

The full retained corpus is `successor-s4/attempt-1/development-inputs.json`,
SHA-256 `01e973c1b1eb59f69bf44fed02c91767ea1452a819e514d328c15af94f2cbd4a`.
All **54 original units and 54,910 characters** were preserved through the actual
`acquire_context`, `packet_from_context` and `audit_packet` functions. The
20,543-character circular was split within the existing limit, giving **55
packet units**. Exact reconstruction was checked for every original unit.

The four inputs are explicitly labelled local reconstructions of retained text,
with original source files, hashes, per-unit mappings and qualifications. They
are not represented as original HTTP bytes. The selected UT Chapter 6/first five
pages, uncertain applicability and edition, Appendix extraction disagreement and
visual-content findings remain qualified. The parser's inherited `normative=True`
for every unit is explicitly unreviewed; headings and page navigation are not
thereby legal rules. No download or extraction-fidelity claim follows from this
character-preservation result.

The measured source-and-qualification request is **93,741 bytes**, below the
existing 200,000-byte input ceiling. This is a source-only diagnostic. The full
generated dossier request was **not measured or qualified**: qualification stopped
earlier on stale evidence. No source, uncertainty, candidate or criticism was
silently dropped to fit a limit.

## Tests and exact qualification failure

The command

```text
.venv/bin/python -m pytest -q tests/assurance/test_investigation_answer.py
```

reported **28 passed in 13.89 seconds**. It generated a fresh synthetic
`CompleteInvestigation` dossier with the current code and exercised the optional
consumer through `CompactProvider`. Negative controls cover stale revision,
changed question/dossier/qualification, omitted and duplicate question/reading/tool
accounts, fabricated quotes, stale tool use, overflow, invalid response retention,
evidence mutation during dispatch and repeated output-directory use. The fresh
integration fixture has no installed optional backend; the tool-account tests
are controlled boundary tests. Their limits must not be hidden.

The command

```text
.venv/bin/python scripts/legal_mission_answer.py qualify
```

attempted to reuse
`artifacts/legal-integration-repair/2026-10-08/R2/final/dossier.json`, revision
`0ebcbd374a8f2235a0e2095049f74af9f97da7e7e48413b2f4d8cad98c36760f`.
It exited 1 after the consumer returned `REJECTED`, with
`E_HASH_MISMATCH: src/legalmath/cli.py`. **Zero provider calls were made.**

All 282 references in the outer dossier still match their retained files. Its
nested replay has 319 upstream references; 12 implementation references differ
from the current checkout. For the first failure, the retained CLI hash is
`7728b61ff41697835d1381f6fe7dad4f999ac1f842d90408e6629f0a3ec991b4`, while
the current hash is
`b92c8d3d1608f099403677b1694a32db7b3b52d6db08b8766fac614d1b45e691`.
The complete list is retained in the postmortem. It includes subsequent legal
product changes and an unrelated prospectus module included by the broad replay
identity. None of those files was changed by this attempt.

The preparation plan's proposed historical comparator was therefore wrong for
current-method qualification. The pre-run audit anticipated stale-evidence risk
but did not verify this nested dependency before selecting the fixture. The
runtime check caught that mistake. This invalidates that qualification setup;
it does **not** show source corruption, reject a legal candidate, disprove tool
usefulness, or invalidate the fresh-fixture test result. Historical hashes and
evidence remain unchanged. Qualifying by rewriting the old references would be
wrong.

## Decision and refreshed substantive return

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Retain optional consumer as tested local code | Fresh-fixture structural checks pass | Installed-tool historical comparator fails nested identity | Full target output and live tool consideration remain untested | Review a current-method comparison within the existing product task | Complete integration or a correct legal answer |
| Retain derived source preparation | All retained characters survive the actual source route; source-only payload fits | No source-preservation veto | Full original authority/extraction/current-law completeness remains qualified | Reuse this exact source/qualification mapping in both arms | Full-dossier capacity or legal sufficiency |
| Stop this engineering attempt | Installed-tool/full-dossier qualification incomplete | Explicit identity continuation veto fired | Fresh current-method dossier and downstream size unknown | Return to `product-contribution`; require a reviewed revision before more execution | A second automatic repair or renewed budget |

There is no stochastic comparison or ranking. No selected tool becomes fully
evaluated. All four original questions and 46 obligations remain open; the
original 35 readings remain distinct from the later generated candidates.

The next method review should settle three concrete points, within the existing
product task rather than a new phase:

1. Use a freshly produced, currently verified tool-enabled dossier for current
   integration qualification. An isolated old checkout could reproduce the old
   experiment, but would not qualify today's method. Do not weaken verification
   or restore old code in this worktree.
2. Separate source preflight from generated-stage admission. The final dossier
   cannot be known before the investigation generates its claims and readings.
   A reviewed live protocol must freeze each known initial request, enforce
   byte/pair/call caps before every later dispatch, and permit a capacity stop
   without dropping readings or criticism. A small synthetic fixture cannot
   establish full-corpus feasibility. The illustrative 176-call ceiling in the
   earlier pilot is not a costed, ready invocation.
3. Preserve the actual P10 fulfillment and evidence-sufficiency questions, equal
   sources, generated criticism and source review in both arms. The first useful
   product result remains a complete source-grounded answer comparison. Another
   successful tool receipt would not substitute for it.

No further experiment or implementation followed the veto; only diagnosis,
result retention and mission refresh. This additional local window began at
08:03 UTC and was bounded by 09:33 UTC; it closes early on the veto. Its one
engineering attempt is consumed, even though part of the code passed. The
prior 90-minute package remains spent; the cumulative authorized local product
allowance was 180 minutes, not 180 minutes of measured computation. This is one
additional local engineering attempt beyond the previously recorded cumulative
repair 8; historical live ledgers are not rewritten.

The historical live deadline remains expired at 04:16:42 UTC on 9 October. No
live calls, installations, network acquisitions, GPU computations, commit or
push occurred. No live approval is requested on the incomplete invocation.

The strongest alternative explanation for apparent progress is that a carefully
structured but legally empty answer satisfies the new schema. The synthetic
receipt demonstrates that limitation. Only a matched complete-answer experiment
and source-grounded review can overturn it. The weakest evidence is still
answer-level legal inference and tool contribution, not passing test totals.

Retained evidence is under
[`answer-preparation/`](../../../../artifacts/legal-mission-control/2026-10-09/answer-preparation/):
`source/result.json`, `source/run-manifest.json`,
`qualification/consumer/result.json`, `qualification/result.json`, and
`final/qualification-postmortem.json`. The test result is a clearly labelled
transcription of the tool output in `final/test-result.json`; no JUnit receipt
was requested. Pre-close documents and executed source bytes are copied under
`final/executed-source/`, protecting earlier result references from this refresh.
