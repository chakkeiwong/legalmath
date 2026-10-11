# BES onward-source disposition and applicability consumer

The reviewed onward-source phase passed its final bounded execution on 11
October 2026. The command was:

```text
timeout 1200 .venv/bin/python docs/implementation/prospectus-integration-closure/bes-onward-sources/consumer.py
```

The consumer ran in the worktree CPU environment with
`CUDA_VISIBLE_DEVICES=-1`. It consumed the same eight retained BES documents
as the protected source-chain comparator, preserved all 18,036 source units,
and kept the final-terms source map and question statuses equal to that
comparator. The final bounded runs completed in roughly 167 seconds, within
the 1,200-second bound.

The source disposition contains eleven incorporated financial records and
three agency agreements. Each row has an introducer hash/page/quote, expected
date, issuer, scope, candidate paths, original-byte hash, acquisition status
and authenticity status. No separately authenticated original bytes were
retained, so all 14 rows remain `UNRESOLVED`. This is a retained-corpus
disposition, not an exhaustive internet search.

Four source-specific applicability categories were retained separately:
named agency instruments and precedence; Portuguese law and jurisdiction;
Interbolsa book-entry and Common Representative language; and generic ICSD
common-safekeeper language. Four applicability edges and eight Q1/Q2
dependencies resolved because their reviewed passages were present. Four
matched omission controls made the corresponding dependencies unresolved, and
wrong-edition and wrong-date controls rejected their adverse requests.

| Decision | Primary evidence | Veto status | Consequence |
|---|---|---|---|
| Retained-source disposition | 14 exact rows, source/date/issuer/scope bindings, absent bytes explicit | PASS | Preserve the 14 missing-source rows as unresolved |
| Applicability passage consumption | Four category-separated edges and eight dependencies resolve | PASS | Retain conditional source applicability only |
| Omission integrity | Four representative omissions expose both Q1 and Q2 dependencies | PASS | Do not infer an edge when its representative passage is absent |
| Edition/date integrity | Wrong-edition and wrong-date controls reject | PASS | Keep exact source identity and date checks |
| Legal or package completion | Independent acceptance, authenticity, collateral eligibility and superiority | NOT_ESTABLISHED | No legal conclusion or completion promotion |

The first execution stopped on `KeyError: BES-DEP-12` because the historical
dossier contains 29 rows while this comparator carries only
`BES-DEP-01` through `BES-DEP-11`. `failure-001.json` preserves that attempt.
The bounded repair filtered the disposition inventory to the admitted eleven
records; this was a local request-construction defect and says nothing about
the PDF extractor or service package. A second evidence-hygiene repair also
excluded ignored `__pycache__` and `.pyc` files from the retained manifest.

The final report remains `ASSISTED`: Q1 and Q2 are `UNKNOWN`, Q3 is `PARTIAL`,
Q4 is `UNKNOWN`, Q5 is `UNSUPPORTED`, and Q6 is `UNKNOWN`. The actual agency
agreements and financial records, independent legal readings, actual
Eurosystem collateral eligibility, native dependency confinement, second-host
portability and broader scan-family coverage remain open.

## Retained evidence

`result.json` records the final counters and boundaries; `report.json.gz` is
the actual service report; `request.json` is the admitted request;
`source-disposition.json` and `agency-applicability.json` preserve the source
review; `checks.json` preserves omission and adverse controls;
`failure-001.json` preserves the failed local attempt; and `manifest.json`
hashes the complete package while excluding only the manifest itself and
ephemeral Python cache files.
