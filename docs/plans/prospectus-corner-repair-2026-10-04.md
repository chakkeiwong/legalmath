# Repair priorities after the 4 October 2026 corner-case study

## Scope and evidence

This is the next-phase plan, separate from the frozen acquisition and diagnostic plan.
The current task ends with retained corner cases, diagnostic results and documentation;
no reader repair is applied to the frozen 293-file baseline.

The baseline is commit 2d6b737b plus the exact 293 file hashes in
`docs/prospectus/difficulty-2026-10-04/freeze.json`, not the commit alone.
The original 24-document run and extension run-001 remain immutable. Any repaired
candidate needs a separate method snapshot, runner and output directory; do not
weaken the old verifiers to permit changed code.

The extension contains 30 test specifications with 51 source anchors, supported by
24 PDFs and six readable official CJEU judgments. Seven whole-document runs and
three clause probes all abstained. Three unpaid-cancellation clauses were wrongly
classified as cancellation after repayment. These are clause defects, not measured
issue-level false negatives or a legal accuracy estimate.

## Research intent and evidence contract

Question: can the reader preserve payment relations, conditions, issue identity and
dated legal scope while returning unresolved results when evidence is incomplete?

Comparator: unchanged archived reader on the exact original inputs. Primary repair
criterion: all three retained unpaid-cancellation passages cease to be discarded
as ordinary repayment; their prerequisites and exceptions are retained, and true
post-payment cancellation and paid amortisation controls keep their proper meaning.
A minimal unresolved answer is safer but is not enough to establish full semantic
repair. The next phase must test condition-preserving interpretation explicitly.

Promotion vetoes: wrong issuer/series/date, dropped exception, false claim of OCR
coverage, changed source text, missing dependency, loss of an existing valid control,
or an unadjudicated complete legal conclusion. These prohibit promotion, not further
repair. Continuation vetoes: corrupt baseline or output, unavailable reproducible
environment, unaccounted requests, exhausted authorised request budget, or test
harness that cannot bind observations to exact input and method versions.

Repair triggers: any reproduced wrong exclusion, merged subjects, missing condition,
incomplete extraction or unresolved dependency. Explanatory diagnostics: abstention
count, unresolved count, elapsed time, test count, downloaded-document count and
local quote matches. None measures legal accuracy. No population inference,
production readiness, ultimate recovery or transaction permission follows from a
passing engineering check.

## Skeptical audit

PASS for this staged repair design; implementation remains future work. The
important baseline is the archived dirty method, and the candidate must be recorded
separately. Three probes are related examples, not independent legal events.
Switching them all to unresolved can pass the existing minimum screen while still
losing exceptions, so the repair criterion explicitly adds condition tests.
Judgments and issuer notices must not be treated as prospectuses. Missing annexes
and primary measures remain missing rather than being replaced with search snippets.
The plan does not demand that all inputs produce definitive answers.

A key alternative explanation is segmentation: the recorded quote can contain
neighbouring numbered conditions. Inspect the segment and local action relation
before changing a keyword exclusion. Merely deleting the exclusion could reverse
the earlier false-positive problem for paid amortisation.

## Material defaults and assumptions

| Choice | Provenance and status | Justification | Failure mode | Earliest check |
| --- | --- | --- | --- | --- |
| Frozen dirty method as comparator | Archived prior study; baseline | Matches the actual recorded observations | Comparing only HEAD loses earlier repairs | Verify 293 file hashes and method.zip |
| Retained PDF and official judgment anchors | Reviewed source preference | Makes interpretation inspectable | Text extraction drops a qualifier or combines clauses | Inspect original page and adjacent condition |
| Minimum screen permits unresolved | Existing diagnostic criterion only | Prevents silent exclusion of unpaid loss | Everything abstains while understanding remains absent | Separate minimum screen from exception and condition tests |
| Current Python3 environment | Existing environment; convenience | Avoids installation during bounded diagnostics | Same command resolves to different interpreter later | Record executable, versions and available PDF/OCR tools |
| Targeted stress corpus | Deliberate selection, not a random sample | Exposes difficult mechanisms | Percentages mistaken for population rates | Report case-level decisions and repeated source families |
| 42 public requests remaining | User allowance; hard resource limit | Closes specific missing source links | Repeated access failures waste requests | Count all receipts before each small batch |

No learned component, stochastic ranking, GPU experiment or hyperparameter transfer
is proposed. If a later repair introduces one, write its own evidence contract.

## Phase 0: preserve and isolate

Run the following existing commands from the worktree. The second command is
expected to exit 1 while all three defects remain; preserve that failure.

```text
python3 -m scripts.verify_prospectus_corner_archive
python3 -m scripts.check_prospectus_corner_findings
```

Use an isolated candidate checkout or restore the archived method into a dedicated
candidate directory. Add a candidate runner that records source hashes, candidate
method hashes, baseline reference and new output paths. Never overwrite run-001,
the original freeze, or the existing test specifications.

