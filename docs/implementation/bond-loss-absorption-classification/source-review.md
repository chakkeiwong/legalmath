## Correctness review — 29 September 2026

The source review supports the reported feature distinction, with qualified
negative readings and one unresolved case. It does not establish that the
reader interprets every prospectus correctly. Reading a repayment clause
cannot, by itself, prove that a different clause never permits a write-down.
The negative decisions still depend on the declared document selection and
the bounded clause recogniser. Test and quotation counts do not measure legal
accuracy.

Two supporting explanations needed correction. Standard Chartered's previous
summary cited a Newco reorganisation provision on PDF page 55. That provision
alone does not establish the mandatory trigger. Condition 7(a)(i) on PDF page
41 explicitly provides automatic conversion into ordinary shares after a
Conversion Trigger Event; Condition 7(a)(vi), spanning PDF pages 42–43, also
provides a full principal write-down after a Non-Qualifying Relevant Event
followed by a Conversion Trigger Event. The revised generated summary cites
the latter clause, already present in the retained evidence. Its positive
answer remains supported. Duke's 2054 senior issue previously cited the 2034
series' redemption clause. The revised summary selects the clause for the
2054 Notes on PDF page 15. The negative answer remains qualified by the same
document-completeness limits.

These are real explanation defects despite the passing tests. The summary
selection was repaired and tested. The frozen reader still contains the
overbroad source candidates; they remain visible in JSON and require a future
semantic repair. The presentation correction is not evidence that these
underlying interpretation defects have been eliminated.

For the requested corporate examples, Tesco and Compass specify repayment at
100% of nominal amount. Veolia's two final terms specify €100,000 redemption
per €100,000 note (PDF page 5), consistent with the base prospectus's nominal
repayment provision. No qualifying principal-loss mechanism was identified
in their declared offering terms. NatWest and BPCE differ: their cited terms
explicitly allow statutory bail-in to reduce principal, so their senior status
does not make the feature negative. CBA's negative depends in particular on
excluding ordinary creditor-approved restructuring: its Condition 13 permits
collective modifications that can bind dissenting holders. That exclusion is
an explicit working assumption, not a proof that principal can never be lost.

Shell remains unresolved in the programme. Its final terms give a £1,000
calculation amount on PDF page 2 and £1,000 final redemption per calculation
amount on page 3. Those amounts agree, but the frozen reader does not compose
the two fields. The abstention reports an implementation limit; it supplies
no evidence of a loss-absorption feature. No answer has been forced merely to
meet an expected negative.

This feature test is separate from the SFC's overall product-complexity and
selling rules. The [SFC's examples of complex products](https://www.sfc.hk/en/Rules-and-standards/Suitability-requirement/Non-complex-and-complex-products)
also include perpetual and subordinated bonds and other special features.
Thus a junior bond can receive a negative result here and still be complex
under those rules. The [SFC's 2018 circular](https://apps.sfc.hk/edistributionWeb/api/circular/list-content/circular/suitability/doc?lang=EN&refNo=18EC89)
describes capital-ratio and government/regulatory triggers for non-viability
loss absorption. This report does not decide transaction eligibility.

The independent formal checks establish the decision and translation logic
under the supplied premises. Source completeness, unrestricted language
interpretation and performance on all future instruments remain unproved.
No human quality labels or source-answer accuracy score were used in this
review.
