# Review repair: execute the v2 follow-up requests

The initial N1 implementation validates and reconciles scoped judgments, but its
repair result is only an instruction to a caller. That is insufficient to
demonstrate the user's required automatic processing after a discrepancy. The
local follow-up route must be executable before treating this interface as an
operational assurance path. This review extends the existing local N1 work; it
does not authorize any additional live call or change the locked main plan.

Build an opt-in v2 investigation route beside the existing v1 route. Bind packet,
claims, candidates, exact typed questions, required pairs, route settings and
budgets in an immutable EvidenceJournal. Use small exact batches. Obtain two
initial perspectives without exposing one response to the other. Each response
is stored before validation. A malformed response consumes an attempt and
receives an explicit schema/reference repair diagnostic. Valid disagreements
receive a follow-up request carrying the retained disputes. Never discard a
proposal or use majority vote. Three rounds by default, at most six; budget and
deadline persist through resume. A transport/resource failure opens a persistent
stop condition; no hidden transport retry, no reset on resume.

Tests use local scripted providers and are engineering fixtures only. Required
outcomes: disagreement executes another call; all exact pairs survive; maximum
rounds preserve unresolved proposals; missing pairs trigger validation repair;
the first transport failure prevents subsequent dispatch even on resume; changed
question/source/settings invalidate the run; failed and interrupted actions are
retained; resumed accepted results cause no new invocation. A live provider must
not run through this route without a separately reviewed integration to the
shared numerical allowance. The local route will explicitly reject live
providers for this round, rather than pretend its local action cap authorizes
paid/live use.

Skeptical audit: PASS for an offline executable path under these conditions.
Fewer unresolved labels is not a promotion criterion. Source support remains a
proposed judgment, and repeated local fixture values do not demonstrate legal
accuracy or statistical independence. The original full regression remains
intact; after the controller change, invalidate and rerun the dependent phases
and full regression under the same master and the same per-phase attempt cap.
