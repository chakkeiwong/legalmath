# Round-15 skeptical review and repairs before live dispatch

The accepted execution contract is `docs/plans/assurance-round15-execution.md`.
The first draft did not survive review. Its passing four local tests did not
establish the desired contract; several mirrored a wrong implementation.

The review found and repaired these defects:

* The shared allowance had already advanced beyond the round-14 summary. The
  final binding uses the full 487-call prefix and the existing 500-call user
  maximum. The origin of the 21 appends is not established here and their
  results receive no evidentiary credit. They remain consumed.
* Excluding 48 rows because of old CONTEXT flags would recreate the routing
  defect. All 231 executable restored pairs are now scheduled. A copied claim's
  CONTROL field is only a scheduling flag; its source text and historical
  classification remain preserved, and no substantive relevance is asserted.
* Global batching could cross two source packets. Each batch now has exactly
  one packet and explicit pair IDs.
* Re-running the old round-14 delivery writer would reject an appended allowance
  and could modify historical delivery files. The new audit verifies recorded
  delivery hashes and accepted immutable phase receipts without rewriting them.
* The master originally could not resume after consuming a call, did not bind
  implementation hashes, and always reported completion. It now verifies the
  allowance prefix, binds current code and dependencies, reuses immutable
  completed phases, and reports pending live work explicitly.
* The draft repair command merely produced advice. It now resumes the same
  bounded execution journal. Schema repairs and one bounded batch split execute
  in the live phase. Failed phase attempts remain in their journal.
* A cached-provider transport retry could consume a hidden second call. The
  round-15 wrapper performs one counted transport attempt. The first transport
  failure stops further live dispatch.
* Draft authority/PDF work only recreated queues. The implementation now fetches
  two exact public PDFs, creates page-linked review packets, and restricts
  automatic PDF resolution to a unique exact footer already located on the
  retained raster. Fault tests must reject substantive numbers and ambiguity.
* Threshold mutations alone did not address fractional input or common-mode
  classification errors. The new exact-ratio representation has a checked
  algebraic relation and fractional boundary cases; tokenised-asset input
  mistakes and conflicting evidence remain separate tests.

Existing Python/Java preflight checks passed before these additional repairs.
They are superseded for acceptance by the focused tests of the final code and
the recorded execution. No live request was made by the rejected draft.

Verdict: execute the reviewed bounded program after final focused tests. A
model finding, compiling child, exact arithmetic, or successful retrieval cannot
close an English-meaning question. Source concerns require the recorded next
investigation; absent authority or independent references remain explicit.
