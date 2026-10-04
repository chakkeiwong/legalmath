# Prospectus corner cases: sources and observed failures

The extension adds **30 distinct test specifications**, supported by **51 checked
source passages**. We saved **24 new PDFs and six readable official CJEU judgments**.
The unchanged reader abstained on all **seven new offering PDFs**, with **29
unresolved clause records** and no runtime errors. Three additional clause probes
reproduced a specific defect: unpaid principal cancellation was discarded as
ordinary cancellation after redemption or repurchase.

These counts describe a deliberately difficult collection, not 30 independent
issuers or 30 proven investor losses. The 30 legal expectations have not all been
executed by an integrated legal evaluator or independently adjudicated. The three
failed checks are minimum clause-classification checks; the overall issue answers
in those probes remained abstentions.

**Request balance:** 58 of the additional 100 public requests used; 42 remain.
Cumulative receipts: 170, authorised ceiling: 212. Retrieval stopped because the
retained material supports a useful bounded diagnostic. No paid model calls,
installations or GPU work were used.

## Evidence and deliverables

- [Thirty test specifications](test-specifications.json): source hashes, page or
  paragraph anchors, expected distinctions, forbidden inferences and execution scope.
- [Reviewed source catalogue](reviewed-catalogue.json): source roles, identity
  corrections and missing originals.
- [Originals and source index](../../prospectus/corner-cases-2026-10-04/source-index.json):
  PDFs, HTML, extracted text, pages and HTTP receipts.
- [Raw reader results](run-001/summary.json) and [run manifest](run-001/manifest.json).
- [Three reproduced failures](regression-findings.json).
- [Monograph](../../monograph/monograph.pdf), physical PDF pages 81–87, and
  [technical companion](../../monograph/technical-companion.pdf), pages 12–21.
  The full 30-case matrix is on companion pages 20–21.
- [Next repair plan](../../plans/prospectus-corner-repair-2026-10-04.md),
  [rendered review](rendered-review.json), [reset memo](RESET-MEMO.md) and
  [archive verification](archive-verification.json).

The 24 PDFs comprise seven offering documents, ten BES supplements, four UK
judgments and three HETA issuer notices. Six additional CJEU judgments are retained
as readable official HTML. Discovery pages, challenge responses and failed downloads
remain in the request record but are excluded from the 30 substantive documents.
The original 24-document study and its reviewed results remain a separate, preserved
comparison.

## The corner cases

| Cases | Source family | Distinction tested |
| --- | --- | --- |
| CC01–CC05 | BES final terms and two programme editions | An empty text layer does not establish absence; bond identity, issue date, supplement set, issuer/guarantor and senior/subordinated options must match |
| CC06–CC09 | Novo Banco, CJEU 2024 and 2021; UKSC Oak loan | Pre-suit and pending-suit retransfers have different recognition questions; loan and bond claims differ; challengeability does not itself suspend an act |
| CC10–CC12 | HETA notices | Maturity stay differs from haircut; 46.02% remaining differs from a 46.02% reduction; a renamed issuer differs from a related banking network |
| CC13–CC14 | Dana Gas, 2017 English judgment | Different documents can have different governing laws; an assumed fact is not a finding of illegality |
| CC15–CC16 | Lloyds ECNs, UKSC 2016 | Optional regulatory call differs from conversion/write-down; majority and dissent cannot be merged |
| CC17 | Ukraine, UKSC 2023 | A defence allowed to proceed to trial is not a finding of duress or a debt discharge |
| CC18–CC20 | Kotnik and Kuhn, CJEU | Commission policy differs from a domestic power; private arrangements differ from official measures; jurisdiction classification does not decide haircut merits |
| CC21–CC23 | Banco Popular and Snoras, CJEU | Share-specific remedies do not become bond rules; deposit guarantees and investor compensation have distinct conditions |
| CC24–CC27 | Adriatica Finance, 2007 ABS | Public receivables and seller support are not note guarantees; protected funds, enforcement delay and unaccelerated underlying payments affect recovery |
| CC28–CC30 | Adriatica, Adriano Lease and Adriano Finance | Unpaid cancellation retains dates and exceptions; cross-page certificate/notice conditions matter; one claw-back exemption does not establish another |

The legal sources are useful precisely because their limits are preserved. A promise
to pay, a statutory power, an actual intervention, recognition abroad, access to
assets and ultimate recovery are different propositions.

