# What has been verified, and what correctness still requires

Before the user's follow-up, the executable regulatory example covered the
selected 23EC35 SPI profile. The other four circulars in the pilot corpus were
tested for source intake and metadata, including the 23EC53/26EC22 replacement.
They had not been translated into independently checked executable controls.
The 154-test acceptance established the engineering workbench; it did not measure
translation accuracy on new circulars. The drafting provider remains a stub that
returns supplied candidate fixtures, rather than interpreting arbitrary prose.

On 22 September 2026 we added a second, deliberately limited example from
[SFC circular 23EC46](https://apps.sfc.hk/edistributionWeb/gateway/EN/circular/doc?refNo=23EC46),
dated 24 October 2023. The official content was fetched again; its raw bytes
matched the retained snapshot exactly. The selected requirement is paragraph 10's
gift restriction and fee/charge-discount exception, read with the distributor
context and paragraph 9's qualified treatment of additional returns. The actual
Code provision and cited FAQ remain unresolved dependencies in this test.

## The concrete interpretation under test

The assessment concerns one incentive component offered by a distributor in
promoting an SFC-authorised fund. A reviewer supplies whether the component is a
gift, whether it is solely a fee/charge discount, and whether it is linked to a
specific product or particular product type. These classifications are evidence
inputs; the software has not established them by reading a marketing document.

Within that deliberately narrow scope, the proposed prohibition trigger is:

```text
gift offered
AND (specific-product promotion OR particular-product-type promotion)
AND NOT solely a discount of fees or charges
```

The first two scope inputs establish the actor and product/activity profile.
OUT_OF_SCOPE means this limited example cannot answer the case. The broader Code
requirement may still apply. The September 2026 validity interval is a synthetic
engineering setting, not an inferred effective date of the regulation.

TRUE means the selected prohibition is triggered. FALSE settles only that
subcondition and grants no permission to proceed. Structured-product authorisation,
advertisement standards, redemption rights and the circular's other requirements
still need separate decisions. An offer containing both a fee waiver and a voucher
must assess the voucher as a separate component; the discount does not exempt it.

| Source-based scenario, with the stated classifications | Expected result |
| --- | --- |
| A voucher classified as a gift is linked to one fund | Prohibition triggered |
| A gift is linked to a fund category, without naming one fund | Prohibition triggered |
| The assessed component is solely a fee/charge discount | This prohibition not triggered; other checks remain |
| A fee waiver is accompanied by a separate voucher; assess the voucher | Prohibition triggered |
| Additional returns are offered, but gift classification is unresolved | UNKNOWN |
| The incentive is a gift but fee-discount classification is unresolved | UNKNOWN |
| Evidence establishes one product link while another possible route is unknown | Known sufficient route can trigger the prohibition |
| Gift evidence is expired or recorded after the historical cutoff | UNKNOWN |
| Referenced classification evidence conflicts | CONFLICT |

The source's qualified treatment of additional returns is a material trap. A
translator that automatically labels every additional return a gift, or treats a
finding of “not a structured product” as clearing the gift requirement, changes
the meaning. A translator that ignores the product-type route misses gifts linked
to categories or the paragraph's fund-house example. A translator that treats a
fee waiver as exempting every item in a combined offer applies the exception too
broadly.

## Results and their limits

The [oracle packet](../../examples/second-circular-23ec46/oracle.json) contains 22
named expected outcomes and their source reasoning. Its hash was
[recorded before candidate construction](../../examples/second-circular-23ec46/oracle-freeze.json).
The candidate was then manually encoded in RuleIR. A separate truth-table oracle,
which imports neither RuleIR nor its evaluator, enumerates Boolean completions
for unresolved body facts and handles applicability separately.

The [verified run](../../artifacts/runs/second-circular-23ec46-final/result.json)
passed all **22 named scenarios** and **729 T/F/U combinations** of the six inputs
in both Python and the actual generated Java class. Full semantic responses,
source/evidence traces and each backend's native result identity were checked.
The 729 combinations exhaust this small abstract input table; they do not exhaust
real documents, legal interpretations, dates, conflicting histories or all code
paths in the general application.

Four deliberately incorrect candidates were compiled to Java. The frozen named
cases detected all four:

| Deliberate error | Cases detecting the change |
| --- | --- |
| Remove the fee-discount exception | g03, g07, g16, g19 |
| Omit the product-type promotional route | g02, g14, g15 |
| Assume a gift without supporting evidence | g06, g08, g18, g20, g21, g22 |
| Ignore the actor/product scope | g10, g11, g12, g13 |

The complete circular was inventoried as 18 numbered paragraphs and four
footnotes. Only paragraph 10 has an executable control in this new example. The
other passages have explicit contextual, qualitative, separate-control or
dependency dispositions. An inventory is not an implementation of those passages.

The candidate retains **five unresolved review issues** and **two unresolved source
dependencies**. Attempting to submit it for review was rejected with E_DEPENDENCY;
it remains DRAFT and no release record exists. Candidate compilation and passing
tests confer no meaning approval. The original accepted application and Java
delivery remain unchanged; their evidence audit still passes.

This result is **correct execution relative to the stated interpretation and
supplied fact classifications**. The stronger claim that the source was correctly
translated is **not established**. One agent authored both the candidate and the
source-based cases. Writing the cases first and using a separate oracle reduces
some implementation coupling, but it does not create independent legal judgment.
23EC46 was already in the research corpus, so this is also not a blind held-out
evaluation of generalisation. No language model translated the circular in this run.

## How to establish correctness in the product

Correctness needs evidence at each transition. A mathematically correct program
can enforce a mistaken interpretation perfectly; an accurate interpretation can
still produce the wrong operational decision from stale or misclassified facts.

| Transition | Evidence required | What a passing check establishes |
| --- | --- | --- |
| Official material to retained source | Version/date checks, all annexes and cross-references, exact hashes, page/paragraph anchors and visual review where extraction is uncertain | The reviewed words are traceable to the retained authority; a hash alone does not establish authority or completeness |
| Source to interpretation and decision table | Independent clause inventory, actor/activity scope, triggers, duties/prohibitions, exceptions, dates, definitions, qualitative judgments and explicit unresolved issues | A designated reviewer accepts the stated meaning within its declared scope |
| Interpretation to RuleIR | Expected cases written independently of generated code; boundaries, exceptions, competing interpretations, missing/conflicting evidence and coverage of every operative clause | The executable specification reproduces the adjudicated cases and makes omissions visible |
| RuleIR to generated Java | Shared conformance cases, native identity checks, independent traces/oracles, compiled mutations and bounded counterexample search; optional proof for a formally specified supported fragment | The tested binary preserves the reviewed executable meaning within the checked cases/domain |
| Facts and Java result to bank action | Evidence lineage/freshness, correct entity/product mapping, effective release selection, withdrawal/amendment handling, exact artifact deployment, and atomic/idempotent host tests | The right version and evidence were used at the decision point under the tested integration protocol |

For the source-to-interpretation transition, use two separate roles. A compliance
reviewer derives requirements and expected answers from the circular, applicable
Code/FAQ and agreed facts before seeing the translator's candidate. The translator
then proposes the interpretation and RuleIR. A second reviewer adjudicates
disagreements and records why a qualifier, exception or source reference changes
the answer. The implementing agent's agreement with itself cannot substitute for
this step. Unresolved legal questions stay explicit and block the relevant release.

The source inventory must be independent of what the translator happens to extract.
Otherwise, a system can omit an entire paragraph and still report every extracted
rule as tested. For each operative provision, require either a linked executable
control, a reviewed manual procedure, a justified out-of-scope disposition or an
unresolved issue. Qualitative duties such as reasonable judgment or best endeavours
should not acquire invented numerical thresholds merely to fit the language.

The expected cases should distinguish plausible mistakes. Each exception needs
cases on both sides and a missing-evidence case. Each date rule needs expiry,
late-arriving evidence and historical replay. Each alternative route needs an
example where it alone changes the outcome. Mutations test whether these cases
actually detect the mistakes. Python/Java agreement alone is insufficient because
the two implementations can share an incorrect specification.

Formal proof becomes useful after semantics and assumptions are explicit. One
possible target is: for every valid input in a specified RuleIR fragment, the
generated Java returns the same decision as the reference semantics. Another is
an invariant that no order commits using consent or exposure versions changed
during evaluation. Those are software propositions that can be stated and checked.
They do not prove that an English clause has the intended legal meaning, that a
fact supplied by an upstream system is true, or that the selected circular set
covers the bank's entire perimeter. Current Z3 checks search a declared fragment;
their outcomes are not universal compiler proofs or proofs of compliance.

## Next discriminating validation

The next stage should use circular families the candidate authoring process has
not seen. Freeze the source, legal scope, expected requirements and adversarial
cases through independent review before running a real drafting provider. Preserve
the exact prompt/model configuration and every candidate, revision and abstention.
Compare with the manual process on the same documents and evidence.

Count omitted obligations, wrong applicability, lost exceptions, invented rules,
unsafe acceptance and unnecessary blocks separately. Report unresolved cases and
coverage as well as accuracy. Record reviewer correction effort and elapsed time,
but do not interpret a small convenience sample as a demonstrated productivity
gain. A source-faithfulness error or false legal permission vetoes that candidate's
release; it should trigger repair rather than be averaged away by easy cases.

| Decision from this run | Primary criterion | Veto result | Main uncertainty | Next justified action |
| --- | --- | --- | --- | --- |
| Accept the scoped engineering check | 22 fixed cases and 729 combinations agree in the generated class and Python | No execution/source-identity mismatch; all four mutants detected | Cases and interpretation share one author | Independent compliance adjudication of the source and case packet |
| Keep this candidate unreleased | Meaning, scope, classifications and referenced sources remain unresolved | Review submission is blocked | Actual applicable source versions and fact classifications | Resolve the five issues and two references through designated reviewers |
| Leave automatic translation accuracy unassessed | No real prose-to-rule provider ran | No independent held-out results | Generalisation, omitted clauses and legal fidelity | Registered multi-circular pilot after a real provider is implemented |

The strongest alternative explanation is a shared source misreading in the rule
and the oracle. An independently adjudicated counterexample would overturn the
source-to-rule interpretation even if every current software test continued to
pass. That is the weakest part of the present evidence and the reason the next
validation must involve an independent source judgment.

Reproduce using the [example instructions](../../examples/second-circular-23ec46/README.md).
The [plan](../plans/second-circular-verification.md) records the pre-run audit and
criteria; the [run manifest](../../artifacts/runs/second-circular-23ec46-final/run-manifest.json)
records commands, environment, input/result hashes and timing.
