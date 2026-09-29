# Transaction compliance for a private bank

A prospectus describes an instrument. Permission to deal also depends on the
client, the bank's legal entity and branch, its capacity in the transaction, the
other parties, the settlement route and the applicable date. This applies to
ordinary bonds, equities, preferred shares, funds and derivatives as well as
CoCos. A sophisticated-investor qualification discharges only its specified
requirements; it cannot grant an exception to another law or bank policy.

JPMorgan's [Asia disclosure](https://privatebank.jpmorgan.com/apac/en/disclosures/legal-disclaimer)
identifies JPMorgan Chase Bank, N.A. Hong Kong/Singapore branches as providers of
dealing, advice, discretionary management, banking and custody, as notified to
the client. It also identifies different entities elsewhere. The brand is not
a substitute for the legal entity on the actual agreement. A foreign branch of
a US entity and a separately incorporated foreign subsidiary require different
analysis. [OFAC FAQ 11](https://ofac.treasury.gov/faqs/11) explicitly distinguishes
programs that extend obligations to foreign subsidiaries.

## Required layers

| Layer | Question and information required |
| --- | --- |
| Entity, jurisdiction and coverage | Which booking, advising, executing and custody entities participate? What are their branches, locations, licenses and capacities? Which effective rules and exceptions apply to each? |
| Sanctions | Screen issuer, relevant ownership, client/beneficiaries, counterparties and intermediaries under each applicable program. Distinguish blocking, securities restrictions, geographic restrictions, licenses and reporting. |
| Bank regulation and licensing | Does this entity have authority to perform this activity? Assess bank, broker, adviser, derivatives and prudential restrictions only where applicable. Agency, principal dealing and financing may differ. |
| Client and account controls | Establish identity, ownership/control, residence and relevant US status, account purpose, source-of-funds requirements, AML monitoring and required enhanced diligence. Keep jurisdiction-specific definitions separate. |
| Product, distribution and conduct | Apply offering restrictions, client category, suitability, disclosure, market-conduct and instrument-specific rules. This is where the existing SPI/CoCo results belong. |
| Bank policy and mandate | Apply versioned internal restricted lists, product approvals, risk limits, account mandates and any permitted policy exceptions. These inputs have not been supplied. |
| Settlement, custody and reporting | Check the actual counterparties, custodians, currencies and route, and retain applicable post-decision duties. A permissible purchase does not establish permission for every later corporate action. |

The rows describe required assessment categories, not a claim that every rule
pack is implemented. An applicable legal prohibition cannot be overridden by a
favorable suitability result or internal approval. A rule-specific statutory or
OFAC authorization must satisfy its own scope, conditions and time limits; it
does not waive other programs. An internal exception can affect only the policy
that permits it. Conflicting jurisdictions remain explicit unresolved questions.

## Shared front end and implementation

The modular front end should produce the instrument's sourced terms alongside
the party/account facts, legal-entity relationships and transaction context.
Versioned rule packs select and evaluate the obligations. Translation to RuleIR
or Catala follows the same normalized facts and specifications. Neither target
language is the authority on which laws apply.

`src/legalmath/compliance.py` implements a Python composition component, not a
complete natural-language interpreter or a new native RuleIR/Catala rule pack:

- `Context` binds instrument, client, booking entity, establishment, service,
  action and two timestamps. Immutable content references bind the party facts,
  settlement route and policy snapshot. The caller must supply the corresponding
  evidence; naming a hash does not prove its meaning or completeness.
- `Requirement` declares a versioned obligation in one of the seven layers.
  `Finding` supplies its reason, source references, effective interval and
  earliest knowledge time. Even non-applicability needs supporting evidence.
- `assess` checks source bytes and bindings, retains every unresolved condition,
  prohibition and duty, and only returns `SATISFIED_UNDER_DECLARED_SCOPE` when
  every declared requirement passes and every layer is represented. The result
  always says complete legal compliance is not established. It cannot execute a
  trade, freeze assets or submit a report.
- `cmic_check` is a conditional implementation of selected EO 14032/OFAC
  premises. A US principal and a US bank supplying specified services for a
  non-US party are different cases. List membership, exposure, effective dates,
  licenses, beneficial parties and otherwise-permissible activity are explicit
  interpreted inputs. Unknown and contradictory inputs survive evaluation.
- `blocked_ownership_closure` propagates the 50% rule through exact direct
  ownership stakes. It requires the blocking-program selector and rejects
  NS-CMIC. An entity that is not reached is not thereby cleared.

The integrated `legalmath.transaction` package now retrieves evidence, derives
conditional findings against a fixed obligation inventory and connects the
shared formal models to both compiled targets. It retains official sanctions
snapshots and provides transaction-event replay. Its [implementation guide](implementation-guide.md)
describes the commands, proofs, tests and remaining rule families. The full
integrated verification command is:

```sh
.venv/bin/python scripts/run_bank_compliance_program.py
```

The retained prospectus campaign remains evidence for its original recorded
method. It does not certify these new compliance rules or current legal coverage.

## Discriminating legal examples

For the Chinese military-industrial securities regime, a US bank's own purchase
of a covered designated issuer's security can be prohibited while specified
support services for a permissible non-US transaction remain allowed. The
beneficial party and the bank's actual capacity are indispensable inputs.
Continued holding, sale during an applicable divestment period, and sale after
that period are also distinct. A full blocking regime has different consequences.
See OFAC FAQs [902](https://ofac.treasury.gov/faqs/902),
[1046](https://ofac.treasury.gov/faqs/1046) and
[1048](https://ofac.treasury.gov/faqs/1048).

Under the blocking ownership rule, if blocked X owns 50% of A and A owns 50%
of B, B is blocked under the supplied ownership premises. Multiplying the two
stakes and stopping at 25% gives the wrong result. Two blocked owners' direct
25% stakes also aggregate to 50%. A solely NS-CMIC-listed parent does not cause
this automatic propagation to its subsidiary. See OFAC FAQs
[401](https://ofac.treasury.gov/faqs/401) and
[857](https://ofac.treasury.gov/faqs/857).

US national-bank BSA program obligations provide another reason to represent
institution-level controls. Their existence does not mean every account rule
has identical territorial scope. In the retained 2025 edition,
31 CFR 1010.620(a) specifies private-banking accounts established, maintained,
administered or managed in the United States; 1010.605(m) supplies a defined
account category. A Hong Kong address alone settles neither predicate. The
2025 PDFs are historical sources, not a complete September 2026 currentness
determination. See the [source manifest](sources/manifest.json) and its explicitly
rejected eCFR access responses.

## What the checks establish without human grading

The permission rule is a conjunction over a declared finite requirement set.
If any required finding is absent, stale, unknown or conflicting, the conjunction
cannot establish permission. A valid prohibition always prevents proceeding,
irrespective of any other layer. The tests enumerate all 2,187 combinations of
satisfied/prohibited/unknown across seven layers and separately challenge
non-applicability, unmet controls, conflicting evidence and source/context changes.

For ownership, begin with the supplied blocked entities and repeatedly add any
entity whose direct stakes held by already blocked entities sum to at least
one half. Each step only adds entities, so on a finite graph the procedure
terminates. Any set containing the initial entities and closed under that rule
contains every added entity, by induction. The terminal set is itself closed;
therefore it is the least such set. An independent check intersects all closed
supersets for each of 512 three-entity graph/seed combinations. Tests also cover
aggregate stakes, the threshold, invalid inputs and unseeded ownership cycles.

These are exact results about supplied formal premises. They do not establish
that an ownership register is complete, that a source interpretation is correct,
or that a new future law has been captured. Generalization means reapplying the
same checked semantics to new supported inputs and qualifying unsupported
situations. It does not mean predicting future legal changes.

## Next implementation phase

The [reviewed closure program](../plans/bank-compliance-closure.md) implements the
evidence path, declared inventory, selected rule packs, sanctions ingestion,
native execution and lifecycle checks. The [current guide](implementation-guide.md)
distinguishes these mechanisms from the remaining substantive rule families,
actual bank/account inputs and unproved source interpretation. The executable
program refreshes its next-phase instructions after each phase and preserves
failed attempts for repair. New future-source observations remain a separate
series; no real prospective accuracy is claimed.
