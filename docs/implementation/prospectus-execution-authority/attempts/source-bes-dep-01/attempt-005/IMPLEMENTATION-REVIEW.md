# Pre-run implementation review

The product's ordinary digest and the authority's retained profile digest use
different JSON encodings. The supplied profile was frozen using compact,
sorted UTF-8 JSON. `statement_cells.profile_digest` explicitly reproduces that
encoding; ordinary P1–P5 identities still use the existing product digest.
This mismatch was corrected by code inspection before any validation start.

Validate the source reading before assembly in P2 so rehashed changed source
text/geometry is refused for the specific source-reading mismatch. Recompute
it again at P3 and final consumption. Product hashes alone cannot establish
that the supplied optional evidence survived the pipeline. Test missing,
changed and unsupplied data after re-sealing all phase-parent hashes.

The existing PDF layout tests would invoke native extraction. The targeted
regression command excludes the two PDF layout cases; all other selected
report, original statement-scope and consumer controls remain selected.
Subprocess creation is disabled for every validation command. This is a
documented scope limit, not evidence that native layout tests passed.
