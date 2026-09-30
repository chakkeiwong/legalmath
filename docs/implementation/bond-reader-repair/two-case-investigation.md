# Santander and Unilever: investigation and proposed repair

The Santander abstention is a language-coverage gap. The Unilever abstention was
blocked by a missing source; the exact dated source has now been recovered.
Neither published classification has been changed in this investigation.

## Source findings

Santander's retained July 2025 AT1 circular defines Common Shares as ordinary
shares on PDF page 86 and the Trigger Event on PDF page 97. Condition 5.1(c),
PDF page 103, requires the Bank to convert the securities without holder consent
when the trigger occurs. Condition 5.2, PDF page 104, also states that conversion
is in whole and is not available at the holders' option. The cover's copular
construction, “are mandatorily and irrevocably convertible”, and the separated
list structure in Condition 5.1 are outside the current positive recognizer.
Adding only a keyword would miss the actor, obligation and scope dependencies.

The general repair should construct a conversion relation from the selected
security, trigger, obligated actor, mandatory action and ordinary-share target.
It should support both the copular construction and the scoped list in
Condition 5.1. It must distinguish negation of a holder option from negation of
mandatory conversion. “Preferred Securities” is the instrument's defined name;
the instrument type must be bound to its own terms, rather than inferred from
the word “preferred”. The source supports a qualified loss-absorption reading
under the user's feature definition. That is not a new machine result or an
independent proof of English interpretation.

Unilever's retained final terms name the Information Memorandum dated
16 May 2025. The issuer URL again returned HTTP 403. The public asset endpoint
for the same issuer-linked asset returned a valid 131-page PDF, whose content
SHA-1 matches the filename in the issuer URL. Its cover names the required
issuers and date. The PDF, SHA-256 and HTTP headers are preserved under
[`classification-reader-v2-repair`](../../prospectus/classification-reader-v2-repair/README.md).
The recovery record states the limit: the issuer endpoint did not supply a
second body for an independent byte comparison.

The next repair must bind that memorandum to the selected Unilever final terms,
resolve relevant dated source dependencies, distinguish uncompleted programme
forms from selected terms, and examine the complete retained text. Repayment
fields alone do not prove absence of a loss-absorption clause. A negative result
is permissible only under the reader's declared source and language coverage,
with remaining completeness and interpretation qualifications displayed.

## Reviewed sequence

1. Preserve the current report, freeze and two abstentions as the baseline.
   Work in an isolated checkout because the shared main checkout contains a
   separate assurance campaign. Create a new inventory for the recovered
   memorandum; do not rewrite the frozen fresh-source inventory.
2. Specify conversion relations and derive adversarial constructions before
   changing the reader. Cover mandatory versus optional conversion, ordinary
   versus preferred shares, selected versus other securities, scoped list
   negation, hypothetical descriptions, undefined aliases and contradictory
   definitions. Preserve source offsets for every relation slot.
3. Implement and independently check source binding, relation witnesses and
   formal evaluation. Rerun the original 26 cases, the two exposed cases,
   prospectus regression tests, finite/SMT checks and native RuleIR/Catala
   executions. Inspect every changed classification and explanation.
4. Challenge the source checks with a wrong memorandum edition, omitted
   supplement, missing/reordered pages and altered source bytes. These must
   block unsupported answers. If the recovered source reveals further
   dependencies or unsupported language, record the failure and refresh the
   next phase rather than forcing the desired negative result.
5. Freeze the revised method before acquiring additional unseen issuer and
   wording families. Treat Santander and Unilever as exposed development
   cases after repair. Preserve failures, source coverage, abstentions and
   qualified results; regenerate the report and PDF after successful checks.

## Skeptical audit and evidence contract

The engineering question is whether a general relation parser and a recovered,
edition-bound source bundle can resolve these abstentions without introducing
unsupported answers. The exact comparator is the preserved v2 implementation
and report at commit `dc4e424ab73bebc4503badd8666464eee388221c`.

Passing requires reproducible, source-bound derivations for any newly resolved
case, correct formal execution, rejection of adversarial source and relation
mutations, and explained regression changes. A case remaining unresolved is a
coverage result, not proof that the research direction failed. Wrong source
identity, invalid source bytes, inconsistent derivations or broken execution
invalidate the affected run and trigger repair. New unsupported constructions
trigger a scoped parser repair and plan refresh.

Counts of resolved cases and agreement between backends are explanatory
diagnostics; they cannot establish legal correctness or future generalization.
Backend agreement cannot validate a shared frontend error. Source-linked
English relations remain qualified unless their meaning can be independently
proved. There are no human answer labels or model-majority verdicts used as
quality authority.

The main assumptions are the user's feature definition, applicability of the
selected issue terms and base edition, and the bounded English constructions.
Their provenance is respectively the user request, explicit document references
and the parser specification. Early checks are the four-fact formal contract,
dated issue/source binding, and minimal contrastive relation tests. Source
scope and English coverage remain hypotheses; senior rank, issuer identity and
the desired answer cannot substitute for them.

The plan passes this audit as a proposed bounded repair: it preserves the right
baseline, avoids counting repaired cases as unseen evidence, separates
acquisition from classification, and defines repair and stop conditions.
Implementation and classification reruns remain to be executed. The completed
work here is source investigation, PDF preservation, and verification of all
33 original files used by the existing 26 cases.
