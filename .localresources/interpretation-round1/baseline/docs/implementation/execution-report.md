# LegalMath implementation result — 22 September 2026

The public/synthetic engineering prototype is implemented. The T00–T22 acceptance
suite passed **154 tests**, the specification harness executed all **35 RuleIR
cases**, and a fresh installation loaded the packaged schemas, Java runtime and
local web console. The complete 23EC35 walkthrough generated and released Java,
processed consent withdrawal, released a synthetic amendment, and reproduced the
original decision exactly after exporting and restoring the history.

Status: **ENGINEERING_MVP_COMPLETE**, under **LOCAL_SYNTHETIC** authority.
The user reported Claude's review complete and instructed us to skip another
review. No Claude process was invoked during implementation. This report records
engineering results; bank interpretation approval and human usability remain pending.

The subsequent [second-circular check](second-circular-verification.md) records
the exact application limit: this accepted run exercised 23EC35's selected profile;
it did not test automatic translation of unseen circulars. The later 23EC46 test
adds a manually authored paragraph-10 candidate, with independent legal
adjudication still pending. Its evidence is separate from this original acceptance.

## Use the delivered program

[Run instructions](../../README.application.md) cover the prepared workbench,
fresh installation, reproduction, source discovery and Java export. The concrete
delivery is [policy.jar](../../artifacts/runs/mvp-accepted/java-release/policy.jar),
with its [build manifest](../../artifacts/runs/mvp-accepted/java-release/build-manifest.json),
[verification report](../../artifacts/runs/mvp-accepted/java-release/verification-report.json),
[release manifest](../../artifacts/runs/mvp-accepted/java-release/release-manifest.json)
and [separate Java host](../../artifacts/runs/mvp-accepted/BankHost.java).

The generated class is `hk.legalmath.Policy_87e4416d72408979a341`. Its `evaluate`
method takes the fact snapshot, rule identifier, assessment time, knowledge cutoff
and mode. Integer and money values are exact decimal strings; money is HK cents.
It returns a decision with supporting trace, source/evidence identifiers and
execution hashes. The exported JAR runs with Java 17 alone. The host still owns
release selection, client identity and the atomic transaction; a true subcondition
does not authorize a trade.

The local web service has five review/operation screens and 22 API paths. Its
source/rule view includes original PDF links, interpretation, typed input units,
rule flow, distinguishing cases and recorded questions. Historical decisions
retain the exact request and evidence. The API console is packaged locally and
requires no CDN. The retained [OpenAPI contract](../specs/v0.1/openapi.json)
includes the actual rule, fact, event and result schemas.

## What the complete scenario exercised

The run imported circular 23EC35 and both annexes, checked all 51 provision
dispositions, and retained five circulars in the pilot corpus. The selected
business profile is an individual client and solicited transaction using Annex 1
paragraph 8.3(a) execution monitoring. The remaining circular provisions retain
their explicit dispositions; the program does not silently apply this profile
to corporate clients or other monitoring routes.

The original SPI policy passed 32 independent example outcomes through its
generated Java class. Eight attributed consent/duty histories also ran in the
exact candidate JAR before release. Separate synthetic author, meaning reviewer
and engineering reviewer identities approved the exact manifest. A separately
compiled host invoked the exported JAR successfully. Consent withdrawal then
changed the selected streamlining result from TRUE to FALSE.

A clearly synthetic one-cent financial-threshold amendment received a new bundle,
build, verification, coverage review, scope assessment, approvals and release.
Its October interval follows the original September interval. The two JARs are
different, while the September decision retains its original bundle, evidence
and result hash. Exporting the public/synthetic history and restoring into a new
database reproduced that original result exactly. The scenario record is
[walkthrough.json](../../artifacts/runs/mvp-accepted/walkthrough.json).

| Delivered identity | SHA-256 |
| --- | --- |
| Original bundle | `87e4416d72408979a341bdb80581201bbd7306be4bb1d81157693f641025ec4e` |
| Original JAR | `6b069b605a331480d618561b61e26c133f08f657813c779bc8c374a2aea62e51` |
| Amended JAR | `fb0d1c41a98e8f072834998fbd1c70447a9b54e15198c1d46f683524b5166df2` |

## Acceptance evidence

