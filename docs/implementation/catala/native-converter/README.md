# Direct native Catala development profile

The converter takes retained source text, a question and a factual interface,
then generates a native Catala program and asks a fresh model context to review
its reading of the source. Computation goes directly through Catala. There is no
RuleIR translation in this route. The existing RuleIR-to-Catala backend remains
a separate implementation.

The factual interface declares values and their meanings. It does not encode
rules: records, lists, exact decimals, money, dates, Booleans and integers can be
inputs and outputs; nullary enums can classify records. The candidate supplies
native calculations, reusable scopes and labelled exceptions. Version 1 rejects
imports/includes and compiler attributes. Builtin sums are supported by the
pinned Catala 1.2.1 compiler, although upstream marks them deprecated. Optional
values, enum payloads and a pinned subset of imported modules are available in
the explicit version 2 profile described below. Recursive types remain rejected.

Set `native_profile` to `legalmath.catala.native.v2` on a task to opt into that
profile. `optional[integer]`, for example, accepts known absence as JSON `null`
and presence as `{"present":"42"}`. The surrounding fact must still be known,
complete and temporally eligible. Payload enum cases use declarations such as
`{"name":"Amount","type":"money"}` and values such as
`{"case":"Amount","value":"1250"}`; a nullary case in the same enum has a
null payload. Nested acyclic records, lists and options are supported. Existing
version 1 tasks keep their original commitments.

Version 2 permits task-declared `imports` from `Integer_en`, `Decimal_en`,
`Money_en`, `Date_en` and `List_en`. The builder supplies aliases such as
`Decimal` and verifies the complete dependency closure against the original
toolchain lock. Candidate source cannot introduce imports or filesystem access.
Representative operations from all five modules have executable probes; this is
not validation of every standard-library function. In the pinned release,
`List.sequence` excludes its upper bound.

A source critic returns SUPPORTED, CHALLENGED or UNRESOLVED. A challenged candidate
may undergo one revision followed by fresh criticism. Compiler errors can also
trigger that revision. Every model dispatch and response is retained, and
resumption checks commitments before reusing completed calls. A dispatch lost
before its response was saved remains counted and stops the run. A model's
SUPPORTED verdict means it found no source defect; it does not establish legal
correctness or pass the separate behavioral verification.

The public commands are:

```text
legalmath catala-convert generate --task TASK.json --out RUN --allowance EXISTING_LEDGER.json --jdk JDK --compiler CATALA --upstream PINNED_SOURCE --lock LOCK.json
legalmath catala-convert build --task TASK.json --candidate CANDIDATE.json --out BUILD --jdk JDK --compiler CATALA --upstream PINNED_SOURCE --lock LOCK.json
legalmath catala-convert verify --build BUILD --cases CASES.json --out REPORT.json --jdk JDK --compiler CATALA
legalmath catala-convert execute --build BUILD --snapshot SNAPSHOT.json --jdk JDK
```

Generation defaults to at most four calls and one revision; it requires an
existing explicitly supplied allowance. Add `--resume` to reuse a run with
unchanged source, interface, code, model route and resource commitments. Completed
candidate bytes can be inspected in the run's attempt directory. A candidate's
`source` field contains executable scope definitions in closed Catala fences;
source quotations and identifiers belong in its anchors. Draft execution
can evaluate a separately authored candidate and is not a release approval.

Integers and money minor units are canonical decimal strings. Money units and
currency are declared in the interface. Decimal values are reduced rational
objects, for example `{"numerator":"1","denominator":"3"}`. Dates use
`YYYY-MM-DD`. JSON floats are rejected. The bridge reads Catala's exact numerator
and denominator, never its `double` conversion.

Every known input has an explicit completeness flag and validity/recording times.
Evidence IDs identify each field, list and item by JSON path. A complete empty
list is usable; a missing, contradictory, stale or incomplete list causes
abstention. Optional source-quoted `bounds` declare exact minimum/maximum values
for numeric inputs; the Python host abstains outside those bounds and the Java
caller rejects direct out-of-domain values. The task author must declare these
bounds: prose assumptions do not create validation. Integer and rational
components are limited to 1,000 decimal digits in this profile.
Absent optional values are not implemented in version 1. All required
inputs must be usable even if a particular branch might not need them; this
conservative policy differs from RuleIR's partial-information evaluation.

Both instrumented and uninstrumented Java programs are built into deterministic
standalone JARs, with source/task/candidate/toolchain commitments embedded. The
version 1 builder inserts observations at compiler-generated scope output assignments;
copy constructors are excluded. The trace records actual scope, field and value
observations from that Java process. It does not identify every evaluated branch,
justify why a value follows from law, or turn an inferred source anchor into an
executed clause. Source quotations and code locations remain navigation aids.
Version 2 additionally records source-position conditions, executed branches,
option decisions and enum arms. A separately pinned derivative of the Catala Java
emitter produces these observations. The original compiler performs invariant
checking and produces the uninstrumented comparator. The derivative's trace
transform does not pass the upstream nested-scope inversion check, so its build
records `trace_invariant_check=untouched_compiler_only`; value preservation is
checked through actual execution. Standard-library internals are not traced.

The isolated preparation script is `scripts/prepare_catala_trace.py --out
.localresources/catala-toolchain/native-trace-v1`, run with the project Python.
It needs the existing pinned opam switch and source tree. It creates a separate
compiler, patch and lock; the reviewed lock is
`docs/implementation/catala/gap-closure/trace-toolchain.json`. A rebuilt compiler
must match that lock or receive a new reviewed identity before use.
Verification compares both Java variants with independent expected values and
checks the expected values inside Catala before exporting a Boolean. This avoids
the pinned interpreter's lossy numeric JSON output.

`NativeHost` stores immutable, content-addressed native packages containing builds,
retained source bytes, cases, verification and review commitments. The
`legalmath.catala.native.package` module exports and installs ZIP packages against
an externally supplied package hash. `NativeHost.stage_package` verifies the
import and reruns its retained cases before it can receive local approvals.
Execution uses the packaged JAR and Java 17. Compiler/interpreter verification
also needs the pinned native toolchain and compatible OCaml library plugins;
this run validated that verification environment on Linux.

The trusted embedding application supplies the named identity/role registry.
External callers use `NativeAuth` bearer tokens; provisioning requires trusted
admin authority, an expiry and roles already assigned to the named person. Plain
string callers are an embedding API and must never be populated from untrusted
request fields. Tokens are stored as hashes and cannot be revived or rebound.

Engineering and legal approval require two distinct people. Each authenticated
reviewer obtains `auth.review(token, release, role)` and supplies its digest to
`auth.approve(token, release, role, expected_review=digest(review))`. Approval can
expire or be withdrawn. Activation uses an expected-current-release comparison;
rollback requires a previously activated package and current approvals. Release
revocation and credential revocation persist across restarts.

Before committing a transaction receipt, the host rechecks the release,
approvals, credential validity and subject revision in one SQLite transaction.
Historical replay verifies the original package and reruns the calculation,
including after a release has been revoked for new use. Legacy host rows without
package commitments require staging and approval again. The native host remains
a separate adapter; institution-specific identity, transport and authorization
policy still belong to the embedding application.

The frozen development pilot and result note are separate from this API guide.
Finite case agreement establishes behavior on those cases, conditional on the
reference and declared factual abstraction. The
[gap-closure results](../gap-closure/results.md) record the executed semantic
comparisons, source-conversion development study and reviewer collection dry run.
Independent legal review, representative heldout evaluation and human reviewer
measurements remain outstanding.
