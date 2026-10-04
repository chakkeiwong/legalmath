# Two real CoCos with opposite conditional purchaser-route results

The comparison uses the same hypothetical individual resident and located in the
United States, buying **USD 200,000 principal for their own account and benefit**.
The individual is explicitly not a qualified institutional buyer (QIB).

| Real issue | Preserved offering document | Selected purchaser condition |
| --- | --- | --- |
| Barclays PLC, 7.625%, issued 25 February 2025; ISIN US06738EDC66 | [18 February prospectus supplement and accompanying prospectus](../originals/barclays-at1-2025.pdf) | **PASS** under the declared public US offering route. |
| Standard Chartered PLC, 7.625%, issued 16 January 2025; restricted ISIN US853254DF47 and offshore ISIN USG84228GP72 | [8 January offering circular](../originals/standard-chartered-at1-2025-january.pdf) | **FAIL**: the individual does not satisfy the QIB route or the non-US offshore route. |

Both are real contingent convertible securities. Both specify USD 200,000
minimum denominations and USD 1,000 increments. These are preserved original
offering terms, not simultaneously available live primary offers. Coupon rates
are initial rates, subject to their reset terms.

“Pass” is approval of the **selected purchaser condition under the declared
interpretation and fictional investor premises**. It is not SFC approval, SEC
endorsement, bank approval, suitability, principal protection, a completed
Rule 144A/Regulation S exemption analysis or permission to settle. The negative
result concerns this original distribution; it is not a lifetime prohibition
on all transfers or a rejection of the issuer.

## Source examination

The [input dossier](cases.json) records issue identity, exact original/extraction
hashes, page/span references, denomination terms and interpretation proposals.
The [source manifest](sources.json) also binds the two retained official CFR
definitions in [sources](sources/). Span hashes establish which words were
examined; they do not prove their legal meaning.

- Barclays: PDF pp. 2, 5--6, 13, 23, 29 and 105--111. Printed S-6 describes the
  Form F-3 filing; S-99 explicitly describes distribution to the public. The
  phrase “registered form” alone does not establish Securities Act registration.
- Standard Chartered: PDF p. 4 is the dated, priced cover; pp. 24--25 give
  denomination and identifiers; pp. 149--152 contain selling restrictions;
  pp. 158--159 contain purchaser/account and offshore representations.
- Rule 144A: the retained 2025 annual edition, especially (a)(1) and (d).
  QIB is an institutional/account category, not a synonym for a wealthy
  individual, accredited investor or Hong Kong PI/SPI. Seller duties and other
  exemption conditions remain separate.
- Regulation S: section 230.902(k), especially residence and the account/branch
  exceptions. Its US-person definition must not be replaced by an OFAC flag.

The Standard Chartered electronic transmission notice says the document is
subject to completion. This triggers the archive's preliminary-text detector.
The flag is preserved. The priced, dated offering inside it and the issuer's
final-document link supply the separately recorded edition basis. A protected,
unreadable November 2025 file found during discovery was not used as evidence
for the distinct January issue.

## Execution and qualifications

Run from the repository root:

```sh
.venv/bin/python scripts/run_coco_purchaser_cases.py
```

The fixed runner validates sources, runs focused regressions, checks an
independently written formal relation, compiles and executes both RuleIR and
Catala, and attaches each case to the existing bank investigation. It preserves
attempts and refreshes `next-phase.json` after successes and failures. Failed
attempts are evidence for repair, not completed results.

The inputs contain no human/model answer labels. QIB-account changes, offshore
US benefit, issuer affiliation, source changes, missing/conflicting evidence,
expiry and unsupported transaction stages challenge the calculation. A QIB
buying for its own account can pass the Standard Chartered purchaser test;
a QIB bank purchasing for a non-QIB customer does not pass merely because the
bank is a QIB. Issuer names are not predicates in the model.

Both integrated investigations retain all seven bank assessment categories and
the fixed fourteen-obligation inventory. Actual client information, booking and
service authority, other selling requirements, sanctions identity, internal
policy and settlement evidence remain unresolved. Neither case authorizes an
actual transaction. The formal proof covers the explicit Boolean relation,
not English interpretation, exhaustive law discovery or future legal validity.

Results and repaired attempts are in
[the execution record](../../implementation/coco-purchaser-cases/result.md).
The monograph explains the investor categories before applying the cases in
Section `sec:coco-purchaser-cases`.
