# Fact correspondence review

These are generated readings awaiting review. No semantic mapping is approved.
This packet exposes model proposals and cannot serve as blind reference annotation.

Source packet: `f7a64d3de90d02e99196d98ccef21e753d809b06de92036166db0eb3639b7449`

## Left reading

For an application or submission to IPD concerning an IPD-administered product within footnote 1's listed classes, the submitting actor must use e-IP from 30 November 2024. Existing channels remain accepted through the extended parallel run. Annual-fee settlement through e-IP is optional. A true result within scope satisfies only the selected submission-route control; outside scope no compliance determination is made.

Distinction: Treats the attached, unqualified product enumeration as an exhaustive definition. Unlike r2, an otherwise qualifying submission concerning an IPD-administered product outside every listed class falls outside this selected control. The strongest uncertainty is that the footnote contains no express exclusivity language. This difference is conditional; the packet establishes no actual unlisted IPD-administered product.

| Fact | Type | Declared meaning | Unit | Judgment required | Source units |
|---|---|---|---|---|---|
| is_product_submission | bool | The assessed event is an application or submission to IPD concerning an investment product; fee settlement alone is excluded. Classification of borderline communications requires judgment. | Boolean | True | ['u1', 'u3', 'u9'] |
| product_administered_by_ipd | bool | The investment product concerned is administered by IPD. | Boolean | True | ['u1', 'u9'] |
| product_in_footnote_classes | bool | The investment product concerned belongs to at least one product class enumerated in footnote 1. | Boolean | True | ['u17'] |
| submission_date | date | Gregorian calendar date on which the assessed application or submission is made to IPD. | Gregorian calendar date | False | ['u1', 'u9'] |
| submitted_via_eip | bool | The assessed application or submission is submitted to IPD via e-IP. | Boolean | False | ['u1', 'u9'] |

Scope: `(and is_product_submission product_administered_by_ipd product_in_footnote_classes (>= submission_date (date 2024-11-30)))`

Result expression: `submitted_via_eip`

Assumptions:

- The assessment concerns one identified submission event and only its route.
- Footnote 1 is an exhaustive product boundary for this circular.
- Extending the parallel run carries forward existing-channel acceptance through 29 November 2024.
- The event date controls commencement; no unstated grandfathering exception is assumed.
- Product administration, product classification and submission classification remain supplied facts; no truth values are inferred.

Unresolved questions:

- Is the footnote intended to exclude any IPD-administered product outside its enumerated classes?
- Which communications during an existing application count as submissions?

## Right reading

Selected control: compulsory e-IP submission route after the extended parallel run. Existing channels remain available through 29 November 2024. For each covered application or submission made from 30 November 2024, the submitter must use e-IP. Existing reporting requests are announced as integrated into e-IP, while annual-fee payment through the system remains optional. The practicability qualification concerns SFC enhancements only.

Distinction: This reading tests the route used for an individual covered submission from the transition date. It neither makes annual-fee payment through e-IP compulsory nor creates underlying reporting obligations. The strongest uncertainty is the precise product and communication scope, including any qualifications in the unavailable earlier circular. The supplied text does not support a materially different transition date or a general post-transition choice of channels.

| Fact | Type | Declared meaning | Unit | Judgment required | Source units |
|---|---|---|---|---|---|
| is_covered_submission | bool | The evaluated event is an application or submission to IPD concerning an investment product administered by IPD. Classification must account for footnote 1; optional fee payment alone does not establish this fact. | Boolean classification of one submission event | True | ['u1', 'u3', 'u9', 'u17'] |
| submission_date | date | Gregorian calendar date on which the evaluated application or submission is made to IPD. | Gregorian calendar date | False | ['u1', 'u9'] |
| submitted_via_eip | bool | The evaluated application or submission is submitted to IPD via e-IP. | Boolean route observation for one submission event | False | ['u1', 'u9'] |

Scope: `(and is_covered_submission (>= submission_date (date 2024-11-30)))`

Result expression: `submitted_via_eip`

Assumptions:

- Extending the parallel run extends its stated feature of accepting existing channels through 29 November 2024.
- The transition applies by the date of each submission event; the supplied text provides no exemption based on when the underlying matter began.
- Whether a particular product and communication fall within the IPD submission scope must be established separately; unknown classifications remain unknown.

Unresolved questions:

- Do any omitted provisions qualify the submission-date treatment of pending matters?
- Is footnote 1 exhaustive, and how are borderline communications classified?

## Questions for the reviewer

- Do the same events, actors, dates, quantities and exceptions supply both sets of facts?
- Does the same Boolean or scalar result mean the same thing in both statements?
- Which correspondence assumptions are contradicted, unresolved or supported by the retained source?
- Does the source require additional facts or referenced authorities absent from either reading?

Record an explicit one-to-one mapping and the assumptions for each changed declaration. A different number or decomposition of facts may require a new interpretation rather than a mapping.

## Retained source

**u1 — Retained text line 1**

This circular informs the industry that the Securities and Futures Commission (SFC) will extend the parallel run period of its new online application/submission system for investment products, e-IP, by one month to 29 November 2024. After the extended period, applications and submissions of investment products administered by the Investment Products Division (IPD)1 must be submitted to IPD via e-IP from 30 November 2024.

**u2 — Retained text line 2**

Background

**u3 — Retained text line 3**

Following the “Circular on launch of e-IP application/submission system on WINGS” dated 8 July 2024, the SFC launched e-IP on its WINGS2 portal on 29 July 2024 to streamline and enhance the efficiency of processing new product applications and post-authorisation/registration submissions to IPD.

**u4 — Retained text line 4**

A three-month period of parallel run from the launch of e-IP up to 29 October 2024 was provided at the initial stage. During this period, the SFC continues to accept applications and submissions via existing channels.

**u5 — Retained text line 5**

Parallel run period extension and upcoming enhancements

**u6 — Retained text line 6**

Since its implementation, the SFC has closely monitored the functioning of e-IP and actively engaged with industry participants to obtain their feedback on user experience.

**u7 — Retained text line 7**

While e-IP has garnered widespread industry support and is running smoothly, new features and more advanced settings will be introduced to further enhance user experience based on users’ comments. To facilitate these enhancements, the SFC will extend the parallel run period of e-IP by one month to 29 November 2024.

**u8 — Retained text line 8**

Full adoption of e-IP

**u9 — Retained text line 9**

Starting 30 November 2024, ie, after the parallel run period, applications and submissions of investment products administered by IPD must be submitted via e-IP. The current submission requests from IPD via the IP E-submission system will be integrated into e-IP, including reporting of net asset values, large redemptions and suspensions of dealing. In addition, e-IP users can also settle recurring annual fees associated with relevant investment products through the new system.

**u10 — Retained text line 10**

Feedback and enquiries

**u11 — Retained text line 11**

The SFC will continue to review and enhance the operation of e-IP where practicable. If you have any questions, please contact the relevant case officers.

**u12 — Retained text line 12**

Investment Products Division

**u13 — Retained text line 13**

Securities and Futures Commission

**u14 — Retained text line 14**

End

**u17 — Retained text line 17**

1 Investment-linked assurance schemes, mandatory provident fund products, open-ended fund companies, paper gold schemes, pooled retirement funds, real estate investment trusts, unit trusts and mutual funds and unlisted structured investment products.

**u18 — Retained text line 18**

2 Web-based INteGrated Service.

Missing or supplied dependencies:

```json
[
  {
    "dependency_id": "external-authorities.24ec50",
    "source_hash": null
  }
]
```
