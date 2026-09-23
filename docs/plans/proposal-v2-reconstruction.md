# Reconstruct the proposal around literature coverage and implementability

## User verdict and intended result

The user rejected v0.1 as rough, rushed, incomplete in its literature review, and
insufficient for an implementing agent. The main reader is now an implementing
agent/technical lead working with a compliance sponsor. They must be able to
identify the chosen design, implement its modules in dependency order, run its
acceptance checks, and know which source/interpretation questions prevent release.
The canonical deliverable remains an extensive cited LaTeX proposal and PDF.
Normative machine specifications and an implementation backlog accompany it.

The protected baseline is `.localresources/proposal-v01-baseline/`, including
source/PDF digests. The prior formatting checks did not establish substantive
completeness or implementation readiness. Human rejection remains recorded.

## Skeptical plan audit

The prior baseline is inadequate: a few examples, package suggestions and a
twelve-week schedule do not define a system. Increasing page count or paper count
would be a proxy response. The repair must settle semantics, chosen dependencies,
module interfaces, data/authority boundaries, failure behavior, and exact acceptance
expectations. It must explain literature mechanisms deeply enough to justify those
choices and screen omitted families rather than merely append attractive citations.

The new work is document/specification engineering, not a model benchmark. Small
schema and example checks establish consistency of the written specification only.
No extraction accuracy, legal completeness, production readiness, proof replay or
cost benefit will be claimed. No private bank data or adjacent-repository mutation
is needed. This plan passes preflight under those constraints.

## Gaps and repairs

| Gap in v0.1 | Required repair | Check that can expose an inadequate repair |
| --- | --- | --- |
| Citation expansion was selective and unaccounted for | Search protocol, screened candidate ledger, backward/forward citation coverage, field taxonomy and unresolved retrieval list | Every included/excluded candidate has a disposition; relevant architectural families have inspected primary sources |
| Literature mostly summarized contributions | Explain semantics/algorithms, inspect relevant methods and implementations, derive SFC transfers and failures | Each architectural decision cites an inspected mechanism and a concrete transfer test |
| Custom language proposed without complete meaning | Fixed versioned grammar, types, unknown/conflict behavior, exceptions, time and obligation semantics | Machine schemas and conformance cases are mutually consistent; every operator has a defined result or rejection |
| Core engine and adapters left undecided | Concrete MVP stack, rejected alternatives, supported fragment and explicit deferred extensions | Agent does not have to select a framework before beginning |
| No component contracts | Repository layout, storage/identity model, API payloads, error codes, deterministic hashing and lifecycle | Contract fixtures validate and round-trip under a local checker |
| Happy-path flow not complete | Source-to-draft-to-review-to-evaluate walkthrough including amendment and failure paths | Each state transition has a trigger, guard, stored change and observable output |
| Scenarios lacked exact outputs | Source-linked fixtures, expectations, negative cases and mutation requirements | Checker can validate fixtures now; future implementation commands and required assertions are specified |
| Local reuse remained analogy | Exact inspected functions/files, adapter boundaries, calls and fallbacks | Clear import/protocol versus pattern-only distinction |
| Schedule not implementable backlog | Ordered work packages with files, dependencies, interface obligations, tests and completion commands | First work package is startable without further architecture decisions |

## Research coverage and stopping rule

Screen the retained Catala and Stipula forward-citation results and references.
Search separately for (1) executable statutes and Rules as Code, (2) default and
defeasible logic, (3) deontic obligations and repair, (4) temporal/process compliance,
(5) legal provenance/document standards, (6) legal languages and compiler/testing
work, (7) LLM formalization and legal evaluation, and (8) applicable rule engines.
Expand references of sources that supply a missing mechanism. Keep local full text
for every academic work materially used; inspect technical sections and original
code when available. Use ResearchAssistant for available discovery/parse support.

Coverage is adequate for this proposal when all architecture-bearing families have
primary-source support, all requested seeds have local full texts, and every record
in the two retained forward-citation neighborhoods has an explicit disposition.
The broader searches and backward expansion must supply the previously missing
foundations. This revision uses architectural coverage, not citation-network
saturation, as its stopping criterion: a second complete citation expansion has
not been performed. Recent comparators and retrieval gaps remain in the coverage
ledger and must be reopened before a decision depends on them. Report this
bounded coverage honestly, without an exhaustive-field claim.
Retrieval failure remains a visible gap, not a reason to pretend a source was read.

## Stages and interpretation of evidence

1. Diagnose the complete baseline and preserve a unit/equation coverage ledger.
2. Complete a broader literature search and technical synthesis; freeze the MVP's
   semantic and architectural decisions with explicit evidence and alternatives.
3. Specify ingestion, RuleIR, facts, decisions, obligations, review, amendments,
   storage, APIs and evidence checks; create conformance fixtures and a checker.
4. Write agent work packages, environment/bootstrap commands and evaluation plans.
5. Reconstruct the LaTeX argument around the chosen design and worked cases.
6. Check specification consistency, citations, source/paper integrity, then compile
   and read the complete rendered manuscript in ordered segments. Contact sheets
   are layout checks only. Preserve changed equations/claims and regression notes.

Correct schema validation is engineering evidence about the specification pack.
It is not evidence that the future runtime exists. Author review remains distinct
from user acceptance. The final status must identify remaining interpretation or
research limitations without using them to leave routine engineering undecided.
