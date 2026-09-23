# RuleIR 0.1: normative execution semantics

Status: proposed engineering specification, 21 September 2026. This document fixes
the prototype's meaning. Its regulatory interpretations require compliance review.
The JSON Schema fixes structure; this document fixes constraints that a schema
cannot express. Every implementation must reject unsupported constructs.

## 1. Scope and terminology

RuleIR is a finite, acyclic expression language. It computes named subconditions
from dated evidence. It is not a general legal logic, natural-language parser,
authorization system or implementation of the whole Catala/default-logic calculus.
Its default operator borrows explicit exception structure from Catala; its
three-valued treatment of missing data is a separately specified design choice.

A `RuleBundle` contains declarations, rules, source spans and interpretation
identifiers. The interpreter takes a bundle, a rule identifier, a fact snapshot,
`valid_at` and `known_at`. All timestamps use UTC, exactly
`YYYY-MM-DDTHH:MM:SS.ffffffZ`. Local legal dates use ISO `YYYY-MM-DD`; calendar
conversion uses the explicit `Asia/Hong_Kong` zone. Neither time is inferred from
the process clock. `valid_at` is the event time being assessed; `known_at` limits
the evidence that may be used. Interval endpoints are `[from, until)`, with null
`until` meaning no specified end. Missing effective dates prevent release.

The prototype is about evidence of particular conditions. `FALSE` does not mean
the transaction is unlawful; `OUT_OF_SCOPE` does not mean it is permitted.

## 2. Types, values and evidence

The only scalar types are `bool`, `integer`, `money_hkd`, and `date`.
Known booleans use JSON booleans. Integers and money use canonical signed base-10
strings matching `0|-?[1-9][0-9]*`, with arbitrary-precision integer arithmetic.
`money_hkd` is **HK cents**, so HK$40 million is `"4000000000"`. Money may be
negative, for example net assets; declaration-specific bounds constrain a domain
when needed. Dates must be valid Gregorian dates from 0001-01-01 to 9999-12-31.
JSON floating-point numbers, exponent notation, `-0`, implicit casts and null as a
known value are forbidden. Foreign-currency conversion is outside RuleIR 0.1.
It produces an independently evidenced HKD input with rate, instant and rounding
policy. A missing rate produces unknown evidence, never a guessed conversion.

Each declared fact has one snapshot entry. Its evidence status is `known`,
`unknown`, or `conflict`. A known entry supplies a value, evidence identifiers,
validity interval and recorded timestamp. Unknown entries supply reason codes
such as `MISSING`, `STALE`, `UNREVIEWED_ASSESSMENT` or `ORDER_UNRESOLVED`.
Conflicting entries preserve the contradictory evidence identifiers.

The input-normalization boundary selects records valid at `valid_at` and recorded
no later than `known_at`. Two admissible, non-superseded records with different
values yield conflict. Identical values may combine evidence. A correction must
name the record it supersedes; arrival order is not an authority ranking.
The evaluator does not pick between conflicting sources. Facts outside their
valid interval are unknown. There is no global freshness default: feed-specific
freshness rules must supply the validity interval.

Before evaluating, validate every fact in the **static transitive dependency
closure** of the requested rule, including its scope and exception branches.
Conflicting evidence in that closure returns `CONFLICT`, even if another route
could establish the result. A conflict in an unrelated declared fact does not
block this rule. This conservative input policy is deliberate and differs from
three-valued Boolean short-circuit reasoning.

## 3. Expressions and type checking

Every expression has a bundle-unique `node_id`. Identifiers are ASCII and match
`[a-z][a-z0-9_.-]*`. A `fact` reference names a declaration; a `rule` reference
names a rule result. Referenced rules must have unconditional scope (`true`):
otherwise the author must explicitly expose the scope as a Boolean definition.
This prevents silently treating `OUT_OF_SCOPE` as false. Dependencies include
scope, exception guards and all branches. Cycles are rejected before execution.
Source-span IDs and interpretation IDs must also be unique within their own
bundle collections. Every interpretation's source references must resolve, just
as rule and exception source references do. The current fixture helper is not
a complete validator for these requirements; master-plan T05 implements them.

| Expression | Required fields | Type and meaning |
| --- | --- | --- |
| `literal` | `type`, `value` | The declared scalar value; no unknown literal |
| `fact` | `name` | Declared fact type; unknown if its evidence is unknown |
| `rule` | `name` | Referenced unconditional rule's declared type |
| `all`, `any` | nonempty `args` | Boolean operands; truth tables below |
| `not` | `arg` | Boolean negation |
| `compare` | `cmp`, `left`, `right` | `eq`, `ge`, `gt`; identical integer, money or date types; Boolean result |
| `add`, `sub` | `left`, `right` | Both integer or both money; same result type |
| `scale` | `arg`, `numerator`, `denominator` | Integer or money times a nonnegative integer numerator divided by a positive integer denominator |
| `if` | `condition`, `then`, `else` | Boolean condition, equal branch types |
| `default` | `base`, `exceptions` | Base and every exception value have the same type; guards are Boolean |

