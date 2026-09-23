# Implementation checkpoint — 22 September 2026

## Latest research continuation: competing interpretations

The user's request for deliberate multiple hypotheses has a literature-supported
design in `docs/research/interpretation-search.md`, with a separate BibTeX file
and eight added full texts in `docs/papers`. The strongest direct precedent is
AGATHA's search over case-law theories. The proposed module preserves semantic
families, source/evidence dependencies and unresolved alternatives; it generates
discriminating cases for review and separates heuristic search scores from legal
acceptability and calibrated probabilities. It is not implemented by this update.

DynareMCP's source offers hypothesis and falsifier records and a priority frontier,
not an identified generic UCT engine. Reuse the patterns; its writers are tied to
its own research workflow. ToT/LATS code and Carneades 4 were inspected as possible
references, without execution. Proposed adoption begins with deterministic breadth
and best-first investigation; optional MCTS requires a registered comparison on
independently adjudicated circulars. The 23EC46 ambiguity examples are development
hypotheses, not SFC rulings or independent legal validation. Existing acceptance
integrity still passes; original application/proposal files remain unchanged.

## Outcome and authorization

The user authorized execution of the master implementation plan and instructed
us to skip another Claude review. Public/synthetic core tasks T00–T22 are complete
with recorded engineering acceptance. No Claude invocation, bank deployment,
private client-data ingestion or live-model pilot occurred.

Start at README.application.md and docs/implementation/execution-report.md.
The machine task ledger is docs/implementation/master-plan.tasks.json. The program
is in src/legalmath; Python 3.11 runs in the isolated .venv; dependencies are pinned
in requirements-dev.lock. The parent tfgpu environment and adjacent repositories
were not modified. The retained JDK is
.localresources/java-toolchain/jdk-17.0.20.1+1. There is no Git repository; manifests
record file hashes instead of a commit.

## Final evidence

- artifacts/runs/acceptance/run-manifest.json: exact commands, environment, CPU-only
  execution, source hashes, elapsed times and results. Full suite: 154 passed,
  no failures/skips. Two TestClient/AnyIO deprecation warnings remain visible.
- artifacts/runs/acceptance/spec-runtime.log: all 35 RuleIR cases executed. Its
  event/release false flag concerns that script only; separate tests execute them.
- artifacts/runs/acceptance/contracts.log: 31 JSON files reproduced, including the
  22-path OpenAPI snapshot.
- artifacts/runs/mvp-accepted: complete original/amendment source-to-Java run,
  separate BankHost.java, 32 generated SPI decisions, eight event histories in the
  candidate JAR, 51 provision dispositions, synthetic review/releases, withdrawal,
  exported history and exact original decision reproduction after restoration.
- artifacts/runs/fresh-install: current non-editable package in a fresh isolated
  environment; packaged schemas, runtime, API JavaScript, CLI and dependencies pass.
- artifacts/runs/browser-review: five rendered views, authenticated API request,
  keyboard expansion and mobile layout. API, decision and mobile screenshots were
  inspected. Independent compliance-reader usability remains pending.
- artifacts/runs/acceptance/final-artifacts.json binds the delivery and supplemental
  checks. scripts/check_execution.py passed: 23 core tasks, 154 tests, 119 input
  files, 36 evidence files, 24 protected originals and 67 initial review inputs.

The actual safe discovery client performed a read-only product-circular refresh:
159 entries over two pages. Its database is artifacts/runs/discovery-client; raw
page evidence is artifacts/runs/sfc-live-refresh. This is category discovery,
not complete bank perimeter coverage or automatic interpretation of every item.

## Repairs and environment findings

Final repairs covered structural validation precedence, malformed snapshot identity,
6,000-digit exact values, deep rule chains, authenticated provision coverage,
initial-snapshot reviewer attribution, uploaded-source authority and worker launch
failure. Candidate verification invokes the generated class in the exact binary.
The selected release verifies both decision and attributed-event components.