The [run manifest](../../artifacts/runs/acceptance/run-manifest.json) records exact
commands, input hashes, Python environment, execution context, elapsed times and
outputs. The workspace is not a Git repository, so it records content hashes
instead of an invented commit. Computation used the CPU; no GPU, training or live
language-model experiment ran. The retained source snapshot date is 21 September
2026. Test data and the amendment are synthetic.

The [JUnit record](../../artifacts/runs/acceptance/tests.xml) contains 154 passing
tests with no failures or skips. Two dependency deprecation warnings concern the
TestClient transport and AnyIO alias; neither changed the result. The
[runtime check](../../artifacts/runs/acceptance/spec-runtime.log) reports 35 executed
decision cases. Its `event_and_release_outcomes_executed: false` refers only to
that older specification-checking script; event and release execution is covered
by the separate tests and complete walkthrough.

Contract regeneration, including OpenAPI, reproduced all 31 JSON files byte for
byte. Clean compilation produced identical JAR bytes in separate build
directories, excluded injected stale class files and rejected a non-Java-17
toolchain. Complete Python/Java results agree across the language cases after
excluding their intentionally distinct backend identities; each native result
hash is independently reconstructed. Three compiled outcome-changing mutations
were detected. The original narrow Java demonstration, including its eleven
consent regressions, remains unchanged and retains its earlier isolated replay
evidence.

The [fresh-install record](../../artifacts/runs/fresh-install/import.txt) comes
from a non-editable package installed in a new temporary environment with the
locked dependencies. The [browser record](../../artifacts/runs/browser-review/report.json)
covers five actual Chromium screens, an authenticated API request, mobile layout
and keyboard expansion of the rule tree. Rendered API, decision and mobile views
were also inspected. These are engineering checks; no independent compliance
reader has yet completed a usability study.

The implemented restricted discovery client also completed a live read-only SFC
product-circular refresh: 159 index entries over two pages. The retained page
responses, cursor record and database preserve that observation. Pagination tests
cover repeated pages, changing totals and fetch errors. This category is only
part of a private bank's regulatory perimeter. The actual 23EC53/26EC22 replacement
relationship is retained; 25EC48 remains a review announcement without an invented
numeric rule.

## Task disposition

The [machine task ledger](master-plan.tasks.json) binds each task to its actual
test files and evidence. All rows below use the full-suite run; a listed task
command is not represented as having been separately rerun when it was covered
by that suite.

| Task | Implemented behavior and decisive evidence |
| --- | --- |
| T00 | Fixed boundary/semantic errors, temporal/identity rules, attributed events, release sequence, schemas and A01–A16 expectations. Contract regeneration passed. |
| T01 | Isolated Python 3.11 package, pinned dependencies, CLI and clean non-editable installation. |
| T02 | Canonical JSON, atomic content-addressed blobs, WAL database, migrations, foreign keys, transactional idempotency/audit and corruption checks. |
| T03 | Retained source/annex import, raw/text/page/offset verification, extractor identity and original-document display. |
| T04 | Provision dispositions, definition dependencies, applicability dimensions and authenticated meaning review. Missing coverage/dependencies block release. |
| T05 | Full AST validation, stable diagnostics, duplicate/reference/type/cycle rejection and bounded expanded call depth. |
| T06 | Dated records, interval-local supersession, late corrections, evidence merging and explicit unresolved/conflicting evidence. |
| T07 | All RuleIR operators and scope/default/unknown/conflict semantics; all 35 original cases executed. |
| T08 | Independent result/trace verification, altered link/hash/order/duplicate rejection and retained independent boundary outcomes. |
| T09 | Full Java semantics, actual generated-policy verification, 32 migrated SPI cases, non-Boolean results and three compiled mutants. |
| T10 | Deterministic clean Java 17 builds, exact binary evidence and a separate caller without Python/model services. |
| T11 | Registry roles, author/reviewer separation, stale revisions, exact-manifest approvals, source/coverage checks and atomic audit records. |
| T12 | Legal interval plus operational-time release selection, overlap/retirement rejection, exact-byte export and history restoration. |
| T13 | Attributed event persistence, ordering, completeness, consent generations, duty deadlines, late evidence and explicit leap-day policies. |
| T14 | Full Python/Java event-result agreement, release verification of the event component and consent-to-decision composition. |
| T15 | Synthetic versioned host: simultaneous reservation, consent/release changes, bounded retries and idempotent orders. |
| T16 | API, local identity, stable errors, persistence, bounded background jobs, cancellation, restart and launch failure. |
| T17 | Source/rule/case/amendment screens and local API console; Chromium, keyboard, exact HKD formatting and injection checks. |
| T18 | Knownness-aware bounded comparison, strict-boundary/OR–AND counterexamples replayed in both engines, empty-domain and unsupported/timeout outcomes. |
| T19 | Restricted live discovery, hash-bound pilot manifest, attachment changes, replacement metadata and unsafe-network rejection. |
| T20 | Deterministic drafting provider, exact source citations, bounded repair, timeout/manual-review outcomes and no tool/approval authority. |
| T21 | Definition/source/fact/rule impact, fresh exact-version approvals, preserved historical decisions and unchanged opening versions for existing duties. |
| T22 | Complete original/amendment review-to-Java scenario, external host, export/restore, full suite and fresh-install/browser checks. |
| T23 | **NOT_RUN, optional:** no research adapter is required for the core. A real adapter invocation, licensing review and any proof-search experiment remain separate work. |
| T24 | **PENDING:** independent human participants, adjudicated tasks and a registered live-model/comparative protocol are required. No effectiveness claim is available. |

