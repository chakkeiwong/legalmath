# Direct native Catala converter: executed development results

The branch now contains a direct source-to-native-Catala converter, exposed as
`legalmath catala-convert`, with generation, bounded repair, source criticism,
building, exact verification, draft execution and checked resumption. It accepts
structured primitive inputs and compiles native Catala without passing through
RuleIR. Seven generated programs passed 43 exact development cases. Final host
hardening retained those programs and added five domain-boundary cases: **48
cases passed, six semantic mutations were detected, and four forged execution
records were rejected**.

This establishes a working development route and demonstrated native capabilities.
It does not establish superiority over the existing converter, population
accuracy, human review savings, legal correctness or production readiness. The
six synthetic tasks and one selected retained-source paragraph are a convenience
sample. Each has one selected fresh generation, not multiple independent legal
replications. The source critics use fresh contexts on the same configured
provider; their errors may be correlated. The reference functions are separate
exact Python computations authored and audited by the executing Codex agent,
not independently adjudicated legal answers.

## Review findings and repairs

The original design needed revisions before execution. The skeptical audit found
that interpreter JSON numerics are lossy, the Java backend lacks native tracing,
imports need their own locked profile, the large proposed study lacks a sampling
frame, and the host/resume requirements were not concrete. The executed plan
therefore used exact equality inside Catala, rational Java codecs, observed scope
outputs, a builtin-only native profile, declared development tasks and explicit
integrity tests. The audit and the tested implementation are retained in the
plan and each run's `reviewed-sources` directory.

Two implementation errors and one probe error were exposed and repaired:

- Generated Java copy constructors duplicated scope observations. Instrumentation
  now captures calculation assignments, excluding those copies. A reusable
  scope executed for three different people produces three corresponding values.
- The source critic returned SUPPORTED with positive explanatory findings, but
  the first acceptance loop required an empty findings list. Run-01 is marked
  `INVALID_ACCEPTANCE_HARNESS`. The repaired loop uses the explicit verdict.
  Its regression test includes positive findings, and the successor retains
  the original requests/responses with explicit reuse provenance.
- A new exception probe initially assumed that identical consequences must
  conflict. The pinned compiler coalesces identical literal consequences;
  interpreter and Java agree on the checked example. Distinct simultaneously
  applicable consequences raise an error. The test now checks this native
  behavior rather than importing RuleIR's multiplicity policy.

The final source audit also found that bands and deadline candidates assumed
host-enforced nonnegative inputs, while the initial interface stated that only
in prose. Source-quoted numeric bounds now enforce that requirement in both
Python and the Java caller. Out-of-domain snapshots abstain before calculation.
This changes the interface commitment, not the native arithmetic. The final
builds retain identical Catala program hashes and record the mechanical candidate
rebind explicitly; they are not represented as fresh model conversions.

## Behavior and implementation evidence

| Source task | Native computation | Generated-program cases | Final cases |
| --- | --- | ---: | ---: |
| Complete holdings inventory | Map/filter structured holdings and sum exact signed rational amounts | 6 | 6 |
| Tiered charge | Variable rates, bands, exact intermediate arithmetic, one final cent rounding | 9 | 13 |
| Calendar deadline | Calendar-month addition with last-day convention and strict late comparison | 6 | 7 |
| Category formula | Exhaustive native enum with signed/large integer calculations | 9 | 9 |
| Household entitlement | Repeated parameterized scope over distinct people in a list | 5 | 5 |
| Exception hierarchy | Base, licensing exception and suspension exception to that exception | 4 | 4 |
| SFC 23EC35 Annex 1 paragraph 3.3 | Net assets and net assets excluding primary residence | 4 | 4 |
| Total | Seven development tasks | 43 | 48 |

The retained SFC task asks only for the paragraph's two arithmetic definitions,
given correctly classified HKD amounts. It does not infer asset classifications,
account attribution, exchange conversion, SPI eligibility or real legal effect
dates. The original PDF/text edition, source hashes and exact quoted span are
retained. The validity interval is an explicit synthetic assessment setting.

Every value case checks the actual instrumented Java program, an uninstrumented
Java build, and exact equality evaluated inside the pinned Catala interpreter.
Interpreter-to-Java agreement is a backend consistency check. The separately
specified expected value is the behavioral comparator. Money is supplied as
minor-unit strings, decimals as reduced numerator/denominator strings, and dates
as ISO dates. No binary float is accepted at the boundary.

The six compiled mutants alter an eligibility filter, currency scaling, calendar
rounding convention, category multiplier, inclusive age threshold and suspension
guard. Each retained `witness.json` contains the independent expected value and
the wrong Java value/trace from a distinguishing input. Four additional faults
alter value, trace, source map or field evidence and recompute the result hash;
actual Java replay rejects all four. They demonstrate sensitivity to these
faults, not exhaustive fault detection.

