# Bond reader repair: results and remaining limits

30 September 2026 (Hong Kong). The bounded repair program is complete. The
original three demonstrated reader failures are repaired, the retained corpus
has been re-evaluated, both language routes agree on the recorded formal inputs,
and the frozen challenge has exposed remaining coverage limits. General English
interpretation and unknown-future legal correctness are not established.

The 26 retained bonds produce **12 qualified positives and 14 qualified
negatives**. The prior result was 12 positives, 13 negatives and a Shell
abstention. Shell now has an exact derivation connecting final redemption of
£1,000 to its £1,000 calculation unit. The other 25 binary answers are unchanged;
that agreement is not an independent correctness oracle. Source witnesses and
supporting reasons have changed where the old reader selected the wrong action
or series.

| Preserved construction | Prior answer | Repaired answer | Obligation |
| --- | --- | --- | --- |
| Duty to notify whether conversion is possible | Positive | Unresolved | Notification does not establish conversion |
| Confirmation that notes cannot be written down | Positive | Qualified negative | Negation must not become a write-down |
| Permanent forfeiture of the principal repayment claim | Negative | Positive | Principal forfeiture must not yield a negative |
| Direct automatic conversion into ordinary shares | Positive | Positive | Preserve the affirmative control |

The [comparison](counterexample-comparison.json) replays the protected v1
reader. Tests also vary subject, action, modality, polarity, series, maturity,
share definitions, exact money/currency fields and tampered evidence. The
checker independently evaluates the formal decision and validates its source
links. It deliberately does not certify the shared English constructions.

**529 prospectus tests pass**, including **387 classifier/presentation tests**.
The current delivery uses **152 native executions**: 100 for the retained
corpus and formal cases, and 52 for the two fresh rows and formal cases.
All 256 partial/conflict input states, two SMT obligations and four deliberately
wrong formal variants are checked. Both native runs have kernel-checked
lowering. The delivery verifier rebinds **7,148 quotations** across **35
retained documents / 2,942 pages**, checks decision/reason consistency and
rejects or leaves unresolved six source-integrity faults. These counts measure
checked engineering work, not legal accuracy.

## Frozen challenge and interpretation

After freezing the code, two new issuer families were acquired. Santander's
177-page July 2025 AT1 circular yields an abstention: its copular mandatory
conversion wording is outside the implemented constructions. Unilever's
seven-page final terms yield an abstention because their named 16 May 2025
base memorandum could not be downloaded. The two issuer URLs returned HTTP
403. Earlier AstraZeneca candidate downloads also failed; their headers are
retained and they are not counted as tested bonds. Search snippets and newer
editions were not substituted for missing original documents.

Thus the published report covers **28 bonds: 12 positive, 14 negative and two
unresolved**. There is no demonstrated binary transfer on these two fresh
families. This is a coverage failure for the present candidate, not evidence
against the formal rule or Catala. Neither backend can repair missing or
misinterpreted front-end premises.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain bounded repairs | Recorded failures and constructed obligations pass | No current regression/formal/source-link failure | Shared English interpretation | Use qualified answers with exact evidence | Universal legal correctness |
| Retain retained-corpus results | 26 decisions with checked derivations | Missing/ambiguous sources block answers | Omitted language and document closure | Reacquire/re-evaluate when dependencies change | A negative proves absence |
| Reject broad transfer claim | Both fresh rows abstain | Promotion veto for broad coverage; no continuation veto | Unsupported construction and missing original | New construction/dependency study under another freeze | Research direction rejected |
| Retain RuleIR and Catala as conditional routes | Identical formal inputs pass | No backend mismatch | Front-end premises remain qualified | Preserve shared front-end checks | Catala improves legal parsing |

## Repairs, retained failures and next phase

The first corpus attempt over-blocked ordinary waivers and missing coupons.
The second exposed a checker incorrectly treating an intervening benchmark
ISIN as a repayment-field identity. Another attempt found that definition
checking used unscoped text. Those failures were repaired, retained in their
attempt directories, and followed by new test and corpus runs. A final active
versus passive reduction counterexample caused another reviewed correction
and rerun. None of those superseded runs is used as the final delivery evidence.

The next study should add copular mandatory-conversion constructions using
formal actor/action/polarity/target variants, then treat Santander as exposed
development data. It should recover Unilever's exact named edition through a
verifiable public archive and retain its dependencies. A new frozen source
challenge must follow before making any stronger transfer claim. Full source
closure, unrestricted English semantics and authoritative translation remain
research problems; this program does not hide them behind passing tests.

The strongest alternative explanation is that the repairs fit the exposed
construction families while missing other formulations. The fresh Santander
abstention supports that concern. An unsupported binary result on a new
construction would overturn the corresponding bounded support claim and
trigger repair. The weakest evidence remains English relevance and
completeness, particularly for negative answers.

## Reproduction and evidence

Use `.venv/bin/python` in this repository. Runs are deterministic and CPU-only;
no GPU framework or paid external model is used. Each run manifest records
its commit, dirty method hashes, command, environment, source versions, wall
time and artifact hashes. Native execution is serial within each run.

- [Reviewed plan](../../plans/bond-reader-repair-program.md)
- [Protected baseline and hashes](baseline-v1/manifest.json)
- [Final regression](prospectus-regression-final.xml)
- [Retained-corpus manifest](corpus-final-002/run-manifest.json)
- [Fresh challenge manifest](fresh-final/run-manifest.json)
- [Complete method freeze](../bond-loss-absorption-classification/execution/freeze-reader-v2.json)
- [Published report](../bond-loss-absorption-classification/results.md)
- [PDF](../bond-loss-absorption-classification/results.pdf)

The original checkpoint, including prior Catala and compliance work, was
pushed as `374e07d54d4745004f6f8c146b9eb82647570775`; the Catala worktree was
fast-forwarded to it. The final repair commit is followed by the authorised
fetch/merge/push and a second Catala fast-forward, with clean-state and remote
verification recorded in the session's final result.

Concurrent-work boundary: a new assurance-gap-closure campaign began writing
files during final staging. Its unfinished source, monograph and run changes
are preserved and excluded from this repair commit. This prevents a truthful
claim that the shared main checkout is globally clean. It does not prevent
committing this completed delivery, pushing main, or synchronizing the clean
Catala worktree.
