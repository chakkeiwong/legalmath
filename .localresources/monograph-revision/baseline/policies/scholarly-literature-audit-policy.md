# Scholarly Literature Audit Policy

This policy is intended for research, monograph, survey, and method-design
work where agents cite academic literature or decide whether a literature
review is complete enough for skeptical scholarly review. It is
project-independent. Project-local plans may add stricter rules.

## Core Principles

- Citation counts, journal rankings, and conference rankings are coverage and
  prioritization signals only. They do not prove correctness, relevance,
  originality, convergence, empirical validity, or implementation readiness.
- A literature claim is supported only by checked primary-source technical text:
  the relevant section, equation, theorem, proof, algorithm, appendix, or
  experiment must be inspected and cited with enough specificity for a reviewer
  to find it.
- Abstracts, titles, metadata snippets, introductions, conclusions, and venue
  prestige are insufficient for theorem-level or algorithm-level claims.
- Retractions, withdrawals, expressions of concern, errata, and obvious
  version conflicts must be checked and recorded before a paper is used as
  support.
- A serious literature survey must explain why important omitted papers are
  omitted. Silence about a famous or recent paper is a reviewer-risk item.

## Required Ledgers

Create or update separate ledgers when the task is literature-critical:

1. **Source-support ledger.** For each paper: title, authors, year, DOI/arXiv/URL,
   local artifact path when available, publication status, retraction/quarantine
   status, full-text status, inspected technical sections, inspected equation,
   theorem, algorithm, table, and appendix identifiers, and claims allowed or
   forbidden from that paper.
2. **Citation and venue metadata ledger.** For each paper when metadata is
   available: citation count, citation source, access date, venue, venue metric
   source, access date, and caveats. Record missing metadata as `not available`,
   not as zero.
3. **Backward-snowball ledger.** For each seed paper, inspect the
   literature-survey, related-work, introduction, and method-comparison
   sections. Enter every referenced work that appears relevant to the current
   topic, then classify it.
4. **Forward-snowball ledger.** When metadata sources are available, record
   highly cited citing works, recent citing works, and known follow-up or
   replication papers. Record the query/source/date.
5. **Claim-support ledger.** Map each important chapter/report claim to a
   checked source section or to a derivation in the project notation. Separate
   what the source explicitly states from what is inferred for the current
   setting.
6. **Omitted-paper and reviewer-risk register.** For each plausible missing
   paper: reason for omission, support status, expected reviewer objection, and
   whether the omission is acceptable, blocked, or requires survey expansion.

## Paper Classification

Classify candidate papers before deciding how they enter the exposition:

- `FOUNDATIONAL`: central theorem, method, or concept for the field.
- `DIRECT_METHOD`: directly implements or analyzes a method under discussion.
- `COMPETITOR`: important alternative baseline or rival method.
- `SURVEY_OR_TUTORIAL`: useful for orientation, not theorem support unless the
  specific surveyed claim is checked against primary sources.
- `IMPLEMENTATION_OR_SOFTWARE`: supports availability or engineering context,
  not mathematical validity by itself.
- `EMPIRICAL_EXAMPLE`: shows a domain application or benchmark, not general
  proof.
- `BACKGROUND`: relevant context but not central.
- `PERIPHERAL`: mentioned but outside current scope.
- `SUPERSEDED`: replaced by later work; cite only when history requires it.
- `SOURCE_BLOCKED`: metadata known, full text unavailable.
- `RETRACTED_OR_QUARANTINED`: do not use as support except to explain exclusion.

## Citation Counts And Venue Rankings

- Record citation counts with source and access date. Citation counts are live
  metadata and can change.
- Record journal or conference ranking only with source and access date. Venue
  rank is a proxy for visibility and reviewer expectations, not a correctness
  certificate.
- High citation count normally raises omission risk. It does not force a paper
  into the main exposition if it is out of scope, superseded, flawed, or
  quarantined, but the reason must be recorded.
- Low citation count does not disqualify recent, technical, or highly relevant
  work.
- If metadata access is unavailable, continue the source-based audit and mark
  the ranking/citation fields as unavailable.

## Snowballing Requirements

### Backward Snowballing

For each seed or cited paper used in the main exposition:

1. Inspect its literature-survey, related-work, introduction, and comparison
   sections.
2. Extract referenced works that are foundational, direct, competing, or
   repeatedly cited by multiple seed papers.
3. Add each candidate to the backward-snowball ledger with a classification and
   action: cite, inspect next, omit with reason, quarantine, or block pending
   source.
4. Do not blindly cite every reference. The requirement is that every relevant
   reference is considered and classified.

### Forward Snowballing

When metadata tools or public indexes are available:

1. Query citing works for each seed paper.
2. Record highly cited citing works and recent citing works.
3. Identify later corrections, extensions, replications, and negative results.
4. Add candidates to the forward-snowball ledger with query source and access
   date.

If network/API access is unavailable or not approved, record a blocker rather
than fabricating coverage.

## Retraction And Quarantine Checks

Before using a paper as support, check for:

- retraction or withdrawal;
- expression of concern;
- major erratum or corrigendum;
- arXiv version mismatch relative to the published version;
- publisher page inconsistent with the local PDF;
- predatory or unverifiable venue concerns;
- user or reviewer notice that the source is unreliable.

If any risk is found, classify the paper as `RETRACTED_OR_QUARANTINED` until a
human or reviewed source clears it. Quarantined papers cannot support claims.

## Claim-Support Discipline

Every important claim must have one of these support classes:

- `PRIMARY_TECHNICAL_SUPPORT`: checked paper section/equation/theorem/proof,
  algorithm, appendix, or experiment.
- `PROJECT_DERIVATION`: derivation written in the project's notation and, where
  feasible, audited by mathematical tooling or human review.
- `IMPLEMENTATION_EVIDENCE`: checked code/test/benchmark artifact; supports
  implementation behavior only.
- `SURVEY_CONTEXT_ONLY`: cited for history/context, not claim support.
- `SOURCE_GAP_BLOCKER`: source unavailable or not yet checked.
- `QUARANTINED`: source cannot be used.

Do not promote `SURVEY_CONTEXT_ONLY`, citation counts, venue rank, or abstracts
to `PRIMARY_TECHNICAL_SUPPORT`.

## Final Hostile Review Gate

Before calling a survey or chapter scholarly, perform a hostile review:

- Would a skeptical academic or industrial panel ask why a famous, highly cited,
  recent, or directly competing paper is missing?
- Are citation and venue metrics recorded as dated metadata, not truth?
- Are retracted or unreliable papers quarantined?
- Are technical claims tied to inspected primary text or derivations?
- Are backward and forward snowballing results recorded?
- Are omissions justified in a register?
- Are foundational, direct, competitor, and recent papers represented fairly?
- Are limitations, disagreement with papers, and extrapolations clearly
  separated from what the papers prove?

If any answer is materially weak, the artifact is not review-ready.

## Minimal Output Schema

For a compact audit, produce at least:

```text
decision:
metadata_date:
seed_papers:
source_support_summary:
citation_venue_summary:
backward_snowball_summary:
forward_snowball_summary:
quarantined_sources:
top_omission_risks:
claim_support_gaps:
next_required_actions:
what_is_not_concluded:
```

For a full audit, create the six ledgers listed above.
