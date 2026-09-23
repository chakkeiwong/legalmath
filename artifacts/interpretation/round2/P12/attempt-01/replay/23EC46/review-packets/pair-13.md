# Fact correspondence review

These are generated readings awaiting review. No semantic mapping is approved.
This packet exposes model proposals and cannot serve as blind reference annotation.

Source packet: `7b78bffd5267abb04c58ab204d1e34f621dc3fb03008be1b35980abcaa535ba4`

## Left reading

Selected control: paragraph-10 gift-promotion restriction with a product-related fee-discount exception. Within scope, an offered gift is caught unless it genuinely discounts fees or charges relating to the promoted product or product type. A true result concerns this restriction only.

Distinction: Narrows the exception to reductions in costs relating to the promoted product. An unrelated-service discount can distract from that product’s risks like another promotional gift. In the supplied snapshot, scope and result are true because gift_offered is true and discount_relates_to_promoted_product is false, regardless of the unknown is_fee_discount. This distinguishes the rival from r1 without changing fact meanings. The strongest objection is that u14 never expressly says 'fees of the promoted product'; its purpose cannot conclusively supply those words.

| Fact | Type | Declared meaning | Unit | Judgment required | Source units |
|---|---|---|---|---|---|
| is_distributor | bool | The assessed actor is an intermediary distributing SFC-authorised funds in the assessed activity. | Boolean | True | ['u1', 'u29'] |
| has_product_promotion_connection | bool | The assessed benefit is offered to a client in promotion of a specific fund or particular fund type, including a linkage to funds of certain fund houses. | Boolean | True | ['u14'] |
| gift_offered | bool | The assessed benefit is offered and qualifies as a gift before applying the fee-discount exception; an additional return is not automatically classified as a gift. | Boolean | True | ['u13', 'u14'] |
| is_fee_discount | bool | The assessed benefit genuinely constitutes a discount of fees or charges, irrespective of which service those fees concern. | Boolean | True | ['u14'] |
| discount_relates_to_promoted_product | bool | The fees or charges discounted by the assessed benefit relate to the promoted investment product or product type. | Boolean | True | ['u14'] |

Scope: `(and is_distributor has_product_promotion_connection)`

Result expression: `(and gift_offered (not (and is_fee_discount discount_relates_to_promoted_product)))`

Assumptions:

- The assessment concerns one offered benefit in a distributor’s promotion of SFC-authorised funds.
- A genuine discount can be treated as excepted even where it otherwise falls within the assessed gift category.
- The product-specific context and anti-distraction purpose imply that excepted fees or charges must relate to the promoted product or product type.
- This implied limitation is a provisional purposive reading, not an express condition in the retained wording.
- Unknown facts remain unknown; Boolean conclusions may nevertheless follow where a known fact makes an exception unavailable.

Unresolved questions:

- Does the missing authority support the implied product-related limitation despite the exception’s unqualified wording?
- If such a limitation exists, how does it apply to bundled account or platform fees covering several products?

## Right reading

Selected control: fund-context gift-offer restriction. For an intermediary distributing SFC-authorised funds, an identified benefit offered to a client in promoting a specific SFC-authorised fund or a particular type of such funds is caught by the 'should not offer' restriction if it is a gift and is not a qualifying fee-or-charge discount. Product-type linkage includes relevant funds offered by certain fund houses. Structured-product status and actual distraction are not additional conditions.

Distinction: The same distributor's gift promoting only a different investment product is outside this selected application, while gifts connected to SFC-authorised funds remain covered. Outside scope does not mean permitted under the full Code. The strongest uncertainty is that u14 itself states no express SFC-authorised-fund limitation.

| Fact | Type | Declared meaning | Unit | Judgment required | Source units |
|---|---|---|---|---|---|
| is_distributor | bool | The actor is an intermediary distributing SFC-authorised funds within the distributor description in u1. | truth value | True | ['u1', 'u29'] |
| benefit_offered_to_client | bool | The identified benefit is offered to a client; actual acceptance or delivery is unnecessary for this offer fact. | truth value | True | ['u14'] |
| benefit_is_gift | bool | The identified benefit qualifies as a gift, assessed before applying the express discount exception; an additional return or incentive is not automatically classified as a gift. | truth value | True | ['u13', 'u14'] |
| benefit_is_fee_discount | bool | The identified benefit itself qualifies as a discount of fees or charges within u14's exception; merely including a discount elsewhere in a package is insufficient to establish this fact. | truth value | True | ['u14'] |
| has_product_promotion_connection | bool | The offer is made in promoting a specific investment product or particular investment-product type to the client, including promotional linkage to a type such as funds from certain fund houses. | truth value | True | ['u14'] |
| promotion_concerns_authorised_funds | bool | The product or product type to which this benefit's promotion is connected falls within the circular's SFC-authorised-fund subject matter. | truth value | True | ['u1', 'u13', 'u15'] |

