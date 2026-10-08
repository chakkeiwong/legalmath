# Prospectus adoption execution

Implementation baseline: `5ad615d570fa98834e465edc305bf88d411f49cc`.
Production comparator: `a05e18bbdeefbf278d29a6755e274124f97bda35`.
Specification: [adoption program](prospectus-adoption-program-2026-10-07.md).
Results: `docs/implementation/prospectus-adoption/`.

## Skeptical audit before implementation

The specification passes as a research direction, but fails as an executable
plan: it has no registered A0–A6 jobs, fixed trial commands, or concrete source
slice. Implementation proceeds under this corrected plan. The existing controller
will gain a named program, retaining its locking, immutable attempts, repair
admission, recovery and next-phase refresh. Historical P0–P8 receipts and the
survey hashes will not be rewritten. Code changes invalidate old receipts; they
do not retrospectively invalidate the historical results.

Code inspection confirms three defects: AST accounting follows only selected
branches and skips all instructions; predicates reject more than twelve names;
and controller bindings are declarations, despite a docstring calling them actual
reads. Further gaps are a missing typed reference closure, no exact coupon/event
profile, and no version-bound annotation exchange. A successful test run cannot
establish that the unresolved German contract or actual legal events are settled.

Wrong baselines: compare with retained raw extraction and finite enumeration,
not defect assertions or aggregate counts. Fairness: preserve the same questions,
source bytes and target evidence for both parser arms. Hidden defaults: no
reference-period, calendar, timezone, reader, fact or legal-scope inference.
Environment: application Python supplies Z3/Hypothesis; optional tools use isolated
environments. Stop conditions distinguish input corruption and budget exhaustion
from a failed candidate. Parser and annotation runtime results must identify
whether a real engine was used; adapter tests alone cannot count as trials.

Audit verdict: PASS for the bounded engineering sequence below. Tool feasibility
checks may revise A3/A4 before a model download or financial comparison. Record
the revision and preserve the failed candidate when that happens.

## Research intent and evidence contract

Question: do explicit occurrence dispositions, Boolean constraints, reference
closure, exact conventions and tracked inputs prevent the observed silent-loss,
unsupported-answer and stale-result failures?

Primary engineering criteria: exact source quotations and complete interval
dispositions; finite/Z3 semantic equality for a declared corpus; missing reference
or cyclic support remains unknown; exact coupon fractions and rounded transfers;
incremental results equal fresh recomputation. Critical source loss, a wrong
supported answer, a corrupt binding, or a guessed convention veto promotion and
trigger repair. Corrupt original/comparator data, unintended paid execution, and
exceeded resource bounds veto the affected run. Human/fact absence vetoes release
only. Timing, coverage counts and generic OCR scores are explanatory.

No population accuracy, independent adjudication, full settlement, automatic
German legal interpretation, or native-process confinement will be concluded.
The declared cohort is exposed development data. Repairs may not relax criteria.

## Commands, limits and phase decisions

Run from `.worktrees/bond-gap-closure`:

```text
python3 -m scripts.prospectus_delivery --program adoption phase --phase A0
python3 -m scripts.prospectus_delivery --program adoption phase --phase A1
python3 -m scripts.prospectus_delivery --program adoption phase --phase A2
python3 -m scripts.prospectus_delivery --program adoption phase --phase A3
python3 -m scripts.prospectus_delivery --program adoption phase --phase A4
python3 -m scripts.prospectus_delivery --program adoption phase --phase A5
python3 -m scripts.prospectus_delivery --program adoption phase --phase A6
python3 -m scripts.prospectus_delivery --program adoption status
python3 -m scripts.prospectus_delivery check
```

Final verification runs the same A0–A6 commands, the focused regression suite,
an identical replay requiring seven reused receipts, and a current-state check:
`python3 -m scripts.verify_prospectus_adoption`. It preserves each attempt under
`docs/implementation/prospectus-adoption/verification/`, including failures,
command logs, JUnit results and a manifest. Its 1800-second command bound is an
additional verification budget, not permission to expand the two-page trial.

