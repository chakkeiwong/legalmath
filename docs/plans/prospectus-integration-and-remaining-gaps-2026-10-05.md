# Prospectus integration and remaining gaps — 5 October 2026

## Integration scope and skeptical audit

The user authorizes committing the completed prospectus work, merging with main,
pushing both branches and synchronizing their tips. The active task branch is
`feature/prospectus-evidence-master`. After fetching origin, both local branches
and both corresponding remote branches point to
`2d6b737b27aa6f028d8b37ccac17cbd5816d4488`.

The audit found two integration hazards. Main contains unrelated, uncommitted
assurance work, including six generated PDFs also changed by this task. Record
the identities of all its dirty files, save the six PDFs, stash only those six
paths, fast-forward main, and restore those paths from the saved stash without
changing the index. Keep all unrelated work uncommitted. Second, the repository's
LaTeX scratch rule also ignores execution logs named in evidence receipts. Include
the retained evidence logs and verify the committed archive in a separate clean
checkout so locally present ignored files cannot hide missing evidence.

The approximately 2 GB working files contain repeated source snapshots and
content-addressed stores. Preserve their required paths and exact bytes; Git
deduplicates identical blobs. Check unique new blob size and the individual file
limit before push. Exclude runtime locks and Python caches.

The integration criterion is equality of the two local and two remote branch
tips, with a clean prospectus worktree and unchanged identities for the unrelated
main-worktree files. Evidence integrity is a separate veto: a missing or changed
required file must be repaired before push. Remote divergence requires inspection
and ordinary merging; it does not authorize a force push. Stop and investigate
unexpected collisions, concurrent file changes, conflicts, oversized files or
failed verification. Commit and branch equality do not establish legal accuracy.

The audit passes with these preservation and clean-checkout checks. No numerical
defaults, classifiers, legal premises or candidate promotion criteria change in
this integration. The frozen reader remains the comparator; the cancellation,
intake and external-law repairs remain in the reviewed isolated candidate.

## Evidence available

The completed repair report records 885 passing candidate tests, three repaired
unpaid-cancellation defects and two preserved paid-amortisation controls. The
25 declared legal scenarios match their engineering expectations: 12 conditional
and 13 unresolved. These are deterministic checks of declared premises, not
independent legal labels or a population accuracy estimate. The seven offering
inputs produce five abstentions and two conditional positive readings.

The execution report, source review, patch, addendum and verification receipts
are retained under `docs/implementation/prospectus-corner-repair-2026-10-04/`.
Its `run-manifest.json` binds the accepted tests, comparisons, legal scenarios,
inputs and report. The four-page addendum was rendered and visually inspected;
human prose acceptance remains pending.

## Ordered closure plan

| Remaining gap | Work to close it | Acceptance evidence |
| --- | --- | --- |
| Two empty extractions and one partial extraction | Produce OCR derivatives with original image hashes, tool versions and page mappings. Review the issuer, identifier, dates, operative clauses, exceptions and cross-references against the images. | Reviewed field and clause comparisons; ambiguous or missing text still forces abstention. Manual image reading alone is not recorded as OCR. |
| Three incomplete BES issue dossiers | Obtain Series 23's 2010 base and six supplements, Series 35's 2013 base and two supplements, and Series 36's 2013 base and four supplements; identify already retained dependencies, fill remaining ones, and complete incorporated accounts and precedence review. Distinguish issuer, guarantor, class and exact instrument identifier. | Every required dependency and version is sourced; precedence conflicts are resolved or explicitly unresolved. Keep terms dates separate from actual issue dates: 15 July 2011, 21 January 2014 and 8 May 2014 respectively. |
| Missing primary legal and offering instruments | Recover the Portuguese 29 December 2015 decision and Annex 2B identifiers; HETA's original FMA decree and liability/guarantee list; Dana 2013 listing particulars; Lloyds 2009 offer/trust deed; Ukraine 2013 offer; Popular/Snoras originals; and the exact historical Italian bankruptcy Articles 65 and 67. | Original or clearly labelled mirror bytes, provenance, scope, edition/date and operative passages reviewed. Law 130 Article 4's Article 67 exemption does not establish an Article 65 exemption. |
| Legal outcomes lack independent adjudication | Obtain independent review of all 25 scenarios, including jurisdiction, operative date, instrument/claim scope, procedural stage, facts and exceptions. Resolve or retain disagreements explicitly. | Independently justified labels and source anchors. Unresolved cases stay unresolved; internally passing expected labels cannot substitute for this review. |
| Generalisation and production adoption | Freeze the repaired candidate and reviewed labels, then evaluate genuinely unseen prospectuses with adversarial negation, payment/loss, distant cross-reference and document-precedence cases. Review the candidate patch and run downstream integration checks before changing the production reader. | Predeclared criteria, paired baseline/candidate results and qualifier-preserving evidence. Count changes or fewer abstentions alone cannot promote the candidate. |
| Human acceptance of the explanation | Obtain human review of the rendered addendum and relevant manuscript chapters; revise confirmed readability problems and rebuild. | Recorded human feedback and resolved substantive issues. Compilation and model review alone do not establish acceptance. |

Do source recovery and OCR first because incomplete inputs prevent legal
adjudication. Independent adjudication must precede treating unseen-case outcomes
as legal accuracy evidence. Unseen-case validation and integration qualification
must precede production adoption. Human prose review can proceed alongside these
steps. Missing adjudication blocks promotion, not continued local repairs.

The public-source request ledger records 187 of 212 requests used, leaving 25.
Spend these only on specific new acquisition routes; retain failed responses and
do not repeat the ineffective search shells or unavailable endpoints already
recorded in `ACQUISITION-REVIEW.md`. No source requests or paid model calls are
needed for Git integration.

## Integration execution record

Local preservation and index audits are recorded in
`/tmp/prospectus-sync-20261005/`. The preservation audit covers 37,751 unrelated
dirty files on main and separately backs up all six overlapping PDFs. The index
audit covers 6,413 changed paths, including 136 retained evidence logs. Repeated
snapshots reduce to approximately 436 MB of unique new uncompressed Git blobs;
the largest individual blob is approximately 29 MB. All final-manifest input,
method, orchestration and artifact paths are present in the index. Runtime locks
and Python caches are excluded.

The focused whitespace check finds only a final blank line in the historical
jurisdiction plan and phase dispatcher. Their exact bytes are retained because
they are bound in the execution evidence; neither finding changes behavior.
The clean checkout verification passed for commit `df64b03f` in
`/tmp/prospectus-sync-20261005/checkout` using
`python3 -m scripts.run_prospectus_corner_repair verify`. Receipt
`phases/023-verify/receipt.json` in that temporary checkout records the result:
293 frozen method files, 681 candidate Python files, all 22 prior phase receipts,
the accepted 885-test record, acquired sources, candidate patch, report and four
visually inspected PDF pages all passed their integrity checks. The final run
manifest remains SHA-256
`fca1f51d4b24075e47c5e0e06fcce08db1303e586693ec195a9aa9dc8d2ef36f`.
This check used only committed project files and made no source requests. It
verifies the saved results; it does not rerun the test suite or adjudicate law.
The following documentation-only commit records this verification. The historical
run manifests retain the commit and interpreter of the original experiments;
they are not rewritten to pretend those experiments ran after this integration.
