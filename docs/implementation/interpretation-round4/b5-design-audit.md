# B5 pre-execution audit: local integration versus institution deployment

PASS WITH LIMITS for the local adapter and executable deployment package. Build
on the existing bounded monitor, immutable revisions and generated Java library.
The registry must supply explicit control IDs, root sources, dependencies,
selected scope and fact bindings. A scheduler tick has a finite control limit,
time bound and retry budget. Persist reservation before dispatch; process death
cannot silently replay paid work. Report stale/overdue/source-missing/failed/
exhausted status, retain history and prevent a monitor callback from authorizing
a release. Pending uncertain interpretations cannot replace an active control.

Acceptance is an actual separate Java process loading a generated JAR, evaluating
an explicit snapshot, and repeating after a source revision. Compare its output
with the declared controlled expectations and retained conformance evidence.
Demonstrate unaffected controls stay unchanged and that changed controls produce
successor evidence. Corrupted source/JAR/configuration must veto the update. This
is a local host integration exercise, not an institution deployment.

No institution-owned registry endpoint, service identity, staging host, scheduler
or release-role configuration has been supplied. Those are real external inputs;
the agent cannot invent them. Complete the locally reviewable package and tests
first, then report institution operational acceptance as blocked on those inputs.
The package must require explicit installation/configuration; it must not create
a background service or send messages without authorization. Existing global
model-call limits remain binding across all scheduled invocations.
