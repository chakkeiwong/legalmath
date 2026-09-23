# Run LegalMath

LegalMath is a local workbench for turning selected SFC requirements into
source-linked RuleIR conditions and a verified Java 17 library. The prototype
includes dated evidence, explicit unknown/conflict results, attributed consent
and achievement-duty replay, review and release records, counterexample search,
source discovery, amendment impact and a candidate-only drafting interface.

All examples use public sources and synthetic clients. The drafting provider is
a deterministic stub. Bank interpretation approval, bank integration, live-model
quality and human usability remain pending.

Core tasks T00–T22 passed their engineering acceptance: 154 tests, all 35 RuleIR
cases, the complete original/amended Java delivery, fresh installation and browser
checks. The [current evidence audit](artifacts/runs/acceptance/execution-check.json)
binds this result to the retained files.

The [second-circular verification](docs/implementation/second-circular-verification.md)
adds a manually authored candidate for 23EC46 paragraph 10: 22 named scenarios,
729 T/F/U combinations and four compiled mutation checks. It remains unreleased
pending source/meaning review. Neither this example nor the stub demonstrates
automatic translation accuracy across new circulars.

## Start the prepared workbench

From this repository:

```sh
.venv/bin/legalmath serve \
  --data-dir artifacts/runs/mvp-accepted/database \
  --identities artifacts/runs/mvp-accepted/local-identities.json \
  --jdk .localresources/java-toolchain/jdk-17.0.20.1+1 \
  --comparison-jar artifacts/runs/mvp-accepted/java-release/policy.jar \
  --port 8765
```

Open `http://127.0.0.1:8765`. The original-source/rule screen includes the retained
paragraphs, source PDF links, interpretation, input units, rule tree, distinguishing
scenarios and open questions. Saved decisions show their exact historic evidence
and traces. The amendment screen lists affected definitions and rules. API
operations are available through `/docs`; mutation calls require a bearer token
from the local identity file and an `Idempotency-Key`. These identities are for
the local synthetic demonstration only.

## Reproduce from a fresh directory

Use Python 3.11 and the retained JDK 17 (or a separately verified JDK 17). The
application has no dependency on adjacent research environments.

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
.venv/bin/legalmath demo --repository . --workdir /tmp/legalmath-demo-new \
  --jdk .localresources/java-toolchain/jdk-17.0.20.1+1
```

The work directory must be empty. This command imports 23EC35 and both annexes,
retains five pilot circulars, checks the 51-provision disposition, builds and tests
the complete selected SPI profile, records synthetic meaning/engineering review,
exports the JAR, compiles a separate Java caller, replays withdrawal, builds and
reviews a clearly synthetic one-cent amendment, and exports/restores history.
The original historical result must reproduce exactly. Each immutable build,
verification, release manifest and approval is a separate record.

The equivalent named command is `legalmath acceptance --scenario spi-23ec35
--offline --out NEW_DIRECTORY`. To import only the retained pilot sources, use
`legalmath sources import --manifest corpus/sources/pilot.json --data-dir NEW_DATABASE`.

## Java delivery

The accepted walkthrough exports
`artifacts/runs/mvp-accepted/java-release/policy.jar`, its external manifests and
the original generated source under `candidate/`. The amended JAR has a separate
release. The generated class name is recorded in the build response and its
filename. Its two `evaluate` overloads accept strict JSON or a Map plus rule ID,
valid time, knowledge cutoff and mode, and return strict JSON or a deeply immutable
Map. Integer and money values are decimal strings; money is HK cents.

The separate `BankHost.java` in the run directory is compiled against the exact
exported JAR. It demonstrates the invocation without Python or model services.
The library evaluates a named subcondition; the host must enforce release,
identity, evidence and transaction controls. Merely passing `production` does
not grant release authority. The synthetic transaction host tests versioned
consent/release/exposure reads, bounded retry, atomic reservation and idempotency.
Its in-process state is an integration example, not durable bank order storage.

Candidate compilation is also available through `legalmath build-java --help`;
controlled export through `legalmath export-java --help`. Both use the stored
version/release records. Source discovery is read-only:

```sh
.venv/bin/legalmath refresh --data-dir /tmp/legalmath-discovery --category products
```

It stores page hashes and cursor results, rejects unsafe redirects and incomplete
pagination, and distinguishes an empty result from a failed request. The recorded
22 September refresh retrieved 159 product circular index entries over two pages.
That category is not the bank's full regulatory perimeter.

An API source imported as uploaded bytes is labelled UPLOADED_UNVERIFIED and cannot
enter review or release. Fetch through the restricted official-source client for
verified acquisition, or use the trusted, hash-bound retained corpus. Review still
owns the legal scope and interpretation of an acquired source.

## Verification

```sh
.venv/bin/python -m pytest -q
.venv/bin/python scripts/check_contracts.py
.venv/bin/python scripts/check_spec_pack.py --runtime legalmath.conformance:evaluate_case
python3 scripts/check_execution.py
```

The API tests use a thread-based local HTTP transport. In the Codex environment
its thread wake-up is blocked by the default sandbox; run those tests in the
trusted context. The minimal `scripts/service_probe.py` reproduces that boundary.
This is separate from the application's behavior in the ordinary host environment.

`bash scripts/fresh_install.sh` verifies a non-editable install in a temporary
environment. Browser verification uses the optional development dependency
Playwright and a retained Chromium headless shell under `.localresources/browser`.
Run `scripts/browser_walkthrough.py RUN_DIRECTORY` in a context permitted to
launch the browser and bind localhost. Its screenshots and keyboard checks do
not replace a compliance reader's usability review.

History archives contain public/synthetic data and unsigned local review evidence.
Import verifies content identities and database constraints. Authentication tokens
are disabled in exported histories. Direct SQLite administration is trusted;
hash chaining detects accidental changes and does not protect against an
administrator rewriting the records. Enterprise identity, signed retention and
real bank data connectors belong to a separate deployment project.

Read the [execution record](docs/implementation/execution-report.md),
[master plan](docs/implementation/master-plan.md),
[contracts](docs/specs/v0.1/contracts.md) and
[implementation clarifications](docs/specs/v0.1/implementation-closure.md).