## Reproduced clause errors

All three minimum checks fail against the preserved outputs. The observed disposition
is `repurchase_or_redemption_cancellation`, which the reader describes as
cancellation after repayment or repurchase.

| Check | Retained source | What the original condition says | Why the observed exclusion is wrong |
| --- | --- | --- | --- |
| CC29-final | Adriano Lease Sec., Condition 8.1.3, PDF p140 | Insufficient funds at final maturity can leave amounts cancelled; payment improperly withheld or refused is excepted | The cancelled amounts can be unpaid |
| CC29-exhaustion | Adriano Lease Sec., Condition 9.2.3, pp144–145 | After the specified servicer certificate and representative notice, no further claim remains and unpaid claims are discharged | This is conditional exhaustion of unpaid claims, not evidence of completed repayment |
| CC28-cancellation | Adriatica Finance, Condition 7(b), p121 | Unpaid amounts remain after December 2021 maturity until the later December 2026 Cancellation Date, with a gross-negligence/wilful-misconduct exception | Timing and the exception govern the unpaid balance |

The rule at `loss_absorption_reader.py:92` checks for a repayment-related word and
cancellation together, without requiring that repayment actually occurred.
`clause_features` then exempts this disposition from semantic interpretation.
The next repair must inspect segmentation as well: neighbouring numbered conditions
can carry different actions and conditions. Deleting the exclusion indiscriminately
would risk reintroducing false positives for genuinely paid redemption.

The source-reviewed expectation is narrow: retain the unpaid-cancellation meaning
or leave it unresolved. Full repair requires preserving all prerequisites, dates,
subjects and exceptions. Passing this minimum screen alone would not establish
correct legal applicability.

## Whole-document observations

| Offering PDF | Text/extraction observation | Result | Unresolved clause records |
| --- | --- | --- | ---: |
| BES Series 23 final terms, 14 July 2011 | Scan; OCR required | ABSTAIN | 0 |
| BES Series 35 final terms, 20 January 2014 | Scan; OCR required | ABSTAIN | 0 |
| BES 3 November 2010 base prospectus | Partial text; one empty page flagged | ABSTAIN | 17 |
| BES July 2013 base prospectus | Text extracted | ABSTAIN | 1 |
| Adriano Lease Sec., December 2011 | Text extracted | ABSTAIN | 2 |
| Adriano Finance, 2009 RMBS | Text extracted | ABSTAIN | 5 |
| Adriatica Finance, March 2007 | Text extracted | ABSTAIN | 4 |

All three additional clause probes also abstained. Empty scans produced no evidence;
zero unresolved clauses in those outputs is not completeness. The two scans were
inspected as images and fields were transcribed separately. Those transcriptions
were not substituted into the frozen raw-PDF runs, and no automatic OCR result is
claimed.

Run command: `python3 -m scripts.run_prospectus_corner_tests analyze`.
Elapsed time: 13.236 seconds. The manifest records commit
`2d6b737b27aa6f028d8b37ccac17cbd5816d4488`, branch
`feature/prospectus-evidence-master`, exact input/output hashes and Python
`/home/chakwong/miniconda3/envs/tfgpu/bin/python3`.
The run was CPU only with CUDA intentionally hidden; no ML framework was imported
and no GPU was probed. Seeds are inapplicable to this deterministic diagnostic.

## Source corrections and open dependencies

BES Series 23 is EUR81.4m, 6.875%, due 15 July 2016, ISIN **PTBEQBOM0010**.
C-500/22 describes a BES bond with that coupon and maturity and records a 2015
coupon followed by 2016 nonpayment after the December 2015 retransfer. The judgment
does not print the ISIN. This is a strong candidate match, pending the original
Portuguese decision and Annex 2B. It is not an independently established exact
identifier link. The 2010 base and all six named supplements are saved.

BES Series 35 is EUR750m, 4%, due 21 January 2019, ISIN **PTBENKOM0012**.
The previously retained Series 36 is EUR750m, 2.625%, due May 2017, ISIN
**PTBEQKOM0019**. Their 2013 base and four supplements are now saved; the two
issues require different supplement sets. Incorporated financial reports, full
precedence analysis and exact measure-to-instrument matching remain open.

