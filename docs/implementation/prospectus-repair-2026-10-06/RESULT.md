# Ordered repair execution — 7 October 2026

The production service now executes supplied legal premises, preserves source
occurrences and dated facts, groups financial allocations by legal identity,
and consumes the actual P1–P5 products through the installed CLI. The ordered
program has been executed, repaired after failures, and replayed successfully.
**This is a substantial engineering repair, not completion of R0–R6 or legal
release.** Full contract construction, interpretation, settlement and independent
acceptance remain incomplete.

Worktree: `.worktrees/bond-gap-closure`; branch:
`feature/prospectus-evidence-master`. Implementation started from `5f1e333b5`;
the preserved defect investigation used `7fd9c4e86`. The source changes, tests
and their hashes distinguish this execution from both baselines. Historical
successor receipts and the 18 original findings have not been rewritten.

## Verification and decision

The primary question is whether the declared engineering invariants hold and
whether accepted upstream changes reach the installed report. Test counts,
remaining bracket counts and execution times are descriptive; they cannot
establish correct legal interpretation or production readiness.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Retain the implemented engineering repairs | Focused regressions and installed product changes pass | No current failing engineering check in the executed set | Unexamined inputs and legal translations | Complete the source construction and its discriminating tests | Universal correctness |
| Continue BASF development | 77 source-backed edits; copied-character checks pass; 83 unresolved brackets, no unmatched delimiter | Completeness still vetoed | Numbering, fields, margins, incorporated documents | Admit and test a complete selected-contract representation | A fully constructed German contract |
| Retain 25 law scenarios and three financial examples as development evidence | Exact source bindings and frozen hypothetical expectations pass | Actual-event and independent-review requirements unmet | Legal editions/applicability; financial conventions beyond named calculations | Supply dated facts and independently check each translation/calculation | Actual loss, ultimate recovery or complete settlement |
| Keep release blocked | No independent cohort, labels or bound sign-offs supplied | Legal promotion veto active | Independent correctness and useful coverage | Obtain genuine blinded readings after scope freeze | Legal approval or transaction permission |

The broad check passed **983 tests** with no failures, errors or skips. That
result is in [finalization/manifest.json](finalization/manifest.json). A later
visual BASF source correction and two permanent source regressions were then
checked by the **90-test focused suite**, again with no failures, errors or
skips. The current code's execution, replay and hashes are in
[finalization/run-002/manifest.json](finalization/run-002/manifest.json).
The two counts are separate runs; they must not be added.

Commands actually run, from this worktree:

```text
python3 -m scripts.verify_prospectus_repairs
python3 -m scripts.verify_prospectus_repairs --focused
python3 -m scripts.build_reader_facing_monograph
python3 -m scripts.render_prospectus_repair_review
```

The verifier runs `scripts.prospectus_delivery run`, the relevant `check`, an
identical `run`, and `status`. All nine latest phases are current; replay reports
REUSED while preserving partial/blocked dispositions. CPU execution deliberately
sets `CUDA_VISIBLE_DEVICES=-1`; the dispatcher pins the worktree source and shared
application interpreter. P6 separately installs the package under `/tmp` without
source-path injection. No new model call, OCR installation or paid service was
used. Manifests preserve actual commands, environment, source/method hashes,
wall times, outputs and receipt identities. Random seeds are inapplicable to
these deterministic checks.

Current attempts are P0/P1 009; P2/P3 008; P4/P5/P6 007; P7/P8 004.
P6 compares installed and worktree reports exactly, compares all 14 bank
catalogue records, rejects corrupted P1–P5 products, and exercises three valid
changed inputs:

| Change through installed CLI | Expected and observed |
|---|---|
| P2 synthetic repayment construction becomes UNKNOWN, descendants regenerated | Q1 NO → UNKNOWN |
| P4 necessary synthetic premise true → false, P1/P2/P3/P5 unchanged | Q4 YES → NO |
| P5 Deutsche hypothetical required loss 50 → 60, principal pool unchanged | Allocated loss 25 → 30 |

The installed package check also exposed two packaging defects during execution:
`ContactHistory.java` and `BooleanLowering.lean` were absent from the distribution.
Both resources are now included and checked byte-for-byte alongside the Python,
JSON, Java and Lean package files. Failures remain in their original attempts.

