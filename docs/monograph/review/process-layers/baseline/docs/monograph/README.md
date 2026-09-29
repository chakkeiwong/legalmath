# From SFC Circulars to Reviewable Bank Controls

[Read the monograph](monograph.pdf) · [Technical companion](technical-companion.pdf) ·
[Illustrated process guide](process-guide.pdf) · [LaTeX source](monograph.tex) ·
[Current revision audit](review/catala-update/review.md)

The current built draft contains a **332-page monograph**
and a **78-page technical companion**. The monograph opens with an
executive summary, a twelve-page illustrated process guide and ten chapters. It follows
two circulars from the bank's practical questions to interpretation, evidence,
mathematics, reliable execution and supervised operation.

Chapter 2 now includes the instrument-independent bank and transaction
compliance layers in section 2.4. The [design and implementation guide](../compliance/README.md)
separates sanctions, bank regulation, client controls, product rules, internal
policy and settlement, with explicit entity/jurisdiction scope. The
[original execution report](../implementation/bank-compliance/report.md) records
the initial conditional checks. The [integrated implementation guide](../compliance/implementation-guide.md)
now covers retrieved evidence, the fixed obligation inventory, compiled
RuleIR/Catala execution and event replay, while preserving missing rule/policy
inputs and unproved legal meaning.

The [continuing-investigation successor](../plans/assurance-successor-execution.md)
adds a self-contained account of the four separate interpretation questions,
conditional factual bridges, authority distinctions, the narrow Lean certificate,
raw contact-history Java inputs and the unfamiliar-source study. Its
[operator guide](../implementation/assurance-successor/operator-guide.md) explains
the exact evidence and repair procedure. The campaign's final assessment is
**engineering verified, study incomplete**: 1,303 tests passed with zero failures,
errors or skips, while none of the four frozen unfamiliar investigations completed
every required ensemble stage. The recorded-execution section retains that
failure. See the [execution result](../implementation/assurance-successor/execution-result.md),
[gap and closure audit](../implementation/assurance-successor/closure-audit.md)
and [measured continuation](../implementation/assurance-successor/next-phase-plan.md).
The new grant used 463/500 reservations; the earlier exhausted ledger is unchanged.

The controlling quality requirement is
[proof or explicit qualification](../implementation/proof-qualified-generalization/product.md),
without human quality labels or approval gates. The separate shared qualification
increment is included in the current regression. Its checked formal propositions
and existing prospective window remain distinct from the unresolved English
meaning and incomplete source investigations.

The current implementation account also describes the shared frontend and its
two executable targets. RuleIR remains the checked baseline for its bounded
profile; Catala can lower that common profile and can execute the documented
richer shared model through its native route. The
[Catala master summary](../implementation/catala/master-program-summary.md) and
[modular translation results](../implementation/catala/modular-translation/results.md)
contain the exact validation checkpoints and the limits on what they establish.
They report no universal language ranking, legal correctness or production
approval.

The chapter-six section “A proof-carrying investigation joins the methods without
joining their claims” and the process guide explain the
file-bound dossier, actual source/argument/RuleIR/Java/Catala checks, imported
interpretation alternatives, required abstention states and repair/refresh
controller. The [reviewed master plan](../plans/proof-carrying-assurance-integration.md),
[operator guide](../implementation/proof-carrying-assurance/operator-guide.md) and
[rendered review](../implementation/proof-carrying-assurance/rendered-review.md)
describe this increment. It explicitly records rejection of an initial adapter
that asserted successful checks without executed evidence. Current records are
under `artifacts/proof-carrying-assurance/verified-execution-v3`; the original
sibling attempts are preserved but not accepted. No fresh model call or legal
adjudication is claimed.

