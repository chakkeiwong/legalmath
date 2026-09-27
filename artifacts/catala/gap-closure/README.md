# Accepted Catala gap-closure evidence

Interpretation, limitations and decisions are in
[results.md](../../../docs/implementation/catala/gap-closure/results.md).

- `semantics/conformance.json` identifies the accepted executed conformance run.
- `study/results.json` contains the original frozen three-arm conversion study.
- `schema-repair-probe/result.json` records the separate exposed repair probe.
- `source-review/` preserves the original source packet; `source-review-successor/`
  contains the explicitly revised context and factual meaning. Both await legal
  adjudication and are ineligible as heldout sources.
- `reviewer-study/current.json` identifies matched v5. Only per-participant files
  should be shown to study participants; owner keys and builds reveal defects.
- `validation.json` maps all 725 collected tests to passing runs and retains the
  initial archive failures as well as their successful repair.
- `final-integrity.json` records build, packet and code-archive integrity checks.
- `invalidated-drafts.json` inventories excluded drafts, retained locally in the
  ignored `drafts/` directory.

Original compiler output, tool logs and the compiler patch retain their exact
bytes, including generated whitespace. Do not reformat committed evidence to
silence a whitespace check: that would change source or verification hashes.
Whitespace checks on maintained source, scripts, tests and documentation pass.
