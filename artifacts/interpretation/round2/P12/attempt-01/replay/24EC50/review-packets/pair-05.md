# Fact correspondence review

These are generated readings awaiting review. No semantic mapping is approved.
This packet exposes model proposals and cannot serve as blind reference annotation.

Source packet: `f7a64d3de90d02e99196d98ccef21e753d809b06de92036166db0eb3639b7449`

## Left reading

Selected control: route used for a covered submission from 30 November 2024. Such submissions must use e-IP. Existing-channel acceptance continues during the extended parallel run through 29 November 2024. The practicability qualification concerns SFC review and enhancement, and the enhancement rationale does not defer the stated transition date. Reporting integration does not itself create underlying reporting duties, and annual-fee payment through e-IP remains optional.

Distinction: Exception-attachment investigation retains the parent's event-based control. A proposed practicability exception for submitters fails because the qualification belongs to a separate sentence about SFC operations. A proposed delay until enhancements are complete also fails: their facilitation explains the fixed extension without making completion a condition. Optional annual-fee functionality supplies no exception for otherwise covered submissions. No materially different rival route rule is supported by the retained text. The strongest uncertainty is whether the missing earlier circular supplies additional qualifications; the incomparable diagnostics cannot resolve it.

| Fact | Type | Declared meaning | Unit | Judgment required | Source units |
|---|---|---|---|---|---|
| is_covered_submission | bool | The evaluated event is an application or submission to IPD concerning an investment product administered by IPD. Classification must account for footnote 1; optional fee payment alone does not establish this fact. | Boolean classification of one submission event | True | ['u1', 'u3', 'u9', 'u17'] |
| submission_date | date | Gregorian calendar date on which the evaluated application or submission is made to IPD. | Gregorian calendar date | False | ['u1', 'u9'] |
| submitted_via_eip | bool | The evaluated application or submission is submitted to IPD via e-IP. | Boolean route observation for one submission event | False | ['u1', 'u9'] |

Scope: `(and is_covered_submission (>= submission_date (date 2024-11-30)))`

Result expression: `submitted_via_eip`

Assumptions:

- Extending the parallel run preserves its existing-channel acceptance feature through 29 November 2024.
- The transition applies to the date of each submission event; no grandfathering rule for existing matters is supplied.
- Product and communication classifications must be established separately, with unknown facts remaining unknown.
- This proposal is limited to the retained text; unavailable authorities have not been treated as establishing or excluding additional exceptions.

Unresolved questions:

- Do unavailable provisions establish a contingency or grandfathering exception?
- What criteria determine whether borderline communications are covered submissions?

## Right reading

Selected control: compulsory e-IP submission route from 30 November 2024. For each covered application or submission made from that date, submission to IPD must use e-IP. The extended parallel run permits existing channels through 29 November 2024. Enhancement plans do not make the transition conditional, and the annual-fee facility remains optional. The formal result tests only routing when its scope holds; an out-of-scope item receives no compliance verdict from this control.

Distinction: The express text supports one mandatory-route reading, without a sufficiently grounded rival that postpones the date, exempts existing cases or makes annual-fee payment compulsory. A covered submission made through an existing non-e-IP channel on 29 November 2024 falls within the extended parallel run; the same submission on 30 November falls within the compulsory e-IP control and fails that route check. A fee payment alone does not become a covered submission merely because e-IP can process it. The strongest uncertainty concerns operational treatment of legacy-case follow-ups and the event fixing the submission date.

| Fact | Type | Declared meaning | Unit | Judgment required | Source units |
|---|---|---|---|---|---|
| covered_submission | bool | The identified item is an application or submission to IPD concerning an investment product administered by IPD, interpreted with the product categories in footnote 1. Optional fee payment alone does not establish this classification. | Boolean | True | ['u1', 'u3', 'u9', 'u17'] |
| submission_date | date | The Gregorian date on which the identified application or submission is treated as submitted under the applicable timing convention. Dispatch-versus-receipt treatment is not specified in the packet. | Gregorian calendar date | True | ['u1', 'u4', 'u7', 'u9'] |
| submitted_via_e_ip | bool | The identified application or submission was submitted to IPD via e-IP. | Boolean | False | ['u1', 'u9'] |

Scope: `(and covered_submission (>= submission_date (date 2024-11-30)))`

Result expression: `submitted_via_e_ip`

Assumptions:

- The control is evaluated for one identified application or submission, not for whole-institution compliance.
- Extending the parallel run extends its existing-channel acceptance through 29 November 2024.
- The supplied submission date is established under the applicable timing convention; this packet does not define that convention.
- Product and communication classification is supplied with professional judgment where needed.

Unresolved questions:

- For a case initiated through an existing channel before the transition, is later correspondence itself a covered submission requiring e-IP?
- Does unavailable operational guidance distinguish attempted transmission from accepted receipt when determining the submission date?

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
