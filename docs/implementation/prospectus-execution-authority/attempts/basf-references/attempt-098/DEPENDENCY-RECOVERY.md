# Corrected prerequisite sequencing

The first issuer-definition extraction was invoked after the finish command
yielded a session, but before that session completed. It failed immediately on
the missing receipt.json. No extraction, interpretation, result or second
network request occurred. This is an agent sequencing mistake, not a source or
parser failure. The independent ordinance-index preparation completed normally.

Bounded recovery review: finish has now completed successfully and its retained
receipt exists. Permit one extraction with that newly available prerequisite;
this is not a retry of an unchanged source request or an altered frozen method.
Wait for actual exit/result of each dependency before dispatching its consumer.
The failure is retained here and receives a conservative5second accounting
charge; include it in the final source accounting addendum. No allowance resets.

The sandbox DNS failure and exact trusted GET are retained separately. The
source request receipt's20seconds is a conservative charge equal to its timeout,
not measured elapsed execution. Preserve this distinction in the final note.
