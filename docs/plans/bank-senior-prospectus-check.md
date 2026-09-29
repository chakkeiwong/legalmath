# UK, EU and Australian senior-bank prospectus check

Question: under the user's explicit principal-write-down/compulsory-common-share
conversion definition, which examined senior bank notes have loss absorption,
and can the current repository program produce that classification?

Scope: acquire final terms and the matching prospectus for NatWest Markets plc
(UK, March 2025 senior notes), BPCE (France/EU, December 2025 senior preferred
notes), and Commonwealth Bank of Australia (October 2025 senior notes). Retain
the registration document and specified supplement where needed. These are
dated issue examples, not an assertion about all banks or current amended terms.
Use source documents hosted by the issuer or its exchange announcement service.

Evidence contract: one source-derived, qualified assessment per issue, with
exact issue identity, rank and applicable clauses. Write-down alone suffices
without proving the class of shares in an alternative conversion power. Generic
capital-note, third-party and subordinated-note provisions cannot transfer to
senior notes. Keep prospectus features separate from HKMA regulatory scope and
transaction permission. A negative requires inspecting the relevant senior terms
and the scope of any resolution disclosure; a keyword miss is not evidence of
absence. Record remaining incorporated-document/currentness limitations.

Comparator: execute the current `prospectus.evidence` retrieval/description
functions unchanged on retained documents as a bounded diagnostic. They answer
a different complex-bond question, so do not score their output as binary
loss-absorption accuracy. Inspect whether the requested feature field, document
composition and statutory/contractual distinction are implemented. Preserve
source/code hashes, command, environment and actual output. No fresh model calls,
no budget reset and no fabricated human answer labels.

Skeptical audit: ranking alone is a wrong baseline; UK/EU bail-in can be relevant
even for preferred senior debt, and a multi-product Australian programme can
contain capital conversion wording that does not apply to senior issues.
Issuer jurisdiction is distinct from issue currency, listing place and the
location of an underwriter. Base-prospectus clauses must be joined to the exact
final terms. Native/backend agreement cannot prove English scope. The current
dedicated classifier was only planned in the prior turn; do not report it as
implemented. These checks make the bounded source and implementation diagnostic
meaningful; the audit passes before acquisition and diagnostic execution.

Procedure: preserve original PDFs and page text under
`docs/prospectus/bank-senior-controls/`, inspect issue terms and resolution
sections, run the unchanged retrieval diagnostic, then publish source evidence
and a program-gap note under
`docs/implementation/bond-loss-absorption-classification/bank-senior-study/`.
Update the existing implementation plan with these concrete cases.

Downloads have a 45-second timeout, no automatic retries and explicit filenames.
Unreadable/mismatched PDFs, missing controlling terms or source mutations veto
the affected conclusion. Missing a document triggers a search for its issuer or
exchange copy; it does not justify a negative. A diagnostic crash blocks only
the program-behavior claim until repaired. The diagnostic should take less than
five minutes; otherwise stop and diagnose before extending it. No training,
stochastic ranking, universal legal-correctness or clearance claim is planned.

Pre-run refresh after acquisition: the NatWest base download returned HTTP 500
once and succeeded on the second bounded request. The first Australian
supplement was ASB-only; retain it as a rejected wrong-issuer document and use
the separately downloaded CBA EMTN supplement of 13 August 2025. Do not use the
similarly dated covered-bond supplement. NatWest's relevant clause is Condition
7 (PDF page 69, printed page 66), not Condition 18. BPCE's is Condition 17.

The CBA document introduces a definition boundary: Condition 13 permits
creditor-approved reductions binding dissenting holders. The working feature
definition excludes ordinary collective restructuring, purchase/cancellation
after repayment, coupon changes, and currency conversion. Record restructuring
separately; under an alternative definition including every creditor-approved
principal reduction, CBA would also be positive. The user has been asked this
optional definition question. No negative will be promoted as a machine-proved
absence while this or document-closure uncertainty remains.

Exact diagnostic command (180-second bound):

```sh
timeout 180 python3 docs/implementation/bond-loss-absorption-classification/bank-senior-study/run_diagnostic.py
```

Use the installed `python3` with PyMuPDF and this checkout on `sys.path`; the
project `.venv` lacks PyMuPDF. No package installation is needed. Imports are
limited to PDF extraction and deterministic Python logic. Record Python,
PyMuPDF, original-byte and implementation hashes in the run manifest. Diagnostic
pass means original binding and quotation locators work and actual outputs are
preserved, not that English interpretation is correct. Source assessments are
written separately and are never fed into the diagnostic as expected answers.
The implementation-interface check and keyword hit counts are explanatory;
an exception, source mutation or locator failure vetoes that diagnostic run.
This refreshed bounded diagnostic passes the skeptical audit.
