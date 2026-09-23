# Five additional circulars: executed integration results

Five previously untested circulars now have scoped source-to-Java integration
checks. **75 named scenarios passed in Python and generated Java; all ten
compiled incorrect interpretations were detected.** All five investigations
retained unresolved questions and rejected meaning acceptance and release after
three repair rounds. The integration and interpretation regression suites
passed **113 tests**, including 27 tests in the new corpus module.

Before this work, 23EC35 had a complete selected SPI demonstration and 23EC46
had a paragraph-10 candidate, 22 named cases and 729 three-valued combinations.
23EC53, 26EC22 and 25EC48 had discovery/relationship tests. Importing five source
records was not equivalent to interpreting and executing five circulars. The
new corpus excludes 23EC35/23EC46 from its count of five additional circulars.

## Sources, scope and results

| Official source | Executed slice | Named cases | Inventoried text units | Selected source units | Incorrect compiled readings detected |
| --- | --- | ---: | ---: | ---: | --- |
| [23EC49: money-market annualised returns](https://apps.sfc.hk/edistributionWeb/gateway/EN/circular/doc?refNo=23EC49) | Seven-day companion; inclusive six-month track record; basis disclosure; extra channel duties below seven days | 16 | 139, including appendix | 7 | Omit seven-day companion; require more than six months |
| [24EC16: T+1 transition](https://apps.sfc.hk/edistributionWeb/gateway/EN/circular/doc?refNo=24EC16) | Standard US/Canadian securities settlement-regime count and distinct cutovers | 15 | 17 | 3 | Ignore Canadian footnote date; apply securities rule to FX |
| [24EC50: mandatory e-IP](https://apps.sfc.hk/edistributionWeb/gateway/EN/circular/doc?refNo=24EC50) | Electronic submission route from 30 November 2024 | 13 | 16 | 4 | Retain old October cutover; exclude first mandatory day |
| [24EC57: ESG-provider diligence](https://apps.sfc.hk/edistributionWeb/gateway/EN/circular/doc?refNo=24EC57) | Direct/incidental Type 9 discretion; evidence of diligence/monitoring; group standards and local responsibility | 16 | 22 | 9 | Exclude incidental activity; require voluntary-code membership |
| [26EC23: tokenised secondary trading](https://apps.sfc.hk/edistributionWeb/gateway/EN/circular/doc?refNo=26EC23) | Connecting-broker price alert and primary-market alternative | 15 | 72 | 6 | Alert at equality; omit primary-market alternative |

A sixth source, [25EC48](https://apps.sfc.hk/edistributionWeb/gateway/EN/circular/doc?refNo=25EC48),
is an announcement-only negative control. Its 76% historical CIS sales-growth
statistic is not encoded as a transaction limit. This is a manually authored
non-rule disposition, not a successful automatic detection by a language model.
A malformed member response is injected in that control and becomes an explicit
member-failure issue; it does not create a bundle or count as agreement.

The raw official JSON, extracted text and the 23EC49 illustrative appendix are
retained. The inventory partitions every non-whitespace character of these
text derivatives into 266 units across the five sources. A text unit is a
retained line/paragraph fragment, not necessarily one legal duty. PDF extraction
and HTML link/structure completeness still need reader review. Full text
inventory is distinct from complete implementation: each scope-disposition file
lists the selected source units and those retained for later manual work.

## Concrete checks and their meaning

| Scenario | Expected and observed result | Error exposed |
| --- | --- | --- |
| MMF has exactly six completed calendar months of history | TRUE | A strict `> 6` comparator rejects the boundary incorrectly |
| Additional 30-day annualised return but no seven-day figure in the document | FALSE | Omitting the companion-figure condition incorrectly clears the selected check |
| Online six-day figures are not updated daily | FALSE | Confusing the sub-seven-day duty with ordinary performance disclosure |
| Canadian standard-security trade on 27 May 2024 | VALUE 1 business day | Reusing the US 28 May date misses the footnote |
| Canadian trade before cutover with unknown prior settlement count | UNKNOWN | The circular alone does not establish Canada's prior standard |
| FX leg associated with US securities trading | OUT_OF_SCOPE | Securities T+1 must not be applied to the FX leg |
| IPD submission on 29 November via existing channel | TRUE for this route check | Ignoring the extended parallel run |
| IPD submission on 30 November via existing channel | FALSE | Excluding the first mandatory day |
| Incidental Type 9 discretionary activity using covered ESG products | TRUE when the selected diligence evidence is present | Excluding an expressly included activity |
| Non-member of voluntary ESG code with adequate evidence | TRUE | Turning optional code participation into a prerequisite |
| Group resources with local responsibility removed | FALSE | Treating group reliance as transfer of responsibility |
| Deviation equals the supplied alert threshold | TRUE without alert, if the primary-market reminder is present | `>=` differs from the selected strict `>` trigger |
| Deviation below threshold but no primary-market reminder | FALSE | An alert-only control omits a separate broker duty |

TRUE/FALSE refer only to the named control and supplied classifications. They do
not mean the fund, transaction or bank is compliant as a whole. VALUE 1/2 is a
standard settlement *business-day count*, not an actual settlement due date.
The T+1 check does not calculate holidays, exceptions, market cutoffs or funding.
The MMF input is completed calendar months, not an assumed 180-day conversion.
The illustrative 100-basis-point alert threshold is a supplied scenario policy,
not an SFC-prescribed number; a 250/251-basis-point case checks parameter use.

Every circular has unknown, contradictory, expired and future-recorded evidence
cases. The reference and generated backend are compared on complete semantic
results, including source traces, missing/blocking inputs and diagnostics.
Backend identities differ; each result hash is independently reconstructed.
This protects more than agreement on one Boolean value.

Each incorrect reading is valid RuleIR and is actually compiled. Detection
requires fixed expected scenarios to disagree with both the Python result and
the generated Java class. A build failure is not counted. The ten variations
are adversarial mutations, not ten legally plausible interpretations. They are
kept visible as challenge readings in the investigation record.

## Repair, uncertainty and release controls

Each investigation begins with three pre-authored substantive readings and a
separate inventory role. They deliberately omit the same relevant source unit:
MMF minimum track record, Canadian footnote, e-IP start paragraph, incidental
Type 9 scope, or token-price alert footnote. The first scripted repair supplies
the omitted citation. The subsequent repairs supply no new authoritative legal
evidence. With seven issued actions and three repair rounds, the run stops at
`ROUND_LIMIT` and produces `BLOCKED_UNRESOLVED`.

The exact initial candidate fields are preserved. Structural evidence records
that the source reference was restored and explicitly keeps
`legal_source_commitment_resolved=false`. Citation repair is not meaning repair.
The packet's inventory remains UNREVIEWED: this run does not manufacture a
human review by using a synthetic meaning credential. The system's coverage
label `IMPLEMENTED` currently records a candidate reference; the additional
scope-disposition files prevent reading it as proof that every cited clause has
been compiled.

External authorities and bank-owned definitions remain missing: Advertising
Guidelines, UT Code, market settlement rules/calendars, the e-IP launch source,
Code of Conduct, ESG VCoC definitions, intermediary tokenisation guidance and
VATP Guidelines. The MMF appendix and 26EC22 tokenisation dependency are acquired
and are recorded separately. Each run has 8 or 9 unresolved issue records;
repeated provisional assumptions are separate records, not 8 or 9 independently
identified legal questions.

The test attempts an actual `ACCEPT_MEANING` operation and calls the release
guard on the bound bundle. Both return `E_RELEASE_BLOCKED` for all five even
though Python/Java verification passed. No review decision or release is
created. Re-driving a terminal run neither changes its report nor issues another
action. The full database is exported to `history.zip`, restored with disabled
login tokens, and every report hash verifies again. Altered source text/offsets
and a report that hides unresolved issues are separately rejected by tests.

## Evidence and reproduction

- [Final report](../../../artifacts/interpretation/multi-circular-round1/attempt-03/report.json)
  and [run manifest](../../../artifacts/interpretation/multi-circular-round1/attempt-03/run-manifest.json).
- [Regression JUnit report](../../../artifacts/interpretation/multi-circular-round1/regression-tests.xml): 113 passed, no failures/skips; two existing dependency deprecation warnings.
- [Frozen cases and fact definitions](../../../examples/multi-circular-2026/circulars.json),
  [source hashes](../../../examples/multi-circular-2026/source-freeze.json),
  [test module](../../../tests/integration/test_multi_circular_interpretation.py)
  and [runner](../../../scripts/run_multi_circular_integration.py).
- [Pre-run plan and subsequent repair](../../plans/multi-circular-integration-2026-09-23.md).

The final durable run took 50.69 seconds on CPU, using Python 3.11.15 and Java
17.0.20.1. Each circular's directory preserves packet, bundle, scenarios,
requests, generated Java/JAR, full verification results, two mutant bundles and
results, configuration, complete investigation, report and scope disposition.
The attempt also retains exact input bytes, hashes and an exported database.
The manifest records the base commit **plus dirty working-tree input hashes**;
the run must not be attributed to the base commit alone.
Extracted source text and frozen input copies retain original whitespace for
hash fidelity. Generic whitespace warnings on those files are expected; authored
test, runner and documentation changes pass the scoped whitespace check.

```sh
.venv/bin/python -m pytest tests/integration/test_multi_circular_interpretation.py -q
.venv/bin/python scripts/run_multi_circular_integration.py \
  --output /tmp/legalmath-circular-verification-new/report.json
```

Use a fresh output directory; the runner refuses to overwrite evidence. It
requires the existing Java 17 toolchain or `--jdk /path/to/jdk17`. Tests are
offline and call no model/provider. The full regression command was:

```sh
.venv/bin/python -m pytest tests/integration tests/interpretation -q \
  --junitxml=artifacts/interpretation/multi-circular-round1/regression-tests.xml \
  -o faulthandler_timeout=60
```

That command passed in the trusted context in 108.35 seconds. The initial
sandbox execution stalled in the pre-existing FastAPI TestClient test and was
interrupted; that is not evidence of a product failure. The focused source/Python
checks also passed independently before the final Java run.

## Review findings, repairs and decision

The preliminary harness was too weak: it reused two existing circulars, supplied
generic proposal labels, tested fragments, ran no repairs and discarded the
underlying temporary history. It was replaced with five additional circulars,
concrete rules/scenarios, full extracted-text inventory, compiled challenge
readings, bounded repair and durable history. The superseded structural-only
report remains under `preliminary/` and is not the acceptance result.

Attempt 02 passed 73 cases. Subsequent review found an implicit pre-transition
Canadian T+2 assumption. Attempt 03 makes the prior count a supplied fact and
adds two missing-evidence cases. The earlier oracle/freeze are retained under
attempt-02/fixture-snapshot, and the current freeze explicitly records that this
revision followed execution. Neither version is a blind evaluation.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Accept engineering regression | All 75 named outcomes, full Python/Java parity, ten compiled mutations detected; 113 regression tests pass | No engineering veto in final run | Same-author rules and oracle may share a legal error | Keep as development regression corpus | Legal interpretation accuracy |
| Release these candidates | Exact meaning/evidence requirements | Vetoed for all five | Missing authorities, unreviewed mappings and deferred obligations | Obtain independent adjudication in explicit successor investigations | Whole-circular/bank compliance |
| Evaluate automatic ensemble interpretation | Independent hidden labels and real provider output | Not evaluated | Correlated readings and missed alternatives | Implement E11 reviewer annotations and reserve unseen circulars, then E10/E12 evaluation | Probability of correctness or superiority over a baseline |

The strongest alternative explanation for the pass is shared error between the
manual interpretation and manual oracle. Independent reviewers could overturn
a case outcome or identify an omitted duty; that should revise this development
corpus and invalidate affected candidate reviews. The weakest evidence remains
the English-to-formal step. The result supports executable engineering behavior
relative to explicit candidate readings, not a theorem that those readings are
legally correct.