Refresh record: baseline integrity, actual interpreter, candidate location and
exact candidate commands. Stop implementation if the baseline cannot be reproduced.

## Phase 1: payment relation and clause boundaries

Investigate `src/legalmath/prospectus/loss_absorption_reader.py`:
`_candidate_features` currently excludes a clause when it contains purchased,
redeemed, surrendered or repayment plus cancellation without a capital-trigger
keyword; `clause_features` then exempts that result from semantic interpretation.
Check `segments` and the resulting spans before narrowing this rule.

Use Adriano Lease Condition 8.1.3 (PDF p140), Condition 9.2.3 (pp144–145) and
Adriatica Condition 7(b) (p121). Bind cancellation to the outstanding unpaid amount
and its conditions; preserve certificate, notice, no-further-recovery,
improper-withholding and misconduct qualifications. An incomplete condition must
remain unresolved rather than become an unconditional positive.

Controls must include true cancellation after completed redemption/repurchase,
paid amortisation from the earlier Mizuho study, partial payment plus a separate
unpaid balance, negated redemption, and the same condition split across a page.
Retain existing loss-absorption tests and extend them with source-based assertions.
Run only focused tests first; run the wider prospectus suite after those pass.

Refresh record: failures eliminated, new regressions, exact candidate hash, remaining
condition errors and whether segmentation or action binding explains each result.
A remaining candidate failure triggers the next repair, not abandonment.

## Phase 2: extraction, editions and claim identity

Treat empty or incomplete text as an explicit extraction limitation. Keep raw PDF,
OCR derivative, page image, engine version and reviewed fields separate. Compare
OCR fields against the already reviewed BES images; do not label manual transcription
as OCR. Inventory existing OCR availability before considering installation.

Build dated dependencies for BES Series 23 (2010 base plus six supplements),
Series 35 (2013 base plus the first two) and Series 36 (2013 base plus four).
Track incorporated financial reports, precedence and series choices as unresolved
until checked. Reject a substituted newer base and distinguish issuer from guarantor,
senior from subordinated options and related entities from renamed issuers.

Primary criterion: exact dependency set and scope are preserved; missing inputs
force a stated unresolved result. Refresh record: complete versus open dependencies,
field mismatches, and the next smallest source or parser repair.

## Phase 3: dated law and judicial reasoning

Implement a source-bound evaluator for the legal specifications. Keep separate:
contractual entitlement, statutory power, actual measure, recognition in the forum,
procedural posture, enforcement constraints and observed payment.

Discriminating comparisons include pre-suit versus pending-suit BES retransfer;
Oak loan versus bond claims; challengeability versus suspension; HETA delay versus
haircut and interest buckets; Dana Gas assumption versus finding; Lloyds majority
versus dissent and call versus conversion; Ukrainian triable defence versus
discharge; state-aid guidance versus domestic powers; shares versus bonds; deposit
guarantees versus investor compensation; and public-fund attachment restrictions.

The retained judgments support these distinctions. They do not supply every original
offering document or final legal outcome. Independent legal adjudication is required
before complete legal labels are promoted. Local software checks can test the
representation and faithful preservation of reviewed premises first.

Refresh record: source-supported distinctions, unresolved applicability, adjudicator
disagreements, missing originals and what evidence could change each expected result.

## Phase 4: targeted acquisition, within the existing allowance

Start at 170 cumulative receipts, ceiling 212. Prioritise:
1. Portuguese 29 December 2015 decision and Annex 2B with exact bond identifiers.
2. Original HETA FMA measure and exact debt/guarantee list.
3. Dana Gas 2013 listing particulars, Lloyds 2009 ECN offer/trust deed, Ukraine 2013 offer.
4. Historical Italian statutory versions and the Popular/Snoras original offers.

Create a separate dated follow-up queue, source index and policy snapshot. Do not
change the frozen extension source-index or run its extraction command again.
Preserve every failed response; use an accessible official route or clearly labelled
mirror, without defeating access controls. Stop repeated inaccessible targets and
spend requests only when the next source can resolve a stated uncertainty.

Refresh after each small batch: receipt count, inspected identity, versions, new
evidence and any revised expectation. Publication dates are not proof of acquisition
before a historical event.

## Phase 5: compare and report

Run candidate outputs against fixed case-level expectations and paired controls.
For the legal layer, adjudicate before calculating accuracy. Report original and
candidate abstentions alongside incorrect exclusions, missed conditions and scope
errors. Keep failures in the output. Passing the three minimal checks establishes
only that those known exclusions were removed.

Save candidate manifest, focused and broader test logs, unresolved-case table,
source-bound reasoning, reviewed next-phase plan and reset memo. Rebuild the LaTeX
documents only when reported behaviour changes; inspect changed rendered pages and
preserve all source qualifications. Human review of prose remains pending.

Decision table for each phase: primary criterion, vetoes, main uncertainty,
next justified action and what cannot be concluded. Stop only for a continuation
veto; otherwise refresh and execute the next repair justified by the observations.
