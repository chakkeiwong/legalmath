# Prospectus interpretation and SFC decisions: executable master program

29 September 2026. Status: reviewed design; implementation and execution follow.

## Question and scope

Can LegalMath preserve original offering documents, recover useful source-linked
instrument descriptions, and execute justified product-classification, selling-rule
and sophisticated-professional-investor (SPI) decisions without human quality
labels? The user-provided documents are development sources. They are not a
representative sample or an untouched generalization test. Their accompanying
Gemini descriptions are not answer keys.

The question has three separate propositions: the bytes and quotations were
preserved; a decision follows from specified formal premises; the premises fully
and correctly represent the relevant documents and law. Machine checks can
establish the first two in stated domains. The third remains NOT_ESTABLISHED
unless a particular obligation is independently discharged. No human ratings,
adjudication, approval, or acceptance contributes quality evidence. Operational
permission to run commands is unrelated to correctness.

## Design amendments after inspecting the actual documents

* Retain preliminary and final documents separately. Resolve a final document as
  a new source, never by filling blanks in the preserved preliminary text.
* Model an instrument document package, not one PDF. Base programmes, issue
  terms, supplements, incorporated documents and subsequent amendments have
  distinct roles. Incompleteness is a result, not an implicit negative fact.
* Distinguish contractual conversion, contractual principal write-down,
  discretionary distributions, insolvency and statutory resolution. In particular,
  the supplied UBS draft includes conversion. Country or issuer labels cannot
  determine the loss mechanism. A non-cumulative dividend is not principal
  cancellation.
* Preserve page-level text and quotations, explicit candidate interpretations,
  missing premises and contradictions. Literal matching verifies quotation
  provenance; it does not prove entailment, scope, authority or completeness.
* Keep instrument semantics separate from SFC rule semantics and client/trade
  facts. Use the shared LegalRuleModel and direct target adapters for both
  RuleIR and Catala. Never ask either backend to independently interpret English.
* Results are per question and as-of date: classification, relevant selling
  obligations and permission to streamline this transaction. A complex product
  is not automatically ineligible; an incomplete client file is not evidence of
  eligibility. Use conservative possible-world evaluation for missing facts and
  retain conflicts. Regulatory discretion is an explicit input event.

## Research intent and evidence contract

| Item | Contract |
| --- | --- |
| Main question | Can source-grounded conditional decisions and formal guarantees survive unfamiliar contractual combinations and incomplete evidence? |
| Mechanism | Versioned source packages, typed event/rights models, independent formal semantics, explicit qualifications, shared backend execution |
| Baseline | A documented name/keyword classifier as a deliberately naive diagnostic; existing shared-model assurance is the engineering comparator |
| Primary pass criterion | All retained sources accounted for; checked scoped theorems; independent semantic challenges and supported backend executions agree; no missing premise produces unconditional permission; phase repairs and refresh actually execute |
| Promotion veto | Wrong semantic result, unexpected backend disagreement, invalid proof, stale evidence, silently discarded input, false complete/final claim, hidden failed phase |
| Continuation veto | Corrupted original source, unavailable required checker after bounded recovery, exhausted campaign budget, or unresolved implementation error that invalidates subsequent evidence |
| Repair trigger | Fetch failure, preliminary/missing issue terms, failed parser/codec invariant, stale derivative, failed phase or regression |
| Explanatory only | Counts of extracted clauses, keyword agreement, runtime, source coverage, number of passing examples |
| Non-conclusions | Unrestricted English/legal correctness, complete discovery of applicable law, future-law generalization, source authenticity from hashes alone, superiority of Catala over RuleIR |
| Evidence | docs/prospectus originals and acquisition manifest; artifacts/prospectus-master versioned phase attempts; machine reports, proof logs, tests, phase reviews and refreshed next-phase plans |

The naive baseline is not a promotion comparator for legal accuracy. Its mistakes
are useful counterexamples to the tempting country/name heuristic. The principal
comparison is exact agreement with independently specified mathematical semantics
on generated inputs. Real-document reports preserve uncertainty rather than
being assigned authored correct-answer labels. An all-undetermined run may be
honest but cannot count as useful extraction; report that coverage separately.

