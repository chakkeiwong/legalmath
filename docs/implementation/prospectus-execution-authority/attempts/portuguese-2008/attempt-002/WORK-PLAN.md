# Pre-run context review and commands

The bound plan and dossier govern this admitted continuation. Both original
source images were inspected again: p248 retains the NCA definition/exception;
p251 separates the historical related-party event, auditors' date and signed
committee report date. Whole original readings and image hashes will be frozen.

Forty-eight tests passed initially. Self-review found the signatory regex's
singular inflection was incomplete; corrected it before the source trial and
added a single-auditor case. All 49 tests then passed (context-tests-002.xml).
The original 48-test report remains. No source-target score has been observed
under the new context profile and no thresholds were tuned after that score.

Skeptical implementation audit: production receives a full P2 reading and bound
supplied facts, not document IDs or target positions. It preserves the supplied
facts, exposes exact full-context evidence, and withholds conditional report-use
support if the selected profile cannot justify date/definition context. A
nontriggered NCA check is labelled only as nontriggered. V1 remains unchanged.
Unsupported language/closing form, ambiguous signatures or unsupported exception
definitions stay unresolved in v2. These rules remain finite development
constraints; they do not independently verify general legal or accounting truth.

The actual current v1 output will be compared to the retained pre-edit admission
method for all three input variants. Reuse only the unchanged historical P1 graph;
verify its complete original output manifest and original PDF hash. Recompute P2
and require the exact original full readings. Then run six separate bounded
current P3/final consumers: positive, wrong event date, and omitted exception,
each through v1 and v2. Shared P1/P2 bytes are retained once; each route retains
its own scope, actual P3/P4/P5 products, answer and manifest. Product hashes may
differ when interpretation inputs differ; compare the intended legal payloads
and bind every actual consumption rather than require false hash equality.

Each invocation uses `timeout 120 .venv/bin/python` followed by this attempt's
`run_context.py --case <prepare|positive-v1|positive-v2|wrong-date-v1|wrong-date-v2|omitted-exception-v1|omitted-exception-v2>`.
The script pins this worktree's src and hides GPUs before imports. Use one-second
yields and wait for each session before the next dependent case. Freeze product
methods during prepare. Keep the 60 MB compressed-evidence bound, all failures,
original admission lineage and source/external unknowns.

Actual final focused-test command:

```text
timeout 120 .venv/bin/python -c 'import os,sys; os.environ["CUDA_VISIBLE_DEVICES"]="-1"; sys.path[:0]=["src","."]; import pytest; raise SystemExit(pytest.main(["-q","tests/prospectus_successor/test_report_scope.py","--junitxml=docs/implementation/prospectus-execution-authority/attempts/portuguese-2008/attempt-002/context-tests-002.xml"]))'
```
