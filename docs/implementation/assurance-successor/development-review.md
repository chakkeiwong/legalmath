# Development checks before campaign phase acceptance

The first grant/scoped check ran 72 tests: 71 passed and a new test failed because
it matched an error code against the human-readable exception message. The code
correctly rejected the ungranted live provider before dispatch. The test now
checks `exception.code == E_AUTHORITY`; this is a test-assertion repair, not a
relaxation of authorization. The complete affected check is rerun by S2.

Source audit correction: the base PDF inventory performs no OCR, but the installed
sidecar already performs OCR, layout comparisons and region investigations.
Likewise `abstractions.py` already proposes rival factual schemas. This successor
reuses those implementations; missing end-to-end integration and source-supported
dispositions remain separate from installed tool availability.

The first raw-contact Java tests hit a pytest fixture-scope mismatch before
compilation: a module-scoped builder requested the function-scoped repository
fixture. The builder now resolves its own stable repository path. All eight
tests then passed, including actual raw-history execution and malformed-input
rejection. This was a test setup repair; no implementation requirement weakened.

The complete investigation's original resume path rewrote cached diagnostic
receipts, changing their file hashes. Accepted dossiers now return only after
hash verification and remain immutable. A new source revision marks the active
state unfinished before execution; a caller requesting the old active revision
is rejected. Both old and new historical dossiers remain independently readable.
The focused revision/resume checks passed.

The live study's phase criterion requires every selected joined investigation
to execute completely. Merely retaining an incomplete task in the denominator
does not pass the phase. Retention prevents optimistic reporting; it does not
substitute for required implementation or execution.

The final acceptance audit now reconstructs scoped summaries from their executed
journal rows, revalidates exact source and representation references, checks the
retained action files, and independently regenerates every supported live Lean
certificate and Java-domain check. Five focused mutation tests reject detached
proposals, changed counts, false receipts and altered raw responses. The retained
twelve-pair completed batch from S6's first attempt also passed reconstruction
without changing its original files. Historical results lacking the later
four-dimension count retain their format; the audit computes that count from the
original judgments instead of backfilling a success flag.

Five controller tests passed for start-manifest persistence, tampered predecessor
rejection, stale final-report invalidation, executed-repair requirements and
nonresettable attempt limits. These are integrity checks, not evidence of source
meaning or future legal accuracy.

The evaluation preflight found that actual frozen circular case IDs start with
digits. The response contract previously imposed a lower-case-initial identifier,
and Java's subject validator would also have rejected those IDs. The response
now accepts only exact requested case IDs; the executor preserves them and derives
a separate deterministic, valid internal subject ID. All sixteen frozen IDs pass
the identity check, an unrequested ID is rejected, and a numeric circular case
reached the actual generated Java program with the expected Boolean result.
The combined final-acceptance development suite passed twenty tests.

The controller audit also identified a read/write race: an unlocked status refresh
could overwrite a phase's newly completed state. Status now takes the master lock
when it can, and otherwise computes a read-only report. A concurrent-reader test
verifies that neither state nor the next-phase file changes while a writer owns
the lock; deferred invalidation is persisted once the writer is absent. New phase
manifests also bind the successor driver files, in addition to package code.

The PDF composition check reproduced an exact-codec rejection on the real retained
four-page authentication appendix. Its sidecar report includes fractional geometry.
The integrated boundary now retains and hashes the original report while converting
only diagnostic fractional values into decimal strings in the dossier view. The
exact financial codec is unchanged. Source-processing identity was versioned and
now includes the boundary implementation so old normalized results cannot be
silently reused. Eleven focused PDF-boundary and complete-workflow tests passed,
including preservation of every value in the retained 480,156-byte report.

An installed-method audit also corrected a plan assumption: the repository has
the executed symbolic and extraction routes but no dedicated NLI classifier in
this increment. It is not counted as independent semantic evidence. Installing
one would require its own source-domain and joint-miss evaluation, not merely
accepting a pretrained score as legal entailment.

The Boolean-certificate boundary review found a large-domain reporting defect:
`4**30` exceeds the exact JSON codec's integer range, even though the profile
already refuses to enumerate that domain. The diagnostic now stores the exact
required count as an integer string and retains `NOT_RUN_DOMAIN_LIMIT`. A
thirty-fact check confirms that the limit can be reported without starting Java
or weakening the codec. All twelve proof-profile tests passed after the repair.

The unfamiliar-study scheduling audit found that an `EXECUTED` summary with
`execution_complete=False` would have been incorrectly reused on retry. Only
complete ensemble executions are now reused. A pilot gate retains all four tasks
but waits for engineering repair before spending their remaining budgets; it
does not gate on a favourable legal result. Once the pilot executes, the other
three task directories run concurrently within the same shared grant. Two
controlled driver tests passed for the failed-pilot/repair/resume sequence, full
denominator retention, empty single-reader rejection and zero model dispatch
from the tests. No new live study task has been started by these checks.

The source-comparison audit found that an explicitly supplied `retained` document
is a catalogue item, not an initial interpretation root. With reference depth
zero, the authentication appendix would be inspected by the PDF sidecar without
entering the language-model packet. The study now selects it as a root for both
arms and freezes their shared packets before any study answer. Its source hash is
checked against the original S1 extraction input; bytes are read once and hashed
before use. Every original root passage and every frozen reference quotation
remains unchanged. The authentication packet now has 263 units from two documents.

Both arms use lossless metadata compaction, retaining exact source text and unit
IDs. The large authentication inventory uses the existing five-piece protocol
with a cross-piece check for each reader, rather than dropping appendix lines.
The 8,000-character/80-unit piece limits are bounded scheduling choices, not
accuracy claims. Smaller source families retain their original whole-inventory
route. Four source-freeze and scheduling tests passed after updating a synthetic
fixture to supply the unit-count metadata used by the new preflight.
