# Enforce existing scope consistency in the response schema

The v12 replacement for batch 17 returned one-span quotations successfully but
failed the unchanged fidelity validator. Ten proposed NOT_APPLICABLE_TO_THIS_QUESTION
rows omitted their question-relation evidence and paired that label with OMITS
correspondence. The retained raw reply and failed receipt show both faults.
They are invalid under the already stated target; they do not establish that
the claims are relevant, irrelevant or omitted from executable meaning.

## Reviewed remedy

Express the existing conditional rules in the compact response schema using
two nested `anyOf` object branches. One branch permits a not-applicable
question judgment only with nonempty source evidence and NOT_APPLICABLE
correspondence. The other branch excludes both not-applicable labels and
requires evidence for RELEVANT judgments while retaining UNCERTAIN and
UNASSESSED without a forced evidence claim. Keep all four question labels
available. Each branch keeps the original rationales, followups, authority
assessment and source assessment. The original internal validators still
adjudicate validity after alias expansion.

The schema encodes dependencies already enforced by fidelity_v2.validate; it
does not select any pair's legal label. State the rules concisely in the model
instructions. Do not send the prior answer, copy its relevance judgments,
locally fill citations or rewrite OMITS to NOT_APPLICABLE. Request a fresh
source-first response and then the still-unissued qualification-first response.
Preserve the original batch, questions, source, failure history and attempts.
Use this same schema for later batches only after fresh checks pass.

## Evidence contract and defaults audit

The baseline is v12's retained invalid response under the unchanged original
source and twelve pairs. The engineering pass criterion is two validated
perspectives with complete dimension coverage. Local tests must reject both
observed faults and still accept supported RELEVANT comparisons, UNAVAILABLE,
BLOCKED, and a supported NOT_APPLICABLE proposal through the original validators.
Schema preflight must accept the nested anyOf structure. This is a hypothesis
about structured-output reliability; provider support is tested by the bounded
live repair, not assumed from local schema validation.

Missing identities, source/question drift, fabricated evidence, invalid
responses, dispatch failures or exhausted resource ceilings veto further live
execution. Labels and latency remain descriptive. Passing would establish
contract compliance, not semantic/legal accuracy or superiority. Correlated
model bias remains; preserve both failed and changed proposals for substantive
review. The overall legal research direction is not rejected by this response
failure; the planned response repair directly addresses it.

## Finite budget and audit verdict

There are 52 consumed reservations: combined 34, baseline 3 and repair 15.
There are 18 recorded repair entries. This implementation revision and its
live replacement use the last two repair entries. One replacement repair call,
one unissued normal perspective, and 46 remaining normal calls project to
**100/100 calls**, with combined 81, baseline 3 and repair 16, and **20/20
repair entries**. The v12 allocation and original authorization need no change.
No time window is extended. Failed calls are never refunded.

Skeptical audit: PASS conditional on the fresh tests and prior-evidence
verification. A prompt-only repeated reminder was rejected as a weaker remedy
because the exact conditional inconsistency can be represented in the
supported nested schema. The schema's branches were compared directly with
the existing validator; they retain uncertain and unassessed states rather
than forcing a result. The source and executable target remain fixed, and
neither schema validity nor completion is promoted into legal closure. The
critical risk is that no repair budget remains after this attempt. Any further
invalid response or timeout ends dependent live execution with an honest
partial denominator, followed by local verification and a recovery report.

Keep the exact approved wrapper and closed actions: `test`, `verify`, `repair`,
then `execute`. This review authorizes only batch 17 attempt 2 as a fresh
repair; it is not permission for a generic retry loop.
