# One receipt repair, preserving the rejected evidence

Revision 441 completed all seven candidate/current/installed segments, sealed the
result, and received REJECT rather than RECORD. The controller command itself
exited zero in 35.227056 seconds. Its generic validator requires both status PASS
and result.task equal to the admitted task ID. Our new submission script omitted
task from result.json. This is an implementation defect in our receipt writer,
not a source-meaning failure or package limitation. The previous submission audit
missed this concrete validator contract. The sealed result and rejection remain
unchanged.

Use the continuation's one permitted changed recovery. No substantive tests or
product trials are repeated. Verify the full sealed rejected attempt, all seven
candidate/current/installed results, complete answer deltas, current and installed
package identities, and frozen runtime/support evidence. Produce a new receipt
that references that immutable evidence and names source-bes-dep-09 explicitly.
Exercise the actual generic validator on the original malformed result, a corrected
partial result, a wrong task and a failed status before seeking the new admission.
The correct result must return False (partial RECORD), never True (ACCEPT).

| Work | Requires success | Independent/completion-only work | Evidence |
|---|---|---|---|
| R0 diagnose/preflight | Intact rejected attempt and unchanged production | Remaining source review stays possible | Actual validator rejects malformed/wrong-task/failed receipts; corrected partial receipt is retainable |
| R1 revision 442 | R0 and cumulative bounds | No new product meaning or source scope | Retain all 17 admissions, add one explicit recovery admission, freeze evidence references |
| R2 corrected submission | R1 and admission 018 | Failed original remains sealed | Validate new task-bearing receipt before sealing, then RECORD/refresh |
| R3 substantive return | R2 or retained failed recovery | Continue original source groups if common authority/evidence remains valid | Remaining-policy review; no second receipt-repair loop |

Keep the same 2960-second, 600-MiB cumulative ceilings and 600-second/160-MiB
continuation limits. Add at most 30 substantive seconds for this recovery; every
prior cost, the 240-second historical conservative allocation, failed wrapper,
rejection and original sealed files remain. The new proposal explicitly extends
only admissions 17 to 18 under the same budget key. No new runtime/storage ceiling
is granted. Freeze forecast includes the full proposal and revision, current
program growth, references and small preflight files. Authority record/projection
commands retain their separate measured ledger and 60-second bound.

The primary criterion is correct attribution of a partial retained result to its
actual task, supported by unchanged complete substantive evidence. Rejecting a
bad receipt tests the controller contract; it does not establish financial truth.
Changed sealed evidence, mismatched answers/imports or exhausted limits stop this
recovery. No authority event is rewritten and no rejected attempt is resubmitted.

Skeptical audit: PASS for one bounded receipt correction. The exact failure is
reproduced by the actual validator contract, the production package is unchanged,
the new receipt is checked before sealing, and success leads back to substantive
source work. Original partial coverage and all legal/transaction refusals remain.
The correction cannot claim the rejected attempt itself was accepted.
