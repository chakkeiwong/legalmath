# Source-order manuscript correction

The bounded unit is the construction paragraph in
`docs/monograph/chapters/02f-prospectus-adoption.tex`, within the prospectus tool
discussion. The target reader is a researcher or legal-service developer who
needs to distinguish preserving every extracted character from preserving the
printed clause's order. The baseline chapter and PDF are copied outside the
source tree and bound in manuscript-baseline.json. The adjacent tool findings,
coupon derivation and its assumptions, independent-reader requirements and legal
acceptance limits remain protected.

The correction explains the observed font-box sorting failure with the printed
NGN instruction, states the five reviewed permutations, and updates the current
interval count while preserving the historical count. It must not suggest that
these changes provide a complete reading-order method or ten new legal decisions.
The two-page Docling rejection remains distinct from this repair of the retained
BASF constructor. Exact source images and the corrected construction, not the
test count, support the new account.

Reader checks before editing:

- How can every character survive while a contractual sentence is wrong?
- Which source evidence justifies the changed order, and how narrowly does it apply?
- Why does the new unresolved-interval count still leave the contract incomplete?

Skeptical document audit: PASS for this paragraph-level correction. No equation,
citation or legal premise is removed. Build with the repository's
`python3 scripts/build_reader_facing_monograph.py`, then inspect the changed
rendered pages and adjacent transition. A build pass alone cannot establish
readability. Human readability and legal acceptance remain pending.

## Build and final rendered inspection

Build-001 failed on an undefined quotation macro. Ordinary TeX quotation marks
fixed the build without a new package. Build-002 passed, but its rendering left
one opening line of the new paragraph alone at the foot of printed page 60.
Local club-line protection corrected that defect. Build-003 passed: monograph
390 pages, companion 90, document checker PASS with 319 citation occurrences.
The logs and hashes for all three attempts are retained separately.

I inspected the final physical pages 95–98 (printed 60–63), including the
transition into the following discussion. `rendered-001/manifest.json` binds
the final PDF, chapter, build record and four inspected images. The historical
build record's pending visual field is superseded by this separate inspection.
The new explanation starts intact on page 61. The source wording, old and current
interval counts, and scope limitation are legible. The annotation discussion
continues across pages 61–62 without clipping; the coupon premises, full fraction
derivation and interpretation remain together on page 62. No further correction
was required in this slice.

| Ledger | Implementer finding |
|---|---|
| Reader comprehension | The text explains how top-edge sorting changes word order, why original images justify five local corrections, and why the remaining intervals still require source review. The three reader questions can be answered from the rendered slice. Human acceptance is pending. |
| Mathematical integrity | No equation or coupon assumption changed relative to the protected baseline; the displayed arithmetic remains intact. No new financial validation is inferred from this inspection. |
| Source fidelity | The correction distinguishes exact occurrence preservation, observed row/cell order, unresolved legal meaning and independent review. It retains the rejected Docling decision and the synthetic-reader limits. |
| Typography | The isolated opening line was repaired; no clipping, displaced heading or malformed quotation/equation was observed on the four final pages. |

Baseline comparison found no removed equation, citation or substantive
qualification. The former current interval count is now explicitly historical,
and the added paragraph supplies the observed failure, correction and current
count. This focused implementer inspection does not certify whole-document
readability or independent legal acceptance.