## Phases and automatic continuation

| Phase | Work and required evidence | Repair and next-phase consequence |
| --- | --- | --- |
| P0 preserve | Download every distinct supplied link, original bytes, URLs, times, HTTP status, checksums and document role; parse PDFs/HTML | Retry bounded transient failures; retain failure records; acquire official mirrors without replacing source identities |
| P1 complete | Inspect document packages; acquire final UBS/Capital One and a specific HSBC AT1 where available; retain preliminary and programme-only cases | Execute available document repairs; unresolved referenced terms become explicit open dependencies |
| P2 interpret | Page-linked observations, candidate instrument features, event/rights models and source-bound SFC rule specification | Re-extract stale derivatives; fix observed scope/negation/format bugs; do not infer missing terms |
| P3 prove | Kernel-check stated formal theorems and solver-check independent obligations; complete finite domains and exact numerical boundary checks | Repair implementation/theorem mismatch and rerun focused checks; never weaken the declared property silently |
| P4 execute | Generate shared models and factual cases; execute RuleIR and native Catala with existing pinned toolchain and independent evaluator | Correct local conversion/serialization failures; preserve both failed and repaired evidence |
| P5 challenge | Missing/conflicting evidence, amendments, issuer/name changes, negation, threshold boundaries, dependency failures, tampering, and controller interruption/resume | Record counterexamples and apply bounded documented repairs; regressions must pass before continuation |
| P6 freeze/report | Replay verification, record qualification for every document/question, freeze source/method identities and future-test protocol, final review | Refresh an actionable next program from actual remaining gaps; no fabricated future observations |

The controller records each attempt in a new directory. It classifies failures
before deciding whether to repair, continue with explicit qualifications, or stop.
After each phase it writes a result-driven review and a new next-phase plan with
resolved/open issues, required inputs and validation. Resume rechecks source and
method hashes and invalidates affected downstream evidence. A phase marker alone
does not establish completion. Intentional fault-injection repair tests are
labelled as such; actual source-completion repairs are reported separately.

## Test and proof programme

1. Archive integrity: PDF signatures/page extraction, HTML title/text, raw-byte
   changes, failed HTTP bodies, duplicate and missing documents, final/draft roles.
2. Evidence: exact quotation/page binding, amendment precedence only when stated,
   foreign-issuer references, negation, contingent versus ordinary conversion,
   unknown versus affirmative absence, input facts without expected-answer fields.
3. Contractual semantics: permanent/temporary write-down, restoration limits,
   equity conversion and surviving rights, exact rational amounts, all threshold
   sides, independent trigger predicates, cancelled dividends versus principal.
4. Decision semantics: complete and incomplete clients, incorrect/unselected
   categories, absent/withdrawn consent, conservative objectives, threshold modes,
   leverage and solicited versus unsolicited procedures. A bounded implemented
   rule subset must never be advertised as the complete SFC regime.
5. Universal formal properties: soundness of definite decisions over enumerated
   possible worlds, preservation under removing uncertainty, necessary conditions
   for streamlining, and relevant contractual loss identities. State whether a
   theorem covers the abstract specification, the actual generated program or a
   backend. A constructor-lowering proof is not a backend correctness theorem.
6. Generated semantic tests: construction supplies a mathematical specification,
   independent evaluation supplies expected values, and metamorphic transformations
   have explicitly justified invariants. No human or LLM quality labels.
7. Real target checks: same rules/facts through both languages; conditional source
   interpretations remain conditional even when all executors agree.
8. Generalization: hold out entire contractual combinations in the generated
   grammar when fitting a learned extractor; this deterministic first campaign
   instead enumerates every combination in its declared finite event domain.
   Freeze a prospective protocol for new issuer/template/time families.
   No existing downloaded document is relabelled as unseen future evidence.
9. Supervisor: failure retention, executed repair, refreshed plans, changed-source
   invalidation, idempotent resume, missing evidence and bounded retries.

## Assumptions, defaults and pre-mortem

