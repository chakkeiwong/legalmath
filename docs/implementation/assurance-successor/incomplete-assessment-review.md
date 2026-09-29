# Preserve study failure while completing its assessment

The reviewed evidence contract makes an exhausted required resource a veto for
the affected live action. It does not justify skipping case evaluation,
uncertainty reporting, document production, or current engineering regression.
The original sequential controller incorrectly requires an S8 pass for all
these activities. This is a controller defect, not evidence against the
interpretation methods.

Add a fixed `assess S9|S10|S11` mode. It may operate only on a hash-verified,
terminal failed S8 receipt with all frozen tasks accounted for and an explicitly
recorded resource limit. All other predecessors must pass. The mode must retain
S8's failed status and bind the assessment to that exact failed attempt. It
cannot authorize a new study, add model allowance, reset attempts, forgive an
integrity failure, or declare the overall campaign complete. S9 uses the
existing global grant for any case-mapping calls; missing results remain gaps.

The final report must distinguish completed assessment and engineering checks
from incomplete study execution. A subsequent S8 attempt invalidates these
assessments. Required tests reject missing/tampered receipts, a failed task
denominator, a non-resource implementation error and assessment of an earlier
study attempt. Ordinary `phase` mode remains strict. This amendment changes
reporting availability, not any acceptance or promotion criterion.
