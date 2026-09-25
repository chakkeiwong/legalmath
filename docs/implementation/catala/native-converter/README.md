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
values, enum payloads, recursive types and externally imported modules need a
separately tested profile.

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
candidate bytes can be inspected in the run's attempt directory. Draft execution
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
builder inserts observations at compiler-generated scope output assignments;
copy constructors are excluded. The trace records actual scope, field and value
observations from that Java process. It does not identify every evaluated branch,
justify why a value follows from law, or turn an inferred source anchor into an
executed clause. Source quotations and code locations remain navigation aids.
Verification compares both Java variants with independent expected values and
checks the expected values inside Catala before exporting a Boolean. This avoids
the pinned interpreter's lossy numeric JSON output.

`NativeHost` provides a separate development release store. The embedding host
supplies authenticated identities and roles. Two distinct reviewers approve the
exact native build; activation uses an expected-current-release check. Execution
checks subject revision and release again before committing a receipt. Historical
replay selects the original build and reruns the actual calculation. This is not
the existing RuleIR release API and is not a production authorization or a
complete deployment package.

The frozen development pilot and result note are separate from this API guide.
Finite case agreement establishes behavior on those cases, conditional on the
reference and declared factual abstraction. Human legal review, ambiguity across
rival programs, richer imports/options, a representative heldout study, a paired
comparison with RuleIR, and reviewer-time measurements remain separate work.