Scope: `(and is_distributor benefit_offered_to_client has_product_promotion_connection promotion_concerns_authorised_funds)`

Result expression: `(and benefit_is_gift (not benefit_is_fee_discount))`

Assumptions:

- Each evaluation concerns one identified benefit offer to one client; a campaign requires assessment of every relevant offer.
- The actor must be a distributor as defined in u1; the Code's title alone does not expand this actor definition.
- The circular's SFC-authorised-fund context limits this selected application of the general wording quoted in u14.
- Product-type linkage in the promotion is sufficient; proof of actual distraction is not an additional condition.
- Unknown classification or scope facts remain unknown.

Unresolved questions:

- Is the fund-specific context a limit on this circular's selected application, or merely the occasion for restating a broader control?

## Questions for the reviewer

- Do the same events, actors, dates, quantities and exceptions supply both sets of facts?
- Does the same Boolean or scalar result mean the same thing in both statements?
- Which correspondence assumptions are contradicted, unresolved or supported by the retained source?
- Does the source require additional facts or referenced authorities absent from either reading?

Record an explicit one-to-one mapping and the assumptions for each changed declaration. A different number or decomposition of facts may require a new interpretation rather than a mapping.

## Retained source

**u1 — Retained text line 1**

This circular summarises the Securities and Futures Commission’s (SFC) recent observations of licensed corporations’ practices in offering and promoting SFC-authorised funds. Intermediaries who distribute these funds (distributors) have been offering additional returns or other incentives that may divert the client’s focus from properly considering the risks and features of the underlying funds. This circular also highlights the legal and regulatory requirements to be met by distributors.

**u2 — Retained text line 2**

Background

**u3 — Retained text line 3**

In some cases, distributors promoted SFC-authorised funds (often via online platforms) and offered or imposed additional or distinct features or restrictions (eg, “guaranteed returns” or “lock-up periods”) beyond the product features set out in the funds’ offering documents.

**u4 — Retained text line 4**

In other cases, distributors asked clients to provide a mandate or standing instruction to invest in one or more SFC-authorised funds under specific circumstances, eg, using idle money in a client’s securities trading account with an aim to generate additional returns, albeit without any guaranteed or specific rates.

**u5 — Retained text line 5**

These SFC-authorised funds and services were often promoted by the distributors to the public through aggressive and high-profile marketing campaigns.

**u6 — Retained text line 6**

Guaranteed returns

**u7 — Retained text line 7**

Section 103 of the Securities and Futures Ordinance (Cap. 571) (SFO)

**u8 — Retained text line 8**

Typically, the “guaranteed returns” in such cases comprise: (i) the actual return of the relevant fund(s) invested by the investor (ie, fund return); and (ii) a top-up return to make up the difference between the fund return and the guaranteed rate of return offered by the distributor.

**u9 — Retained text line 9**

The SFC wishes to remind intermediaries who engage in promotional activities that these guaranteed return arrangements may constitute a "structured product" under the SFO if the return to investors is determined by reference to the change in value of any securities (including funds).

**u10 — Retained text line 10**

It is an offence under section 103 of the SFO for a person to issue an advertisement, invitation or document which is or contains an invitation to the Hong Kong public to enter into or offer to enter into any structured products, unless the SFC has authorised the issue or an exemption applies.

**u11 — Retained text line 11**

SFC-authorised funds without guaranteed features are required to highlight in their offering documents that they do not have these features and that investors may not get back the principal of their investment1. As such, any guaranteed returns provided by distributors may create a misleading impression that these returns are provided by the underlying fund(s).

**u12 — Retained text line 12**

Paragraph 3.11 of the Code of Conduct2

**u13 — Retained text line 13**

Even where the guaranteed returns offered would not constitute a “structured product” under the SFO, distributors are reminded to have regard to paragraph 3.11 of the Code of Conduct in offering such returns or other incentives in promoting SFC-authorised funds, as they may be considered a gift that should not be offered to investors.

**u14 — Retained text line 14**

