# Shared-resolver compatibility check

The final diff review identified one remaining regression risk: the changed
source-response resolver is also used by the existing executable-reference and
candidate-response profiles. The 193 recorded checks do not cover all of those
call paths. Before accepting the local change, run their existing focused tests
on the same unchanged source. This is the last compatibility check within the
original attempt, not a new capacity campaign or model run.

Exact command: `.venv/bin/python -m pytest -q
tests/assurance/test_continuation_references.py
tests/assurance/test_executable_references.py
tests/assurance/test_executable_references_v2.py
tests/assurance/test_candidate_response_product.py`.

Expected evidence is preserved legacy identity, source quotation, unavailable
candidate, response-schema and restart behavior. A failure blocks local
acceptance and requires inspection; a pass establishes neither actual-response
qualification nor legal validity. Tests use existing scripted providers and
native CPU tools, with no live dispatch. Source must remain stable throughout.
