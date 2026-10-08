# INCEpTION integration reset memo

Baseline: `bada667759a7d9f87ffc01235ff3a012601f5b75`. The reviewed plan is
`docs/plans/prospectus-inception-integration-2026-10-07.md`.

The official 38.0 JAR matches the published SHA256. Main/launcher classes target
Java 17 despite the build manifest naming Java 21; the retained Temurin 17 runtime
is selected explicitly. Official API, schema and curation source files are retained
under `sources/` with the release and runtime identities in `toolchain.json`.

The first startup probe exposed an invalid readiness test: INCEpTION serves an
HTTP 200 startup page before the API is ready. The probe consequently tried to
parse that HTML as a project response. `probe-001` preserves the failure; readiness
now requires the authenticated JSON project-list shape, and application startup
failure is checked separately. This is a harness repair, not platform acceptance.

`probe-002` reached a running Java 17 server but could not authenticate: the
server's inspected password encoder accepts BCrypt and legacy SHA256, not the
proposed noop encoding. The repaired driver creates an encoded BCrypt password
using the existing system libcrypt, keeps credentials in the ignored local
runtime directory, and records no credentials in evidence. It also explicitly
selects the application Python rather than inheriting the shell's TensorFlow
environment. The failed probe and its 300-second startup timeout are retained.

`probe-003` authenticated and created a real project. Its export request used
`/export` rather than the release's `/export.zip` constant; the corrected endpoint
is taken from `Controller_ImplBase.java`. This changed driver justifies a new
probe under the per-unchanged-method attempt bound.

`probe-004` passed authenticated project creation/export. `run-001` then exposed
an installed-package/source mismatch: the application environment's installed
package predates the successor module. The driver now uses this worktree's source
explicitly, as do the existing adoption workers. Twelve focused Cassis fidelity
tests passed, including lost group pieces/links, altered source hashes/text and
changed semantic endpoints. These checks are separate from the server trial.

`run-002` reached the real schema and annotation APIs. The platform rejected the
upload for missing CASMetadata, relation offsets that followed the governor rather
than the target, and whitespace at display-span boundaries. Repair: follow the
official internal schema for a newly imported CAS (`lastChangedOnDisk=-1`), follow
the target for relation display offsets, and retain exact original UTF-16 source
offsets in explicit `sourceBegin/sourceEnd` features while validating trimmed UI
spans against them. This preserves the complete original quotes (including LF and
trailing spaces) and does not disable platform checks or relax source equality.
The distinction between a display selection and the original cited span is now
explicit and covered by two additional regressions.

After the Windows reload, all evidence and edits were present and no trial server
remained running. `run-003` reached annotation persistence but supplied the wrong
API state spelling. The pinned `AnnotationDocumentStateUtils.java` requires
`IN-PROGRESS`; the driver now uses that exact value. The failure is preserved;
the next attempt continues exchange validation under the same source criteria.

`run-004` preserved all three original Unicode exports exactly. The attempted
REST replacement failed the server's concurrency check: newly encoded CAS
metadata had timestamp -1, but the existing annotation had a real storage
timestamp. Inspection confirms normal XMI exports remove CASMetadata and the
API's RAnnotation timestamp has only second precision. The reviewed repair uses
the browser editor for updates and REST for initial import/export. No timestamp
is invented and no concurrency protection is disabled. Both packets must pass
the browser edit and subsequent exact export comparison before acceptance.

`run-005` found stale official API documentation: the permission endpoint lists
USER/ADMIN but calls `PermissionLevel.valueOf`, whose actual enum is
ANNOTATOR/MANAGER (USER/ADMIN are retained JSON serialization aliases). The
driver now uses the runtime enum and explicitly grants each synthetic reader
only ANNOTATOR. This is a configuration repair, not a permission-isolation pass.

`run-006` preserved both packets across all six original exports and confirmed
the two reader role records contain only ANNOTATOR. Browser authentication
worked, but the document URL opened a chooser; its screenshot is not an editor
pass. The next diagnostic explicitly selects the document before inspecting the
rendered annotation controls. No edit has yet been accepted.

`run-007` captured the chooser while its asynchronous document load was still
pending: `networkidle` alone returned before the Wicket callback started. The
browser now waits for the actual editor and rendered span controls. This is a
browser synchronization repair; the previous snapshot is retained as diagnostic.

`run-008` rendered the actual spans and semantic/discontinuity arcs. The next
trial changes the label in each packet through the browser, reloads it, and
checks all three accounts' exported packets. Synthetic reader imports are marked
COMPLETE solely to make them eligible for the curation test; this is not a claim
of completed human review. Opening integrated curation must yield a source-text
CAS with zero LegalEvidence/LegalRelation annotations despite completed inputs.

`run-009` reached rendered annotations, but clicking the SVG group text did not
select a span. The editor's hit target is the polygon carrying `data-span-id`.
The browser action now clicks inside that polygon away from the overlaid label;
export comparisons remain the pass criterion.

