# Prototype defects found before adoption

The first checkpoint prototype assumed reused successes had fresh wire bindings.
Actual current directories have 36 results but only one wire binding, for the
newly attempted `detail-87`. Reused results have retained provenance. The revised
checker authenticates all 35 successes against the unchanged checkpoint and
requires a current wire binding only for the failed call. It rejects invented
success bindings and a missing failed-call binding.

An actual evidence check then rejected reconstruction from canonical JSON.
Restoring record-column order alone was insufficient: the encounter order of
hash identities also determines their wire aliases. This is an evidence replay
issue. The revised replay retains the real constructor's request order, requires
logical equality with the old request, and requires normal encoding to recreate
the entire old wire binding exactly. No encoding algorithm or historical
evidence is modified.

The first complete production replay also exposed a wrong temporal assumption:
the 35 saved successes are the full current census, not all predecessors of
`detail-87`. The requirement loop continues to saved `detail-88` responses after
that failure. The replay now holds the failed response in place without making
a provider call, checks the later retained successes, and requires the expected
incomplete-account verdict at the end. The only missing dispatch must still be
`detail-87`. The frozen installed replay must independently reproduce this.

These local failures reject the initial diagnostic implementation. They do not
change legal acceptance or establish a product failure beyond the retained
service interruption. The final candidate must pass installed regression and
actual production reconstruction before adoption. Temporary probe errors and
the original failed replay output were inspected; neither is reported as PASS.
