# Catala implementation execution report

The eight-phase master program executed successfully in `artifacts/catala/run-03`
on 24 September 2026. The bounded pilot passes its declared engineering checks.
It has **not been promoted to replace RuleIR**. Executing the eight stages does
not mean that human review, full trace compatibility or production integration
has been completed.

Main was committed and pushed as `66d15b2aee8f0c00076ab1dd24334b5f80dac058`.
The Catala branch, `feature/catala-adapter`, starts from that exact checkpoint in
`.worktrees/catala`. The other worker's subsequent changes on main were preserved.
Before the main checkpoint, 506 tests passed across unit/conformance, assurance,
search and interpretation groups; the reader-facing monograph check also passed.

## Executed evidence

| Phase | Result and practical limit |
| --- | --- |
| 1. Freeze | 35 fixed reference cases checked; reference files match the pushed checkpoint; 112 comparison cases retained |
| 2. Toolchain | Catala 1.2.1 built from pinned upstream source; compiler and source inventory hashed; actual runtime compiled for Java 17 |
| 3. Fragment | Four fixed bundle versions accepted for two pilots; unsupported fixture rules rejected; legal source anchor and six definition locations verified |
| 4. Pilot | Financial-condition and synthetic-exception scopes typechecked with invariant checks and compiled to Java |
| 5. Conformance | 112 exact projected-result comparisons passed across reference Python/current Java and Catala interpreter/Java; two candidate mutations detected; masked-input payload independence checked |
| 6. Host | Draft package executed through the validated Python boundary and a separately compiled Java caller; altered jars, rewritten manifests and malformed Java requests rejected. Existing transaction/release integration remains incomplete |
| 7. Reviewer | Source-linked explanation, five plain-language cases, compiler HTML and rendered PDFs prepared and inspected. No human study has been performed |
| 8. Decision | Optional bounded pilot viable; adoption rejected for now because broader semantics, trace, host and human-review requirements remain |

Of the 112 cases, 82 execute Catala calculations. The other 30 are resolved by
documented shared-boundary rules for conflicting facts, scope or version time.
Those 30 do not provide independent evidence about the Catala compiler. Four
current-Java builds also agree with the full reference results on their cases.
The candidate comparison covers status, type, value, mode, diagnostics, reasons,
missing inputs and blocking inputs. It deliberately does not claim equality of
RuleIR traces; candidate results retain their own source-map identity.

The new implementation and the existing unit, conformance and Java-host regression
checks passed together: **126 tests**, including 19 Catala tests. The definitive
master run took approximately 14.38 seconds, excluding toolchain preparation.
These are exact deterministic checks, not a stochastic performance ranking.

## Findings that affected the implementation

The pinned upstream equal-consequence example coalesces two true exceptions with
the same outcome. The existing RuleIR fixture instead requires `CONFLICT`.
Catala therefore computes an explicit ambiguity code before the host accepts the
amount. The program verifies both the native amount of ten and the ambiguity
code, and detects a deliberate mutation that suppresses the ambiguity check.

The first complete run exposed a missing explanatory message in the version-error
diagnostic. Run 01 is retained as failed evidence; its dependent stages did not
execute. The stable diagnostic constructor repaired the defect. Run 02 then
passed. The final review strengthened result identity, source locations, exact
code snapshots and the separate Java caller before the definitive run 03.

Toolchain preparation first exposed Conda compiler settings inherited beyond
PATH. A fresh switch built in an explicitly selected environment resolved this.
The successful dependency export and preparation logs are retained under
`toolchain-evidence/`. The existing Python environment and JDK were reused without
modification. The installed compiler and downloaded upstream sources remain in
the ignored, isolated `.localresources/catala-toolchain/` directory.

## Decision and next work

| Decision | Primary criterion | Veto diagnostic status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Keep optional pilot; no replacement | Passed for the declared projection and corpus | Human-review, full-trace and transaction/release conditions remain unmet | Generalization and reviewer benefit | Review the source-facing pilot, implement trace and transaction integration, then expand accepted rule profiles | Legal correctness, general semantic equivalence, compiler proof or production readiness |

The next engineering step is to implement the existing host's full trace and
transaction/release contracts for an expanded SPI profile, then run that host's
forced-interleaving and release tests with Catala supplying the decisions.
Human reviewers should compare the same questions and cases in RuleIR and Catala,
with presentation order counterbalanced and correctness and assistance recorded.
That review is a separate evidence requirement, not a reason to discard this
working pilot.

The strongest alternative explanation is that two manually authored scopes avoid
difficulties in arbitrary nested rules and exceptions. An accepted-input
counterexample or broken source commitment would overturn the local conformance
finding. The weakest evidence concerns human reviewer benefit and production-host
acceptance: neither has been established.

## Durable entry points

- Master program: `scripts/catala_master_program.py`.
- Plan and audit: `docs/plans/catala-adapter.md`, `program-review.md`, `program-review.json`.
- Exact final evidence: `artifacts/catala/run-03/run-manifest.json` and `comparison.json`.
- Java package: `artifacts/catala/run-03/host-package/`.
- Trusted package manifest hash: `4e8146b925c6e3dd32baee6c24cd2678cfd16ca6a0887422a1bbac9a9494a8b7`.
- Reviewer text: `artifacts/catala/run-03/reviewer-packet.html`.
- Rendered review: `docs/implementation/catala/rendered/` (two pages per PDF).

The final run snapshots reviewed inputs, records compiler/source/adapter or jar
identity, and hashes every retained result file. Its run manifest contains the
actual command, Git baseline, Python environment, CPU-only status, corpus version,
wall time, plan and result paths. Random seeds are inapplicable to this run.
