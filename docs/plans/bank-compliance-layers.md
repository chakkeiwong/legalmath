# Bank, client and transaction compliance layers

## Question and scope

Can the shared front end preserve an instrument's terms while evaluating the
additional constraints on the client, the servicing bank and the transaction?
The comparator is the existing product/SPI and CoCo conditional review. It does
not establish transaction permission for a US bank. The new component must be
instrument-independent and usable before either RuleIR or Catala translation.

This increment implements evidence-bound composition and selected conditional
sanctions calculations. It does not invent JPMorgan internal policies or import
every US domestic banking rule into every overseas account. JPMorgan's public
Asia disclosure identifies JPMorgan Chase Bank, N.A. Hong Kong/Singapore branches;
the actual account agreement must identify the booking and servicing entities.
No live client, account or trade is evaluated.

## Evidence contract and research intent

- Primary pass criterion: no transaction proceeds under the declared scope
  unless every required layer has current, context-bound supporting findings;
  a prohibition survives favorable product, suitability and bank-policy results.
- Mechanism: separate scope/context, sanctions, bank regulation, client controls,
  product/distribution, internal policy and settlement assessments. Missing
  assessments, expired evidence and conflicting findings retain qualifications.
- Expected failure modes: equating a US intermediary with a US beneficial
  investor; applying the blocked-person ownership rule to NS-CMIC; equating an
  operational hold with a legal asset freeze; treating missing bank policy as
  approval; reusing a decision after the booking entity, action or time changes.
- Promotion veto: any counterexample to those invariants, source corruption,
  ambiguous result labeling, or absent test evidence. A test failure triggers
  repair and re-execution, not rejection of the general architecture.
- Continuation veto: inability to preserve unrelated work or obtain necessary
  source text. Unsupported legal questions remain unresolved, while engineering
  work with an explicitly conditional specification can continue.
- Explanatory diagnostics: test counts, document page counts, source hashes and
  backend agreement. None establishes completeness or faithful interpretation.
- Non-conclusions: comprehensive sanctions coverage, autonomous interpretation,
  actual JPMorgan policy compliance, future-law correctness or Catala superiority.
- Artifacts: `docs/implementation/bank-compliance/`, `docs/compliance/`, focused
  tests and a bounded new monograph section. No human quality labels are used.

## Assumptions and early checks

| Choice | Provenance and reason | Failure and early check | Status |
| --- | --- | --- | --- |
| Entity and branch, not brand, determine scope | JPMorgan Asia disclosure; OFAC FAQ 11 and 31 CFR 586.307 | Subsidiary mistaken for branch; paired legal-entity cases | Source-bound conditional rule |
| Separate bank and ultimate investor | OFAC FAQs 902, 1048 | All non-US client trades at a US bank rejected; agency/principal counterexamples | Bounded CMIC model |
| Aggregate blocked ownership by a least fixed point | OFAC FAQ 401 examples | Percentage multiplication misses a blocked chain, or a cycle creates its own seed; independent finite closed-set checks | Exact engineering specification |
| An assessment is bound to context and a knowledge interval | Existing source/version discipline | An old approval survives a changed action/entity; mutation tests | Conservative design choice |
| Bank policy is an independent required layer | User's institutional scope | Public law is substituted for unavailable internal policy; missing-policy case | Requirement, contents unknown |
| No blanket adoption of US domestic AML rules abroad | Program-specific territorial definitions | A Hong Kong account silently assigned US-account requirements; applicability remains a separate obligation | Required qualification |

## Skeptical audit before implementation

The initial idea of one additional sanctions Boolean fails: blocking sanctions,
CMIC trading restrictions, control deficiencies and internal restrictions have
different effects. An equally flawed shortcut would reject every NS-CMIC
transaction merely because JPMorgan is a US bank: OFAC allows specified services
for non-US persons when the underlying trade is permissible. A final issue is
that a passing source hash cannot prove that the source remains legally current.

The revised plan keeps reasons and duties separate, refuses a global legal
clearance label, and binds all results to explicit source and transaction scope.
The baseline is a conditional engineering component, not human interpretation
or the old backend's answers. There is no stochastic performance ranking or
environment transfer. These revisions pass the scoped pre-execution audit.

## Execution and repair phases

1. Preserve touched manuscript baselines; retain primary bank/regulatory source
   bytes and reading notes. Resolve inaccessible sources or qualify their use.
2. Implement the reusable context, evidence and composition component, a bounded
   CMIC actor/action check, and exact blocked-ownership propagation. Keep CoCo
   product results as one input rather than a privileged decision authority.
3. Test all layer-state combinations in a small declared domain, context/time
   invalidation, cross-instrument invariance, CMIC service distinctions and
   ownership fixed points against an independent specification. Repair failures.
4. Document the architecture and unresolved rule/policy inputs; add a linear
   monograph section, compile and inspect its rendered pages. Preserve all prior
   substantive text and citation contexts.
5. Record actual commands and results, review remaining limitations, and refresh
   the next-phase plan. Existing prospectus campaign receipts remain scoped to
   their recorded methods; new checks receive separate evidence.

## Completed phases and repairs

1. Retained 12 primary-source documents and four rejected eCFR access responses.
   Repaired those acquisition gaps with the official EO PDF and explicitly
   historical 2025 CFR PDFs. No access-response HTML is used as legal text.
2. Added the instrument-independent component, conditional entity/CMIC scope
   checks, blocked-ownership propagation and a reproducible verification command.
3. Initial 43 new checks and 63 existing checks passed. A subsequent code review
   found that the principal route also needs the other/ultimate party's US
   status, even if the bank itself is not a US person. Repaired that predicate
   and added a discriminating counterparty test; final evidence is recorded in
   the execution manifest. This was an implementation repair, not a reason to
   stop the direction.
4. Added monograph section 2.4 and preserved all earlier section prose and
   citation contexts. The first build passed. Rendered-page review triggered
   expansion of the OFAC/OCC acronyms and identification of both executive-order
   numbers before use; the final rebuild and page checks are recorded separately.
5. Remaining rule packs and live/private inputs are recorded in the next phase
   below and the execution/reset report. No real bank account has been cleared.

## Refreshed next phase

Build source-bound jurisdiction/activity and role inventories, then implement
current sanctions-data/identity resolution and versioned rule packs. Full
AML/CDD, market-conduct, tax, licensing, other sanctions and confidential
bank-policy interpretation remain separate obligations. Lower the same supported
specifications through RuleIR and Catala and test each against independent
semantics. Observe future unseen legal changes under a frozen method; preserve
qualification for unsupported scope or meaning. Do not infer internal bank
policy or real account facts from the public website.
