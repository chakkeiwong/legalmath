# HKMA circulars to ODRL: literature and software survey

## Objective and authority

User-authorized research survey, not implementation or continuation of the legal-mission or prospectus execution campaigns. Deliver a sourced survey, retained primary literature and software inspection notes, and a concrete recommendation for an HKMA circular translation pilot. Existing worktrees and campaign state are protected. No model calls, subagents, external messages, software installation, production changes or benchmark runs are planned.

The user selected the 28 July 2023 SFC–HKMA sophisticated-professional-investor suitability circular (23EC35), Annex 1 and Annex 2 as the primary case. Other circulars are contextual leads only; this survey does not claim to have translated them.

## Research intent and evidence contract

- Question: what published methods and open-source implementations can support faithful, reviewable translation of HKMA circulars into ODRL, and what remains outside their demonstrated scope?
- Comparators: direct natural-language-to-ODRL; reviewed source-linked policy model with ODRL export; ODRL plus executable calculations; related legal/deontic formalisms.
- Primary criterion: recommendations supported by inspected technical methods/evaluations and corresponding source code where available, tied to actual circular clauses.
- Promotion veto: unsupported semantics, absent source fidelity evidence, or code/documentation mismatch blocks claims of suitability or readiness.
- Repair triggers: inaccessible publisher source triggers bounded search for author/open-access copy; unavailable code triggers explicit unverified classification.
- Explanatory evidence: publication/repository metadata, examples, stars and recency. These are not correctness or readiness criteria.
- Continuation veto: invalid authorization or corrupted common evidence; individual unavailable sources do not stop independent research.
- Non-conclusions: no exhaustive proof of literature absence; no production readiness, legal correctness, benchmark superiority or automatic document understanding from a paper, schema validation or repository inspection.
- Artifacts: `docs/research/hkma-odrl-survey-2026-10-22/` and `.localresources/hkma-odrl-survey-2026-10-22/`.

## Dependency graph

| ID | Required result | Requires success | After completion | Alternative/recovery | Attempts/resources |
|---|---|---|---|---|---|
| S1 | Circular source and clause inventory | none | none | Use archived source; qualify version status | Local reads, one extraction per selected file |
| S2 | Search log and candidate literature/software list | none | none | Search engine, bibliographic API, official indexes | Public read-only requests; bounded follow-ups |
| S3 | Technical reading notes and retained copies | S2 | none | Publisher → author repository → preprint; otherwise mark unavailable | At most three source routes per paper |
| S4 | Source-code and license/maintenance inspection | S2 | none | Official repository → archived release; otherwise mark unverified | At most two acquisition routes per project |
| S5 | Comparative survey and pilot recommendation | S1 | S3, S4 | Report source-specific limits without blocking synthesis | New isolated documentation files |
| S6 | Citation, local-link, claim and scope review | S5 | none | One focused correction pass | Local documentation checks |

S1/S2 and S3/S4 are independent when their inputs are available; only disjoint downloads/reads run concurrently. All reasoning and edits remain sequential in the root agent. Preserve failed retrievals and actual inspection scope. A failed source blocks only conclusions depending on it. Completion requires survey, bibliography/source manifest, software notes, actual circular mapping and review, not completion of a separate implementation campaign.

## Assumptions and skeptical pre-execution review

The archived 2023 circular is a useful historical pilot, not assumed to be the current consolidated law. Verify its source and identify amendments as a separate concern. ODRL is a rights/policy model, not assumed to encode every regulatory norm. Open source means an inspected license, not merely a public repository. Tests reported by authors are attributed and not represented as locally rerun. Shared generation can create shared interpretation errors. A solver or Catala comparison requires explicit supported semantics and independent source-based expectations.

Audit: PASS for this research plan. It preserves the actual source baseline, includes direct and adjacent literature, prevents metadata and syntactic validity from becoming semantic success criteria, distinguishes availability from suitability, and has bounded retrieval recovery and a finite deliverable. No scientific experiment is being run.

## Execution record

- Initial inspection: official W3C ODRL model retrieved successfully; multiple HKMA circulars and prior legal-formalization literature are present locally. No ResearchAssistant/web-search connector is exposed in this session; use public primary websites and APIs through HTTP and retain copies.
- S1 complete: all three archived source texts inspected; official annexes retained and verified byte-identical to the archived PDFs. The official circular body was retrieved and inspected. Annex 2 FAQ 6 is an essential counterexample to treating all above-threshold transactions as prohibited.
- S2 complete: Crossref, OpenAlex, GitHub and the W3C community landscape provided candidates. General search-engine and DBLP challenge responses were not counted as searches. No HKMA-specific ODRL paper was found in these searches; this is not an exhaustive absence claim.
- S3 complete: retained and technically inspected direct translation papers (AMR, LLM4ODRL, AgentODRL), the 2021 critique, 2025 declarative semantics, ODRE and 2026 OVAL/normalisation; also inspected the relevant standards and focused portions of existing Catala/eFLINT papers. Reading notes identify exact scope and unavailable originals. Eight new technical papers are retained as readable PDFs alongside the earlier local papers.
- S4 complete: nine pinned public checkouts inventoried; selected implementations, documentation and licences inspected at the levels recorded in the manifest. AgentODRL, OVAL, FORCE, ODRE and EDC findings are static, not executed results. pySHACL documentation was inspected separately. No licence grant was established for LLM4ODRL or ODRL-shape. Existing SPI-specific models and the merged prospectus/translation code provide concrete local reuse.
- Recovery note: the 2019 compliance-paper WU attachment returned 403, a guessed old repository path returned 404, and the corrected old path redirected to the publication landing page; its linked attachment also returned 403. Stop this retrieval branch and report the original technical text as unavailable. This does not block the other source readings or synthesis.
- S5 complete: the survey compares translation orders, explains Catala's verification limits, maps actual circular provisions to modelling choices, evaluates the software shortlist and proposes an ODRL-first pilot with independently reviewed scenarios. The report and supporting reading/software notes are in `docs/research/hkma-odrl-survey-2026-10-22/`.
- S6 complete: manifest/hash, reference, relative-link, Markdown and scoped diff checks passed. Selected pages of a temporary rendered preview were inspected; the preview is not a deliverable. The review record documents the code/documentation discrepancies, precise clause anchors, retrieval limitations and the correction of a checker assumption about timed-out requests. No third-party benchmark or translation was run.
- Final ready set: empty. Status: **COMPLETE for the requested survey**. Individual unavailable originals constrain the relevant claims; they are not a global blocker. No legal-mission or prospectus campaign state was changed. The proposed implementation remains a separate next task, not an unfinished survey item.
