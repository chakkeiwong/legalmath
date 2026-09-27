# Independent legal review packet

Development convenience sample: 4 tasks, 3 circular families; 26EC22 supersedes 23EC53; all retained editions have prior project exposure.

Review each quoted provision against the retained edition, assess the supplied factual classifications, and accept, revise or reject the selected reading and rival. All decisions below are provisional. Record your identity, source review, reasons and concrete distinguishing values in an adjudication record.

## native.closure.netassets

Compute only net assets excluding primary residence from paragraph 3.3. Input classification, account ownership and conversion to HKD are supplied; do not infer SPI eligibility. Signed input amounts are admitted for arithmetic stress tests. Dated retained edition; assessment timestamps are a synthetic test setting.

3.3 “Net assets” refers to the value that is calculated by deducting total liabilities from total
assets. “Net assets, excluding primary residence” refers to the value that is calculated
by deducting the value of primary residence from net assets.

**Proposed reading:** Deduct total liabilities and the primary residence from total assets.

**Rival to assess:** Deduct the primary residence twice when interpreting net assets excluding residence.

**Current provisional disposition:** REJECT_AS_SOURCE_UNSUPPORTED_MUTATION

Distinguishing input and outcomes: `{"inputs":{"assets":"10000","liabilities":"3000","residence":"2000"},"rival":"3000","selected":"5000"}`

Every supplied source unit is used in this selected control; cross-referenced controls and whole-product approval require separate review.

## native.closure.gifts

For a distributor promoting products to a client, compute whether the quoted paragraph 3.11 gift prohibition applies. The four supplied classifications are evidence inputs. This is only the quoted gift control; section 103 and the rest of the Code are outside the selected question. Dated retained edition; assessment timestamps are a synthetic test setting.

Paragraph 3.11 of the Code of Conduct provides that distributors should not offer any gifts (other than a discount of fees or charges) in promoting a specific investment product or a particular type of investment product to a client. The purpose of the requirement is to avoid the use of gifts to distract investors from the features and risks of a particular product. If gifts are offered in such a way that they are linked to a particular type of investment product, such as certain types of funds or funds offered by certain fund houses, then such gifts will be bound by this requirement as investors may be distracted from the unique features and risks of such particular funds3.

**Proposed reading:** The discount exception applies on both the specific-product and product-type routes.

**Rival to assess:** The parenthetical discount exception attaches only to the specific-product route.

**Current provisional disposition:** PROVISIONAL_REJECT_RIVAL_PENDING_REVIEW

Distinguishing input and outcomes: `{"inputs":{"discount":true,"gift":true,"producttype":true,"specific":false},"rival":true,"selected":false}`

Every supplied source unit is used in this selected control; cross-referenced controls and whole-product approval require separate review.

## native.closure.network

For a Product Provider within the circular scope, compute whether the selected sentence prohibits the proposed network use. The controls and proper-input classifications are supplied by reviewers. Do not turn this one control into overall product approval or resolve other referenced requirements. Dated retained edition; assessment timestamps are a synthetic test setting.

Product Providers should not use public-permissionless blockchain networks without additional and proper controls (eg, Product Providers to impose additional control by using a permissioned token)4.

**Proposed reading:** Public-permissionless use fails the selected control unless controls are both additional and proper.

**Rival to assess:** Any additional control suffices irrespective of whether it is proper.

**Current provisional disposition:** REJECT_AS_OMITTED_QUALIFIER

Distinguishing input and outcomes: `{"inputs":{"controls":true,"proper":false,"publicnetwork":true},"rival":false,"selected":true}`

Every supplied source unit is used in this selected control; cross-referenced controls and whole-product approval require separate review.

## native.closure.consultation

Compute whether prior consultation is required under the two selected sentences. Classification of a material change is supplied. Do not equate consultation with prior approval: the source separately says such changes may require approval. Dated retained edition; assessment timestamps are a synthetic test setting.

For new investment products that have tokenisation features and plan to seek the SFC’s authorisation, prior consultation with the SFC is required.
Prior consultation is also required for tokenisation of existing SFC-authorised investment products and/or material changes to the tokenisation arrangements of tokenised SFC-authorised investment products. Such change(s) may require prior approval8.

**Proposed reading:** Consultation applies to a new tokenised product seeking authorisation, tokenisation of an existing authorised product, or a material arrangement change.

**Rival to assess:** For existing authorised products, tokenisation and material change must both occur before consultation is required.

**Current provisional disposition:** PROVISIONAL_REJECT_CONJUNCTION_PENDING_REVIEW

Distinguishing input and outcomes: `{"inputs":{"existingtokenisation":false,"materialchange":true,"newproduct":false,"seeksauthorisation":false},"rival":false,"selected":true}`

Every supplied source unit is used in this selected control; cross-referenced controls and whole-product approval require separate review.
