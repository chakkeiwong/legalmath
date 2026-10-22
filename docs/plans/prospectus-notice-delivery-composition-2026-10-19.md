# Derive the notice date before evaluating the agent-change interval

This is the proposed next refinement of original basf-office, conditional on
the preceding complete-answer notice integration passing and being recorded.
It is not another execution authority and grants no additional attempt.

## Question and source

Can the answer carry the selected section 13 notice route through to the
necessary agent-change notice condition, without treating publication or
clearing delivery as immediate notification of holders?

The complete retained publication paragraph says notices are deemed effective
on the third day after publication on the Luxembourg Stock Exchange website.
The complete clearing-substitution paragraph says that while the notes are
listed, paragraph (1) applies; where exchange rules permit, the issuer may
substitute a notice to the clearing system for forwarding to holders, deemed
communicated on the seventh day after the notice to that system. Holder-to-agent
notices are a separate direction and must not receive either issuer-route delay.

## Proposed exact supported calculation

Under an explicitly supplied civil-date reading, proposed holders-informed
date = qualifying publication date + 3 days, or qualifying clearing delivery
date + 7 days. These are candidate dates conditional on the route's premises.
Known route failure must not create a legally operative notice date; missing
route facts preserve UNKNOWN and conflicting facts preserve CONFLICT. The
declared reading and historical applicability remain separate premises.

Bind instrument, agent, change event and notice identity throughout. The source
event role is PUBLICATION_ON_LUX_EXCHANGE or CLEARING_DELIVERY_FOR_FORWARDING.
The calculated date becomes HOLDERS_INFORMED only inside the composed
conditional scenario. Refuse holder-to-agent notices, missing route identity,
wrong subject/event, unsupported counting conventions and attempts to supply
both a calculated and a contradictory holders-informed date.

Reuse the existing agent-notice evaluator, which calculates inclusive 30/45
bounds and the insolvency exception. Retain every previous answer field and
profile pin. Do not infer actual listing, publication, clearing-system delivery,
exchange permission, issuer election, insolvency or office authority.

## Skeptical review required before admission

The easy but wrong shortcut is adding three or seven days without checking
which direction of notice, which selected branch, or whether substitution is
permitted. Another is setting section13_notice=True from arithmetic alone.
The implementation must derive a conditional route result separately from
the candidate date, then compose both with the notice-window condition.

Baseline: complete passing notice-integration answer. Primary criterion:
independent integer Gregorian date addition plus source-bound route truth
tables, actual ordinary CLI composition, preserved baseline and isolated
installed equality. Require leap-year and month/year crossings, missing and
conflicting permission/listing/election facts, invalid direction, and examples
where using publication/delivery directly reverses the 30/45-day answer.

Counts and runtime are explanatory only. Wrong dates, lost source conditions,
invented legal effectiveness or a changed prior answer veto promotion. Broken
evidence, invalid harness, method drift or a resource limit veto continuation.
An implementation failure calls for a diagnosed changed repair, not a package
incapability verdict. Record costs and update the same-task authority before
execution; do not borrow an unreviewed additional admission.

The original calculation-agent office and historical-law/source issues remain
open after this finite conditional composition. Successful scenario tests do
not establish universal prospectus interpretation or whole-build completion.

## Pre-implementation review and assumptions

Skeptical audit PASS for preparing a candidate with the following restrictions.
The consumer must call the existing notice evaluator rather than duplicate its
30/45 calculation. Route facts mean only the explicit modeled prerequisites;
they do not independently establish every section 13 legal requirement. Keep
the complete source context and actual-event/non-sufficiency qualifications.
Earlier frozen source, profiles, methods and results remain unchanged.

| Choice | Provenance/status | Risk and early diagnostic |
| --- | --- | --- |
| Delays 3 and 7 | Complete original source plus retained supplied reading | Wrong route; bind paragraphs and check each delay independently |
| Civil dates only | Explicit supported hypothesis, not governing law finding | Hidden counting rule; refuse other conventions and keep applicability open |
| Route qualification premises | Selected listed-note source branch | Inferring permission/election/listing from date; test each missing/false/conflicting premise |
| Supplied valid-event premise | Hypothetical scenario only | Arithmetic becomes an actual event; prohibit actual labels and preserve qualifications |
| Existing notice evaluator | Prior exact independent tests | Wrong composition identity or date; compare every derived input and final result |
| Prior full answer | Passing original-task integration, required before admission | Frozen work altered; compare all fields and reuse unchanged pins |

Preparation may inspect and write new candidate/review files while the previous
installed check runs. Production installation and trials require that check to
pass, recording/refresh, and a reviewed same-task revision. Proposed admission
4 to 5; retain all earlier budgets, costs and unknown time. Forecast at most
900 new measured seconds and 100 MiB, still within the combined 12,600 seconds
and 2,048 MiB including 4 MiB reserve. Stage 210 seconds, CLI child 195 seconds,
tests 150 seconds. One-second tool yields and polling; no external calls.