Java runtime sources live in `src/legalmath/java/runtime` so the installable package
can generate a standalone JAR. Export/history logic lives in `review/releases.py`
and `storage/archive.py`. The synthetic transaction host is packaged with the
Java runtime. The complete scenario test is `test_full_walkthrough.py`. These are
recorded path changes from the proposed tree, with the same acceptance obligations.

## Findings repaired during implementation

The final audit repaired validation-stage precedence, hashable malformed snapshots,
Python's default decimal conversion limit, deep inter-rule recursion, reviewed
provision coverage, initial-snapshot reviewer attribution, uploaded-source authority
and persistent worker launch failure. Candidate verification was corrected to
invoke the generated class in the exact JAR. The final suite includes adversarial
checks for these failures, including 6,000-digit integer values.

The browser initially rejected a Playwright string-evaluation wait under the
application's content security policy. The harness was changed to wait on DOM
locators; the policy was retained, and the authenticated browser check then passed.
The [final evidence manifest](../../artifacts/runs/acceptance/final-artifacts.json)
records this harness revision and the hashes of the final delivery and checks.

The Codex sandbox also blocked the minimal TestClient thread-wakeup probe.
The same probe and service tests passed in the trusted host context. Dependencies
were kept pinned rather than changed to conceal that environment mismatch.

## Decision and remaining work

| Decision | Primary criterion | Veto checks | Main uncertainty | Next justified action |
| --- | --- | --- | --- | --- |
| Accept the local engineering MVP | T00–T22 executable checks passed | No failing source, identity, numerical, event, review or release check in this run | Unseen inputs and shared mistakes can escape finite testing | Independent code/security review and compliance walkthrough using the delivered workbench |
| Keep bank release pending | Bank-owned scope, meanings and mappings unapproved | Synthetic review cannot confer bank authority | Actual data, Java target/framework, concurrency and identity interfaces | Specify and test a real bank adapter with designated owners |
| Keep live-model effectiveness unassessed | No model/human experiment run | No independent adjudication or held-out results | Draft quality, reviewer understanding, error reduction and time saved | Register T24 with participants and a defensible comparator |

The strongest alternative explanation for passing conformance is a shared
misinterpretation in the fixtures and both engines. Hand-derived cases, compiled
mutants and trace checks reduce software risk but cannot settle legal meaning.
A source-faithfulness counterexample, forged release accepted by the service,
non-reproducible Java result or failed restore would overturn the corresponding
engineering acceptance and trigger repair.

This is a localhost, public/synthetic prototype. It uses unsigned local review
records and trusts database administration. The transaction example is an
in-memory adapter, not durable bank order storage. PDF parsing is locally bounded
by file/page/text limits but is not an OS-isolated hostile-document service.
Source inventory completeness, legal scope and evidence definitions need human
ownership. Solver results concern only the declared finite language fragment;
no universal compiler proof, proof of legal compliance, or comparative model
effectiveness is established by this run.
