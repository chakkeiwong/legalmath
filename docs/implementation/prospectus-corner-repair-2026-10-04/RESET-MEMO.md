# Repair execution reset memo

Branch: feature/prospectus-evidence-master. Original HEAD and dirty method are preserved.

Candidate: docs/implementation/prospectus-corner-repair-2026-10-04/candidate.
Passing evaluation receipts are bound in run-manifest.json. Do not rerun old acquisitions or overwrite old PDFs.

All 3 cancellation and 2 paid-amortisation checks pass; full suite 885 tests passes. 25 declared legal scenarios are engineering checks, not independent legal outcomes. Source and OCR/dependency gaps remain open; see REPORT.md and ACQUISITION-REVIEW.md.

Budget: 187/212 public requests; 25 remain. No broad search repeats or repeated unavailable URLs. Continue acquisition only with a specific new source route.

Before final completion, inspect all addendum pages and record rendered-review.json, then run the verify phase. If code changes, rerun affected evaluation phases; finalisation rejects a changed candidate. Human prose acceptance and independent adjudication remain pending.