The native tests additionally cover missing/conflicting/stale/incomplete inputs,
complete empty collections, field/item evidence, exact fractions, invalid enum
and scalar boundaries, quote coverage, import/attribute rejection, deterministic
builds, damaged JARs, stale/corrupted resumption, two-role host approvals,
idempotency, concurrent revision change, release replacement and historical
replay. A deliberately changed subject revision between calculation and commit
prevents the receipt from being committed.

A broad regression run passed **242 tests**, including the original Java and
Catala backends and merged main's assurance workflows, before the final native
bounds/probe additions. After those additions, all **28 native tests passed**.
The intermediate failed probe and corrected test logs are retained. The package
wheel builds and contains the native Python API and Java bridge; the public
execution CLI returned an exact `1/3` result from a retained portfolio case.

## Runs and model accounting

| Record | Outcome |
| --- | --- |
| `run-01` | Seven handwritten controls / 43 cases passed; live acceptance loop invalidated by verdict-handling bug; 19 model calls retained |
| `run-02` | Same seven task/reference hashes; 11 exact saved completions reused and three fresh calls; all seven candidates passed 43 cases |
| `hardening-01` | No model calls; same generated programs with explicit source-domain metadata where required; 48 cases, six mutants and four evidence faults checked |

The shared ledger advanced from **153 to 175 of 500 calls**. This work used
**22 of its 24-call cap**, including eight unnecessary revision/review calls
caused by the acceptance bug. None were refunded, omitted from costs or counted
again when replayed. Retained usage totals across the 22 distinct completions
are 460,541 input tokens, 66,432 cached input tokens, 4,884 output tokens and
345 reasoning output tokens, as reported by the provider. Billing was not
estimated. The model route was the user's configured `gpt-6-astra` route.

The manifest records Python, JDK 17, pinned Catala 1.2.1, source/toolchain hashes,
exact commands, wall time, source data version and artifact locations. This was
CPU execution; no GPU runtime was imported. Random seeds are not applicable to
deterministic reference cases, and provider samples were fresh unseeded contexts.
The baseline commit was `5290bc53`; copied source fingerprints bind uncommitted
implementation bytes actually executed, rather than attributing them to that
older commit.

## Decisions and uncertainty

| Decision | Primary criterion | Veto diagnostic | Main uncertainty | Next justified action | Unsupported conclusion |
| --- | --- | --- | --- | --- | --- |
| Native converter is a working development feature | Seven candidates compute the expected answers on the declared cases | No remaining observed case mismatch; wrong programs and forged observations rejected | Convenience tasks and finite cases; same-provider correlated interpretation errors | Use the explicit native profile for further reviewed source tasks | General legal correctness or universal expressiveness superiority |
| Final native boundary is usable in the declared development host | Exact values, completeness, time, bounds and transaction checks pass | Domain-assumption gap repaired; corrupt/stale inputs and packages rejected | Production authentication, institutional controls and richer profiles unassessed | Review actual institutional integration separately | Production approval or a drop-in RuleIR release replacement |
| Retain the current default pipeline | No comparative promotion criterion has been measured | No paired quality/cost study or human review study | Additional native expressiveness may or may not improve end-to-end conversion | Prepare representative heldout sources and comparable budgets before ranking | Native converter is better or more accurate than RuleIR |

| Inference status | Finding |
| --- | --- |
| Hard veto screen | Initial acceptance harness invalid; corrected and preserved. Native host assumption gap repaired. All final declared behavioral checks pass. |
| Statistically supported ranking | None; no paired competitor arm or representative sampling design was executed. |
| Descriptive-only differences | Seven of seven development tasks passed; costs and wall times are descriptive observations. |
| Default readiness | Not established; this is a separate optional development path. |
| Next evidence needed | Independently reviewed legal references, whole-source heldout tasks, paired current-RuleIR/minimal-native/reviewed-native arms, uncertainty at source-family level, and human reviewer observations. |

The strongest alternative explanation for the positive result is that explicitly
specified, small computations with declared factual interfaces make this sample
easy, while difficult legal classification has been supplied by the task author.
Unseen qualifiers, ambiguous references or competing readings could expose
failures immediately. These results would not rescue a candidate that fails such
a source test. The weakest evidence remains source interpretation: a fresh model
critic and exact quotations cannot substitute for legal adjudication.

Version 1 explicitly excludes imported modules, optional values, enum payloads,
recursive types and automatic discovery of factual interfaces or domain bounds.
It retains unresolved readings as blocking uncertainty but does not yet search
automatically for a complete set of rival programs. Scope-output observations
are real execution evidence, not full branch tracing. The larger comparative
and human-review portions of the original research agenda remain unexecuted;
their evidence prerequisites are described in the plan.