`run-010` stopped before annotation work on an upstream wall-clock error:
`ProjectExportServiceImpl.importProject` passes
`currentTimeMillis() - start` to `formatDurationWords`, which rejected a negative
duration. The transaction failed; its database is not reused. A second isolated
attempt of the same method is within the three-attempt bound. No server binary,
system clock or concurrency setting is altered, and a recurrence remains visible.

`run-011` had no clock recurrence. Pointer hover exposed draggable span handles
that intercepted the polygon click. The repaired browser uses the annotation
sidebar's explicit Select button, inspected in the rendered DOM, to reach the
same feature editor. The driver now also seals attempt files, binds codec/input/
runtime bytes, checks reader permissions, restricts redirects/browser resources
to localhost, and implements an offline verifier. These are harness changes;
acceptance still requires an actual persisted edit and exact exported packets.

`run-012` selected the correct annotation. INCEpTION's rendered string-feature
labels lack a `for` association, so the accessible-label selector could not find
the visible input. The driver now selects the input in the row whose literal
feature label is `label`; no feature ID or positional index is guessed.

`run-013` persisted/reloaded the Unicode edit and changed the BASF label. The
BASF annotation renders in two fragments, so a strict single-element visibility
assertion was wrong. Wait for a visible fragment, then continue to the exact CAS
comparison, which remains responsible for detecting duplicated or lost evidence.

`run-014` passed both browser edits/reloads, twelve exact original/edited/unchanged
reader export comparisons, and two empty curation exports after opening curation.
Offline verification attempt-001 passed. Its account check established configured
roles, not a runtime denial. The final reviewed extension tests separate synthetic
guest sessions against peer/admin annotations; guest display names cannot prove
identity and are expressly forbidden for real independent acceptance. It also
binds the supplementary official sources and rechecks runtime bytes at completion.

`run-015` repeated the edit/curation checks, but the guest page failed because
sharing is disabled by default in 38.0. `InviteServiceAutoConfiguration` requires
`sharing.invites.enabled=true`; guest entry separately requires
`sharing.invites.guests-enabled=true`. Enable both only in the isolated synthetic
trial. The error is preserved and is not interpreted as a successful access denial.

`run-016` made the sharing importer active and exposed its required database
field: invitation expiration cannot be null. The synthetic invitation now has
a one-hour expiry, longer than the bounded workflow. Its exact exported value
is retained; it is not a source/document date or a legal fact.

`run-017` rejected the invite because the maximum annotator count includes the
administrator as well as both synthetic readers, and the server checks that
threshold even for an existing reader. The finite limit is now four. The
retained empty-project export is also promoted to a hash-bound template with
provenance so a fresh `probe` no longer depends on attempt number 004. JSON
checkpoints are atomic and individual HTTP timeouts respect the phase deadline.

`run-018` logged into Reader A and displayed the original annotation. The denial
assertion incorrectly expected the administrator's detailed error: inspected
`AnnotationPageBase.failWithDocumentNotFound` deliberately gives ordinary readers
the generic "Requested document does not exist or you have no permissions to
access it." Use the mounted document URL fragment and assert that exact generic denial
in the returned page. It must arise for a document already shown accessible to
the same session; a missing document alone cannot satisfy the intended test.

`run-019` still reopened the chooser. Source inspection identifies the actual
document/owner route as `annotate#!d=...&u=...`; the previous request used query
parameters. The next diagnostic uses that fragment and still requires the exact
access-denial response after the same reader has loaded the existing document.
This is a routing hypothesis, not yet evidence of authorization. Skeptical audit
PASS for the diagnostic: unchanged source/comparator, bounded runtime, no weaker
acceptance criterion and no inference of human identity from guest login.

`run-020` passed the complete bounded server exchange. REST imported and exported
the Unicode and BASF packets for the administrator and both synthetic readers;
browser edits to both packets persisted after reload; all twelve original/edited/
unchanged packet comparisons matched exactly; and integrated curation produced
empty evidence exports with automatic merge disabled. The four cross-account
requests now use the documented Wicket fragment route and were denied with the
server's generic permission message after each reader had loaded its own document.
The sealed result, access checks and stopped-server record are retained under
`run-020/`. Offline verification reports twelve exact packet checks and keeps
independence and legal acceptance pending. The server trial therefore closes the
bounded exchange-integration obligation; it does not establish human identity,
independent first readings, legal correctness, source completeness or production
readiness.

The resumed final checkpoint is complete. Offline `verification/attempt-004.json`
passed all twelve exact comparisons against the unchanged `run-020` manifest.
The 18 focused tests passed again; output is retained in
`validation/resume-001/focused-tests.log`. The earlier 115-test adoption regression
and successful document build remain current for this checkpoint. Final physical
monograph pages 95–97 were inspected and preserved under
`document-review/rendered-001/`; DOCUMENT-REVIEW.md records the rendering result
and final hashes without rewriting the historical build manifest. The log-ignore
exception now follows the generic documentation-log rule, preserving 150 trial
logs. No driver, codec, verifier, trial plan or historical attempt changed during
this resumed verification. Human readability and legal acceptance remain pending.
Continue with source reconstruction under the adoption NEXT-PROGRAM.md; another
unchanged server trial would supply no new evidence.