The portable evidence checkpoint preserves 84 oversized outputs: 4,765,819,896
original bytes become 153,614,137 bytes of unique compressed content. Packing
and a separate `verify --campaign repair` both passed SHA-256 round-trip checks.
Original files remain intact. All 2,198 output hashes across 63 phase receipts
match, as recorded in [checkpoint verification](finalization/checkpoint-verification.json).
Ignored campaign files are covered by the checkpoint except for the runtime
lock. The [archive manifest](checkpoint/manifest.json) lists exact paths, hashes
and the restore command. Compression changes storage, not the evidence.

## Disposition of the original 18 findings

Tests below are in `tests/prospectus_successor/test_repairs.py` unless identified
otherwise. “Regression repaired” is limited to the indicated representation and
input; it is not a claim of complete interpretation.

| Original finding | Production repair and evidence | Remaining limit |
|---|---|---|
| P3-occurrences | Exact intervals; `test_duplicate_and_multiline_occurrences_are_covered` | Source layout/meaning still supplied or bounded grammar |
| P1-excluded-reference | Ignore references in explicitly excluded/header units; `test_excluded_reference_does_not_poison_other_questions` | Full question-root reachability and AST target resolution remain incomplete |
| P1-line-segmentation | Paragraph reconstruction and cross-line intervals; same multiline test | General column, margin and dehyphenation interpretation incomplete |
| P3-multispan | Validate every interval and union their coverage; same multiline test | Coverage does not prove faithful meaning |
| P2-visibility | BASF adapter marks invisible units EXCLUDED, matching generic assembler | Full BASF construction remains partial |
| P3-explicit-negative | Execute negative typed assertions; `test_negative_conditions_conversion_subquestions_and_scope` | Global versus local negation needs reviewed scope |
| P3-condition-execution | Finite executable conditions/exceptions and referenced predicates; partial truth-table tests | At most 12 facts; general recursive definitions/priority not implemented |
| P3-question-collapse | Q2.v2 compulsory/possible/common-only; Q3 all declared questions | No independent validation of question translation |
| P4-ignored-premise | Execute actual expression; `test_all_declared_premises_participate_and_dates_are_bitemporal` and installed true/false pair | Reviewed legal expression remains a premise |
| P4-unresolved-source | Exact visible document/hash/unit/substring required; same test rejects free strings | Hash equality does not establish source authority/authenticity |
| P4-fact-valid-time | Separate effective, knowledge and observation times; same test plus existing dated counterfactual | Open end does not prove legal currentness |
| P5-invalid-shape | Validate all branches before arithmetic; `test_invalid_price_shape_is_structured_even_if_event_does_not_trigger` | Unsupported shapes return UNSUPPORTED; this is not a settlement profile |
| P5-group-identity | Require legal_holder_id; identical names stay separate; `test_distinct_legal_holders_with_identical_names_do_not_merge` | Identity and contractual aggregation must be established externally |
| P6-context-join | BASF senior-bond context with source/date/purpose mapping; stale mapping rejected | Actual bank/client/capacity facts absent |
| P0-unwired-inputs | Read review/cohort/exposure admissions; real change-ingestion regression | All supplied real assignments remain empty; count links are edition links, not adjudicated overlap |
| P3-P6-dataflow | Sealed parent-bound products, installed changes and corrupt-product rejection | Hashes are integrity checks, not signatures; scope semantics remain partial |
| controller-missing-input | Phase-specific source/store/admission/import/tool-version bindings; immutable product copies, output rehash and recovery regressions | Shared code changes still over-invalidate; exhaustive hidden-read proof and full mutation matrix remain open |
| P0-P7-P8-independence-scope | Implementer cannot adjudicate; labels/report/support/sign-offs bind cohort/method/scope | Identity assertions are not authenticated signatures or proof of actual independence |

Additional regressions reject question-scope hiding and promotion of an example
to an operative clause. Conditional repayment no longer proves absence while its
condition is false or unknown. Financial validation checks inactive branches too.
Source bytes are rechecked after intake; a valid content hash cannot silently
refer to changed local source bytes. Tests also cover interrupted receipt-pointer
publication, corrupted content-addressed products and unchanged repair admission.

## What the retained sources establish

BASF still uses four pinned documents, 519 pages, 43,626 units and 489 detected
references. The supplement is dated 27 February 2023 on p1; the annual report
records publication on 24 February 2023 on p296. Source images and findings are
retained in [document-review/REVIEW.md](document-review/REVIEW.md).

