# Policy-to-ODRL proposal: delivery checkpoint, 22 October 2026

The requested survey was absent from the canonical LaTeX proposal. It is now integrated as section 4.18, with the concrete implementation proposal in section 8.3. The same two substantive source files produce a focused 23-page reading copy. The complete proposal has 422 pages.

## Deliverables and recommendation

- `docs/proposal/policy-to-odrl.pdf`: focused literature, software and repository review, plus implementation proposal.
- `docs/proposal/proposal.pdf`: updated complete proposal, byte-identical to `docs/monograph/monograph.pdf`.
- Shared source: `docs/monograph/chapters/04b-policy-to-odrl.tex` and `docs/monograph/chapters/08a-odrl-proposal.tex`.

The recommendation is a reviewed, source-linked `PolicyInterpretation` richer than either export. Deliver ODRL first, using selected Catala calculations and checks where appropriate. Independent source-based scenarios must challenge both outputs. Agreement between outputs cannot establish the correctness of their shared interpretation.

The 2023 SFC–HKMA suitability circular and both annexes anchor the proposal. It distinguishes eligibility for streamlined procedures, conditional relief, continuing duties and client changes. It specifies profiles, modules, export/evaluation contracts, worked JSON-LD, eight scenario families, deliberate mutations and six implementation milestones. Existing prospectus source graphs, reference closure, clause checks, SPI calculations and verification patterns are reusable; their limits and proposed adaptations are explicit. No ODRL runtime or feature was implemented or benchmarked during this document task.

## Evidence and validation

Retained research is under `docs/research/hkma-odrl-survey-2026-10-22/`, with papers, pinned code and official sources under `.localresources/hkma-odrl-survey-2026-10-22/`. Eight newly retained papers received technical reading and nine public code checkouts were inspected. Unavailable originals and documentation-only findings remain identified. The review does not claim a general absence of HKMA-related work or legal accuracy from published structural scores.

Actual successful build commands:

```sh
latexmk -xelatex -interaction=nonstopmode -halt-on-error -cd docs/proposal/policy-to-odrl.tex
python3 scripts/build_reader_facing_monograph.py
```

Build logs, protected baseline, citation-integration record, render copies and final delivery manifest are under `.localresources/hkma-odrl-latex-2026-10-22/`.

| Check | Result |
|---|---|
| Canonical document checker | PASS, no errors; 158 citation documents, 389 occurrences, 207 retained source-unit labels |
| Preservation | All pre-existing chapter content and 325 previous occurrence judgments preserved |
| Added reading-record quotations | All 21 source probes pass against retained material |
| PDF aliases | Canonical/proposal aliases byte-identical; companion alias also matches |
| Final render inspection | All 23 focused pages and new canonical sections/boundaries inspected; four detailed table/diagram/listing renders inspected |
| Human readability acceptance | Pending; requested provisional PDF is ready for delivery |

The focused PDF SHA-256 is `a5ac0270d5c07ebc8f700d05ffe20b146ac5faee33353104c1829fb9b790a72e`. The canonical/proposal PDF SHA-256 is `2bd55801e5350f5eb8fb3848bfddd319d8adfecf604d39a64ccec277b322b9bd`.

D1–D6 are complete. No authorized document work remains ready. The next possible work is reader-requested revision or a separately scoped implementation of the proposed manual eligibility export. Preserve unrelated worktree changes. Do not rerun the one-off citation integration helper, overwrite historical baselines or interpret successful document checks as legal validation.
