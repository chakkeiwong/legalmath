# Prospective public-source reference dossier

These are proposed interpretations for a controlled experiment, prepared before
new model responses are inspected. Complete official pages, extracted text, exact
selected regions, source hashes and current observed versions are retained in
`.localresources/interpretation-round5/public-qa-v1`. The supplied body includes
the introduction, all questions/answers, footnotes and visible update notice.
The rest of each page remains in the retained original bytes. Script/navigation
differences between text extractors remain recorded; selection does not certify
whole-document or historical legal completeness.

The fixed scenario clock is a reproducibility convention, not an effective-date
determination. The page acquisition record separately gives its actual retrieval
time. No result asserts that the observed page was the governing edition at an
earlier historical instant.

The source is authoritative evidence of what the SFC page says. Neither our fact
definitions nor our scenario labels acquire regulatory authority by quoting it.
The experiment tests translation of the selected trigger after judgment-bearing
facts are supplied. It does not determine those facts, all exemptions, the
institution's compliance, or correctness across all possible readings.

## Family offices: conjunction and judgment

The [Family Offices FAQ, Q3](https://www.sfc.hk/en/faqs/intermediaries/licensing/Family-Offices)
describes three factors that must all be present for a licensing obligation:
regulated services, carrying on a business, and carrying on that business in Hong
Kong. The same answer discusses the intra-group carve-out and the fact-sensitive
business test. Q1 and Q2 explain why a family-office label or family membership
does not itself determine the licensing question. Q4 discusses shared infrastructure;
Q5 returns to the three factors for multi-family offices. All five answers remain
in the model's source context.

Let R mean services are regulated after applicable carve-outs, B mean they are
provided as a business, and H mean that business is carried on in Hong Kong.
The proposed selected trigger is R AND B AND H. Each fact explicitly requires
judgment. Eight known Boolean combinations test all combinations; two additional
cases distinguish an unknown business determination from a known missing condition.
The expected truth table is written independently of the expression evaluator.
For example, R=true, B=false, H=true does not satisfy this trigger, while three true
facts do. If R and H are true and B is unknown, the trigger is unknown.

The hypothetical variant replaces the single requirement that all factors be
present with a requirement that at least one be present. It is a deliberately
altered copy, not a second SFC rule. The reference OR trigger must change the
appropriate scenario answers. Separately, executable mutants replace AND with OR
or omit B; the acceptance command must produce concrete Java witnesses against
both. This tests a common implementation error without declaring the original
source interpretation independently adjudicated.

## Client money: role does not displace the money conditions

The [Client Money Rules FAQ of 30 September 2024, Q1](https://www.sfc.hk/en/faqs/intermediaries/supervision/Client-Money-Rules/30-Sep-2024---Client-Money-Rules)
addresses an RA13 depositary acting as a Transfer Agent. The answer describes
application to scheme money received or held in Hong Kong in the course of RA13,
regardless of the corporation's role. The following paragraph preserves relevant
Schedule 11 duties for other money. Q2 has a clock-start condition and an unknown
receipt footnote; Q3 distinguishes REIT account arrangements. Those qualifications
remain visible, although the reference Boolean concerns only Q1 applicability.

Let C identify the stated RA13 context, S classify the funds as scheme money, H
identify receipt or holding in Hong Kong, and T identify the Transfer Agent role.
The proposed Q1 trigger is C AND S AND H, independently of T. Seven scenarios
include role changes, absent conditions and unknown classifications. With C, S
and H true, changing T from true to false or unknown does not change this selected
trigger. An unknown S remains unknown. A false result cannot imply that no other
money-protection obligation exists.

The hypothetical variant replaces the role-independent clause with an exclusion
for the Transfer Agent role. Its proposed trigger adds NOT T. Exact bytes before
and after the sole edit are recorded. Executable adverse controls also omit H or
invent that role exclusion against the original answer. The test must show which
scenarios distinguish those formulas in Java.

## Two qualification families without invented full-law answers

The [Professional Investors FAQ](https://www.sfc.hk/en/faqs/intermediaries/supervision/Professional-Investors/Professional-Investors)
contains an explicit adverse example in Q4: an investor's written representation
alone is insufficient. Q1-Q3 require a holistic assessment specific to products
and markets. Adding an audit trail or one document therefore cannot be assigned a
positive full-assessment outcome without further premises. The page also displays
a 2024 update within its body despite a 2020 footer. Its observed bytes are retained;
the footer is not used to assert an historical edition.

The [Triggering of Suitability Obligations FAQ](https://www.sfc.hk/en/faqs/intermediaries/supervision/Triggering-of-Suitability-Obligations/Triggering-of-Suitability-Obligations)
provides useful contrastive examples: an execution-only communication versus a
subsequent recommendation following factual information. The answer's categories
are likely and unlikely, with context and sequences of actions considered together.
Encoding either category as a categorical legal trigger would change the meaning.
The entire page, including the Annex and later discretionary-account answers, is
retained as a qualification challenge. No categorical truth label is fabricated.

These two exclusions are declared before live outcomes. They reveal a limitation
of a Boolean reference set, rather than evidence that difficult clauses were solved.
A successor study needs set-valued/modality-sensitive reference dispositions for
these cases. Any headline performance result restricted to the easier two families
would omit this limitation and be misleading.

## What the frozen comparison would measure

The frozen study has four cases, two source families, four actual method adapters,
and an 18-call ceiling per case/method: 288 reserved calls. The 18-call ceiling is
a feasibility hypothesis inherited from the full assurance path, not a demonstrated
optimal allocation. Job-order seed 924 is a reproducibility choice; there is no
claim of seed robustness. Exact fact-meaning alignment may cause abstention even
where two explanations appear similar; such abstentions must remain visible.

Only 22 calls remain in the existing allowance. Admission must refuse the complete
comparison. A separate one-family assurance run may consume at most 18 calls and
must report method failures, uncertain context, unaligned facts and surviving
interpretations. It cannot estimate the difference between methods. The two
families are a convenience sample, not IID draws from all SFC requirements; source
pretraining exposure is unknown. Neither the number of scenarios nor the altered
copies increases the number of independent families.
