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

For each covered application or submission made to IPD on or after 30 November 2024, the submitting actor must use e-IP. Existing channels remain accepted during the extended parallel run through 29 November 2024. The identified reporting requests fall within the integration described by the circular, without this text independently establishing when reports are due. Annual-fee settlement through e-IP remains optional. Within the formal scope, a true result means that this submission satisfies the selected route control; outside that scope, the formalization makes no compliance determination.

Distinction: This reading applies the transition to each covered submission event, including later submissions relating to an earlier case where they otherwise qualify. It preserves optional fee settlement and treats enhancement completion as rationale rather than a commencement condition. The strongest uncertainty is whether unavailable migration provisions qualify the treatment of existing cases; the retained text supplies insufficient support for a separate grandfathering reading.

| Fact | Type | Declared meaning | Unit | Judgment required | Source units |
|---|---|---|---|---|---|
| covered_submission | bool | The assessed event is an application or submission to IPD concerning an investment product administered by IPD. Classification takes account of footnote 1 and does not classify use of the optional annual-fee facility alone as a covered submission. | Boolean | True | ['u1', 'u3', 'u9', 'u17'] |
| submission_date | date | Gregorian calendar date on which the assessed application or submission is made to IPD. | Gregorian calendar date | False | ['u1', 'u9'] |
| submitted_via_eip | bool | The assessed application or submission is submitted to IPD via e-IP. | Boolean | False | ['u1', 'u9'] |

Scope: `(and covered_submission (>= submission_date (date 2024-11-30)))`

Result expression: `submitted_via_eip`

Assumptions:

- The assessment concerns one identified submission event, not whole-institution compliance or whether an underlying filing is due.
- Extending the parallel run carries forward its existing-channel acceptance through 29 November 2024.
- The event's submission date determines application of the compulsory route; no unstated grandfathering exception is inserted.
- Product and submission classification remain supplied facts requiring judgment where the retained text is insufficient.

Unresolved questions:

- For an existing case, which later communications count as applications or submissions subject to the new route?
- Does missing migration guidance provide any express exception to the event-date reading?

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
