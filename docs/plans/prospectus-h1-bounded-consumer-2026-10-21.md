# Complete Note 27 with bounded, resumable consumer verification

The sole authority is program.json. This changed continuation of source-bes-dep-05
addresses attempt 043's interrupted ordinary worker. Its exit was 143 with no
receipt or surviving worker; the cause is unknown. Source, gzip persistence,
production registration and 41 tests passed. Preserve 043 and failed 042; use
successful 041 as the answer comparator. The candidate registry already contains
the exact Note 27 profile, so reuse and verify it without rewriting production.

The question is whether the unchanged Note 27 reading reaches the actual ordinary
and installed consumers and preserves the complete 041 answer and historical
composition. Primary criteria are actual consumer results, exact prior-answer and
phase-payload comparisons, all original source/adverse checks, source reading
identity, full historical composition identity and installed import/answer
agreement. No subprocess success or partial receipt substitutes for these checks.
Any discrepancy, accepted corrupted product, missing stage, wrong import, altered
source, source interpretation or prior answer vetoes the candidate. Invalid
authority, corrupt common evidence, or exhausted reservation vetoes continuation.
An interruption blocks that branch, retains its observed evidence and requires a
changed reviewed recovery; independent coverage still runs.

Split the former monolithic consumer into separately dispatched steps: baseline
ordinary answer, candidate ordinary answer, comparison, composition and negatives;
package build/install; installed candidate answer, comparison/composition and
installed negatives. Each step writes a durable result, command timing and hashes.
Record both the supervising stage and child process identities before waiting.
After interruption inspect both identities and any completed receipt; a started
stage cannot be redispatched or sealed while its outcome is unresolved.
Never rerun a completed step, and never silently adopt incomplete output. Preserve
the unchanged tests/source results from 043, whose source bytes are authenticated.
No additional test-suite replay is needed because production is unchanged.

Trace inspection also found repeated serialization of all accumulated answers in
each historical composition comparison. The complete baseline answer is about
91 MB decoded; repeating it across growing compositions multiplies allocations.
Compute the identical sorted JSON hash from cached top-level encoded values and
changed answer fields. Prove byte-for-byte agreement with the existing encoder on
discriminating nested/Unicode/number examples and verify every retained 016/017
and successful 021–041 composition hash. This is an execution repair only; it must
not substitute a different hash, omit fields or weaken earlier comparisons.
Read/build/consume still use the actual service and exact original products.

Defaults audit: successful 041, immutable original graph/PDF and 043's source
reading/registry are authenticated baselines. Splitting can hide state or import
dependencies, so bind all prerequisite files and verify the actual module origins
and complete comparison in each environment. Full answers/products need larger
retained files than the old 2 MiB auxiliary-file cap: use deterministic gzip with
a separate reviewed 32 MiB cap for these named files only and keep 2 MiB for
receipts. Reserve 256 MiB total including 4 MiB failure reserve; reject growth
before each step. Worker bound 120 seconds, package command bound 60 seconds,
total 1,200 seconds plus 60 control seconds. Reserve each command's full time
bound before dispatch. Each worker writes progress markers
around build, consume, compare and save. Timeout/termination is a failure, not a
permission to retry unchanged. Earlier interrupted 360 seconds are conservative
accounting, not a measured runtime claim.

|Item|Needs success|Completion only / independent|Recovery|Limit|
|---|---|---|---|---|
|A preserve 043, inspect execution and hash method|Recorded originals|043 coverage/seal/record|Revise unfrozen design|One changed preparation|
|B bounded helper/serializer preflight and final review|A|No production writes|Correct unfrozen helper|One preflight|
|C revise/admit and authenticate reused source/tests/registry|B and refreshed 043|None|Retain mismatch|One revision/adoption|
|D ordinary baseline and candidate|C|Independent of each other's success; serialized resources|Retain failure|One each|
|E compare, composition, ordinary source/consumer negatives|Both D success|None|Retain mismatch|One each|
|F package and installed candidate/compare/composition/negatives|E and each required predecessor|None|Retain failure|One each|
|G coverage|C|Independent of D–F success|Retain actual coverage|One|
|H seal, record, refresh, continue policies|None|D–G outcomes|Changed reviewed recovery|One|

Proposed revision 407/attempt 044 retains all 43 admissions, original obligations
and cumulative costs. Policy drafts are shifted to subsequent successful baseline
and cannot use failed 043. No network, OCR, model, GPU or subagent work. Each tool
call yields after one second, output is bounded, and the same session is polled.
Authority and shared accounting are serialized. No change to host allow lists or
external approval is needed for these authorized local repairs.

Pre-mortem: splitting could merely shift an oversized operation into another step,
or a new hash helper could verify a different representation. Inspect the largest
individual operations and use timed progress markers plus explicit bounds. Test
exact hash equivalence before admission, then require all retained full
composition hashes during the admitted composition stages. The
termination cause stays unknown unless direct evidence appears. No package
unsuitability, automatic extraction, financial truth, legal acceptance or build
completion follows from this repair. A failed verifier is a local implementation
or execution finding, not a rejection of the substantive direction.

Draft skeptical audit: PASS for helper preparation and small equivalence checks.
It preserves the baseline and acceptance criteria, avoids repeated monolithic
work, records remaining uncertainty and explicit resource stops, and distinguishes
branch failures from global vetoes. Final audit must inspect the helper and
preflight results before admission.

Recovery audit, 21 October: authority check passed at revision 406; resume
reported no worker and admit correctly refused an unchanged completed attempt.
The draft had two redundant registry-control calls, ambiguous wording about the
41 tests, omitted the retained explanatory arithmetic from its final receipt,
and did not record child identities. These are corrected before freezing.
Installed registry refusals must now match ordinary refusals explicitly. Resource
checks reserve time before dispatch, and finalization refuses an unresolved
started stage. Original receipts, production, and acceptance criteria are intact.

Final skeptical review: PASS to prepare and admit this finite repair. The exact
command `.venv/bin/python -B -m scripts.prospectus_h1_bounded_consumer equivalence`
passed four direct and four nested byte-identity cases, including Unicode,
escaping, negative zero, and large integers. Inspection confirms identical
separators, ordering and encoder use. This smoke check establishes only those
cases; every actual historical answer/composition must still match its retained
hash. Successful 041 is the baseline, failed 043 supplies authenticated source
and tests only, and current production must match those tested bytes. No
unexamined numerical default or relaxed acceptance criterion is introduced.
Timeouts and size limits are reviewed execution hypotheses, not performance
claims. The independent coverage step continues after candidate failure.
