# Circular 23EC35: executable Java demonstration

This example translates an explicit, source-linked **individual client / solicited
transaction / paragraph 8.3(a) execution-monitoring** specification into Java.
It is a demonstration with synthetic evidence, not an approved bank control.
The proposal's language lesson, dry run and Java chapter explain the whole method.

From the repository root:

```sh
python3 examples/java-dry-run/build_and_verify.py \
  --jdk .localresources/java-toolchain/jdk-17.0.20.1+1
```

The project-local Temurin JDK archive was verified against the official SHA-256:
`3808d1d15e3ec6bd5b84057fb5d84c33d8a1536a258146bcea2e603fc726e08e`.
Another JDK 17+ can be supplied with `--jdk`; its compiler identity is recorded.
Python 3.11 and `jsonschema` are needed at build time. The deployed Java code uses
only the Java standard library and targets Java 17 (class version 61).

The build regenerates the specification and synthetic inputs, validates source
spans, generates Java, compiles with `--release 17 -Xlint:all -Werror`, packages a
JAR, independently recompiles and checks binary reproducibility, then compiles and
runs separate callers against the JAR. It compares all result fields and hashes
with the independent Python reference. It also compiles/runs strict-boundary,
OR-to-AND and consent-bypass mutations, requiring outcome mismatches to detect them.

Current execution evidence: **32 decision cases, eleven consent histories, all three
mutations detected**, and unsupported `scale` compilation rejected. These are
finite deterministic checks of this profile. They do not prove universal compiler
correctness or faithful interpretation of every circular provision.

- [Generated Java](generated/GeneratedSpi.java)
- [Compiled JAR](build/spi-controls-demo.jar)
- [Complete separate host caller](generated/BankHostExample.java)
- [Verification record and hashes](build/verification.json)
- [Full decision results](build/decision-results.json)
- [Host output](build/host-output.txt)
- [Typed bundle](spec/spi-control.bundle.json)
- [Decision inputs](spec/decision-cases.json) and [consent histories](spec/consent-cases.json)

The host output is:

```text
BEFORE_WITHDRAWAL STREAMLINING_CONDITIONS_MET
AFTER_WITHDRAWAL STANDARD_PROCESS_REQUIRED
RESULT_AUTHORITY DEMONSTRATION_ONLY
```

To call the already-built library, compile your caller against
`build/spi-controls-demo.jar` and invoke
`hk.legalmath.spi.GeneratedSpi.evaluate(snapshot, validAt, knownAt)`. The public
`DecisionRuntime` types are immutable records. `GeneratedSpi.INPUT_TYPES` declares
the required fact names/types. Supply an explicit unknown for unavailable evidence;
an absent declaration or wrong type is malformed input. `BigInteger` amounts are
HK cents. No Python or model call occurs inside Java evaluation.

All facts must concern one legal client, selected category, arrangement and
transaction. The host owns imported PI definitions, ownership/FX calculations,
assessments, document verification and complete consent-stream attribution. The
library trusts the normalized evidence values; it does not authenticate documents.
Consent replay assumes the host's complete stream window and authoritative sequence.
In particular the host must never fabricate a completeness assertion when late
withdrawal events can still be missing.

The ten rules cover financial alternatives, category qualification, assessment,
arrangement/consent, threshold, conditional explanation/warning and retained
information. `annual_review_current` is a reviewed composite; suspending
streamlining when it is false is a proposed **bank restriction**, not a claimed
automatic legal consequence of paragraph 14. Corporate, unsolicited and designated-
account profiles return outside profile. Full obligation scheduling, default
expressions, date/FX calculations and automatic prose extraction are not implemented.

SPI-Demo1 uses the RuleIR 0.1 bundle structure but a deliberately smaller runtime
response and supported operator set. The [full Java contract](../../docs/specs/v0.1/java-backend.md)
and W03J describe what the implementing agent must extend. The 35 general RuleIR
fixtures are a separate future conformance target, not 35 extra executed cases.

Source span digests bind retained public SFC material under `.localresources/sfc`.
No bank's actual source systems are connected. Deployment requires an approved
release, real data mapping, and transactional consent/exposure reservation checks
in addition to the pure decision library.
