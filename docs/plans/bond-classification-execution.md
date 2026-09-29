# Executable bond feature classification and reasons

Authorized on 29 September 2026: acquire UK/EU non-bank senior bond examples,
add discriminating cases, review and execute the existing L0–L4 plan, and emit
a yes/no answer with reasons for every bond. Ordinary creditor-approved
restructuring is recorded separately from capital-loss triggers and statutory
bail-in. This is the working interpretation consistent with the user's new
negative-control request. Issuer sector or senior rank never supplies an answer.

## Evidence contract and research intent

Question: can the implementation compose dated issue documents and produce a
traceable loss-absorption feature result without confusing principal, coupons,
ordinary repayment, or another security? The mechanism under test is explicit
issue/document scope, candidate-clause analysis, and a small formal decision
layer. Baselines are the old reader's retrieval/interface and naive keyword
matching; neither is a legal-accuracy oracle. The independent formal predicate
and identical RuleIR/Catala cases assess formal execution only.

Pass criteria: the requested report exists for every inventory row, reasons
are generated from evidence and decision states, finite formal/unknown/conflict
cases agree with an independent specification, source alterations and missing
operative material cannot yield an accepted negative, and controlled confounding
cases fail to contaminate the result. At least UK/EU non-bank senior examples,
two junior examples, actual CoCo conversion and actual CoCo write-down, and
statutory senior-bank examples must be represented. A human or model's answer
is never a quality label. English interpretation and document relevance remain
qualified; a successful finite test is not universal future legal correctness.

Source hashes/locators, source identity, selected issue/version and unresolved
operative dependencies are promotion vetoes. A harness/compiler mismatch is a
continuation veto for dependent formal claims until repaired. An unrecognized
clause triggers source-analysis repair or an unresolved row, not a forced
negative. Counts, runtime and keyword hits are explanatory only. Preserve
failed attempts and repairs, with at most four attempts per phase/version.

## Implementation sequence

1. L0: acquire source PDFs under `docs/prospectus/classification-additions`,
   including a UK corporate senior issue, an EU corporate senior issue and a
   contractual write-down CoCo. Resolve actual issuers and exact editions;
   include retained final CoCos and existing senior/junior controls. Programme,
   preferred shares, duplicate sources and unavailable finals get explicit
   dispositions. No issuer-family holdout is inspected until method freeze.
2. L1: build a hash-bound inventory and explicit document/section scope. Read
   all pages for candidates, retain exact locations and every potentially
   qualifying clause disposition. Resolve principal and common-share definitions,
   final/base precedence and relevant dependencies. Expose qualifications.
3. L2: add a reusable classifier and stable phase CLI. Emit yes/no/null, exact
   requested labels, concise substantive reasons, supporting/contrary page
   references, mechanism origin, qualification and missing evidence. Reasons
   must follow the decision and change when its evidence changes. No answer
   table indexed by issuer, ISIN, source hash or country.
4. L3: independent SMT/finite checks, RuleIR/Java and Catala execution, and
   meaningful parser/integration challenges including real source tampering,
   missing pages, wrong issuer/supplement, first-eight-page truncation,
   junior-only, statutory-only, coupons, repurchase cancellation, optional versus
   compulsory conversion, common versus preferred shares, benchmark-administrator
   resolution and collective restructuring. Preserve failures; repair causally.
5. L4: freeze the method, acquire previously uninspected issuer-family material,
   execute it without tuning, and retain qualifications or failures. Any repair
   converts exposed material to development and requires a new freeze/challenge.
   Deliver reports, execution summary and next-phase/repair records.

## Defaults and skeptical review