Each attempt is capped at 1800 seconds, each identical input at three attempts.
Tests have a 180-second subprocess limit unless the phase records a narrower
comparison command. Downloads: at most two retries per resource, 15 minutes per
tool setup, 3 GB total new sidecar/model storage; no paid APIs or GPU execution.
Freeze optional package and model revisions before model execution. Stop expansion
after a critical span fails on the first two layout pages. Keep the existing
extractor when the candidate fails or cannot run within the bound.

| Phase | Implementation and exact evidence | Repair / next-phase refresh |
|---|---|---|
| A0 | Verify retained P1 source/layout products against receipts and PDFs; freeze source, raw-unit, page-label and question manifests. Include all named profiles and four BES extractions. | Correct printed/file numbering before dependent trials. Missing reviewed targets remain explicit; no invented gold. |
| A1 | Versioned per-use AST dispositions and independent interval sweep; BASF map and margin regressions. | Unbound intervals remain unresolved; exercise shared leaves, excluded nested branches, field replacement and amendment boundaries. |
| A2 | Optional bounded Z3 solver and source-bound named constraints; typed reference closure consumed by clause evaluation. | Compare small grammar and selected formulas through 12 variables; report witnesses, inconsistent premises and solver unknown separately. |
| A3 | Lossless annotation/offset bridge and bounded Docling page trial if feasibility passes. | First failure triggers source-map repair or retained baseline fallback. No engine claim from adapter-only tests. |
| A4 | Exact fixed-coupon/event kernel with explicit conventions; independent fraction/date cases and isolated QuantLib 1.38 comparison. | Missing contract or calendar admission remains unsupported. No promotion of a development convention into BASF terms. |
| A5 | ReadContext snapshots/observed reads and tool identity in the existing controller; state-machine recovery tests. | Keep broad invalidation as a safety net. Native reads remain an explicitly unenforced boundary. |
| A6 | Reconcile retained legal sources and actual-fact availability; prepare bound reader/adjudication packet and evaluate release prerequisites. | Preserve alternatives; request real readings and event records only after independent engineering work. |

The controller writes result, manifest, immutable receipt, repair obligations and
a refreshed next-phase plan after each attempt. A failed artifact blocks its
dependents; a valid partial artifact permits independent later engineering.
Coherent local commits preserve the reviewed code and results; no remote action
is part of this continuation.

## Defaults, assumptions and pre-mortem

| Choice | Provenance / status | Risk and earliest check |
|---|---|---|
| Historical P1 products | Verified development baseline | Stale or corrupted data: verify receipt and original bytes before freeze. |
| AST v1 compatibility | Existing API baseline | Silent reinterpretation: retain text output and test v1; require v2 authority for new override certification. |
| Boolean bounds (256 names, 1000 ms/query) | Convenience resource bounds, not completeness theorem | Unknown due to resources: explicit reason and solver statistics; never false. |
| UTF-16 offsets | Inspected INCEpTION export implementation | Split surrogate or normalize text: exact code-point round trip and edition checks. |
| Explicit ICMA quasi-coupon periods | Inspected definition and QuantLib code; development hypothesis | Bad schedule: demand a contiguous supplied partition and independent fractions. |
| Broad code hashes retained | Safety baseline | Excess invalidation: record separately from stale-result correctness. |
| Fixed generated-test seed | Reproducibility choice | Narrow corpus: mandatory named mutants plus a state machine; no statistical ranking. |

The run could pass while misleading us if target labels come from the same
parser, source maps omit margins, a library supplies missing conventions, or a
simulated annotation export is called an actual platform trial. The earliest
checks are independently retained page quotations, raw-byte round trips, explicit
input validation and engine/version records. Tests can establish these bounded
engineering properties; they cannot supply legal judgment or independent readers.