HETA's April notice is dated **11 April 2016**, concerning the decree of 10 April.
It reports reducing eligible nonsubordinated liabilities **to 46.02%** of the
stated amount, including the specified accrued-interest bucket: a 53.98% reduction,
with later interest set to zero. Its March 2015 maturity notice is a separate event.
The original FMA decree and exact bond/guarantee list remain missing. Issuer notices
do not establish the final recovery or every security's treatment.

The files acquired under Hypo search keys are **Adriano Lease Sec., Adriano Finance
and Adriatica Finance**. They are Italian securitisations, not HETA debt.
Adriatica's public-receivable enforcement disclosures and Adriano Finance's
Article 65/67 discussion refer to historical Italian law. The cited statutory
versions have not yet been acquired independently.

Dana Gas's original 2013 offering, Lloyds' 2009 offering and trust deed, and Ukraine's
2013 offering are still missing. Their retained judgments support the specified
reasoning distinctions. Dana Gas assumes the disputed UAE-law premise without
deciding it; the English purchase undertaking is held enforceable. The Ukraine
decision permits specified alleged force-based duress to proceed to trial and
rejects other listed defences; it does not establish duress or final nonpayment.

Kotnik does not prove a write-down of the previously retained SID Bank notes.
Kuhn does not establish the haircut merits or scope for the previously retained
English-law Greek 2057 series. Banco Popular's share-specific remedy ruling and the
Snoras compensation conditions must not be generalized to all bonds or all issuer
credit losses. Original offering forms and independent adjudication remain open.

## Validation, interpretation and decision

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain the new source corpus | Originals, receipts and checked passages preserved | No source-integrity or request-budget veto found | Missing exact annexes and some primary measures | Target the named missing sources | 30 fully proved adverse legal events |
| Preserve the frozen diagnostic | Exact reader/input/output bindings; no runtime errors | Historical and method integrity checks pass | Whole-document selection includes programme options | Compare a separately recorded candidate | Complete issue-level legal validity |
| Reject the three clause classifications | Unpaid claims must not be excluded as paid cancellation | All three minimum semantic checks FAIL | Detailed condition logic still needs implementation | Repair action relation and segmentation with controls | A demonstrated complete false-negative answer |
| Continue the research direction | Concrete failures have identifiable repair targets | No continuation veto fired | Integrated legal evaluation and adjudication pending | Execute the staged repair plan in a separate candidate | Production/default readiness |
| Retain documentation provisionally | LaTeX build and affected-page inspection | No clipping or missing local links observed | Human assessment of prose remains pending | Human review when available | Human readability certified by compilation/model review |

The negative result rejects the current clause reading. It does not invalidate
the retained documents, diagnostic harness or research direction. The strongest
alternative explanation for part of the error is segmentation mixing separate
conditions. The original page inspections and narrow probes establish the
classification mismatch; a future candidate must distinguish clause isolation
from semantic repair.

No stochastic method comparison was made, so no statistical ranking is supported
or requested. Abstention counts and elapsed time are descriptive. A curated stress
set cannot estimate population accuracy.

## Reproduction and document review

From the worktree:

```text
python3 -m scripts.run_prospectus_corner_tests verify
python3 -m scripts.check_prospectus_corner_findings
python3 -m scripts.verify_prospectus_corner_archive
```

The middle command deliberately exits **1** because the three defects remain.
The other commands check integrity, not legal success. They make no network
requests and do not rerun the engine or change its method. Do not rerun extraction:
the source index is bound to the frozen run.

The LaTeX build completed through `python3 -m scripts.prospectus_corner_cases build`:
365-page monograph, 89-page technical companion and 24-page process guide.
The build retained 136 citation documents, 301 citation occurrences and all 207
source labels. The affected rendered pages and the adjacent appendix transition
were inspected. The source comparison preserves equations, citation/link targets,
labels and substantive prior findings; obsolete acquisition statements were
updated to reflect the newly readable judgments and saved BES dependencies.
This is a provisional model review, not human prose acceptance.

The final combined integrity check passed in 3.612 seconds: 3,775 historical
campaign files, 24 prior PDFs, 25 prior output files, 293 reader files, 19 new
result files, 116 receipt-bound response/header files, two policy snapshots,
18 rendered pages and 70 local LaTeX links verified. The three classification
failures remain failures. `git diff --check` also passed. Every removed line of
the manuscript diff was inspected; the removals update superseded acquisition
and permission status, while their legal qualifications remain in the new text.
