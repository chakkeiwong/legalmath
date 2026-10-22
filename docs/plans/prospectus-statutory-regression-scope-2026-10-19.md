# Keep source regression tests scoped to the relation they protect

After timing repair043 is sealed, reproduce the old H38 test against current
v3. Its original whole-spec equality assertion compares every statutory record
to v1 after removing only the H38 correction. This was valid for the original
isolated repair but would reject the intentionally corrected H28 timing fields.
Do not revert those source corrections or mutate the frozen043 method.

Evidence contract: the same H38 baseline fields, eight exact quotes, source
offsets and mutation controls remain protected. Limit the historical comparison
to H38; use a separate H28 baseline comparison that removes only the approved
timing correction. All other H28 fields and source records must remain identical.
This avoids weakening either source test merely to make the suite pass.
Run the combined source/majority suite and preserve the reproduced old failure.
No production source, answer, package or legal conclusion changes.

Skeptical audit PASS for this specific interaction repair. Baselines are immutable
v1 H38 and v2 H28 respectively;current source hashes remain unchanged. Passing
tests establish regression scope,not legal completeness. A production-file
delta,changed source anchor or missing control vetoes the repair. Corrupt sealed
evidence or exhausted resources veto continuation. The candidate failing the
old broad assertion does not invalidate the source corrections.

One bounded diagnostic and one repaired combined suite,each≤60seconds;≤64MiB
including reviewed authority copies. Preserve cumulative0267200s/768MiB bounds
with4MiB reserve,one additional admission only after a fitting forecast. Retain
actual result and refresh master. No network,installation,adviser,client facts,
commit or publication. Continue substantive source applications afterwards.
