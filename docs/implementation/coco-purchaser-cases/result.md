# Two real CoCo purchaser cases: executed result

The same hypothetical US-resident individual, buying USD 200,000 principal for
their own account and benefit, passes the selected Barclays purchaser condition
and fails Standard Chartered's. The individual is explicitly not a QIB.

| Instrument | Source and original issue | Conditional result |
| --- | --- | --- |
| Barclays PLC 7.625% perpetual contingent convertible securities, US06738EDC66 | Prospectus supplement 18 February 2025; issue 25 February; public US distribution described in the supplement | PASS for the declared purchaser condition. |
| Standard Chartered PLC 7.625% perpetual contingent convertible securities, US853254DF47 / USG84228GP72 | Offering circular 8 January 2025; issue 16 January; specified Rule 144A and offshore Regulation S distribution | FAIL: the individual satisfies neither the QIB purchaser/account condition nor the non-US offshore condition. |

Both original documents are preserved under `docs/prospectus/originals/`.
Both minimum denominations are USD 200,000 with USD 1,000 increments. The
difference is the declared offering route, not currency, order size, coupon,
issuer nationality or an inference that one CoCo cannot lose its principal.
The two original offer dates are explicit; no simultaneous live availability
is asserted.

These are **conditional purchaser results**, not SEC/SFC approval labels,
actual JPMorgan decisions or universal permission/prohibition. The negative
result concerns the original distribution, not every possible future resale
or exemption. Barclays' registration effectiveness and all remaining selling
requirements are outside the proved relation. The full bank result stays
qualified for both; the Standard Chartered case additionally records that
the declared route cannot be used.

## Evidence and execution

Command actually executed:

```sh
.venv/bin/python scripts/run_coco_purchaser_cases.py
```

[Attempt 002](attempt-002/summary.json) passed all five executable phases:
source validation, regression, formal comparison, native execution and bank
integration. Its [run manifest](attempt-002/run-manifest.json) records the
dirty Git base, exact command, Python/platform, CPU-only setting, source/method
hashes, plan and elapsed time (169.342 seconds). Tool identities and versions
are bound in the input and source-phase records. Random seeds are inapplicable:
the cases are deterministic Boolean assignments.

- Four source documents and twenty retained page/span anchors were validated.
  The Barclays and Standard Chartered selling clauses were also inspected on
  rendered source pages.
- **165 focused regression tests passed**, with no failures, errors or skips.
- A separate SMT relation agrees with the shared expression for all **512
  Boolean assignments** of the nine declared premises. Six incorrect variants
  produce counterexamples, including ignoring the beneficial account, US
  benefit, US-person status or issuer affiliation, and approving/rejecting all
  CoCos.
- A **Lean kernel-checked certificate** verifies preservation from the
  declared formal expression to the shared model. It is not an English-law
  or whole-compiler correctness proof.
- **157 identical input cases ran in each target: 314 executions.** In each
  backend, 138 complete cases agreed with the independently written evaluator
  (97 true, 41 false). Nine unknown-input cases, nine conflict cases and one
  expired-input case abstained: 38 abstentions across the two targets.
- The pair was attached to the actual evidence-bound bank investigation.
  Both receipts retain **seven categories and fourteen declared obligations**.
  Neither permits transaction execution. No actual account, private policy,
  sanctions identity or bank service authorization was fabricated.

Counterfactual tests change the purchaser and beneficial account, not a human
approval label. A QIB purchasing for itself can pass the Standard Chartered
condition. A QIB bank buying for a non-QIB customer's account cannot pass that
condition through the bank's status alone. Renaming the issuer does not change
the formal decision. Unsupported secondary resale or conversion requests are
qualified instead of reusing the original-offering rule.

Attempt 001 is retained as failed evidence. Its conflict fixture used different
evidence IDs in two representations of the same input; both backends correctly
rejected it. The repair and the earlier invalid-expiry diagnostic are documented
in [the review](review.md). The repaired attempt supersedes its native result.
This was a harness-input failure, not evidence against Catala or the underlying
legal-computing direction. Repair was the planned next phase; no continuation
veto remained.

## Decision and limits

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain the pair as a scoped engineering test | Both real-source route results reproduced; formal/native checks passed | No remaining engineering veto in the executed scope | Source interpretation and applicability are conditional | Reuse the checked relation for supported purchaser premises; recheck source identity and scope | Universal product eligibility or legal interpretation accuracy |
| Barclays transaction remains qualified | Selected purchaser condition passed | Missing account, bank, other-law and policy evidence prevents clearance | Actual service/client and private policy facts | Obtain actual evidence before a transaction decision | JPMorgan or SFC approval |
| Do not proceed with the Standard Chartered original route for this investor | Specified purchaser condition failed | Negative route condition remains | Other offers, resale exemptions and changed terms need their own analysis | Change the actual scenario or investigate a different legally supported route | Permanent ban on the instrument |
| No backend ranking | Both targets passed the same deterministic checks | No mismatch after fixture repair | Broader expressiveness/performance not measured here | Preserve both execution records | Catala superiority or future-law generalization |

The claimed formal target is the selected Boolean purchaser condition in the
plan. The computed quantity is that condition applied to explicit source
interpretation proposals and synthetic investor facts. SMT equivalence, the
preservation certificate, independent evaluations and native records support
equality at that formal level. They do not prove that the condition is a
complete or correct natural-language interpretation, that the retained annual
CFR edition describes all law at either issue date, or that it remains current.

The strongest alternative explanation of a green result is faithful execution
of an incomplete interpretation. A contrary applicable provision, changed
offering terms, different beneficial ownership or missing distribution
condition would require a new qualification and possibly a new formal model.
This is the weakest evidence boundary; adding more copies of the two outcomes
would not repair it. No human quality labels or model-consensus grading are
used to hide that limit.

## Monograph

Section **2.4.5, “One investor, two CoCo offering decisions”**, introduces the
QIB and Regulation S distinctions, identifies both issues, works through the
same investor, derives the conditional equation, changes the premises and
reports the evidence and limits. The prior bank section is preserved in full.
Four archived sources add six citation occurrences.

Build command:

```sh
python3 scripts/build_reader_facing_monograph.py
```

The monograph compiles to **332 pages**, the companion to **78**, and the
standalone process guide to **13**. The document checker passes with **133
archived citation sources and 288 occurrences**, retaining the 207 original
source-unit labels. The changed pages were rendered and inspected. These are
source-binding and typography checks, not a human-readability certificate or
independent legal verification.
