# Execute and inspect a qualified result

The [product requirement](product.md) prohibits human quality labels, ratings,
adjudication and acceptance gates. The executable command accepts a retained
shared model and factual cases. Cases have exactly `id`, `snapshot`, `valid_at`
and `known_at`; supplied expected answers and approval fields are rejected.

```sh
PYTHONPATH=src:. .venv/bin/python -m legalmath.cli rules assure \
  --model model.json --cases cases.json --out fresh-qualification \
  --jdk .localresources/java-toolchain/jdk-17.0.20.1+1 \
  --compiler .localresources/catala-toolchain/opam-root/catala-clean-1.2.1/bin/catala \
  --upstream .localresources/catala-toolchain/catala-0f895e048d19dbe72f24cdd6d5f3398bfe1335fa \
  --lock docs/implementation/catala/toolchain-lock.json
```

Both targets remain in `qualification.json`. A richer model can run through
native Catala while RuleIR remains explicitly unsupported. A missing tool,
unresolved premise, unencodable operation or failed case does not disappear from
the report. The existing translation/build formats remain unchanged. This route
is additive; it does not reinterpret historical release approvals as evidence.

The Lean certificate proves equality between independently reconstructed formal
constructor trees. Consequently every meaning assigned to those constructors
returns the same result on every input context. The current fragment includes
Boolean and integer/money syntax, arithmetic, comparisons, exact scaling,
conditionals, strict defaults, typed helper bodies and rule references. This is
a per-program structural lowering proof. It does not prove the English reading,
the meanings of factual classifications, target lowering, compiler or JVM.
Rich unsupported proof fragments remain qualified even when runtime checks pass.

For complete known observations, an independent evaluator reads the original
formal expressions and computes exact expected results. It uses integer and
rational arithmetic and independently implemented date/list operations. It never
uses candidate output as its answer key. Partial observations and nested partial
results outside this evaluator's domain remain explicit unsupported comparisons.
Native execution is also compared with plain Java and the pinned original Catala
interpreter; scalar execution is checked against the original RuleIR evaluator.
Shared assumptions remain shared and are not presented as independent legal truth.

Recheck against the model and source revision currently requested by the caller:

```sh
PYTHONPATH=src:. .venv/bin/python -m legalmath.cli rules verify-assurance \
  --model model.json --directory fresh-qualification \
  --jdk .localresources/java-toolchain/jdk-17.0.20.1+1 \
  --compiler .localresources/catala-toolchain/opam-root/catala-clean-1.2.1/bin/catala
```

Rechecking regenerates and runs the permitted Lean proof, verifies actual builds,
replays executions and recomputes the qualification. Imported proof text and
claimed checker results are not executed or trusted. Source, model, method,
proof-scope, case-membership and result changes fail verification. Old runs remain
readable for their historical revisions. `QUALIFIED` means the exact stated
properties have evidence; it never means general legal correctness.

## Prospective sources

The separate command manages a frozen source window:

```sh
PYTHONPATH=src:. .venv/bin/python -m legalmath.qualification freeze \
  --out future-window --family public-regulatory-amendments \
  --ends-at 2026-10-28T23:59:59Z
```

Retain the returned `window_hash` outside the mutable directory. Declare all
already-used packet hashes with repeated `--development-source` arguments. An
admission record has exactly `task_id`, `family`, `source_hash`, `question_hash`,
`published_at` and `first_seen_at`. The source identity is the retained packet
hash; the question identity is the retained proposed statement hash. This binding
does not itself prove that the statement answers the original legal question.

`admit --directory ... --window-hash ... --item item.json` records every submitted
task, including ineligible sources. Publication and encounter chronology, frozen
family, development reuse and current method identity control eligibility.
`repair --directory ... --window-hash ... --reason ...` preserves earlier events
and marks subsequent work as development. A repaired method requires a later
untouched confirmation window. API `prospective.observe` rechecks an actual
qualification, matches its retained source/statement/method and rejects synthetic
fixtures as prospective publications. No supplied quality grade is accepted.

`report --directory ... --window-hash ... --head-hash ...` checks an externally
retained event-head commitment and reports eligible, observed, pending and
ineligible tasks. Without a head commitment the report explicitly qualifies the
local hash chain: a self-contained chain cannot detect a fully rewritten history.
Neither hashes nor local timestamps prove publication authenticity or that all
relevant publications were discovered. The current module accepts submitted
sources; an authenticated complete source-acquisition process remains future work.

The engineering campaign opens a real future window and records zero future
publications observed. It cannot produce future observations today. Model
pretraining contamination is also not established absent training provenance.
All prospective reports therefore retain `unknown_future_legal_generalization:
NOT_ESTABLISHED`. This is not a request for human grading.

## Remaining language and execution limits

The qualification includes actual resource expansion, library domains, used
operations, uncertainty, trace coverage and unsupported targets. Current resource
limits remain defensive bounds; the campaign does not increase them. The
versioned library registry describes existing operations and the requirements for
adding signatures, semantics, pinned dependencies and independent challenges.
It does not enable arbitrary imports.

The pinned Catala compiler rejects recursive types. Finite explicit graphs and
bounded traversals require their own meaning-preservation argument; general
recursion requires compiler/language work. Tracing observes emitted Java choices
and scope assignments, while optimized-away choices and external library internals
remain unobserved. A full backend/codec proof, complete partial-value independent
semantics, larger measured resource profiles and general performance comparisons
remain separate extensions. None is silently inferred from a passing case.
