# Review of the additional-allowance execution

The governing plan is `docs/plans/assurance-new-grant-execution.md`. The user's
new grant is recorded verbatim; the two exhausted predecessor ledgers are
immutable. This review concerns engineering and evidence identity, not a legal
quality approval.

## Before execution

Two material traps were identified before live dispatch. A new 500-call grant
must not reset the original 120-call task arms or the six-attempt, 24-hour issue
limits. Also, an added `reading_hash` must not create a new spending identity
for an unchanged source claim, question and representation. The continuation
now checks carried arm balances and canonical original issue identities. It
recovered 32 older request records by matching their exact hashes to the old
ledger, including interrupted requests whose later transport-manifest format
did not yet exist. No unaccounted reservations were dropped.

The original UCITS denominator is 225 pairs. Sixty lacked two validated
perspectives at selection. Eligibility is checked again at dispatch because a
deadline can expire while the plan is being prepared. The first attempted
pilot exposed precisely this case. No model call was charged; the expired pair
remained excluded. A reporting defect for an absent zero-call ledger was fixed
and 21 focused tests passed before retry.

The initial guard tests also exposed a test-harness mistake: error codes were
matched against human-readable exception messages. The expected guards had
correctly rejected the requests. Tests now check `LegalMathError.code`; the
failed run is retained rather than overwritten.

## Whole-method design review

The existing prospective observer checks the qualification component's method
identity. It does not bind extraction, interpretation, question assignment or
search. The new observer derives the method from the actual complete dispatcher
and checks that record against the actual source and interpretation journals,
model route, scoped journal, authority-resolution file, source-context bytes,
candidate denominator and candidate qualifications. It reruns the registered
qualification verifier; reading a successful summary is insufficient.

The first isolated run failed because symlinked tool executables resolved
outside its declared evidence root. The copied Java executables and pinned
Catala compiler/lock now lie within that isolated root. A later check correctly
refused to verify a Catala qualification that had been recorded UNAVAILABLE:
the fixture had omitted the explicit toolchain. The integration test now uses
the pinned toolchain and actual mathematical input cases. This repair changes
the test setup, not the verifier's acceptance rule.

The bounded development regression passed 34 checks, including existing
complete-investigation integration and cross-grant guard checks. These are
synthetic software tests, not observations of future circulars. The active live
run imports unchanged production code while development occurs in an isolated
copy. Final integration and the full regression must use the delivered source.

## Remaining review obligations

The table diagnostic exposed two different failures. Asking for 263 dispositions
timed out twice. Asking for only 66 while retaining the full context returned
responses, but both lacked valid individual question hashes. The source request
had never supplied those hashes. Earlier synthetic fixtures computed them and
therefore missed the real input defect. The general single-reader transport and
bounded-output request now provide the original question-hash mapping; enum
constraints prevent invented digests and the validator still rejects a hash
borrowed from another question. The repaired prompt has a new cache binding.
All four original live failures and their spending remain. Per-concern counters
carry into the one remaining attempt for the first batch.

The repaired live run then returned all eight bounded responses successfully.
Both roles accounted for all 263 concerns, with no question-status differences
between their own batches and no replacement interpretation. The table slice
is now 12/12, including its two timeouts and two invalid identity responses.
This closes the diagnostic's response-accounting question, not its legal
meaning or cross-batch semantic-consistency questions.

The breadth phase retained 15 reservations, 14 returned valid responses and a
subsequent upstream disconnection. Both perspectives are present for all 47
admitted pairs; 32 have all four dimensions assessed. One further original
issue expired before dispatch. The controller correctly rejected its overall
method-identity check when concurrently edited prospectus modules changed the
shared package. The failed phase remains immutable. Its recovery re-resolved
every returned source and executable selection against the original inputs,
with zero new model calls; it does not claim that the original execution used
a frozen whole method. All later phases import copied package trees, and both
integration and full verification use isolated repository snapshots.

The first offline recovery check exposed an additional observer defect: the
journal writer hashes ASCII-escaped JSON, whereas the new observer initially
used the financial codec's UTF-8 canonical digest. These differ on non-ASCII
text. Recovery and observation now use the writer's digest. The integration
fixture now includes Chinese text and a typographic dash; all 17 observer
checks passed with actual Lean/Java/Catala qualification rechecking. The failed
recovery check remains archived. Thirteen carried-grant guards and two driver
checks also passed on the applied code. No historical journal was rewritten.

A final admission audit found that a first encounter after the window end was
not separately excluded, and that a new task ID could submit an already
eligible source/question pair again. Both are now retained as ineligible
submissions. Distinct questions on one source remain legitimate tasks, while
the whole-method report also gives distinct primary-source counts. Nineteen
window tests passed. These rules prevent those two forms of denominator
inflation; they do not authenticate publisher timestamps or establish that
different questions or sources are statistically independent. Tool/model lock
records are bound, but installed third-party package contents and remote model
weights are not attested by those records.

Confirm the final source copies and full regression. Keep model agreement,
successful transport and proof checking separate in the results. Retain
unavailable or unfinished stage records. Preserve the original four tasks and
six authority questions even when only one revised-source question receives
new model processing. A future window needs a final method freeze before its
first eligible publication/encounter; old development sources cannot enter it.

The strongest alternative explanation for any model success is correct use of
an output format with a shared misunderstanding of the source. Exact quotes,
fresh contexts and native backend agreement do not exclude that explanation.
The new observer establishes a stronger record of which method produced which
qualified result; it does not establish natural-language legal correctness.

The revised-source repair returned two further proposals, for four total, all
PARTIAL_SOURCE_SUPPORT. Its round-two encoded requests were 190,645 and
190,653 bytes. The next round grew to 213,860 and 213,868 bytes and stopped
before dispatch. The retained preflight's 190,946 bytes refers to the original
failed request with its original diagnostic context; no identity change is
hidden by those different requests. The four source proposals do not close
the six authority questions. Total live spending after these phases is 33/500.

The frozen provider record also binds the global and arm ledger paths and grant
identity, not just their numeric ceilings. Substituting another 120-call file
must change the method rather than replenish a frozen pilot's spending. Counts
remain variable execution state; their original ledgers remain the authority.

The final F3 integration phase passed 129 checks on its isolated snapshot, with
zero failures, errors or skips. It includes the actual whole-investigation
observer, carried budgets, question identities, bounded output, prospective
admission, operational freezing, executable references and existing complete
investigation/qualification checks. The full-regression phase follows on a
separate final snapshot; its result is not inferred from this targeted suite.

## Completed final verification and delivery

F4 passed **2,097 tests**, with zero failures, errors or skips, on the archived
933-file snapshot. No material source changed between the snapshot and delivery.
The final build has 359 monograph pages, 78 companion pages and 24 guide pages.
Physical monograph pages 27–28 and 261–265 were visually inspected. The added
guide chart reproduces inspected page 27 exactly. No clipping or overlap was
observed in that focused inspection; it does not certify human readability.
The protected 275-file baseline retained every prior line in order.

The whole-method window was frozen from that tested snapshot with zero calls
and zero observations. A separate constructor smoke check executed the
documented future API setup and reproduced the exact frozen method hash,
including native tools inside its evidence root. This check made no admission
or model request. The future API uses the snapshot as the evidence root while
the grant and study ledger stay in the workspace. Keep the snapshot and tools;
reconstructing a different installation requires checking its method identity.

The verified delivery is recorded in `final-report.json`. All earlier failed
attempts, the unclosed questions and the 33 spent requests remain. The
[next plan](next-phase-plan.md) is the continuation record, not a claim that
the historical investigations or English-interpretation problem are complete.
