# Round 13: typed control investigation executed

All six reviewed phases executed. The full suite passed **741 tests**, and all
883 required STR/gifts comparison pairs have recorded outcomes with none pending.
The result is `ENGINEERING_CHECKS_PASSED_WITH_SOURCE_UNCERTAINTY`. This is a
working investigation and conditional Java demonstration; it does not establish
that the English interpretations are correct or suitable for bank release.

The [execution plan](../../plans/assurance-round13-execution.md) implements the
reviewed round-12 successor. The [repair record](repair-executor.md) preserves
both the rejected preliminary executor and the observed failures repaired before
acceptance. The [operator guide](operator-guide.md) gives the bounded command and
explains the records. The next work is in
[assurance-after-round13.md](../../plans/assurance-after-round13.md).

## What was implemented and demonstrated

Controls now carry an explicit question, actor, assessment unit, time basis and
output meaning. Two separately requested readers assign the full claim and
candidate inventories to these controls. Disagreement keeps comparisons in
scope; a mixed question remains unresolved. Exact accounting rejects omitted or
invented identifiers. Failed large routing requests are actually split and
executed, with the complete source supplied to every smaller request.

Source-fidelity checks execute in bounded batches. The controller preserves
completed, failed and pending identities, validates source and representation
quotations, and executes smaller repairs after structural failures. A checkpoint
can be reused only with matching requests, schemas and provider settings, and
verified prior result hashes. Reuse neither consumes another live call nor
counts as another independent judgment. An exhausted allowance stops new
dispatch; it does not create a favorable finding.

Syntax lowering retains the original reading, assumptions, factual vocabulary
and questions. It can replace expression strings but cannot silently change a
question or add a convenient fact. A separate fresh context compares the
backtranslation with the original. Of three actual malformed round-12 proposals,
one e-IP proposal received a conditional correspondence judgment, while the
margin proposal and the other e-IP proposal remained unresolved. Source fidelity
is still required even for the conditionally corresponding proposal.

The source work retained the January 2026 Code, the earlier e-IP launch circular
and the Chinese STR circular. The Code's Schedule 10, Part III, paragraph 7(e)
and footnote 9 explicitly retain the listed equity-option exemption from
4 January 2026 until further notice. That supports a narrow disposition of the
extra transaction-level gazettal condition; historical gazettal timing and later
notices remain separate questions. The e-IP rule exposes the eight listed product
categories. Three English/Chinese STR provision pairs have exact source anchors;
they remain proposed correspondences, not certified translation equivalence.

## Actual interpretation outcomes

| Measure | STR 26EC2 | Gifts 23EC46 |
| --- | ---: | ---: |
| Retained claims | 43 | 53 |
| Retained readings | 17 | 8 |
| Full claim/reading universe | 731 | 424 |
| Pairs excluded by two proposed question assignments | 69 | 203 |
| Required pairs with outcomes | 662 | 221 |
| Deterministic inability-to-encode outcomes | 300 | 53 |
| Actual model assessments of executable meaning | 362 | 168 |
| Model judgment: entailed | 95 | 90 |
| Model judgment: contradicted | 2 | 0 |
| Model judgment: not established | 265 | 78 |
| Pending required pairs | 0 | 0 |
| Additional concern occurrences | 223 | 92 |
| Missing-question occurrences | 24 | 13 |

`NOT_ESTABLISHED` totals in the machine report include encoding failures: 565
for STR and 131 for gifts. The separate rows above prevent those failures from
being mistaken for model assessments. Concern and missing-question counts include
overlap across batches/readers. They are not counts of independent legal errors.
The 272 excluded pairs remain conditional relevance judgments. They have not
been proved legally irrelevant.

The two STR contradiction judgments concern the same retained candidate,
`node.5d8c4ca625a46c41ff2f4098`. Its date-only expression treats an earlier filing
on 2 February 2026 as occurring after implementation; the operational provision
specifies 9:00am. The model identified this against two source claims. The
calendar-date/operational-launch distinction remains an interpretation issue;
these judgments do not adjudicate which boundary governs every linked duty.

The gifts checks retained concrete concerns about whether an offer's funder or
provider is the relevant distributor, the treatment of inseparable mixed
benefits, statutory structured-product definitions and separate advertising
requirements. The findings are useful targeted questions. They are not a
validated error rate for the English translator.

## Java, events and PDF evidence

The new demonstration compiles three separate STR questions: certificate
applicability, satisfaction of the selected channel/method/certificate control,
and the original-event resubmission trigger. Twelve scenarios produce 36
decisions. A separate e-IP rule contributes twelve decisions covering eight
categories and four scope/uncertainty boundaries. All **48 decisions agree
between Python, ordinary generated Java and cvc5**. The **36 STR decisions also
pass the Catala Java backend** with full semantic-conformance checks.

The examples make a consequential distinction executable: an XML submission can
have an applicable certificate requirement and fail to satisfy it. A web form
can be compliant with the selected condition while the certificate requirement
does not apply. Unknown methods stay unknown. The supplied classifications and
scope predicates are stipulated facts; these cases do not automate every factual
or legal assessment needed by the circular.

The original five STR references were not discarded. Four post-launch method
references conditionally match the actual compiled certificate-applicability
outputs under explicit mappings. The urgent-blackout reference remains a
different, unaligned question. These are authored post-generation alignments,
not an independent benchmark. The actual mapping, original expectations and
snapshot hashes are retained in the Java result.

The continuing-duty example executes both an open resubmission obligation with
no invented deadline and recorded performance. Python and Java agree on the
attributed event results. Changed or unknown authority invalidates current
assurance while preserving historical replay. The demonstration uses supplied
events; it does not show bank event ingestion or an independently adjudicated
resubmission deadline.