| Choice | Provenance / reason | Failure and earliest check | Status |
| --- | --- | --- | --- |
| Negative non-bank examples expected | User selection objective | Hidden positive clause; inspect terms before deciding and retain any contrary result | Acquisition hypothesis |
| Exclude ordinary creditor restructuring | Current task's non-bank negative examples and ordinary feature usage | Definition widened to all recoveries/haircuts; report policy and separate restructuring evidence | Explicit working assumption |
| Qualified English source analysis | No independent legal-label oracle exists | Agent annotations masquerade as proof; keep source proposals and formal results separate | Required claim boundary |
| Negative requires affirmative debt/repayment evidence and candidate disposition/coverage | Prior reviewed plan | Zero-hit negative or omitted pages; early missing-page and late-clause challenges | Reviewed requirement |
| Bounded dated offering terms | Downloadable original final terms | Implied present legal clearance; preserve dates and incomplete later-amendment boundary | Bounded baseline |
| Existing Python/JDK/Catala tools | Repository already has native infrastructure | Environment mismatch; version/import smoke before native execution | Reviewed reuse |

Review found two new promotion risks: forcing the user's expected negatives,
and generating explanations unrelated to the source facts. Both are repaired
by evidence-derived outcomes and explanation/evidence consistency tests. The
prior plan's all-abstention completion veto remains. The task is an implementation
and conditional source demonstration, not a scored legal-interpretation benchmark.
An unresolved bond remains published and prevents claiming complete coverage.

Acquisition preflight: public issuer/exchange URLs; 45-second requests, explicit
filenames and no overwrites; reject wrong issuer/edition and HTML error pages.
Use `.venv/bin/python` and installed pypdf/poppler for implementation. No fresh
external model calls or new allowance is needed. No GPU libraries are imported.
Run manifests preserve git commit plus dirty-source hashes, environment,
commands, deterministic seed status, duration and output hashes. Required
commands will be recorded before each execution stage.

The revised plan passes this skeptical audit for implementation. Its hardest
remaining limit is interpreting unrestricted English and deciding relevance of
incorporated documents. Preserve that limit explicitly rather than presenting
backend agreement as a solution to it.

Acquisition repair: the Veolia base is 2,389,381 bytes and two 45-second
transfers stopped at about 0.53 MB. Preserve both incomplete bodies; allow one
240-second transfer for this identified document, with execution yielding while
other work continues. HTTP 200 alone is not acquisition success. Reject truncated
PDFs and compare the completed body length to the advertised length. This is a
document-transfer repair, not a change in legal selection or outcome criteria.

Scope review before the corpus run: the user's target is what the prospectus
explicitly discloses. A negative is conditional on retained dated offering
documents, including identified issue supplements, rather than a claim that
every incorporated financial filing, trust deed and later law has been proved
irrelevant. Record those boundaries for each affected issue. Missing an
identified base or term-changing supplement still blocks the result. Document
selection is a source proposal, not a human quality label or a proof premise
silently promoted to legal truth.

Next commands, using the existing `.venv` and no external models:

```
.venv/bin/python scripts/build_bond_feature_inventory.py
.venv/bin/python scripts/run_bond_loss_absorption_classification.py --inventory docs/prospectus/classification-additions/issue-inventory.json --output docs/implementation/bond-loss-absorption-classification/execution/development --checks
```

Preserve each attempted corpus report and repair record. The final run executes
the identical declared formal policy through native RuleIR/Java and Catala;
formal agreement is not used to validate the English premises.

## Execution outcome

Implementation, acquisition and the requested corporate examples were executed.
The [final report](../implementation/bond-loss-absorption-classification/results.md)
publishes 26 rows with reasons: 12 positive, 13 negative, one unresolved.
447 tests, 244 native executions, independent formal checks and six real-source
fault challenges passed on the accepted version. See the
[reset record](../implementation/bond-loss-absorption-classification/RESET.md)
for exact commands, preserved failures, source qualifications and decisions.

L4 is **partial**, not promoted to full generalization: the first freeze failed
an edition-integrity test and was repaired; the second fresh-family challenge
produced a Danske positive and a Shell abstention. The requested Tesco/Veolia
negatives and reasons are delivered. The remaining Shell gap is the binding
between a stated cash redemption amount and its calculation unit. Keep it
visible rather than forcing the expected negative or treating all source
meaning as proved by formal backend agreement.
