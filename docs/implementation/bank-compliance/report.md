# Bank and transaction compliance: execution result

The new component represents requirements on the bank, client, instrument and
transaction separately. It composes seven assessment categories and preserves
prohibitions, unmet controls, missing evidence and duties. Its affirmative result
is explicitly limited to the declared scope; full legal compliance always
remains `NOT_ESTABLISHED`.

The implementation is `src/legalmath/compliance.py`. The reusable Python API is
independent of instrument type. It has not been connected to live JPMorgan
accounts/policies or lowered into native RuleIR/Catala rule packs. Existing
prospectus/SPI checks remain their own conditional evidence and cannot substitute
for these additional requirements.

## Evidence and decision

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain the conditional composition component | 2,187 layer-state combinations plus context, source and conflict challenges | No failing case in the final focused regression | Completeness and meaning of supplied rule assessments | Implement separately versioned rule packs and evidence adapters | Complete legal permission |
| Retain blocked-ownership propagation | All 512 three-entity graph/seed combinations agree with independent closed-set enumeration; chain/aggregation/boundary challenges pass | Wrong-program selector, floats, duplicate edges and invalid totals rejected | Actual identity, direct stakes and unobserved ownership | Bind to provenance-bearing ownership and designation data | An unreached entity is cleared |
| Retain selected CMIC checks conditionally | Actor/capacity, ultimate party, holding/divestment/license and unknown-input tests | Principal-counterparty omission found in review and repaired | Designation/exposure/authorization facts, other programs and corporate actions | Add source-bound applicability and current-list adapters | Every service to a non-US client is permitted |
| Retain the documentation addition | Monograph builds; source and citation preservation checks pass | No unresolved build diagnostic | Automated/source inspection does not prove legal interpretation or reader comprehension | Continue the source-bound implementation described in the refreshed plan | Human quality certification or future-law completeness |

The final regression contains **107 passing tests**: **44 new compliance tests**
and 63 existing prospectus/qualification checks. The original backend comparison
was not promoted or relabeled: this new increment does not establish a Catala or
RuleIR ranking. Exact commands, CPU environment, commit, uncommitted method
hashes, wall time and source versions are in `run-manifest.json`.

The source dossier retains 12 usable primary-source documents and four access
responses explicitly rejected as legal text. The 2025 CFR editions remain
historical. The dossier does not contain all current US/Hong Kong obligations or
confidential bank policy. Source integrity is not a currentness certificate.

## Repairs and review

The skeptical plan review rejected both a blanket US-bank CMIC prohibition and
a single sanctions Boolean that could conflate rejection with freezing. Source
acquisition exposed HTTP-success access pages; those bytes were retained as
rejected evidence, and official alternative documents were preserved.

After the first passing tests, code review found a principal-capacity omission:
a non-US principal must not clear a transaction whose other/ultimate party is
US and prohibited. The repair includes either party's US status in that route;
the additional test distinguishes the repaired case. A US support intermediary
remains a separate capacity under the specified guidance.

Rendered inspection prompted explicit first-use definitions of OFAC and OCC
and identification of the amended executive orders. Earlier manuscript prose,
equations and citation contexts remain preserved. Section 2.4 teaches the
institution and service distinctions before the seven categories, then explains
the conditional conjunction and ownership argument. The document evidence is in
`document-review.json` and the retained PDF excerpt.

The strongest alternative explanation for apparent legal success is still that
the caller supplied an incomplete or incorrect scope. No number of passing
formal tests removes that uncertainty. A new rule, factual contradiction or
source change must invalidate the relevant prior finding and trigger repair.
The finite formal checks support the component; they do not reject or establish
the broader prospect of independent legal interpretation.

## Reset and next phase

Reproduce the checks with `.venv/bin/python scripts/check_bank_compliance.py`.
Rebuild the manuscript with `python3 scripts/build_reader_facing_monograph.py`.
The workspace contained extensive unrelated changes; they were preserved.
No trade, asset block, filing, publication, merge or push was performed.

The next implementation phase is the jurisdiction/activity inventory and live
source adapters, followed by sourced bank/AML/conduct/reporting rules and actual
versioned bank policy when available. Entity and instrument identity, list
freshness, authorization conditions, legal conflicts and corporate actions need
separate checks. Both native backends must eventually consume the same supported
specification and be tested independently. Unknown future legal situations must
receive qualified results; no human quality labels are used or required.
