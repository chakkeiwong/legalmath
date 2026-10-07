# Adoption execution reset

Branch: `feature/prospectus-evidence-master`. Starting commit: `5ad615d`.
Plan: `docs/plans/prospectus-adoption-execution-2026-10-07.md`.
The survey and historical repair receipts are preserved unchanged.

The reviewed specification is now being implemented as A0–A6 in the existing
controller. `python3 -m scripts.prospectus_delivery --program adoption run`
dispatches this program; it does not overwrite the historical repair program.

First diagnostic: 34 focused adoption/repair tests passed. A0 attempt-001 failed
when pypdf accessed an AES-encrypted retained PDF without cryptography installed.
This is an environment/reader capability failure, not source corruption. Repair:
use the already installed Poppler `pdfinfo` to verify actual page counts and
retained exact page-number occurrences for printed labels. Never equate PDF
metadata labels with printed labels. Ambiguous/missing labels remain unresolved.
Attempt-001 remains immutable. The next run tests this repair.

Optional CPU-only tools are being installed in a separate /tmp environment under
the bounded tool trial plan. No parser or financial candidate has passed yet.

Second diagnostic: the first financial fixture run found an arithmetic error in
the predeclared long-first-coupon expectation, not in the exact kernel. January
31 to February 29 contributes 29/(2*182), and February 29 to August 31 contributes
1/2. The sum is 211/364, not 105/182. Corrected that expected rational after
showing the addition explicitly; the criterion remains exact equality. The
first focused coupon check reported 1 failed / 15 passed before this correction.

Tool setup completed: Docling 2.60.1, QuantLib 1.38 and dkpro-cassis 0.10.1,
CPU torch 2.9.0. Model revision b5b4bd59ad2b69aab715e9b1f1dfd74394c45fd4
(`docling-layout-old`, Apache-2.0 model card) is hash-bound. Sidecar plus model
occupies 1,977,946,881 bytes, within the 3 GB cap. Docling code is MIT;
dkpro-cassis and the matched INCEpTION 38.0 source are Apache-2.0. The installed
Docling layout implementation, options and RT-DETR wrapper were inspected before
inference. Layout-v2 is a historical-model candidate, not the current default
Heron model. Threshold 0.3 is the upstream convenience setting and is only a
candidate assumption. Four CPU threads, OCR/table/VLM disabled, and offline mode
bound the first two-page trial. No model performance claim has yet been made.

First complete A0–A6 pass executed. The exact financial comparison passed all
nine fractions and six adjusted dates. A3 rejected Docling for 20 of 53 critical
source lines lacking exact maps. Inspection separated adapter errors (word y
ordering changed mixed-font lines; list marker stored outside text) from model
normalization (removed hyphens, including legal compound words). Repair preserves
line order and explicit list markers; it does not silently authorize deletion of
hyphens. Expansion beyond the same two pages remains vetoed. The UIMA worker also
failed on an API keyword (`rangeTypeName` versus `rangeType`); the actual Cassis
0.10.1 signature was inspected and the worker corrected. Both failed outputs are
preserved in A3 attempt-001.

Post-run skeptical review also found inert repair admission names and insufficient
installed-path coverage. The controller now advertises only the admissions used
by the jobs (A4 coupon; A6 facts/review), writes parent-bound phase plans before
dispatch, and A5 installs the current package offline and runs the existing
installed semantic probes. Broad hashes cover all packaged source/resources;
Python capabilities still do not prove native-process confinement. This is a
repair of the execution harness, not a relaxation of acceptance criteria.

Continuation audit before final verification: PASS for the bounded engineering
sequence, with all prior receipts treated as historical until rerun. Rechecked
the finite-enumeration comparator, retained source bytes, exact coupon criteria,
two-page layout stop, and offline CPU environment. Test counts and interval counts
remain explanatory; a rejected layout candidate does not block the independent
coupon or recovery phases. The next tests cover the last field/instrument guards,
missing-file replacement, interrupted snapshot publication, and changed package
bytes under an unchanged version. Whole-sidecar hashing retains broad invalidation
and will be checked against the existing 1800-second phase limit. No new download,
cohort expansion, financial convention, legal reading or human identity is assumed.

Final-verification attempt-001 ran all seven phases, but then exposed a CLI
namespace leak: `--program adoption check` configured the adoption DAG before
loading the package-wide tests. Three existing P0/P4 recovery/admission tests
therefore failed, although the same 115-test suite passed with the default check
command. Repair: the check command now starts the suite without selecting a
controller program; phase/run/status/repair still select their requested program.
This is a harness defect, not a failed financial or legal candidate. The failed
verification and its successful phase receipts remain preserved. Rerun the three
failed checks through the exact adoption CLI before the full verification.

Final verification attempt-002 passed: all A0–A6 phases executed, 115 regression
tests passed, identical replay reused seven phases, and status marked every phase
current. Latest A0 is attempt-006; A1–A6 are attempt-004. Execution took 100.33s,
replay 37.34s. Sidecar byte hashing remained inside the phase budget. Actual XMI
group/relation checks and all nine QuantLib fractions/six dates passed. Docling
remains rejected for 14/53 critical lines without full exact maps; release remains
blocked. RESULT.md, REVIEW.md and NEXT-PROGRAM.md distinguish those decisions.

The manuscript now includes the actual adoption findings and the long-first
coupon derivation. The unchanged historical narrative remains intact. Snapshots
are locally preserved and reconstructed via snapshot-manifest.json; large
products use the existing lossless checkpoint tool with `--campaign adoption`.
Do not edit immutable attempts or rerun the historical repair verifier to refresh
this campaign. Use `python3 -m scripts.verify_prospectus_adoption`.

The separate INCEpTION integration continuation now passes as `run-020`, with
twelve exact packet exports, two persisted browser label edits, two empty curation
exports and four cross-account denials. The server has stopped; offline evidence
verification and 18 focused tests pass. See `../prospectus-inception/RESULT.md`
and its reset memo for the actual commands, failed attempts and remaining limits.
RESULT.md, REVIEW.md and NEXT-PROGRAM.md now distinguish this later server evidence
from the earlier A3 Cassis-only receipt. New annotation authoring and real reader
authentication remain open alongside source-complete terms and faithful meaning.
The historical A0–A6 attempts, snapshots and generated state are preserved.

The next source review found that top-edge sorting moved bold fragments ahead of
preceding prose and interleaved two page-124 address blocks. Five original-image
reviewed permutations now bind exact unit text, edition, geometry and order; the
Canadian deletion rule distinguishes its full placeholder from the German agent
label. All 1,578 body occurrences retain their exact text. See
`../prospectus-basf-source-order/RESULT.md` and its reset memo for the failed first
tests, corrected implementation and source images. A1's current unresolved count
is 1,008 with 83 brackets. This repairs source order, not legal meaning.

Adoption verification attempt-003 passed all 125 regression tests, all seven
phases, seven-phase identical replay and current-state verification. Current
receipts are A0 attempt-007 and A1–A6 attempt-005. Execution took 108.93 seconds,
regression 9.28, replay 35.43 and status 5.29. Docling remains rejected for 14/53
critical lines, and legal acceptance remains blocked. Historical receipts and the
INCEpTION run-020 are unchanged; generated state and next-phase records now refer
to the newly tested constructor. The existing 250 snapshot reconstruction records
still cover all snapshots, with no stale retained reconstruction source.
