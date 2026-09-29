# Bond-by-bond prospectus loss-absorption classification

Execution update, 29 September 2026: the classifier and per-bond reasons have
been implemented and exercised under the
[reviewed execution extension](bond-classification-execution.md). The
[published report](../implementation/bond-loss-absorption-classification/results.md)
contains 26 rows, including the retained final Lloyds HTML mirror: 12 positive,
13 negative and one unresolved Shell senior bond. Formal/integrity checks pass;
fresh-family generalization remains partial because the Shell repayment-unit
construction is not resolved. Earlier diagnostic/planning statements below are
the protected pre-execution baseline, not the current implementation status.

## Requested result and scope

Produce one row per distinct issued bond, excluding preferred shares, with the
exact label `loss absorption` or `non loss absorption`, the mechanism, source
clause and page, and a separate qualification/status field. Apply the user's
definition: the prospectus explicitly permits a write-down of this bond's
principal or compulsory conversion of this bond into common/ordinary shares.
The property is the existence of that mechanism; no trigger needs to have
occurred. Partial and temporary principal write-down count, as does full and
permanent write-down. Conversion can count even if the resulting shares have
positive value. Ordinary default loss, subordination, perpetual maturity and
interest deferral/cancellation alone do not establish this feature.

This is a prospectus-feature classification. Keep it distinct from the existing
complex-product test, HKMA/SFC regulatory scope and the fourteen bank transaction
obligations. Under the literal requested definition, an explicit provision
allowing a resolution authority to write down this bond or force its conversion
also counts; record `contractual`, `statutory-disclosed` or `both` separately.
A general warning about bank resolution, the underwriter or other instruments
does not count. Do not silently import the narrower existing regulatory rule
that statutory bail-in alone may be insufficient for its product scope.

The expectation that nearly all CoCos will be positive is a diagnostic
expectation, never an input label or the source of an answer. Preferred shares
and funds are excluded as securities; mentions of preferred shares inside a
bond's general base prospectus must not exclude the bond itself.

## Current implementation and comparator

`src/legalmath/prospectus/evidence.py` currently retrieves candidate quotations
and describes a sufficient condition for complex bonds. Its general description
uses the first eight pages and deliberately does not turn write-down mentions
into contractual facts. `eligibility.py` implements a different regulatory
scope. Neither existing output answers this request. Reuse original-byte
storage, page extraction, source references, typed/qualified facts and backend
infrastructure; add a dedicated classification module rather than relabeling
either existing decision.

Baseline comparisons will include: the current evidence-retrieval behavior,
simple document-wide keyword matching, and the new issue-scoped classifier.
The keyword baseline is explicitly a failure demonstration, not the only
comparator or a promotion target. An independent formal predicate checks the
same declared inputs used by both native backends.

The old complex-product output cannot be scored as a wrong loss-absorption
answer: it answers a different question. Its comparison role is limited to
source-retrieval coverage and identifying the missing interface.

## Acquisition work authorized with this planning request

Preserve four final prospectus bundles in
`docs/prospectus/classification-controls/`, including accompanying prospectuses,
original URLs, retrieval time, content hashes, page counts and extraction hashes:

| Candidate document | Bonds to enumerate | Purpose |
| --- | --- | --- |
| Apple, final supplement 5 May 2025 | 4.000% 2028; 4.200% 2030; 4.500% 2032; 4.750% 2035 | Senior unsecured candidate negatives; generic conversion wording elsewhere in a base prospectus must be scoped. |
| Duke Energy, final senior supplement June 2024 | 5.45% 2034; 5.80% 2054 | Senior candidate negatives and a same-issuer comparison with Duke junior debt. |
| Southern Company, final supplement 8 January 2025 | Series 2025A 6.50% junior subordinated notes due 2085 | Junior candidate negative with interest deferral and a multi-product base prospectus. |
| Duke Energy, final supplement August 2024 | 6.45% junior subordinated debentures due 2054 | Junior candidate negative with reset coupons and optional interest deferral. |

Acquisition completed on 29 September 2026: four readable final PDFs, 201 pages,
eight candidate bond rows, original and extraction hashes recorded in the
[control manifest](../prospectus/classification-controls/manifest.json).
The files are filing PDF copies served by the investor-relations filing CDN;
they are not asserted to be byte-identical to EDGAR HTML. Their incorporated
controlling-document closure and final classifications remain to be established.

These are candidate negative controls, not prelabelled legal answers. Download
and inspect their terms first. If a genuine qualifying feature is found, retain
the positive result and obtain a replacement negative control; never suppress
the clause to balance the test. Historical issue documents are suitable because
this test concerns their stated offering terms, not present trading eligibility.
Record the document's issue date separately from retrieval/current assessment.

