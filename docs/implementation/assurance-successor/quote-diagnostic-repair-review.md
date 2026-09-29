# Exact-quotation diagnostic repair review

Prepare this repair in an isolated /tmp source copy while S8 runs; do not change
its loaded package or evidence identities. The baseline is current check_quotes:
a quote must occur exactly once in its named unit. Preserve that exact predicate.
The engineering question is whether rejected proposals receive the location,
occurrence count and bounded character evidence needed for a targeted repair.

Test ordinary/NBSP differences, embedded nulls, repeated substrings and missing
unit IDs. Each must still reject, with bounded diagnostics; the exact original
quote must pass. Compare acceptance before and after on the same fixtures.
A diagnostic that substitutes text, normalizes a rejected quote into success,
or hides truncation fails acceptance. No model call or source judgment is made
by the staged test. Store its command, XML and proposed patch; merge only after
active package users finish, then run affected current-source and full regression.

The benefit is actionable mechanical feedback, not proof of English entailment
or a guarantee that a later model repair succeeds. Preserve all old failures
and limits; an exhausted question remains exhausted.
