"""Complete failure bookkeeping without rerunning a spent source campaign."""
from datetime import datetime, timezone
from pathlib import Path
import time

from scripts import prospectus_shell_source_chain_repair as r

PLAN = 'docs/plans/prospectus-source-chain-storage-failure-2026-10-21.md'


def finalize():
    started = time.monotonic()
    r.configure()
    states = r.prior.status()['stages']
    assert states == {'tests': 'PASS', 'ordinary': 'PASS', 'package': 'PASS',
                      'installed': 'FAIL', 'verify': 'BLOCKED', 'reconcile': 'PENDING', 'seal': 'PENDING'}
    assert r.read(r.HERE / 'commands/installed.json')['exit_code'] == 0
    assert r.read(r.HERE / 'stages/installed/failure.json')['reason'] == 'Recovery cumulative storage exhausted'
    start = r.read(r.PREP / 'accounting-start.json')
    records = [r.read(p) for p in sorted(r.PREP.glob('commands/*.json'))]
    records += [r.read(p) for p in sorted(r.HERE.glob('commands/*.json'))]
    paths = {p for folder in (r.PREP, r.HERE) for p in folder.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(r.ROOT / n for n in r.FILES + r.TESTS)
    paths.add(r.AUTH / 'revisions/0381.json')
    paths.update(p for p in (r.AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (r.AUTH / 'program.json').stat().st_size - start['program_bytes'])
    resources = {'new_measured_seconds': sum(x['wall_seconds'] for x in records),
        'new_conservative_other_seconds': 60, 'new_bytes_before_failure_bookkeeping': size,
        'known006plus_accounted_seconds': start['prior_seconds'] + sum(x['wall_seconds'] for x in records) + 60,
        'known006plus_bytes_before_failure_bookkeeping': start['prior_bytes'] + size,
        'incremental_storage_limit_bytes': 128 * 1024**2,
        'cumulative_storage_limit_bytes': 384 * 1024**2,
        'storage_bound_status': 'FAIL', 'earlier_and_manual_costs': 'UNKNOWN', 'old_costs_reset': False}
    assert size > resources['incremental_storage_limit_bytes']
    assert start['prior_bytes'] + size > resources['cumulative_storage_limit_bytes']
    r.save(r.HERE / 'failure-completion-method.json', {
        'plan': PLAN, 'plan_sha256': r.sha(r.ROOT / PLAN),
        'method': r.rel(Path(__file__)), 'method_sha256': r.sha(Path(__file__)),
        'reason': 'Frozen runner checks exhausted resource bounds even before completion-only reconciliation',
        'experimental_reruns': 0, 'historical_evidence_modified': False})
    r.save(r.HERE / 'original-requirements.json', {
        'candidate_passed': False, 'checks': states, 'original_task_complete': False,
        'original_obligations': ['G01', 'G20'], 'prior_failure_retained': r.rel(r.OLD_ATTEMPT),
        'functional_workers_exit_zero': True, 'independent_verifier_executed': False,
        'attribution': 'OUR_STORAGE_FORECAST_AND_PHASE_RESOURCE_CHECK',
        'next_action': 'Record failure; continue independent original task, not another source retry'})
    with (r.HERE / 'RESULT.md').open('x') as stream:
        stream.write('''# Consumer repair works in executed checks; campaign fails its storage bound

The97-test formal suite passed, including actual-consumer legacy and forged-report
regressions. The ordinary and installed workers both exited0 after their three
complete Shell cases and ten adverse controls. The wheel matched549 production
files. The installed stage then FAILED its resource check; independent evidence
verification was BLOCKED. The campaign result is FAIL, not accepted integration.

The source010 NameError was our misplaced verifier. The repaired consumer passed
the executed functional checks. The new failure is also ours: duplicated full
product snapshots exceeded an underestimated storage reservation. Runtime
receipts and retained outputs support those separate findings. Neither is
evidence of a fundamental third-party package limitation.

The incremental128MiB and cumulative384MiB storage ceilings were exceeded.
Actual uncapped totals appear in result.json. No evidence was deleted, no budget
was reset, no successful worker was rerun, and no failed stage was relabelled.
The frozen runner also checks exhausted limits before completion-only failure
reconciliation; a bound separate finalizer retains this failure and its method.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Retain changed consumer and evidence | Executed97 tests and both workers pass | Storage FAIL; independent verification BLOCKED | Full independent evidence review not run | Record/refresh, then independent source01 review | Accepted campaign or whole task/build |
| Stop this source campaign | Original ceiling preserved | Cumulative storage exceeded | Correct future lossless retention design | Require reviewed resource decision before any future source execution | No independent work remains |

Post-run red-team: successful worker assertions are weaker than the blocked
independent verifier. Source authenticity, publication, executed agreements,
trustee succession and operative source roles remain unresolved. The next
storage design must enumerate all outputs and reforecast installed output size
from the ordinary run before dispatch; post-write checks alone are insufficient.
''')
    r.save(r.HERE / 'result.json', {'status': 'FAIL', 'task': 'source-authority',
        'classification': 'FUNCTIONAL_CHECKS_PASS_STORAGE_CAMPAIGN_FAIL',
        'whole_task_complete': False, 'whole_program_complete': False, 'build_criteria_claimed': [],
        'checks': {n: states[n] for n in r.prior.CHECKS}, 'resources': resources})
    r.save(r.HERE / 'run-manifest.json', {
        'git_commit': r.read(r.HERE / 'admission.json')['git_commit'], 'commands': records,
        'environment': str(r.ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; GPU intentionally hidden',
        'data_version': r.sha(r.PREP / 'source-bindings.json'), 'seeds': 'N/A deterministic',
        'plan': r.PLAN, 'failure_plan': PLAN, 'result': r.rel(r.HERE / 'RESULT.md'),
        'resources': resources, 'finalizer_started_at': datetime.now(timezone.utc).isoformat()})
    r.save(r.HERE / 'stages/reconcile/result.json', {'status': 'PASS', 'candidate_passed': False,
        'completion_only': True, 'method': r.rel(Path(__file__))})
    r.save(r.HERE / 'stages/seal/result.json', {'status': 'PASS', 'candidate_status': 'FAIL',
        'completion_only': True, 'method': r.rel(Path(__file__)), 'wall_seconds': time.monotonic() - started})
    r.save(r.HERE / 'outputs.json', {str(p.relative_to(r.HERE)): r.sha(p) for p in r.HERE.rglob('*')
        if p.is_file() and '__pycache__' not in p.parts})
    assert time.monotonic() - started < 20
    return {'status': 'FAILURE_RETAINED', 'campaign_status': 'FAIL', 'resources': resources}


if __name__ == '__main__':
    import json
    print(json.dumps(finalize()))
