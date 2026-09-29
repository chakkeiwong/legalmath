# Senior bank issue documents and current program behavior

The retained NatWest and BPCE issues have explicit statutory principal-loss
provisions despite their senior rank. The CBA issue is a candidate negative for
that feature, subject to the definition and document-coverage limits below.
The existing program does not yet produce the requested binary classification.

## Source assessments

The [archive](../../../prospectus/bank-senior-controls/README.md) contains final
terms and matching programme documents for three distinct series. NatWest's
Regulation S and Rule 144A identifiers are retained separately within Series 14;
their fungibility is not inferred from common economic terms. All page numbers
below are PDF page numbers unless a separate printed number is given.

NatWest Markets plc's 4.789% March 2028 notes are unsecured and unsubordinated
(base cover). Final terms p.2 adopts the 17 March 2025 base. Its Condition 7,
p.69 (printed p.66), provides for UK bail-in reducing or cancelling principal
and for conversion, including into ordinary shares. The **loss absorption**
assessment follows from the principal-reduction limb alone. The ordinary
repayment-at-par provision in the final terms does not displace that condition.

BPCE's final terms p.3 expressly selects **Senior Preferred Notes** and the
14 November 2025 base. Condition 17, p.150, permits permanent reduction of
amounts due and defines those amounts to include outstanding principal. The
resolution discussion on p.167 explicitly includes unsecured senior preferred
debt. This supports **loss absorption**, with statutory origin recorded
separately from contractual capital-trigger conversion. It is not necessary to
treat every security received on conversion as common equity: principal
write-down independently satisfies the definition.

CBA's final terms pp.2–4 selects the 1 July 2025 circular and 13 August
supplement, €STR floating interest, and cash redemption at nominal principal.
Condition 3 (p.63) establishes unsecured, unsubordinated rank; Condition 6
(pp.126–130) provides repayment and repurchase mechanics, and Condition 11
(pp.136–137) provides default remedies. The inspected provisions support a
qualified **non loss absorption** assessment for contractual capital triggers
or disclosed statutory principal write-down. APRA payment-direction risk and
bank capital requirements (p.17), deposit preference (p.63), interest-rate
conversion (p.30), and currency conversion (pp.134–135) do not establish either
feature for this issue. The supplement updates financial reporting rather than
adding a capital-conversion condition.

There is a material definition boundary. CBA Condition 13 (pp.137–138) permits
creditor-approved reductions binding all holders. Treating ordinary collective
restructuring separately is a working interpretation of the requested CoCo
feature, not a confirmed additional user rule. If all such principal reductions
count, CBA is also positive. A negative must retain this qualification until the
definition is fixed. Referenced financial statements, the agency agreement and
deed have not been exhaustively acquired or checked; subsequent changes are
also outside this issue-date exercise. The assessment is not a mechanically
proved absence, a regulatory scope decision, or transaction permission.

## Executed diagnostic

The [pre-run plan](../../../plans/bank-senior-prospectus-check.md) states the
question, comparator, vetoes, assumptions and skeptical audit. Reproduce with:

```sh
timeout 180 python3 docs/implementation/bond-loss-absorption-classification/bank-senior-study/run_diagnostic.py
```

The diagnostic invokes the existing `observations`/`describe` implementation
through `investigate`, unchanged. It supplies source metadata and extracted
pages, not the source assessments above. It reads eight applicable documents;
the wrong-issuer ASB supplement is excluded explicitly in the study catalog.
That exclusion is a study disposition, not a demonstrated production capability.

| Observed result | Meaning |
| --- | --- |
| Nine readable PDFs, 758 pages, no empty text pages; eight applicable PDFs, 755 pages | Acquisition/extraction completed, including retention of the rejected three-page ASB document. |
| 1,048 candidate quotation locations checked | Original hashes and normalized quotation offsets passed the existing checks. This establishes text binding, not legal entailment. |
| Six document descriptions, all `UNDETERMINED` | Three final-terms documents and three bases were described. Registration and supplement documents contributed quotations, not independent issued-bond reports. |
| No binary loss-absorption field | The requested dedicated classifier is still unimplemented. Do not translate `UNDETERMINED` into a negative. |
| Zero fresh model calls and no human quality labels | This was a deterministic source/interface diagnostic, with no legal-accuracy score. |