| Choice and provenance | Justification and status | Failure mode and earliest check |
| --- | --- | --- |
| Supplied documents | User-selected development corpus | Familiar-source fitting; never claim held-out legal accuracy |
| Existing Python/JDK/Catala/Lean | Reuse installed pinned tools; reviewed engineering default | Version mismatch; preflight versions and checked identities |
| Deterministic candidate extraction | Transparent bounded initial implementation, heuristic only | Wrong referent/negation; quoted counterexamples, keep unresolved alternatives |
| Explicit formal rule subset | Sources are premises; interpretation remains a hypothesis | Missing exception; obligation inventory and qualification per output |
| Exact rational arithmetic | Monetary/ratio boundary semantics | Currency or rounding mismatch; unit and divisibility tests |
| Three automatic attempts per phase | Convenience budget, not scientific evidence | Infinite retry or lost failure; state-machine tests and retained attempts |
| CPU only; no paid model calls | Sufficient for formal and deterministic campaign | Does not evaluate an LLM front end; disclose this limit |
| Maximum six hours, 256 backend cases, 32 source downloads | Bounds this initial campaign; reviewed resource budget | Undercoverage; publish denominators and remaining work, do not claim exhausted-domain validity |

The campaign could pass while merely proving the wrong encoding. Accordingly,
source meaning, scope, rule completeness, formal semantics, translation and actual
execution have separate result fields. Source quotation checks and solver success
cannot promote one field into another. A missing tool is an environment failure;
a counterexample to an encoded rule is an implementation/specification failure;
neither alone rejects the research direction.

## Commands and permissions

One fixed entry point is used without shell fragments or environment prefixes:

```
/home/chakwong/python/legalmath/.venv/bin/python /home/chakwong/python/legalmath/scripts/prospectus_master.py preflight
/home/chakwong/python/legalmath/.venv/bin/python /home/chakwong/python/legalmath/scripts/prospectus_master.py run
/home/chakwong/python/legalmath/.venv/bin/python /home/chakwong/python/legalmath/scripts/prospectus_master.py status
/home/chakwong/python/legalmath/.venv/bin/python /home/chakwong/python/legalmath/scripts/prospectus_master.py verify
/home/chakwong/python/legalmath/.venv/bin/python /home/chakwong/python/legalmath/scripts/prospectus_master.py future
```

The project allow list lists fixed actions, public source URLs, output locations,
timeouts and budgets. A matching Codex prefix rule is prepared and checked using
`codex execpolicy check`. Installing that rule outside the workspace and trusted
execution use platform approval upfront, with the same literal command prefix.
Existing broad rules are not expanded. No arbitrary shell command, model call,
deployment, secret access or unrelated campaign mutation is part of this program.

## Skeptical review before implementation

REVISED AND ACCEPTED FOR SCOPED EXECUTION. Material flaws in the earlier sketch
were treating a single PDF as a complete contract, using country labels as loss
mechanisms, and risking promotion of runtime agreement into legal correctness.
The amendments above resolve the engineering design flaws and explicitly retain
the unproved interpretation/completeness boundary. Backend comparison uses equal
formal inputs, stale sources invalidate results, repairs are executable and
budgeted, and the final artifact answers the original two SFC questions with
qualifications. No material unexamined scientific default is promoted. Results
will include a decision table, actual run manifest and terminal red-team review.

## Review after first complete execution

The first full execution passed all seven phases. Its source coverage still lacked
the Lloyds issue document. A public Yahoo Finance mirror of the exact SEC filing
was subsequently downloaded and inspected; the next execution adds this separately
identified copy without claiming it is the unavailable issuer PDF. UBS AES parsing
was repaired using installed Poppler; transport negotiation repaired the Capital
One downloads. Each failed attempt remains available.

The first final review also identified that a backend-only prospective observer
could not bind the complete extraction method. The implemented `future` action now
freezes the full method independently of the growing source inventory, registers
chronology before candidate analysis, rejects development sources/changed methods,
and records machine-checked quotations with qualified decisions. Its append-only
observations live outside the immutable completed-phase directories. Tests use
explicit simulated dates and do not count as real prospective observations.

Audit disposition: continue with these repairs, then rerun affected phases and
verification. No baseline, formal obligation or legal non-conclusion is weakened.
Exact enumeration replaces a meaningless synthetic holdout where no fitting takes
place. Unknown future legal generalization remains unproved.