Small acquisition preflight: four identified PDF URLs, no live model calls,
bounded download timeout and no automatic overwrite. Reject HTML error pages,
preliminary terms or unreadable/extraction-empty PDFs. Public acquisition may
proceed during planning; classifier implementation and its experiments remain
the subsequent execution program requested for review.

## Execution phases

| Phase | Work | Acceptance and phase refresh |
| --- | --- | --- |
| L0: inventory | Enumerate every retained CoCo issue from UBS, Barclays, HSBC, Lloyds and Standard Chartered; add the eight candidate-control bonds above. Resolve ISIN/CUSIP, currency, coupon, issue date, tranches, taps, final/preliminary precedence and duplicates. | Every issued bond has one identity and a document set. Funds, preferred shares, background sources and base programmes have explicit exclusion/dependency records. A programme alone cannot be an issued bond. Refresh missing-document tasks. |
| L1: source analysis | Read all pages, operative terms, definitions, risk disclosures and incorporated terms relevant to this feature. Resolve which instrument, principal, actor, trigger and share class each candidate clause concerns. | Exact supporting/contradicting spans survive hash verification; foreign, generic, negated and coupon-only clauses are accounted for. No first-eight-pages shortcut. Refresh unresolved references and precedence. |
| L2: classifier | Implement the user-definition predicate, evidence qualification, CSV/JSON/Markdown report and stable CLI. Keep product complexity, sanctions and transaction clearance as separate outputs. | Positive rows have explicit issue-bound mechanism evidence. Negative rows have complete declared document coverage and no unresolved potentially qualifying clause. Missing or conflicting information cannot default to negative. Refresh counterexamples. |
| L3: verification | Execute the independent formal specification, both native targets, source-binding challenges, transformations and fault injection described below. | Formal outputs agree for every enumerated input state; all declared wrong variants are detected; expected incomplete cases abstain. Preserve failures and execute causal repairs before retry. |
| L4: generalization and delivery | Freeze the method, then acquire a distinct additional CoCo and junior/senior issuer family not used to develop its wording rules. Publish every requested bond row and the coverage/qualification report; document the definition and worked cases. | No post-freeze tuning is counted as held-out success. A repair creates a new version and converts the exposed example into development data. Build/inspect any changed monograph and process-guide pages. Publish the next missing-evidence and implementation actions. |

First delivery must cover all retained final CoCo issues and the eight identified
control bonds. Resolve issue identifiers from originals, not from the issuer's
name or file name. A fungible tap and its original issue share the same security
row when the source supports this identity; separate nonfungible tranches have
separate rows, even if in one prospectus.

Require at least one real write-down CoCo and one real compulsory-conversion
CoCo among the examined positive mechanisms. Acquire an additional write-down
issue if retained sources do not provide one. Also include an actual senior
bank issue with an explicit, issue-applicable statutory write-down/conversion
disclosure, so that seniority cannot become a hidden negative rule.

End-to-end demonstration is complete only when every retained final CoCo issue
has a supported label and the comparison set contains supported negative rows
for at least two senior and two junior bonds. If candidate controls turn out
positive, retain those results and acquire replacements; do not force the
labels. Incomplete rows remain in the report, but all-abstention or unresolved
target rows do not pass this completion criterion. If necessary documents
cannot be obtained, report the demonstration as incomplete with that precise
reason rather than claiming successful classification from coverage counts.

## Decision record and treatment of missing evidence

Each row contains issuer, legal security type, instrument identifier, title,
currency, issue date, prospectus version, requested classification, mechanism,
contractual/statutory origin, compulsory-conversion actor and common-share
definition, exact clause/page, source hashes, document-coverage status, unresolved
dependencies and calculation version. A source-specific qualification accompanies
an inference from English. No fabricated confidence percentage or approval score.

The classification vocabulary has exactly the requested two labels. An unresolved
row has a null classification and separate `needs evidence` status, rather than
inventing a third product class or issuing an unsupported negative. Publication
of one row for every bond is mandatory, including such incomplete rows.

A positive result needs a scoped witness clause and resolution of qualifications
that could defeat it. A negative is a bounded conclusion about the declared
prospectus/controlling-document set: both mechanisms were examined without an
applicable witness. Zero keyword hits cannot establish that conclusion. Missing
operative incorporated documents, unresolved references, relevant conflicts or
illegible pages prevent a supported negative. Prefer an explicit applicable
no-write-down/no-conversion statement where one exists, without requiring that
all ordinary bonds contain such a sentence.

## Test obligations without human quality labels

