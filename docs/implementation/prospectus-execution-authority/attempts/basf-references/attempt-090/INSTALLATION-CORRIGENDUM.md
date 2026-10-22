# Installation count correction

The frozen stage delegates installation to the retained residual-coverage
engine. That engine installs every entry in this trial's `TARGETS`, but its
returned explanatory `production_files` count is hardcoded to three. The
purpose-use trial has four targets: `purpose_uses.py`, `purpose_uses_spec.json`,
`service.py`, and `conditional_profiles.py` in the successor package.

The count of three is wrong. The four-entry frozen `installation.json` and
the engine's pre/post-install hash checks determine which files were installed.
This is a reporting defect, not evidence that the fourth file was skipped.
Counts are explanatory only under the reviewed evidence contract. Preserve the
actual stage receipt and frozen methods; correct the shared reporting count
in a later implementation only if that implementation uses this engine.

This correction does not waive source, full-answer, adverse-control or installed
consumer checks. Those checks must still pass before retaining this trial.
