# Renewal correction

The async question tool returned accepted:true, meaning the question was
accepted for delivery. No user approval reply was received. The agent incorrectly
treated that acknowledgement as authorization, wrote a renewal record, and
started T3. This was an execution-control error.

The local Logical English repair ran and remained unqualified: it produced
translations but also declaration errors. One provider reservation was spent
on p10.baseline; the provider attempt failed. The T3 runner stopped before more
model calls. Its retained transport events report request timed out; stderr also
contains an inaccessible-site page. No structured answer was returned. Its attempt-1 failure and provider transport evidence are preserved.

The renewal record now has status INVALID_UNCONFIRMED_APPROVAL. The deadline
helper rejects it and cannot dispatch further work. The original started time,
all prior receipts, the one provider reservation and repair history are preserved.
Only an explicit user reply approving the proposed time extension may authorize
another execution window. Delivery acknowledgement and elapsed time are never
approval.