A minimal FastAPI TestClient probe blocked on a thread wakeup in the Codex sandbox
and passed in the trusted host. API/full-suite/browser tests were therefore run
trusted. Dependencies were not changed to conceal this boundary. The browser's
first supplemental run rejected a string-based Playwright wait under CSP; replacing
that harness wait with locator assertions passed without relaxing application CSP.
The before/after harness hashes are retained in final-artifacts.json.

## Current contracts and limits

Read docs/specs/v0.1/implementation-closure.md for actual Java Map/String APIs,
boundary behavior, limits, uploaded-source provenance and local identity. Source
and interpretation authority remain separate. Archives disable authentication
tokens and verify hashes; they are unsigned and trust database administration.
The host is a synthetic in-memory transaction adapter. PDF parsing has local
file/page/text bounds but no OS isolation boundary for hostile documents.

T23 optional research adapters are explicitly NOT_RUN: no core dependency requires
them. A future adapter needs license/interface checks and a bounded real invocation.
T24 requires independent participants, adjudicated tasks and a registered live-model
protocol. The deterministic drafting stub establishes integration only. No model
accuracy, time-saving, legal correctness or production readiness claim is supported.

## Resume discipline

The original planning packet is preserved under
 docs/reviews/master-plan-evidence/initial-review-snapshot.
scripts/check_master_plan.py still checks that original no-implementation snapshot;
it is not the current completion checker. Use scripts/check_execution.py for
current task/dependency, source, JAR, evidence and link integrity. Do not overwrite
the accepted run to simulate a new verification; use a fresh working directory.
No further code changes are pending for this engineering milestone. Next work
needs a concrete bank adapter specification or a separately registered human/model
pilot. Finite tests do not resolve the pending bank-owned interpretations and data
mappings. A new correctness counterexample reopens the affected task for repair.


## Subsequent second-circular verification

The user's follow-up exposed a distinction: the original acceptance executed only
the selected 23EC35 profile. Other pilot circular tests covered intake/metadata,
not executable source interpretation. See docs/implementation/second-circular-verification.md.
A new manually authored, unreviewed 23EC46 paragraph-10 gift-prohibition candidate
passed 22 source-written cases and 729 T/F/U combinations in Python and the actual
generated Java class. Four compiled erroneous candidates were detected. The oracle
was frozen before candidate construction, but the same agent authored both, so
independent legal correctness is still unestablished. The 18 paragraphs/four
footnotes are inventoried; only paragraph 10 is implemented. Five legal issues and
two external Code/FAQ dependencies stay unresolved and block review; no release
was manufactured. Fresh official source bytes match the retained 23EC46 snapshot.

The final evidence is artifacts/runs/second-circular-23ec46-final; earlier same-turn
runs remain intermediate evidence. The final script records correct start/finish
and acquisition timestamps and supports external fresh output directories. No
accepted runtime or existing test changed; prior acceptance integrity still passes.
Automatic prose-to-rule translation is unimplemented (provider is a fixture stub).
Next validation needs independent compliance adjudication, a real drafting provider
and a frozen multi-circular benchmark; current counts are not translation accuracy.

## English interpretation research follow-up

The user identified English-to-specification correctness as the main gap.
`docs/research/english-interpretation-assurance.md` now distinguishes source
justification, controlled-language/IR preservation and Java execution. It gives
23EC46 counterexamples and a proposed interpretation-packet, controlled-English,
solver-disagreement and review extension; these components are not implemented.
The pre-work audit is `docs/plans/english-interpretation-assurance.md`.

The literature library adds Amrollahi, Lopez and Barrett's 2026 roundtrip
verification paper, v2, bringing the library to 39 editions / 38 works / 961
pages. Its formal self-consistency check is explicitly heuristic evidence for
source faithfulness, not a proof; shared omissions can pass it. Technical reading
and retrieval limitations are recorded in the new note. No application code,
accepted evidence, test result, legal approval or original proposal was changed.