1. Independently specify the formal rule: an included debt security has a
   qualifying principal write-down or compulsory common-share-conversion
   mechanism, explicitly applicable in its prospectus. Enumerate known, unknown
   and conflicting premise states. Check the same inputs through RuleIR/Java,
   Catala and the independent solver; prove the finite decision/abstention
   properties. These prove the formal rule, not the extraction from English.
2. Exercise positive mechanisms: permanent/temporary and full/partial write-down;
   automatic common-share conversion; a regulator's power to compel conversion;
   mandatory conversion without any actual trigger event; and operative wording
   beyond page eight or reached through a definition/cross-reference.
3. Exercise negative/confounding cases: junior rank alone, perpetual tenor alone,
   coupon cancellation/deferral alone, market-value loss, ordinary default risk,
   optional holder conversion, conversion of another instrument, generic shelf
   alternatives not selected for this issue, underwriting-bank bail-in text,
   redemption followed by cancellation, and conversion only into preferred shares.
4. Exercise ambiguity: exceptions after a no-conversion sentence, an issuer power
   compulsory for the holder, common-share definitions in another document,
   statutory language that may not bind this issue, and explicit principal
   cancellation in liquidation. Do not classify an economically similar clause
   by a keyword without resolving whether it meets the stated definition.
5. Validate exact references independently of the extractor: bytes, page,
   quote/offset, issuer, security, document version and governing precedence.
   Challenge swapped issue IDs, preliminary/final substitution, altered hashes,
   removed definitions and conflicting supplements. Invalid evidence abstains.
6. Require invariance to whitespace, line breaks, page partitioning and
   semantically irrelevant names. Add unrelated preferred-share or other-bond
   paragraphs and confirm that scope prevents contamination. These are declared
   formal/transport transformations, not human-labelled English truth examples.
   Transformations create new source identities and require fresh extraction;
   old quotation receipts must fail against the changed bytes even when the
   resulting classification should be invariant.
7. Inject wrong implementations: junior implies positive; only the first eight
   pages are read; no hit implies negative; coupon cancellation implies principal
   loss; every mention of shares implies common-share conversion; omitted negation;
   statutory-only disclosure silently excluded; and ignored source precedence.
   Each must be rejected by a predeclared discriminating case.
8. Freeze and test newly acquired issuers, reporting unsupported or ambiguous
   conclusions openly. Their findings are source-dependent proposals with
   machine-checkable evidence, not a human-labelled accuracy benchmark or proof
   about unknown future law.

## Research intent, defaults and stop conditions

Question: can a single source-scoped method classify diverse bonds under the
explicit feature definition without confusing seniority, coupon risk, optional
conversion or regulatory eligibility? The mechanism is resolved clause scope
plus a small formal decision layer. Expected failures are missed cross-references,
wrong security referents, broad shelf text and unsupported negative evidence.

Promotion criteria are exact formal correctness, evidence integrity, complete
inventory accounting and correct handling of predeclared controlled challenges.
A real-source result is published only with its supported qualification; native
agreement, keyword counts, document length, model agreement and runtime are
explanatory, not proof of legal meaning. A detected false clause association or
unsupported negative vetoes promotion and triggers the corresponding repair.
Corrupted source snapshots, required tools unavailable, forbidden live dispatch
or exhausted bounded attempts veto dependent continuation. Missing source
evidence blocks that row's label while independent rows can proceed.

| Default | Provenance and justification | Failure mode and early diagnostic | Status |
| --- | --- | --- | --- |
| Exact requested definition | User instruction; stable, separate from regulatory product scope | Mistaking existing HKMA scope for the requested feature; test statutory-only and junior-only cases first | Reviewed task rule |
| Common and ordinary shares treated as aliases only when defined | Prospectus definitions identify the equity class | Preference stock or another issuer's securities mistaken for common shares; resolve definition before label | Source-dependent premise |
| Historical final issue bundles | Concrete downloaded documents support reproducible issue tests | Describing issuance terms as current amended terms; report both dates and missing amendments | Bounded source baseline |
| Eight candidate negatives in four documents | Includes senior and junior debt, two Duke issues and multi-product bases | Selection leakage or actual qualifying clause; keep candidates unlabelled until source analysis | Acquisition hypothesis |
| Read all pages and relevant dependencies | Prior first-eight-pages retrieval is inadequate | Missing page or incorporated terms; coverage inventory and dropped-page challenge | Required coverage check |
| No human quality labels | Persistent user product requirement | Agent judgement disguised as a gold answer; retain formal/source-based support and explicit semantic uncertainty | Required evidence rule |
| No new model budget presumed | Previous grants exhausted; exact call scope must be prepared if model execution is required | Resetting historical ledgers or issuing silent calls; pre-dispatch grant check | Resource boundary |

