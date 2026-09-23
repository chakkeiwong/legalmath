# Literature coverage and source audit

The expanded collection contains 81 cited records, including 52 academic PDF
editions representing 51 works. The two tax-paper editions remain separate.
There are also regulatory documents, two standards and software/local records.
The historical 50-edition library and comma filenames are preserved; the new
underscore filenames in `docs/papers/monograph-citation-archive.json` identify
the copies used for this audit. A zip of selected official source files is an
inspectable documentary snapshot, not a complete installable repository.

## Six retained ledgers

| Ledger | Evidence | Finding and limit |
|---|---|---|
| Source support | `citation-reading.json`, 81 records, and the archived full texts | Relevant methods, semantics, evaluation and appendix passages were read; each record says exactly how far reading and code inspection extended |
| Metadata and versions | `docs/papers/manifest.json`, citation archive, `source-update-check.json` | Retained edition/date/author identities checked; registration-agency metadata captured for 38 DOI records, fourteen without a registered DOI in the historical manifest; four rate limits were resolved by sequential retry and the arXiv DOI by DataCite; absent update relations do not prove no retraction |
| Backward literature | Existing technical notes and `docs/papers/coverage.md` | Default logic, input/output logic, duties, process compliance, argumentation and legal analogy provide inspected foundations; cited theorems retain their original hypotheses |
| Forward literature | Saved Catala and Stipula OpenAlex responses and 60 distinct screened records in `coverage.md` | Historical searches yielded 52 and 13 indexed entries before deduplication; these are edition-specific retrieval counts, not current influence metrics or exhaustive recall |
| Claim support | `citation-occurrence-review.json`, `citation-claims.json`, 211 occurrences; `citation-validation.json` | Each exact manuscript context has an authored, separately retained judgment bound to the read edition, short quotation and inspected section; changed contexts, editions or reading judgments require renewed review. Quotation and page matching is a mechanical check separate from the judgment |
| Omissions and next reading | The table below and existing unresolved-retrieval dispositions | A missing work is neither negative scientific evidence nor read evidence; no implementation claim here depends on an unavailable paper |

The 83 short quotation records were checked against the retained bytes, with
Unicode, punctuation and line-break normalization. PDF page anchors were checked
separately. Quotations evidence actual inspection; the surrounding technical
sections, not an isolated phrase, support the judgments.

The source audit produced substantive corrections. Stipula–KeY's printed and
official Boolean/integer example fails Java compilation; its reported experiment
remains an author report pending reconciliation. A later Stipula workbench has
liquidity-analysis code even though the older paper describes implementation as
unfinished. Weak permission uses constructive negative proof. Tree-of-Thoughts
duplicate strings receive zero value rather than necessarily being removed.
Roundtrip equivalence does not establish English fidelity. The maintenance-duty
definition has a formula/prose inconsistency. The ASPIC author's retained
correction concerns Definition 6.8 and downstream rationality results; the book
uses earlier argument/attack definitions and does not import the uncorrected
theorem. Citation metrics and venue metrics not captured are **not available**.

## Coverage improvements and remaining gaps

| Gap | Addition or justified next work | Consequence for this product |
|---|---|---|
| A real citation may not support the answer | Added and technically read Dahl and Magesh studies, including annotation/evaluation limits | Separate source authenticity, claim support, correctness and abstention; no transfer of US historical rates to Hong Kong |
| AI governance was outside the original regulatory discussion | Added SFC 24EC55 and appendix, and HKMA 19 August 2024 consumer-protection circular | Determine entity/activity/use applicability; internal authoring and customer-facing explanations differ |
| Full regulatory perimeter and incorporated authorities | Obtain and review applicable Codes, subsidiary legislation, related FAQs, earlier HKMA guidance and entity-specific supervisory requirements | The original unresolved Code/FAQ dependencies remain release blockers; the audit must not invent their resolution |
| Omission detection across whole source packets | Independently inventoried Hong Kong packets and adversarial missing-definition/attachment cases | Gold facts/rules supplied by benchmarks cannot measure discovery of those facts/rules |
| Backend comparison on matched meanings | Compare unknowns, conflicts, exceptions, dates and duties across RuleIR, Catala, decision tables and normative languages | Source languages are not interchangeable merely because examples compile |
| Shared extraction/interpretation errors | Vary extraction, inventory and candidate generation independently | Vendor diversity alone does not establish error independence |
| Human review, burden and usability | Independent legal readers and unfamiliar target readers; measured review effort and missed material errors | No current evidence certifies usability, a human voice or legal accuracy |
| Relevant unretrieved scholarship | Lawsky statutory logic/coding work; L4 paper; later Symboleo paper; financial-regulation assurance and methodology comparisons; obligation-logic graphs; later amendment chapter | Retrieve full methods and official code before adopting the associated mechanism; existing narrower sources do not stand in for them |
| New follow-up leads | Policy2Code, CatalaBlocks, explanation codification and integrated statutory/contract models | Screening leads only; no priority or superiority claim without technical reading |

`regulator-currentness.json` retains fresh official SFC API content and appendix
checks. The five core circular bodies matched the retained content; the 2023
tokenisation page explicitly points to its 2026 replacement. The latest product
index capture contains 100 of 159 entries, so it is not presented as a complete
regulatory search. The SFC/HKMA AI documents were retrieved directly for this
revision. Endpoint equality is not proof that no overriding law exists.

This review improves coverage and identifies what remains missing. It does not
claim an exhaustive systematic review, a clean retraction certificate, or an
institution-specific legal opinion.