The [actual outputs](diagnostic.json), [quotations](existing-reader/quotations.json)
and [run manifest](run-manifest.json) preserve the results, source and code
hashes, Python/PyMuPDF versions, command, commit and duration. The checkout was
already dirty; exact code hashes identify the implementation examined.

## What the examples require from the implementation

All three final-terms documents have no hits in the deliberately naive
write-down/conversion/bail-in keyword comparator. Looking only at final terms
would miss the NatWest and BPCE mechanisms. Looking across all base text
without checking meaning would flag CBA too. Therefore final/base/supplement
composition and issue scope are necessary, not optional accuracy refinements.

The current reader searches all pages, but its candidate-description step uses
only the first eight. NatWest's operative provision is on p.69 and BPCE's on
p.150. Base-document descriptions do not populate issue facts. The existing
`bond` pattern targets AT1/contingent-convertible wording, so it also does not
recognize the three senior final terms as positive bond facts.

CBA supplies concrete misleading candidates: the retrieved write-down mention
on p.130 is cancellation after repurchase. Its ten retrieved resolution mentions
concern benchmark administrators, not resolution of these notes. The
subordination pattern also matches `unsubordinated` on p.63. None became a
proved fact in this run, but treating these retrieval labels as facts would be
wrong. Ordinary majority amendments, coupon or currency conversion, and
repurchase cancellation need distinct dispositions. An ASB-only supplement with
the right programme limit and date must fail the CBA document join.

Add those cases to the planned L0–L4 classifier work, together with the positive
UK/EU statutory cases. Preserve page/definition links, legal issuer and exact
terms edition; distinguish principal from coupons, common shares from other
conversion targets, the bank from a benchmark administrator, and actual capital
loss from ordinary repayment mechanics. Missing potentially controlling terms
must prevent a supported negative. Keep the existing regulatory eligibility
predicate separate.

## Decision and reset record

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Acquisition complete for the selected issue documents | Three final/base sets retained, plus the CBA supplement and NatWest registration | Initial HTTP failure repaired; wrong issuer excluded; hashes bound | Complete incorporation and post-issue history not checked | Preserve these as development sources; resolve potentially controlling dependencies during L1 | Whole-document legal closure |
| Existing reader diagnostic completed | Actual outputs and quotation checks preserved | No locator failure or code/source mutation during run | English scope remains unproved | Implement the dedicated issue-level classifier under the reviewed plan | Binary classification accuracy |
| Candidate source assessments: UK/EU positive, CBA qualified negative under the working feature definition | Explicit principal-loss clauses for positives; scoped senior terms for CBA | CBA negative cannot be promoted while scope/definition closure is incomplete | Treatment of creditor-approved restructuring and remaining incorporated material | Resolve definition and negative coverage; retain unresolved status where necessary | Universal legal correctness or future generalization |

The diagnostic validates source preservation and exposes a missing interface;
it does not reject the classifier design or compare RuleIR with Catala.
No source-derived assessment in this note is an independent legal-quality
oracle. Hash/quotation checks, a fresh model, backend agreement and small sample
coverage cannot establish general English correctness. These inspected examples
cannot become untouched holdouts later. L0–L4 implementation, formal/native
checks and a genuinely new issuer-family challenge remain outstanding.

Post-run red-team: the strongest alternative reading counts CBA's collective
principal-reduction provision under the user's broad wording, changing its
label. A controlling loss clause or amendment in a missing document would also
overturn a negative. The weakest evidence is therefore the negative's scope,
not the explicit NatWest/BPCE principal-loss provisions. Record both issues
before promoting any negative; do not conceal them behind quotation counts.