The unmatched bracket at raw offset 14862 is present in the printed p112 source.
Its unselected long-coupon span ends at 15918, before the next definition. No
closing punctuation was invented. Visual re-review also corrected an intermediate
mistake: the p112 margin says the reference-period definition applies to **all**
Actual/Actual options. That definition remains; its short/long-coupon additions
do not apply to the selected annual no-stub coupon. This source correction is
captured in `test_basf_sources.py`. The retained interim run with the over-deletion
is superseded, not silently relabelled correct.

The supplement p12 genuinely contains both 195–209 and 209–290. Both are preserved
pending a justified incorporation interpretation. The general AST has Text,
Sequence, Choice, Field, Reference and dated Override nodes with exact anchors,
but not all BASF construction uses it. Unaccounted raw text remains UNKNOWN;
the current conservative AST does not automatically discharge every unselected
branch or overridden source occurrence.

Seven additional document layouts were retained: four prior OCR extractions
and three native financial-profile page sets. Raw OCR geometry and corrected
transcriptions stay separate. PyMuPDF emitted a coordinate of -0.0000152587890625
at a page boundary. A recorded 0.001-point normalization handles only that
numerical boundary noise; larger invalid coordinates still fail. OCR correctness
and reading order do not follow from this tolerance.

All 25 retained law cases execute under explicitly hypothetical development
facts. Dana's UAE-invalidity premise was assumed in the English litigation,
not adjudicated as UAE invalidity. The HETA percentage is an issuer report of a
specified decree/bucket, not ultimate recovery for an arbitrary instrument.
Lloyds concerns an optional regulatory call; Ukraine's procedural result does
not discharge the debt. These boundaries survive the scenario results.

Deutsche gives loss 25; BBVA gives price 501/100 and three whole shares; SEB gives
price 3 USD and three shares for the declared synthetic accounts/holder. Exact
amounts and hand calculations were checked by the implementer. Independent
calculation review, source conventions and complete settlement remain pending.

## Remaining executable work

R0's diagnosed false-answer and context-join defects are repaired under the
tests above. R1's real dataflow, publication recovery and evidence ingestion
execute. R2–R6 retain engineering as well as external-evidence obligations:

1. Complete the BASF choice/field/numbering and incorporation ledger, then render
   it through a common construction representation with explicit exclusion and
   override accounting. Preserve the common ICMA definition. Test each mapping
   against both the final terms and governing margin. Construct Deutsche/BES and
   G13–G17 agreements with their own editions and amendment priorities.
2. Attach corrected OCR characters to geometry and admit column/margin/paragraph
   relations. Complete indirect dependency traversal and condition/exception
   scope. Run reviewed-construction/reviewed-interpretation, reviewed-construction/
   automatic-interpretation, and automatic/automatic arms on the same questions.
3. Supply legally effective editions and actual entity/forum/event/procedure/
   suspension facts where actual answers are wanted. `P4/law.json` accepts the
   selected instrument's basis/facts; `P4/cases.json` is the distinct development
   catalogue. A power's applicability must remain separate from its exercise.
4. Complete only source-justified calendars, accrual, adjustments, FX, fraction and
   settlement rules. `P5/scenario.json` supplies the selected instrument scenario;
   `P5/scenarios.json` supplies the separate profile cases. No convention should
   be filled merely to make a calculation run.
5. Close controller validation coverage for every declared tool/store/parser and
   imported-rule mutation; reduce shared-code over-invalidation. The worklist
   now distinguishes code/source work from evidence admission. It is not a
   general automatic repair solver, and no such completeness claim is made.
6. Obtain real independent readers, adjudicator, cohort/exposure records, labels
   and sign-offs; bind them to the evaluated method and supported questions.
   Then run the paired finite acceptance exercise and repair any supported error.

The strongest alternative explanation for the passing examples is narrow
development coverage plus supplied interpretation. A source or heldout case
that contradicts a supported answer would overturn a correctness claim for that
scope. The observed source-selection mistake demonstrates this risk directly.
The software harness remains usable; the current general prospectus interpreter
has not met the delivery criterion. Neither failure invalidates the research
direction. Missing independent evidence vetoes promotion while these concrete
engineering repairs remain available.

## Literature and proof boundary

The retained technical literature review and reference derivations remain in
`../prospectus-phase-roots-2026-10-06/`. Occurrence-union coverage, finite Boolean
completion, temporal admission, exact holder allocation and deterministic parent
binding now have production implementations and regression evidence. Their
arguments are conditional on faithful source representations and complete
dependencies. They are not machine-checked proofs of Python, complete legal
interpretation, source completeness or zero future error. The source-specific
BASF failure particularly prevents transferring a representation proof into a
claim that the representation was chosen correctly.
