# Survey review record

Reviewed on 22 October 2026. This record accompanies the [survey](README.md), [technical reading notes](reading-notes.md), [software inspection](software-audit.md), and [source manifest](sources.json). It records an author review of the research documents, not an independent legal opinion or software certification.

## Source and claim checks

The selected circular is the 28 July 2023 SFC–HKMA circular 23EC35, including both annexes. The official annex PDFs match the repository copies by SHA-256. The official circular HTML contains the substantive body, date, footnotes and annex links. The archived body uses a different representation, so byte identity is not claimed for it.

The retained retrievals, inspected source files, upstream licence files, selected code and retrieval helper were checked against their manifest hashes. Pinned upstream checkout commits were checked against the manifest. Bibliographic references distinguish the version inspected from publication metadata. All main-report citation labels have reference entries, and relative Markdown file links resolve. The manifest parses as JSON. The new Markdown files were checked directly for trailing whitespace and unmatched code fences; a scoped `git diff --check` alone would not cover untracked files.

The final local check passed: 57 retained HTTP response hashes, eight readable PDF-copy hashes, nine checkout commits, 37 code/licence hash checks, 22 local source/helper hashes, 31 relative links, nine tables and 19 citation labels. Two additional requests timed out without a response body; their failure metadata is retained. An initial checker incorrectly assumed every request produced a body; it was corrected to verify these explicit timeout records without changing the source manifest or treating them as successful retrievals.

The committed prospectus and translation source trees were compared between main `3c3e462acabfde8c62285f4274f0f8c62b90a790` and prospectus `e8beb52b13399f18bbbff9aecea9636803729d5f`. They have no differences in those paths, and the prospectus commit is an ancestor of that main commit. This supports reuse of the relevant merged code, not a claim that all branches or dirty worktrees are identical.

The substantive correction pass checked these points:

- OVAL's current equality/comparison code attempts numeric conversion; stale documentation must not be quoted as its actual behavior. Its float arithmetic, duty defaults, unmatched-request defaults and unsupported constructs still require explicit choices for a pilot.
- FORCE includes duty-reporting code despite documentation describing duty limitations. Neither that code's existence nor an activation-similarity score establishes enforcement of every permission prerequisite.
- Existing prospectus models include SPI calculations and the designated-account amount exception. Their synthetic/conditional source bindings explicitly leave legal entailment and completeness unestablished.
- Withdrawal is anchored to Annex 1 §13.1(d); category and threshold changes occur in §13.2(c)(iii) and §13.2(d)(iii). The knowledge/experience inventory includes the postgraduate-diploma and one-year work-experience alternatives.
- Annex 2 FAQ 6 defeats an unconditional above-threshold trading prohibition. Procedure relief is not a prohibition on performing the relieved procedure, and permission to use the Streamlined Approach is not general permission to trade.
- RDF/profile conformance, evaluator semantics, agreement with Catala and fidelity to the circular are separate claims. Shared generation cannot make agreement independent evidence of source interpretation.

## Presentation checks

The Markdown structure, table column counts, citation labels and local links were checked. A temporary HTML/PDF preview was rendered using PyMuPDF after a LibreOffice conversion failed. Pages 1, 2, 7 and 12 were visually inspected for prose, headings, table layout and legibility. This was selected-page inspection, not a visual review of every page. The temporary preview replaced the Mermaid diagram with equivalent prose and showed minor table-background pagination artifacts; it is not a deliverable. The Markdown report retains the diagram and is the intended reading copy.

The report leads with the architectural recommendation, explains the circular's legal distinctions before comparing tools, and states paper-specific evidence limits alongside the claims they affect. The final clause-inventory precision edit and review link were checked in Markdown after the preview. No independent human readability review is claimed.

## Decision and remaining limits

| Decision | Primary criterion status | Veto or uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|
| Complete the requested survey and recommend an ODRL-first pilot from a reviewed source-linked model. | Direct translation methods, formal-semantics work, selected code and the circular were inspected and retained. | Several original papers were unavailable; each is labelled. No direct HKMA study was found within the recorded search, without an exhaustive absence claim. | Implement and independently review the bounded pilot described in the report if that becomes the next task. | An automatic legally faithful translator already exists. |
| Reuse prospectus evidence handling and existing conditional SPI calculations; trial a declared ODRL fragment with explicit evaluator settings. | Relevant repository paths and pinned upstream code support the proposed starting points. | Static inspection does not establish runtime behavior or suitability; existing calculations have substantial external premises. | Define the profile and source-based expected scenarios before comparing generated policies. | Any inspected evaluator or existing SPI fixture is production ready or legally certified. |

No third-party tests, live model calls, translator implementation or HKMA benchmark were run. Reported literature scores remain attributed to their authors and are not local results or a ranking for this task. The inaccessible 2014/2019/2025 originals limit conclusions about those works; their absence does not remove the directly inspected evidence.

The case is a historical source bundle. Current legal applicability, subsequent amendments and full closure over incorporated sources remain outside this survey's completed scope. The strongest alternative explanation for a future successful pilot is that a shared interpretation or easy scenarios concealed an omitted exception. Independently specified cases covering FAQ 6, withdrawal, requests for explanations, prior consent and missing facts are therefore necessary before treating executable agreement as substantive evidence.

The survey is complete. Translation and evaluation remain proposed follow-on work, with no claim of implementation or measured legal accuracy.
