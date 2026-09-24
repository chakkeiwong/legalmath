# D1: smaller interpretation tasks with preserved cross-context checks

Date: 24 September 2026. User asks why the provider overloaded and authorizes
breaking the work into smaller pieces and continuing where possible. Baseline
C3 passed 520 tests. Global model allowance: 80/100 consumed, 20 remaining.
Preserve the round5 sources, cases and every prior attempt. Do not touch the
unrelated monograph work or raise/reset the allowance.

## Question and pre-run skeptical audit

Can bounded decomposition complete the previously failed inventory without
silently losing definitions, exceptions or cross-question relationships? The
comparator is the actual C2 request: 29 source units, 4,903 source characters,
21,224/21,308 request bytes and a 3,417-byte schema. One call explicitly reported
server overload; the other hit 180 seconds. These facts do not prove an input-size
limit. Smaller requests are an implementation hypothesis and a useful diagnostic,
not a guarantee that external service overload disappears.

Official documentation search returned 502, and direct official error-guide
retrieval returned 403. Do not invent a documented provider limit or claim a
particular model/account service issue. Use the retained actual failure messages.
The existing provider route and worker isolation remain unchanged.

Audit PASS WITH REQUIRED ENGINEERING CHECKS: naive chunking would lose context,
duplicate claim IDs, accept a partial result as complete, or spend more calls than
available. Repair those risks before live work. A small connectivity success
is not interpretation accuracy or superiority evidence. A failure on a minimal
task is an external continuation veto for larger dependent requests.

## Design and evidence contract

Implement optional chunked inventory with deterministic bounded source-unit
groups, exact IDs/text, a local map to full retained source spans, and distinct
claim/dependency namespaces when merging. Each of two independent readers covers
every piece. After each reader's pieces, a separate compact check sees the full
source text and that reader's assembled claims to identify cross-piece
qualifications. Missing pieces or an unavailable cross-piece check mean that
reader is incomplete. Preserve successful pieces and failures for exact replay;
never give one reader the other reader's output. Do not split an oversized
paragraph silently; report its explicit bound failure.

Compact transport removes repeated hashes, locators and span dictionaries from
model inputs while retaining exact unit IDs/text, source identity and a hash-bound
full request locally. Source text and every schema/evidence validation remain
unchanged. The receiver is asked for concise structured explanations, without
discarding a claim to meet a suggested length. Final generation still sees the
full retained source context. Fidelity already has bounded pair batching.

Primary engineering acceptance: all source units covered exactly, no partial
reader promoted, cross-piece omissions remain unresolved, duplicate local IDs do
not conflate claims, each request/response/source mapping is retained, every live
action is counted, exact replay never spends a second call, and transport errors
stop futile downstream dispatch. Probes and actual Java replay remain required
for generated supported candidates. A passed packet reduction check is only
an explanatory diagnostic, not promotion evidence for interpretation correctness.

For live feasibility, freeze source/settings/code and a small-task request before
dispatch. Allocate at most two service probes followed by an admitted inventory /
assurance path within the same 20-call maximum. The minimal probe contains no legal
reading and does not count as an inventory piece. Preserve actual completed pieces
for manifest-verified replay without another paid call. Retry
only a transient failure once under a separate counted action; an unresolved
service failure stops the live phase while deterministic engineering continues.
No four-arm ranking, population error bound or review-cost saving is concluded.

## Defaults and stop/repair rules

| Choice | Provenance/status | Failure mode | Early check |
| --- | --- | --- | --- |
| About 2,300 source characters and 16 units per inventory piece | Convenience hypothesis from the failed packet | A material relation crosses boundaries or a long unit does not fit | Coverage plus cross-piece adverse test; oversized-unit refusal |
| Two independent readers plus two full-context checks | Existing redundancy extended to pieces | Same model correlation, shared omitted premise | Retain independent inputs and disagreements; no independence probability claim |
| Compact source transport | New optional engineering mode | Wrong citation mapping or dropped qualifiers | Exact text/ID equality and request/hash reconstruction |
| Maximum 20 new calls | Existing user allowance | Pieces consume all budget before synthesis | Compute minimum path before live admission; explicit incomplete result |
| Existing 180-second call deadline | Prior feasibility setting, not optimized | Slow valid response misclassified as defective reasoning | Keep timeout distinct from semantic failure |
| Sequential requests | Avoid additional provider concurrency | Slow completion | Bounded process time and regular progress reporting |

Promotion vetoes: missing coverage, false completion, source mismatch, failed
cross-context check, corrupt replay or unjustified meaning correspondence. These
trigger code repair and new focused checks. Continuation vetoes: no valid source,
unavailable provider on bounded probes, exhaustion of authorized calls or corrupted
history. Expected uncertainty does not stop independent engineering.

## Execution

Use project Python 3.11/JDK 17 and CPU only. No installs or GPU work. New outputs:
`artifacts/interpretation/round6`, notes/contracts:
`docs/implementation/interpretation-round6`, frozen baseline:
`.localresources/interpretation-round6`. Phases: D0 implementation/focused checks;
D1 bounded live probe and decomposed run; D2 observed repairs/full regression and
refreshed successor plan. Review current inputs between phases, retain failed
attempts, and execute repairs before retry; at most three failed acceptance
attempts before an explicit plan revision. Existing approved runner may dispatch
only fixed new commands; no arbitrary command or changed spending ceiling.

Each run records commit, exact commands, source/code hashes, model route identity,
environment, wall time, fixed budgets, local artifacts and result classification.
Provider seed is unavailable. Final note separates engineering correctness,
availability, source-interpretation uncertainty and institution readiness.

## Executed repairs and revised phase sequence

D1 completed both inventories, then exposed a CRLF/LF derivative mismatch before
search creation. The executed exact-derivative repair and 21 focused checks are
recorded in `interpretation-round6/d2-audit.md`. D1R replayed eight inventory calls
and reached four compiled candidate interpretations. The 204-pair fidelity matrix
did not fit the remaining call allowance at 32 pairs per batch; the critic also
returned invalid signed attacks. D1F's reviewed 51-pair attempt timed out and its
circuit stopped further paid calls. D1S then trimmed peer claims from the task
while retaining full source context: its fixed four-pair diagnostic validated in
58.557 seconds. A local serialization failure before dispatch was repaired and
retained as a separate failed attempt. These extensions are separately reviewed
in `d1r-review.json`, `d1f-review.json`, `d1s-review.json` and their audit notes.

The final phase order is D0, D1, D1R, D1F, D1S, D2. D2 runs the complete deterministic
regression without any live call. At the start of D2, 97 of the existing 100 calls
are consumed. Four of 204 fidelity pairs have validated; 200 remain unchecked.
The current provider responded on a four-pair task, so blanket provider
unavailability is no longer the live continuation veto. Completing all remaining
checks at this tested size exceeds the remaining authorized calls. Prepare an
explicit successor budget and preserve every successful response for reuse;
do not infer approval from elapsed time or spend a partial batch series while
reporting complete verification.
