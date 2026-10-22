# Finite rounding validation repair passed

The two defects reproduced in sealed entitlement003 are repaired in our exact
coupon implementation. Declared rounding is validated before holder filtering;
malformed exact quantities, including zero denominators, consistently raise
ValueError. Nonstring rules are refused before set membership. Supported rules,
exact representations, aggregation and arithmetic are unchanged.

All 24 complete valid actual-consumer records match their immutable003 baseline:
16 Danske v1 direct/selected controls and eight Shell v3 global/definitive controls.
The two valid source-bound hypothetical v2 results also match exactly. All 76
malformed direct/selected cases produce the required rounding-specific refusal,
including with all holders excluded; four malformed v2 controls are UNSUPPORTED.
Changed selected terms were readmitted through P3. Graph, assembly, other terms,
law payloads and unrelated direct Q1–Q4/Q6 answers were preserved.

The single focused pytest invocation passed all 333 cases with no skips, errors
or failures, including 159 new parameterized regressions. These exercise v1/v2/v3,
both aggregation modes, valid excluded accounts, actual consumer refusal boundaries,
exact ties and nonmutation. Test totals are supporting engineering evidence; the
complete downstream comparisons and specific refusal checks are primary criteria.

Prepare authenticated the sealed baseline and original sources before editing.
Every lossless delta was reconstructed and checked against its actual expanded
record; verify repeated this and checked actual phase-product identities. No
baseline was rerun. Failed003 remains FAIL, with its original storage overshoot
and all files unchanged. The new storage design uses less than 0.5 MB for004
before final notes/seal, rather than duplicating the large source graphs.
Measured cumulative storage at verification was 63,781,087 bytes, including all
entitlement attempts and the explicitly counted support, within 70,000,000 bytes.

All seven stages passed their individual 30/120-second limits. Cumulative003/004
product-stage time was 290.299310 seconds, below840. The selected
adverse stage took108.349738 seconds, close to its120-second bound; this is an
observed runtime, not evidence of general performance or package superiority.
No duplicate launch, native extraction, render, OCR, network, package/model,
installation or GPU call occurred. CPU devices were intentionally hidden. The
exact environment, dirty-worktree method/source hashes, git commit, commands,
stage durations and completed tool sessions are retained in run-manifest.json.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | What is not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain this local validation repair |24 complete consumer and two v2 valid comparisons equal;76 actual and four v2 refusals correct | No source/method drift, regression failure or bound violation | Finite malformed-input scope and hypothetical premises | Seal, record partial result, refresh and inspect independent routes | Actual ownership, entitlement or settlement; package completeness; program completion |
| Preserve003 failure and budgets | Baseline authenticated without re-execution; deltas reconstruct completely | Original40MB overshoot remains historical FAIL | New codec's evidence is source-bound to003 | Preserve both attempts and the reviewed explicit budget lineage | Retroactive compliance of003 or a reset of admissions |

The claimed target is a finite exact-input validation repair. The actual computed
complete valid records are equal to the retained comparator, and malformed cases
meet their declared refusal boundaries. This supports that local target. Actual
note form, holdings, events and clearing records are absent; independent legal
acceptance and broader financial/settlement coverage remain absent. task_complete
therefore remains false. The defects and storage failure were our implementation
and evidence-handling errors; no third-party package failure was established.

Post-run red team: a passing finite suite cannot establish correctness for every
financial profile. Frozen source graphs and supplied hypothetical conventions are
the weakest evidence for real use. A changed valid complete result, an accepted
malformed rounding declaration or authentic conflicting conventions would require
reassessment. No stochastic comparison or statistically supported ranking is made.