On twelve retained PDF pages, **54 exact running-footer relocation issues were
resolved**, **339 differences remain**, and twelve footnote/column relationships
were checked against frozen development annotations. The tests detected changed
negation, quantity, unit, exception and column header, while permitting harmless
wrapping. Full-page text comparison against an annotation derived from the same
extractor is a preservation check; it does not independently validate that
extractor's legal reading. The page images, locations and residual differences
remain available for review.

## Execution manifest and repairs

The accepted master command, from the repository root, was:

```sh
/home/chakwong/python/legalmath/.venv/bin/python scripts/run_decision_master.py repair
```

| Manifest field | Recorded value |
| --- | --- |
| Git baseline | `67c9a12c30f2cac6b8a5afaa115939bef59b73d8`; dirty implementation bound by file hashes |
| Application | Project `.venv`, Python 3.11 |
| Independent evaluator | Existing assurance sidecar with cvc5 |
| Java | Pinned JDK 17.0.20.1+1 |
| Catala | Retained 1.2.1 toolchain and locked upstream integration |
| Documents | Existing PyMuPDF/XeLaTeX environment; no package installation |
| Hardware | CPU; GPU devices intentionally hidden |
| Random seeds | N/A for deterministic checks; model sampling not controllable, no stochastic method ranking |
| Source data | Four frozen round-12 packets, raw official additions and twelve frozen PDF references |
| New shared model reservations | 90: shared ledger increased from 260 to 350 of 500 |
| Increment limits | Initial ceiling 320; reviewed completion ceiling 400; no resets or refunds |
| Accepted phase runtime | About 66.4 minutes in total, including 55.5 minutes in the live phase and 10.6 minutes in regression/documents; earlier failed attempts are additional |
| Engineering tests | 741 passed; two dependency deprecation warnings; no skipped tests |
| Primary evidence | `artifacts/interpretation/round13/final-report.json`, `evaluation.json`, `execution-reviewed/` |
| Detailed live evidence | `complete-live/26ec2-completion/` and `complete-live/23ec46/` beneath round13 |

The preliminary executor was rejected because it used sliced inputs, keyword
fallbacks and non-dispatched ledgers. Its PASS labels are not accepted evidence.
The first repaired executor passed 737 tests but failed document preservation:
the baseline had accidentally included a generated expanded TeX file. The
correction permits that generated file to change while preserving substantive
sources. Four new source archives and five citation occurrences received scoped
author review. Numbering and citation spacing were repaired after rendering.

The initial live allowance reached 320 with 320 STR pairs pending. The reviewed
continuation used the remaining existing authorization, retaining the complete
old STR journal and copying only its checked ledger state. Its predecessor
record contains 148 failed/refused batch entries, many created after the ceiling
was reached. They remain historical refusal records, not 148 fresh model calls
or independent model failures. The repaired exhaustion path stops dispatch and
reports pending work. The continuation finished with no pending pairs at 350
reservations, below its ceiling of 400.

The monograph build preserved the previous 261-page content and added the typed
decision explanation. The final document-only refresh corrects the distinction
between model assessments and encoding failures and records the completed STR
outcomes. Its separate build/inspection record preserves the executed master
reports rather than rewriting the evidence of an earlier build. No application
code or tests changed during that documentation refresh.

## Decision and inference status

| Decision | Primary criterion | Veto evidence | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain the engineering implementation | Full accounting, executed repair, preserved evidence and 741 tests passed | Initial harness and document failures repaired; final checks passed | Untested inputs and broader supported-profile behavior | Extend focused controls from the retained failures | General compiler proof or production readiness |
| Retain conditional Java examples | 48 Python/Java/cvc5 decisions and 36 Catala decisions agree | No mismatch on the declared cases | Author-supplied scope/classification facts | Test new interpretations and counterexamples with explicit mappings | Correct English interpretation |
| Keep source interpretation unresolved | All required pairs have outcomes | Encoding failures, omissions and timing disagreement remain | Shared model error and relevance-assignment error | Target the listed missing definitions and disputed controls | Independent legal accuracy |
| Retain partial PDF repair | Exact footer evidence and material-change detection | 339 other differences remain | Annotation/extractor dependence | Resolve particular located differences with additional evidence | Complete PDF semantic fidelity |
| Defer effectiveness promotion | No independent comparison/effectiveness study executed | Independent references, second model family and observed review effort absent | Correlation and consultancy savings unmeasured | Design targeted independent cases and effort measurement | Reduced legal-review cost or error rate |

| Inference question | Status |
| --- | --- |
| Hard veto screen | Engineering checks passed; substantive interpretation vetoes remain visible. |
| Statistically supported ranking | None; there is no method/provider ranking experiment. |
| Descriptive-only differences | All model labels, concern counts and source-resolution counts. |
| Default readiness | Optional development mechanisms retained; no unattended legal-release policy is promoted. |
| Additional evidence needed | Independent source-family reference judgments, another authorized model family for correlation studies, and observed reviewer effort. |

The strongest alternative explanation is that both routing readers and the
fidelity reader share the same scope misconception. Agreement and validated
quotations do not rule that out. A missed cross-cutting exception among excluded
pairs would overturn the corresponding relevance finding. A counterexample to
the typed fact mapping would narrow the Java demonstration. The weakest current
evidence remains the lack of independently supported reference interpretations.
That calls for targeted tests and source assessment; it does not justify hiding
the uncertainty or treating the completed matrix as legal proof.