Run each L phase with immutable input/output identities, predecessor checks,
command/environment/time records and a refreshed `next-phase-plan.json`.
Limit retries to four preserved attempts per phase with a causal repair note.
If a counterexample exposes a current candidate, proceed to its planned repair;
do not reject the direction solely because the candidate failed. Further
attempts require a revised reviewed plan, never deletion of failure history.

## Skeptical audit and deliverables

The plan rejects four misleading successes: labelling by the CoCo name; calling
every subordinated bond positive; calling no keyword match a proved negative;
and treating two compilers' agreement as independent English understanding.
It also separates issue identity from the broad base prospectus, prevents
preferred-share exclusion from contaminating a debt row, and retains source
qualifications without converting every source-dependent result into trading
permission. The definition and finite decision layer can be verified directly;
complete natural-language understanding cannot be claimed from this test.

The bounded plan passes this audit. Before implementation, fill the exact
commands and environment in the phase records and confirm source dependencies.

The separate [plan review](../implementation/bond-loss-absorption-classification/plan-review.md)
records the corrections to comparator scope, real-mechanism coverage and the
all-abstention loophole. The four downloaded controls have already been inspected
during planning and therefore cannot serve as the later untouched examples.
Proposed new entry point (not yet implemented):
`scripts/run_bond_loss_absorption_classification.py --phase L0` through `L4`.
Proposed outputs: `bond-classification.csv`, `bond-classification.json`,
`bond-classification.md`, per-issue evidence, formal/native results, mutant
results and reset/next-phase notes under
`docs/implementation/bond-loss-absorption-classification/`.

The present deliverable is this reviewed plan and the four preserved comparison
prospectuses. No claim is made that their final classifications or L0–L4 tests
have already run.

## Senior bank examples added on 29 September 2026

The user requested actual UK, EU and Australian senior bank issue documents.
The [new archive](../prospectus/bank-senior-controls/README.md) contains eight
applicable PDFs (755 pages), plus a rejected three-page ASB supplement. The
[executed source/interface diagnostic](../implementation/bond-loss-absorption-classification/bank-senior-study/result.md)
checked 1,048 quotation locations and obtained six `UNDETERMINED` descriptions
from the unchanged reader. No dedicated binary classifier was implemented or
evaluated. This dated addendum extends the plan; the earlier plan-review hash
continues to identify the earlier version and is not retroactively rewritten.

Add these exact series to L0 and the first delivery:

| Series | Identity and source linkage | Required challenge |
| --- | --- | --- |
| NatWest Markets plc Series 14, 4.789% due 21 March 2028 | Final terms 18 March 2025; base and registration 17 March 2025; Reg S USG6382RGD47 and 144A US63906YAM03 retained without assuming fungibility | Final-terms-only text misses base Condition 7 (PDF p.69 / printed p.66), which permits statutory principal reduction despite senior rank. |
| BPCE S.A. 2025-23, floating due December 2030 | FR0014014YQ1; final terms 17 December 2025 expressly selects senior preferred; base 14 November 2025 | Base Condition 17 (p.150) and p.167 bind statutory write-down to senior preferred debt. The principal definition matters; conversion into unspecified securities alone is insufficient for the common-share limb. |
| CBA Series 6700, €STR floating due October 2026 | XS3206613666; final terms 13 October 2025; circular 1 July and CBA EMTN supplement 13 August 2025 | Candidate non-loss-absorption issue; distinguish repayment, creditor-approved restructuring, capital requirements, interest/currency conversion, and benchmark-administrator resolution. Complete negative coverage before promotion. |

Definition refresh: CBA Condition 13 permits creditor-approved reductions
binding dissenting holders. The working feature definition records ordinary
collective restructuring separately from contractual capital triggers and
statutory bail-in. The user has been asked whether this matches the intended
definition; no answer is assumed. If every such principal reduction counts,
CBA is positive too. Keep the source assessment qualified while this boundary
and document completeness remain unresolved. Do not alter the definition merely
to obtain the desired number of negatives.

Add to L1/L3: reject an ASB-only supplement for CBA despite a matching date and
shared programme limit; distinguish a covered-bond programme from EMTN;
distinguish `unsubordinated` from `subordinated`; reject repurchased-note
cancellation as a principal-loss event; reject resolution of a benchmark
administrator as resolution of the note issuer; reject interest-rate/currency
conversion as conversion into common shares. These are observed retrieval
hazards in retained documents, not hypothetical synthetic-only tests.

The new examples are development sources, not later unseen challenges. Their
qualified assessments are not human labels or independent legal oracles. The
next L0–L4 run must check actual issued-bond composition and negative evidence
closure, preserve honest unresolved rows, and implement the binary output before
claiming correct end-to-end classification. Existing complexity and regulatory
scope decisions remain different comparators.