`scale` requires exact division of a known result; otherwise return
`E_INEXACT_SCALE`. This avoids inventing a fractional-cent ownership policy.
An unknown operand yields unknown without arithmetic. `add`, `sub` and comparison
likewise propagate unknown. Date arithmetic is outside the expression grammar;
reviewed calendar operations belong to obligation scheduling in section 7.

All operators, extra properties, references, result types and literal values are
checked before evaluation. Type mismatches are `E_TYPE`; unknown references are
`E_REFERENCE`; duplicate identifiers are `E_DUPLICATE_ID`; cycles are `E_CYCLE`.
Array order is preserved for trace presentation, never used as normative priority.

## 4. Unknowns and evaluation order

For booleans, known true, known false and unknown correspond to T, F and U.
Negation maps T to F, F to T and U to U. Conjunction is F if any operand is F,
T if all operands are T, and U otherwise. Disjunction is T if any operand is T,
F if all operands are F, and U otherwise. `all` and `any` evaluate **every** operand
in array order and propagate a runtime error or exception conflict even where
another operand would determine a Boolean answer. Thus traces and failures do not
depend on an optimizer's short-circuit choice.

`if` first evaluates its condition. T evaluates only `then`; F evaluates only
`else`; U returns an unknown of the branch type without evaluating either branch.
The skipped branches remain in the static dependency closure and are type checked.
Even equal branches do not collapse an unknown condition. Consequently
`A or not A` returns U for unknown A; this is not classical reasoning over all
completions of A. A solver must encode these truth tables, not silently replace
unknowns with unconstrained classical truth values.

Each result carries `missing_inputs` (all encountered unknown fact references)
and `blocking_inputs` (the subset conservatively blocking the result). For a known
Boolean result the latter is empty even if `missing_inputs` is nonempty. For U,
use the union of unknown dependencies encountered along evaluated branches. This
is a deterministic conservative explanation, not a minimal explanation algorithm.
Arrays of identifiers in results are lexicographically sorted and duplicate-free.

## 5. Explicit exceptions

An exception is `(exception_id, guard, value, interpretation_id, source_span_ids)`.
Evaluate every guard in declaration order before selecting a value.

1. Two or more T guards yield `CONFLICT` with `MULTIPLE_EXCEPTIONS`, even if their
   values would agree. Do not evaluate those values or the base.
2. Otherwise any U guard yields an unknown of the result type, including when one
   other guard is T. The unknown guard might become a competing exception.
3. Exactly one T and all remaining F evaluates that exception's value.
4. All F (including an empty exception list) evaluates the base.

A runtime error in a guard is an error. A conflicting nested default is a conflict.
Priority is expressed only by nesting defaults, with a separately cited and
reviewed interpretation for that nesting. Numeric priorities, first-match wins,
publication-date priority and implicit `unless` translation are unsupported.
This restricted form intentionally avoids the richer team-defeat semantics of
defeasible logic. A rule needing incomparable general priorities stays a review
issue in v0.1.

## 6. Rule results and deterministic explanations

Validate the bundle and input closure, then evaluate the scope. F returns
`OUT_OF_SCOPE`, U returns `UNKNOWN` with `SCOPE_UNKNOWN`, and T evaluates the body.
Known Boolean bodies return `TRUE` or `FALSE`; known non-Booleans return `VALUE`
with their type and value. Unknown bodies return `UNKNOWN`. Evidence or default
conflicts return `CONFLICT`. Validation/runtime failures return `ERROR` with an
error code. These are disjoint tagged results; no result uses a truthy string as
a Boolean value. A bundle outside its validity interval is `ERROR/E_VERSION_TIME`.

The trace is a postorder list of evaluated nodes containing node identifier,
operator, child identifiers, type, value/status, evidence references and source
span identifiers inherited from the rule. Shared rule nodes are memoized per
request. Skipped `if`/default values get explicit `SKIPPED` trace entries without
an invented value. Deterministic explanations are generated from this trace.
Source text and model-produced prose cannot override a computed trace.

The result identifier is the SHA-256 of canonical request plus canonical semantic
result. Exclude wall-clock duration, request identifiers and service timestamps.
The request includes bundle and input hashes, both assessment times and engine
version. Canonical JSON is specified in `contracts.md`; never hash pretty-printed
JSON or mutable file paths.
The exact wrapper is `{"request": request, "result": semantic_result}` as
defined there. Cross-backend equality excludes engine identity and its resulting
execution hash, but checks every semantic field and independently verifies each
native hash. The two backends must not pretend to have the same implementation
identity.

## 7. Separate finite event profile

The event profile is an audit/replay component, not another expression operator.
It supports consent granted/withdrawn, an obligation opened, a matching performance
record, and a watermark. Normative templates define actor, action, subject,
category, activation and either an explicit deadline or `deadline_unspecified`.
Templates can derive deadlines through `anniversary(date, years, leap_policy)`;
`leap_policy` is mandatory (`feb28`, `mar1`, `reject`) and is a reviewed bank
interpretation, not a rule inferred from the SPI circular. Convert the end of a
local due date to the next local midnight exclusive. No business-day calendar or
open-ended temporal logic is implemented in v0.1.