The content retains the worked interpretation cases from round four and adds
the later assurance investigations through round sixteen. The
[round-16 result](../implementation/interpretation-round16/execution-result.md)
documents four separate fidelity judgments, an executable local loop for bounded
follow-up processing, attributed event/time handling, an actual Java decimal
entry point and explicit clean-edition selection. The section “Repairing the
distinctions that a comparison can lose” develops these repairs. It preserves
the 500/500 allowance and makes no new live legal judgment. The
[operator guide](../implementation/interpretation-round16/operator-guide.md)
and [successor](../plans/assurance-after-round16.md) identify the remaining
integration and source-evidence work. The earlier
[round-15 result](../implementation/interpretation-round15/execution-result.md)
records restored-pair reassessment, child limitations, exact fractional exposure,
mutation checks, Java/Python/cvc5/Catala comparisons and remaining source
dependencies. It is engineering evidence and does not certify English legal
meaning.
Source editions, competing readings, separately scoped duties, useful comparison
cases and continuing source review enter through worked explanations. The
companion begins with a current reference organised by implementation task,
followed by provision inventories, detailed tables, interfaces and clearly dated
historical records. Keep both PDFs together for links between them. Mathematical
derivations needed for the main argument remain in the monograph.

The section “The errors that agreement can leave hidden” gives the round-15
explanation. It retains all
earlier source content and citations. The execution completed 140 of 231
executable restored pairs, leaving 91 pending and one separate unencoded pair;
all accepted findings are NOT_ESTABLISHED. The shared allowance is 500/500.
The [round-15 result](../implementation/interpretation-round15/execution-result.md)
and its [successor](../plans/assurance-after-round15.md) distinguish separate controls,
missing qualifications, historical coverage, Java input validation and the
independent reference evidence still needed.

Chapter six also includes the round-12 integrated-investigation design, the
round-13 typed-control implementation and the round-14 conditional decision
method. The
[round-14 execution result](../implementation/interpretation-round14/execution-result.md)
records 765 passing tests, actual Java/Python/cvc5/Catala comparisons and all 883 accounted STR/gifts
pair outcomes, separating model judgments from encoding failures. Round 14
challenged all 272 exclusions and restored 232 pairs for further work. Its new
explanation is “A decision can agree before its interpretations do”; the preceding
section retains the prior round's account. The
[round-14 successor plan](../plans/assurance-after-round14.md) targeted the remaining encodings,
source questions and PDF differences. These results do not certify legal meaning.

The process guide follows the executive summary. Its flowcharts expand every
step from source collection to executable controls and bank use.
They locate breadth-first/UCT search, RuleIR, Catala, Java/Python checks, Z3,
selected Lean proofs and the separate Stipula/JML/KeY research route. The
standalone guide contains the same pages; keep it beside the main book and
companion for its links to fuller explanations.

## Contents

1. A correct program can enforce the wrong rule.
2. Two circulars, from business meaning to executable controls.
3. What can be proved, and under which assumptions.
4. Languages that make interpretation inspectable.
5. Constructing and comparing competing interpretations.
6. Using disagreement to improve a review.
7. From an accepted interpretation to verified Java behavior.
8. What the bank would own and operate.
9. Measuring error, uncertainty and the value of redundancy.
10. Operating the product without losing its evidence.

The examples use public sources and synthetic facts. Earlier live development
observations and later controlled or replayed checks retain their different
meanings. They do not establish independent legal validation, comparative
live-model interpretation performance, reviewer savings or production readiness.
The section “Assurance through methods with different opportunities to fail”
introduces the round-11 multiple-assurance design and source/solver/Java
checking contracts and bounded discrepancy investigation. Its execution evidence
and current limitations are in
[the round-11 program](../implementation/interpretation-round11/operator-guide.md).
Earlier implementation observations retain their original scope.

## Build

From the repository root:

```sh
python3 scripts/build_reader_facing_monograph.py
```

