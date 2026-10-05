# Reusable legal interpretation research, 5 October 2026

Question: which public research and open-source implementations can address the
substantive gaps in the current LegalMath interpreter, particularly reasoning
with case law? Product gap baseline:
`docs/implementation/assurance-evidence-master/product-gap-audit-2026-10-05.md`.

This is a literature and source-code inspection, not an experiment, provider
round, dependency installation or implementation promotion.

## Skeptical audit and evidence contract

Do not infer that a legal research product solves interpretation because it
retrieves cases, predicts outcomes, passes a benchmark or executes encoded rules.
Distinguish facts assumed by a case-based model from facts extracted from a
judgment; legal holdings from outcomes; argument acceptance under stipulated
preferences from authority; and solver correctness from English fidelity.
US, tax and contract tasks provide mechanisms, not validation of Hong Kong
regulatory interpretation. Preserve the machine-only quality requirement in the
controlling product specification; human-labelled legal benchmarks are not
admissible local correctness or selection criteria under that policy.

For each recommendation inspect the relevant method, semantics, evaluation and
limitations sections. Reuse retained papers and inspect official implementation
code where available. Record repository version and licence separately from paper
availability. Pin downloads; do not execute downloaded programs. Statements about
current software must be limited to the source inspected. Distinguish original
Carneades semantics from later implementations, and research prototypes from
available maintained software. New primary papers used materially must be stored
locally along with their retrieval provenance.

Acceptance for the research note: each recommended mechanism maps to a concrete
product gap, identifies its required premises and limitations, and has a traceable
paper or official-code anchor. Failure to obtain technical material downgrades a
lead to unverified; it does not justify a strong claim. No benchmark ranking,
general legal correctness or adoption approval follows from this review.

## Sequence

1. Inspect existing literature notes and retained technical texts.
2. Verify a bounded set of official open-source repositories for argumentation,
   controlled English, evidence extraction and case citation/retrieval.
3. Inspect an empirical study of legal research tools before assessing the claim
   that commercial systems have solved the interpretation problem.
4. Write a gap-to-mechanism comparison, distinguish reusable code from literature,
   and recommend a small product-focused integration sequence.

Audit verdict: proceed with bounded read-only research and local archival. Do not
convert source availability, model agreement or formal self-consistency into
evidence of English interpretation correctness.

Artifacts: `docs/research/legal-interpretation-reuse-2026-10-05.md` and
`.localresources/legal-interpretation-reuse-2026-10-05/`.

## Review outcome

Completed the bounded paper and official-source inspection. The research note
maps mechanisms to existing product gaps and records licence findings, versions,
semantic defaults and limits. It recommends a first substantive slice covering
paragraph 10 and paragraph 14/footnote 5. Source files were inspected, not
installed or executed. No dependency, product implementation or readiness status
was changed. Archived hashes and retained-paper provenance are recorded in
`review-manifest.json` in the archive directory.
