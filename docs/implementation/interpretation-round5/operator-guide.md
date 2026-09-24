# Public-reference study and live feasibility operations

The frozen reference set is
`.localresources/interpretation-round5/public-qa-v1/frozen`. Its parent contains
full official pages, extraction diagnostics, original/altered-source provenance,
reference inputs and limitations. `reference-dossier.md` explains the legal
questions and scenario meanings without requiring the reader to reconstruct them
from formulas. `live-result.md` records the latest provider failure.

## Inspect before execution

```sh
/home/chakwong/python/legalmath/.venv/bin/python /home/chakwong/python/legalmath/scripts/run_reference_study_plan.py status
/home/chakwong/python/legalmath/.venv/bin/python /home/chakwong/python/legalmath/scripts/run_reference_study_plan.py preflight
```

The approved runner uses fixed commands, immutable accepted attempts, exact
current-input review, a three-failure limit, executed-repair records and automatic
successor-plan refresh. Status PASSED concerns each phase's declared acceptance.
C2 explicitly accepted safe recording of the investigation; its interpretation
execution remains incomplete. Inspect `execution_complete`, failures, residual
questions, source dependencies and the external status, not just the exit code.

The global allowance remains
`artifacts/interpretation/round2/live-allowance.json`. Historical protection verifies
unchanged prefixes so new authorized calls can be appended without rewriting
earlier evidence. Its ceiling remains 100. The current count is 80, leaving 20.
Do not reset or replace this ledger. A failed provider call still consumes a slot.

## New evaluation behavior

`assurance-evaluate` still executes all four actual adapters. It now validates
frozen derived fields and expected answers before dispatch. An expected answer
must agree with a reference program on its exact hidden scenario. If several
answers are permissible, every accepted signature needs an explicit alternative
reference program with identical declared fact and output meanings. This checks
internal consistency, not the source interpretation's truth.

Selected source regions bind full raw bytes and extracted-text hashes, with exact
region quotes. Changing selection invalidates an assurance request's cached result.
Selection does not turn an excerpt into a complete legal context. The evaluation
scorer requires exact fact declarations and full output declarations; matching
only a polarity tag is insufficient. An unaligned paraphrase therefore abstains
until a separately evidenced correspondence is available.

The public set uses `PUBLIC_QA_INTERPRETATION` for authored translations of SFC
answers and `SEEDED_TRANSFORMATION` for deliberately changed pages. Neither basis
can be labelled a `LEGAL_OUTCOMES` task. The source has authority; the author's
translation still needs verification. Full raw HTML can contain extraction
differences outside the selected FAQ body; those diagnostics remain retained.

## Concrete commands and stopping rules

To inspect admission for a new output directory using the frozen full comparison:

```sh
.venv/bin/python -m legalmath.cli assurance-evaluate \
  --frozen .localresources/interpretation-round5/public-qa-v1/frozen \
  --out artifacts/interpretation/round5/new-admission-check \
  --jdk .localresources/java-toolchain/jdk-17.0.20.1+1 \
  --allowance artifacts/interpretation/round2/live-allowance.json \
  --total-calls 100
```

The current 288-call reservation is refused before provider initialization.
Do not reduce it by dropping arms or silently disabling interpretation checks.
Any different design needs a new frozen contract and claim of its own.

The latest one-family live contract is already consumed and cannot be rerun.
It is bound to the former 78-call ledger. Read `next-phase-plan.md` for a
separate successor after provider availability returns. An 18-call successor
fits the remaining 20, subject to a fresh budget check and review. New live
commands run under the narrowly approved runner prefix with trusted permissions.
No change to model route, credentials, isolation or allowance is authorized by
a failed result.

Institution staging remains separate. The round4 Java-host packages and scheduler
examples are integration fixtures. No local acceptance, source agreement or
automatic monitoring action grants bank release authority.
