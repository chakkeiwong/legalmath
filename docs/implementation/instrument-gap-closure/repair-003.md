# Missing-calendar report preservation

A final incomplete-input probe supplied a hypothetical event with
`calendar_sha256: null`. The event engine rejected the absent content identity
with `ValueError: SHA-256 content identity required`. That response preserved
the prohibition on an invented calendar, but unnecessarily discarded available
product and bank findings.

The instrument adapter now returns an unknown event schedule/settlement when
the calendar is absent, while still calculating source-dependent product scope
and retaining all fourteen bank obligations. A malformed or corrupted *supplied*
calendar remains an error; absence is distinguished from invalid evidence.
The new missing-calendar case is exercised both directly and in the I3 joined
campaign. No business date is invented and no transaction permission is added.

The focused missing-calendar integration test is the repair reproducer. The
changed method invalidates old acceptance for dependent results, so the final
I0–I4 run refreshes its predecessors. Earlier accepted and failed attempts stay
available. This is an implementation repair, not a change to the legal model or
evidence criteria.