Every event has an immutable ID, stream ID, UTC occurrence timestamp, recorded
timestamp and a positive authoritative sequence number. A stream contains one
client/category or one identified obligation. Equal occurrence timestamps may be
ordered by that sequence only when the connector declares its ordering authority.
Without this declaration return `E_ORDER_UNRESOLVED`; receipt order never settles
the legal order. A duplicate ID with identical canonical payload is a no-op;
the same ID with different content is `E_EVENT_ID_COLLISION`.

Replay selects only events with `occurred_at <= valid_at` and
`recorded_at <= known_at`, then orders by occurrence time and, for ties, the
authoritative sequence. A stream header fixes `inception`, subject/category,
profile version and ordering authority. Consent completeness is an evidenced
statement `complete_from`, `complete_through`, `recorded_at`, `evidence_id`:
it must be known by `known_at` and cover inception (or the reviewed initial
snapshot) through `valid_at`. Obligation watermarks instead attest the stated
window from activation through their `complete_through`; they cannot certify
times beyond the replay's `valid_at`. A completeness assertion is a connector
input whose provenance must be checked, not a fact inferred from an empty queue.
Neither consent completeness nor an obligation watermark may certify an instant
later than its own recording time. Future completeness is an invalid premise;
the replay stays unresolved rather than asserting active consent or a breach.

For consent, grant sets `ACTIVE`, withdrawal sets `WITHDRAWN`; before a grant the
state is `NOT_ESTABLISHED`. A withdrawal is idempotent. A new grant is possible
only with a new evidence reference and creates a new consent generation.
This initial state requires a complete stream from its declared inception, or
a reviewed initial snapshot and a complete subsequent stream. A connector that
cannot establish completeness returns `UNKNOWN/HISTORY_INCOMPLETE`; an empty
partial export does not prove that no consent exists.
Observed transactions are retained even if consent was withdrawn: the audit view
records a violation candidate; the advice view cannot authorize streamlined use.

An obligation's status is `OPEN`, `SATISFIED_ON_TIME`, `BREACHED`, or
`PERFORMED_LATE`. Opening records activation, due condition and source version.
Performance must match obligation ID, actor, action and subject. For the supported
non-preemptive achievement obligation, an occurrence before activation is not
satisfaction. An admissible performance in `[activation, deadline)` satisfies it.
A watermark at or beyond the deadline proves that the ordered observation window
is complete; absent timely performance, it becomes breached. Without that
watermark, absence of a record is insufficient evidence of breach. A deadline-free
obligation stays open until performed and is not declared overdue by elapsed time.
No runtime wall-clock call creates a watermark.

Late performance records `PERFORMED_LATE` and retains `breached=true` plus the
breach identifier once the observation window through the deadline is complete.
Until then, retain the late performance record with status `OPEN`: a missing
earlier performance might still establish timely satisfaction. A separate corrective task may be linked, but does not erase
the breach. Waivers, sanctions, legal compensation, maintenance duties and
pre-emptive performance require later profiles; the engine rejects templates
requesting them rather than guessing their meaning.

Late-arriving records create a new replay result; original decisions and their
`known_at` snapshot remain immutable. A correction may establish that performance
actually occurred on time. The corrected result supersedes the earlier assessment
and explains the changed evidence; it does not rewrite the historic record.

## 8. Solver scope and assurance claim

The v0.1 Z3 adapter accepts acyclic Boolean/integer/money expressions, explicit
knownness bits and bounded input domains. It initially rejects `date`, `scale`,
`default`, event semantics and source/lifecycle validation with `UNSUPPORTED`.
This is a deliberately smaller fragment than the interpreter. Expand it only
with the corresponding semantics and conformance cases.

Encode each Boolean expression as two Boolean formulas (is_true, is_false), with
U represented by (false,false). For conjunction, true is the conjunction of child
true formulas and false the disjunction of child false formulas; disjunction is
dual. Negation swaps the pair. For numeric comparison both outputs require known
operands; then the comparison chooses true or false. Assert that true and false
are never both set. Numeric expressions carry a knownness bit and integer value.

First check the declared domain D for satisfiability. UNSAT returns
`INCONSISTENT_DOMAIN`, not equivalence. Then search D for a difference between
the candidates' tagged results. SAT returns `COUNTEREXAMPLE` and a concrete
snapshot which both interpreters must replay before it is displayed. UNSAT returns
`NO_COUNTEREXAMPLE_IN_DECLARED_DOMAIN`. UNKNOWN or a timeout stays `UNKNOWN`.
Store formula, domain, engine version, input hashes and solver output. A solver
answer is not a machine-checked proof certificate unless a separate checker
actually verifies a supported certificate.

No check in this profile proves fidelity to the circular. That question is
addressed by source coverage, reviewed interpretations and independent scenarios.
