# Live feasibility: provider blocked before interpretation

The fresh public family-office investigation produced no candidate interpretation.
Two source-inventory calls were issued. The first failed with `E_DEPENDENCY` and
the service message “Our servers are currently overloaded.” The second reached
the configured 180-second call deadline (`E_RESOURCE_LIMIT`). The engine preserved
both failures and returned `UNRESOLVED`, `execution_complete=false`, with zero
candidates. Missing independent source inventory stopped dependent generation.
There is no live English-interpretation result to score.

The run consumed two additional calls, moving the existing global ledger from
78/100 to 80/100. Twenty calls remain. Failed calls are not refunded. C2's machine
phase status PASSED means the wrapper correctly retained the failed investigation,
budget accounting and refusal; it does not mean the interpretation succeeded.
The separate empirical status is `BLOCKED_PROVIDER_AVAILABILITY`.

## Manifest and actual command

Plan: `docs/plans/interpretation-c1-reference-study.md`.
Frozen live contract: `docs/implementation/interpretation-round5/contracts/feasibility.json`.
Source study hash: `9453437e1b5b85b71939092c1f878345d16c013620f64179c579fc3927f74736`.
Case: `family-offices.clean`; one retained official FAQ family, complete selected
FAQ body, no historical applicability claim. Base commit:
`c810848dff004b8ea7a57c99e10a63552b88c97b` plus exact input hashes in the manifest.

Executed with trusted permissions:

```text
/home/chakwong/python/legalmath/.venv/bin/python /home/chakwong/python/legalmath/scripts/run_reference_study_plan.py run C2
```

The fixed runner invoked `scripts/run_public_qa_feasibility.py`. Environment:
project Python 3.11, existing fresh Codex provider route, isolated read-only
workers with tools disabled, retained JDK 17. No GPU was used. Provider random seed
is unavailable. The run was capped at 18 additional calls and 1,800 seconds; actual
investigation wall time was 253.973 seconds. Full phase timing, source/configuration
hashes and files are in `artifacts/interpretation/round5/C2/attempt-01/run-manifest.json`.
The retained investigation is in `.../live/investigation/`, including each request,
schema, call status, source/context record and final uncertainty report. Before
and after ledger snapshots are retained beside it.

This is a one-method feasibility configuration, not the frozen comparison's
four-method profile. It permits up to eight search calls, reconstruction and
bounded repair inside the shared 18-call total. The future four-method harness
has its own fixed dispatch profile. The two cannot be pooled as one experiment.

## Interpretation and next action

| Decision | Primary criterion | Veto evidence | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Accept failure recording and accounting | Both issued actions retained; no hidden spending or candidate generation after missing inventory | No evidence corruption; all earlier calls retained | Provider overload and deadline cause, including any request-size effect | Preserve attempt and complete local regressions | Successful interpretation or superior method |
| Stop dependent live work now | No complete inventory was returned | External overload plus deadline prevents this investigation | Whether service recovery suffices for this packet | Once available, freeze a successor against the current 80-call ledger; at most 18 calls fits the remaining 20 | Rejection of ensemble search or a measured error rate |
| Continue engineering acceptance | Source, reference and scorer repairs are independently testable | None from this external failure | Additional regression defects | Execute C3 and repair any observed code failure | Institution operational readiness |

| Inference question | Status and evidence |
| --- | --- |
| Hard veto screen | Missing both required inventories; dependent generation correctly withheld |
| Statistically supported ranking | None: no comparative live outputs |
| Descriptive-only differences | Two failure types and observed time; no interpretation accuracy measurement |
| Default readiness | No new model settings or legal automation policy promoted |
| Additional evidence needed | Successful bounded live execution, defensible references and the separately funded paired study |

The first failure explicitly identifies server overload. The second only identifies
a deadline; it could also reflect request complexity or other provider behavior.
Those causes must not be conflated. A successful bounded retry on the same frozen
packet after service recovery would distinguish a transient availability problem
from a reproducible request/profile problem. No automatic paid retries beyond the
reviewed actions have been launched. The weakest evidence remains the absence of
any returned model inventory on this new family.
