# Full-regression finding and repair

C1 attempt-001 failed one of 833 tests: the reader treated an optional redemption
benchmark's ISIN between monetary fields as if it identified the note being
repaid. The new whole-span series check was too broad. This is an implementation
failure in the candidate repair, not evidence against the source interpretation.

The fix binds numeric witnesses to their own quoted fields and any explicit
statement assigning those fields to a series. An unrelated benchmark reference
does not identify the selected note. The original benchmark counterexample and
the new explicit-other-series counterexample must both pass; the focused command
now includes the existing semantic-repair suite before repeating full replay.

Controller plan review also found an unnecessary dependency: source recovery
should not wait on an unrelated reader review. Dependencies are now explicit:
C1 depends on C0, C2 on C1, C3 on C0, and delivery on C1/C2/C3. `run` continues
ready independent phases after a candidate failure, while preserving the failure
and stopping its dependent promotion. Source responses alone still discharge no
legal requirement.
