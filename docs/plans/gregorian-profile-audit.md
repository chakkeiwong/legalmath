# D3: audit and reproduce the existing Gregorian profile

29 September 2026. This is an offline continuation of the original D0–D6 plan.
The comparator is eligibility-gap-closure G4 attempt 001, not a nonexistent
predecessor implementation. Read `Gregorian.lean`, `gregorian.py`, the independent
source-tree checker, `Lowering.lean`, the actual G4 campaign and mutation tests.
Use the D2 verification snapshot after it has been archived. Do not change the
snapshot or count these repetitions as prospective observations.

## Question and evidence contract

Does the implemented proposition have the declared domain, and can its theorem,
all valid date conversions, native comparisons and nine unchanged retained
reading dispositions be reproduced from the frozen implementation? Primary
criteria: Lean accepts the exact retained propositions with the disclosed
standard axioms and no sorry; all 3,652,059 canonical dates agree with the
independent ordinal and production codec; both native targets agree on all 49
declared cases; eight unchanged encoded readings check and the ninth remains
unencoded. Add declared unknown/conflict inputs to the date fixture to check
both target routes through the shared complete-input boundary. This profile
returns ABSTAIN before native execution. Those boundary cases count as one
shared checking method, not two independent native executions or a new theorem
about lifted semantics.

Promotion veto / repair trigger: an invalid date silently accepted, theorem
premises omitted in a claim, stale reading/source/question identity, a native
comparison or abstention discrepancy, a missing retained reading, imported
certificate assertions trusted without regeneration, or unexplained source
change. A failed candidate triggers its planned repair; it is not rejection of
the research direction. Continuation veto: corrupt required original evidence,
missing toolchain, or a source change during a claimed frozen run. Live quotas
are irrelevant to this offline reproduction and remain zero.

Wall time, case counts and test counts are explanatory. No method ranking,
English interpretation, source completeness, selection of a legally relevant
date, business-day rule, timestamp/evidence selection or whole Java/Catala
compiler correctness is established. A constructor equality theorem is not a
proof of the Python parser. The rank theorem compares integer representations;
canonical string ordering is separately checked over the finite accepted domain.
Keep these proof and computation claims distinct.

## Skeptical audit

The Lean `Date` uses an integer year, zero-based `Fin 12` month and integer day.
`Valid` imposes years 1–9999 and the actual month length. The integer leap formula
and ordinal are checked against lexicographic component order. `rank` deliberately
pads months to 31 days; it is an ordering representation, not elapsed days.
`year_step` uses all integer years, but product dates use the narrower valid
domain. The independent parser checks four ASCII year digits and valid calendar
days. The constructor proof regenerates two trees and asks Lean for equality;
the calendar theorem is separately generated. It does not prove string library
code or a target compiler. These distinctions agree with the current monograph.

G4's 49 native cases have known inputs. They include equality, strict/inclusive
comparison, leap and century boundaries and endpoints. They do not themselves
exercise unknown/conflict facts. The D3 audit therefore adds those factual-state
challenges while preserving the known-date comparator. The first audit incorrectly
expected a native UNKNOWN/CONFLICT status. Inspection of `translation/policy.py`
and `pipeline.py` confirms complete.v1 returns ABSTAIN at its common input
boundary before native dispatch. The repaired check requires that status, the
exact missing/conflicting reason, and an absent native execution record. It
does not count eight boundary requests as native executions or independent
methods. The first failed assertion and all passing G4 reproduction evidence
remain in attempt 01. It reuses no legal labels.
PASS for this bounded audit. A stronger whole-compiler or legal-date claim would
require a different plan and is explicitly outside this acceptance condition.

| Choice | Provenance and status | Failure mode / early check |
| --- | --- | --- |
| G4's full finite date range | Declared supported profile; reviewed baseline | Invalid/leap boundaries missed; inspect parser and enumerate the full declared domain |
| G4's 49 known pairs | Fixed reproduction comparator, not completeness claim | Shared expected answers; independently compute ordinal results |
| Unknown/conflict inputs | Additional engineering hypothesis | Comparison fabricates TRUE/FALSE; inspect both native output statuses |
| Existing Lean/JDK/Catala locks | Recorded project toolchain | Different executable; record hashes and use snapshot toolchain |
| D2 archived implementation | Frozen baseline | Concurrent edits; verify every archived material hash before and after |

## Commands, outputs and bounded repair

The execution entry point is an audit script retained under
`artifacts/gregorian-profile-audit/2026-09-29/`, invoked with the project `.venv`.
It imports the G4 check from the frozen snapshot with explicit `PYTHONPATH`,
regenerates proofs into its own attempt directory, runs the finite codec check,
executes both targets, and writes a command/environment/source manifest, result,
decision table and refreshed next plan. GPU devices are intentionally hidden.
No source downloads, model calls or external writes occur.

Reserve at most three audit attempts before work. A failed attempt keeps its
logs and manifest; retry requires a causal repair note and a passing focused
command tied to current code. Do not reset original investigation issues or
deadlines. A successful audit advances authorized offline work to D4 and records
the remaining proof boundaries. D2's independently running full regression is
still required for its delivery.