The build uses XeLaTeX through `latexmk` and Python with PyMuPDF. It
settles references in both directions, runs the current document checks and
copies the main PDF to the historical `docs/proposal/proposal.pdf` location.
The companion and a `monograph.pdf` return-link target are copied beside it.
The build also exports `process-guide.pdf` with working links inside the guide
and back to the full books. The export can be repeated independently with
`python3 scripts/export_monograph_process_guide.py` after a successful build.

The current checker is `scripts/check_reader_facing_monograph.py`. It verifies
the protected source checkpoint, exact mathematical displays and listings,
labels, citation archives and existing citation judgments, reference resolution,
LaTeX diagnostics and the geometry of every page. It does not assign new citation
support judgments or certify comprehension. A changed citation context needs
explicit author review; moving an unchanged context may retain its judgment.

## Preservation and review

The [current check](review/reader-facing/document-check.json) compares the two
documents with the protected 282-page checkpoint and verifies its 243 retained
files. The 235/69-page pair is protected in a 253-file checkpoint; an earlier
244/76-page pair and build entry point are protected in a 247-file checkpoint.
All 35 original mathematical display groups, containing 37 equation labels,
remain in the main volume. The revision adds two displays in a derived,
conditional uncertainty argument. All 21 original listings remain across the
pair, with three new companion command examples. All 207 original source-unit
labels survive; label retention is a navigation check, not proof that every
rewritten sentence has the same meaning.

The pair now cites 133 archived documents in 288 citation occurrences. The
[two-CoCo offering comparison](../prospectus/coco-cases/README.md) adds six
occurrences from two real issue documents and two official rule definitions.
It explains why the same hypothetical US individual passes the declared
Barclays purchaser condition and fails Standard Chartered's, while both
transaction investigations retain unresolved bank requirements. The bank
compliance section adds 13 occurrences from 12 preserved sources; the preceding
CoCo legal survey added 24 occurrences. The successor
adds five scoped, reviewed occurrences. The preceding
integration section adds six scoped occurrences with retained author-review
records. Round 14
adds four scoped occurrences, retaining every earlier judgment. The earlier
round-13 addition retained prior reviewed contexts and added five scoped
occurrence judgments for four official circulars and an additional Code provision.
Earlier additions include two Code editions, the retained gift FAQ and the
settlement-readiness circular. The
[citation review](review/reader-facing/citation-occurrence-review.json),
[source archive](../papers/monograph-citation-archive.json) and technical reading
notes retain their support and historical limits.

The [Catala and teaching-order audit](review/catala-update/review.md) records the
current changes, terminology review, evidence mapping, build and rendered-page
inspection. Its [preservation check](review/catala-update/preservation.json)
also compares this revision with the worktree draft saved immediately before
editing: all 42 mathematical display groups, listings, labels and 240 citation
occurrences survive. The earlier [process-guide review](review/process-map/review.md)
records the technology mapping and inspection of its seven added pages. Its
236-page visual-preservation result belongs to that earlier edition. The earlier
[evidence-integration review](review/round4/integration-review.md) records the
chapter changes and their scoped inspection. The historical
[round-15 delivery manifest](../../artifacts/interpretation/round15/delivery-manifest.json)
and [document review](../../artifacts/interpretation/round15/document-review.json)
bind that round's revision and PDFs. The current PDF identities are in the
[revision manifest](review/catala-update/manifest.json).
Naturalness and comprehension still need target-reader acceptance.
Automated checks and author/model inspection cannot supply it.

The earlier [unification](review/unification/merge-review.md),
[eight-part assessment](review/revision/final-assessment.md) and
[whole-volume reconstruction](review/reader-facing/reconstruction-review.md)
describe historical editions. Their page counts do not describe this revision.
Use the build and review record above; the historical master program is not
the current delivery command.

[The implementation entry point](../implementation/START-HERE.md),
[ensemble contracts](contracts/README.md) and
[product-risk review](review/revision/product-risk-review.md) retain the separate
engineering and adoption records. This editorial revision did not rerun or
promote concurrent implementation work.
