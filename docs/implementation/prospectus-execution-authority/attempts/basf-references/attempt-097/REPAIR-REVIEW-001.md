# Development failure: source and occurrence coordinates

Development001 retained10 failures and120 passes. The source probe is retained
as development/provenance-001.json. No formal stage has run.

Two original copies have raw offsets1:length+1 and assembly offsets0:length.
These are different coordinate systems: definition_roles.project validates the
assembly substring and its complete character map against the raw anchor.
Requiring the numerical offsets to be equal was wrong. The new guard must
require valid integer assembly bounds of the correct length and the exact same
raw source anchor. It must not reinterpret occurrence coordinates as raw ones.
This qualification checks retained copy metadata; the existing normal consumer
and pinned source profiles supply the underlying graph/assembly checks. The
source-only command alone does not establish document authenticity or a new
character-map proof. Offset/length corruption and changed source anchors remain
adverse controls; a legitimate coordinate shift receives a separate fixture.

The frozen request comes from093 after reviewed role projection and its printed
labels are HEADER. Original registered definition specifications still retain
UNKNOWN. The frozen plan's resumption note and the initial audit/test expectation
that093 labels were UNKNOWN are stale. Preserve the frozen plan and request.
Supplement them here: test HEADER preservation for the frozen093 report, test
UNKNOWN preservation separately, and test that both legacy and structural
registered source specifications continue to admit. No role is promoted by this
guard, and no legal-scope authority follows from either label role.

Audit verdict: PASS for this changed repair. Primary criteria, frozen extents,
complete093 comparator, adverse source/extent checks, limits and nonconclusions
are unchanged. Correct the runner's role assertion and use unique development
numbers so retained failures are never overwritten. Freeze this supplementary
review with the methods. A new development test run is justified only after
these changes, not an unchanged retry or weakened source-equality check.

The first launch after this review stopped before running tests because the
development started.json path was still shared. The0.05549-second pre-start
failure is retained separately. Use unique started-NNN.json paths as well as
unique test/log/result paths. This is a local runner naming error; no candidate
evidence was produced and no formal stage started. Re-review: PASS after the
path change; all outputs use exclusive creation and the old start is retained.
