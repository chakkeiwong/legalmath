# BASF source-order reset

Branch `feature/prospectus-evidence-master`; baseline `bada667`.
Plan: `docs/plans/prospectus-basf-source-order-2026-10-08.md`.
The INCEpTION run-020 checkpoint is complete and its evidence is preserved.

The first source diagnostic nominated four rows in the 1,578 body occurrences on
pages 108–133. Original images on pages 111, 120, 121 and 124 were inspected. Page
124 requires reading both whole label/address blocks by cell, so the reviewed
repair comprises five explicit occurrence permutations. The packaged correction
checks exact text, geometry, edition and contiguous occurrence identity before
permuting; it applies no new geometric sorting threshold.

Focused attempt-001 exposed two follow-on issues: a new test counted the repeated
NGN sentence globally although the source has a third instance, and the repaired
Fiscal Agent block now matches the old Canadian deletion regex as well. The
constructor correctly left the ambiguous deletion unresolved. Repair the test to
check the two exact page occurrences and qualify the Canadian rule with the
printed Canadian-agent placeholder. The German fiscal-agent address must remain.
The failure is preserved; neither issue weakens source equality or legal limits.

Skeptical follow-up audit: PASS for these repairs. The comparator is still the
inspected original page. A duplicated template label needs its complete local
context, not a relaxed match count. The test must use page identity, not a global
count. Re-run focused checks before the full adoption verification.

`python3 -m scripts.prospectus_basf_source_order` passed as run-001: 12 focused
tests, five source-reviewed permutations, all 1,578 source occurrences preserved
byte-for-byte, and no unaccounted intervals. Unresolved intervals changed from
1,018 to 1,008 while the 83 retained brackets remain. This is a consequence of
corrected order and bracket boundaries, not ten adjudicated legal decisions.

Pre-verification audit: PASS. The full adoption verification is justified by a
changed constructor consumed by the installed evaluator; the earlier receipts
remain historical. Run `python3 -m scripts.verify_prospectus_adoption`, preserving
new attempts, focused/full tests, installed checks and identical replay. The
optional parser's existing two-page rejection criterion remains unchanged; its
rerun is dependency verification and cannot promote Docling. The passed INCEpTION
server exchange is unaffected and is not rerun. Stop or investigate any corrupt
source, changed comparator, unexpected legal acceptance or failed regression.

Full adoption verification attempt-003 passed: 125 tests, A0 attempt-007,
A1–A6 attempt-005, seven reused receipts on identical replay, and all phases
current. Source-order run-001 and A1 attempt-005 contain the same construction
bytes. The remaining-work plan and adoption result/review/reset now reflect this
continuation. No further code test is justified without another relevant change.

The manuscript correction explains the sorting defect and preserves both the
historical and current interval counts. Its first build failed because this
manuscript does not define `enquote`; ordinary TeX quotation marks repaired it.
The second build passed, but rendered inspection found a single opening line at
the foot of page 60. The paragraph's club-line protection was added before a
third build and final inspection. All build attempts remain recorded separately.

Build-003 passed, and final physical pages 95–98 were inspected and retained in
`rendered-001/`. The monograph has 390 pages, the companion 90, and the document
checker reports 319 citation occurrences. The opening-line defect is repaired;
the coupon derivation and adjacent source/reader limitations remain intact.
See DOCUMENT-REVIEW.md. Human readability and legal acceptance remain pending.
Next substantive work is the source review listed in adoption NEXT-PROGRAM.md;
unchanged server, layout or master-program reruns supply no new missing evidence.