Paragraph 3.11 of the Code of Conduct provides that distributors should not offer any gifts (other than a discount of fees or charges) in promoting a specific investment product or a particular type of investment product to a client. The purpose of the requirement is to avoid the use of gifts to distract investors from the features and risks of a particular product. If gifts are offered in such a way that they are linked to a particular type of investment product, such as certain types of funds or funds offered by certain fund houses, then such gifts will be bound by this requirement as investors may be distracted from the unique features and risks of such particular funds3.

**u15 — Retained text line 15**

In light of the concerns set out from paragraphs 5 to 10 above, when offering or promoting funds, distributors should not offer additional returns (which are not part of the product features set out in the relevant offering documents) or other incentives to investors in breach of section 103 of the SFO or paragraph 3.11 of the Code of Conduct.

**u16 — Retained text line 16**

Lock-up period and dealing frequency

**u17 — Retained text line 17**

When distributing SFC-authorised funds, some distributors imposed a lock-up period on their clients’ investments or lowered the funds’ dealing frequency. For instance, clients’ redemption was only allowed on a weekly or monthly basis even though the fund provided daily dealing arrangements.

**u18 — Retained text line 18**

Distributors should act fairly and in the best interests of their clients in providing services in accordance with General Principle 1 (Honesty and fairness) of the Code of Conduct. They should not restrict a client’s right to redeem his or her investment in a fund pursuant to the dealing frequency specified in the fund’s offering documents. Such restrictions would limit the client’s ability to make effective and timely investment decisions in response to changing market conditions or individual circumstances.

**u19 — Retained text line 19**

While distributors of SFC-authorised funds may have different fund dealing procedures or cut-off times for administrative efficiency, the SFC expects them to use their best endeavours to adhere to a fund’s dealing frequency as stipulated in its offering documents when dealing in the fund for clients, and not to reduce the fund’s dealing frequency.

**u20 — Retained text line 20**

Other marketing issues

**u21 — Retained text line 21**

In some cases, distributors offered or marketed the services described in paragraph 3 above without any guaranteed rates of return, but highlighted the regular interest payments or distribution features of the services prominently (eg, interest generated daily, or clients’ potential financial return from using such services), which would in fact be derived from the actual return(s) of the underlying fund(s). In preparing invitations and advertisements to promote their services, intermediaries should ensure that they do not contain any misleading or deceptive information, and they must comply with paragraph 2.3 of the Code of Conduct.

**u22 — Retained text line 22**

Where a distributor highlights in an advertisement the financial return of its services, which is in fact derived from the actual return(s) of the underlying SFC-authorised fund(s), the advertisement, particularly the presentation of financial return relating to the services, should be prepared in a manner that is consistent with the principles under the SFC’s Advertising Guidelines Applicable to Collective Investment Schemes Authorized under the Product Codes4.

**u23 — Retained text line 23**

Specifically, the advertisements of these services should avoid giving a misleading impression that the relevant services or underlying fund(s) would generate positive or guaranteed returns without any risk of loss. In addition, the advertisements should not draw a parallel between the services and the placement of cash on deposits, imply they are deposit-like arrangements (including any comparisons between the financial returns of the services and bank deposit rates), or suggest that the services are, or are equivalent to, bank deposits or savings (eg, by emphasising the services can address investors’ “savings needs”).

**u24 — Retained text line 24**

The SFC will closely monitor market practices concerning the promotion of SFC-authorised funds and may take regulatory action and issue further guidance where appropriate.

**u25 — Retained text line 25**

Intermediaries Supervision Department                       Investment Products Division

**u26 — Retained text line 26**

Intermediaries Division                                                             Securities and Futures Commission

**u27 — Retained text line 27**

Securities and Futures Commission

**u28 — Retained text line 28**

1 Pursuant to 6.4 of the Overarching Principles Section as set out in the SFC Handbook for Unit Trusts and Mutual Funds, Investment-Linked Assurance Schemes and Unlisted Structured Investment Products, offering documents of an SFC-authorised fund shall contain the information necessary for investors to be able to make an informed judgement of the investment whilst all key features and risks of the fund shall be highlighted prominently in a succinct manner for investors.

**u29 — Retained text line 29**

2 The Code of Conduct for Persons Licensed by or Registered with the Securities and Futures Commission (Code of Conduct).

**u30 — Retained text line 30**

3 The answer to question 1 of the frequently asked questions on the Code of Conduct issued by the SFC on 30 September 2010.

**u31 — Retained text line 31**

4 As supplemented by the frequently asked questions and other guidance issued by the SFC from time to time.

Missing or supplied dependencies:

```json
[
  {
    "dependency_id": "external-authorities.23ec46",
    "source_hash": null
  }
]
```
