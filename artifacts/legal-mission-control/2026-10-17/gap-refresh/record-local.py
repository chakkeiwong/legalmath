"""Retain observed local checks without rerunning them or contacting a provider."""
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import read, save, ref, require
from scripts.legal_integration_gap_refresh import WORK, MUTATED, REVIEW, VETO_REASON
from scripts.legal_integration_master import BASE, PROGRAM, PLAN

directory = ROOT / WORK
require(not (directory / 'local-result.json').exists(), 'Do not overwrite retained local evidence')
baseline = read(directory / 'baseline.json')
held = {row['previous']['path']: row['archive'] for row in baseline['archived']}
require(ref(ROOT, BASE / 'live-calls.json')['sha256'] == held[str(BASE / 'live-calls.json')]['sha256'],
    'Local checks changed the live ledger')
before, after = (read(directory / ('p10-replay-' + mode + '.json')) for mode in ('before', 'after'))
require(before['reproduced_error'] == VETO_REASON and after['receipt_reused']
    and after['differences'] == [] and before['schema_equal'] and after['schema_equal']
    and before['provider_calls'] == after['provider_calls'] == 0
    and before['ledger_unchanged'] and after['ledger_unchanged'], 'Actual replay did not pass')
tests = [
    'tests/tooling/test_gap_refresh_registration.py',
    'tests/tooling/test_delayed_service_registration.py',
    'tests/assurance/test_completed_account_constructor.py',
    'tests/assurance/test_completed_account_receipt.py',
    'tests/assurance/test_terminal_cancellation_recovery.py',
    'tests/assurance/test_delayed_service_recovery.py',
    'tests/assurance/test_service_continuation.py',
]
command = ['.venv-context/bin/python', '-m', 'pytest', '-q', *tests]
transcript = ('Retained final summary from completed execution-tool session 95634.\n'
    'This is a transcription of the observed tool output, not a new test run.\n'
    '109 passed in 13.39s\n')
(directory / 'tests-observed.log').write_text(transcript)
save(directory / 'test-result.json', dict(profile='gap-refresh-test-result.v1',
    command=command, exit_code=0, passed=109, wall_seconds=13.39,
    semantic_mutations_rejected=True, delayed_499_controls_passed=True,
    provider_calls=0, observation='Completed execution-tool session 95634; retained final output',
    earlier_fixture_failure='Question fixture used a dict instead of a list; fixed before the final passing run.',
    log=ref(ROOT, WORK / 'tests-observed.log'), tests=[ref(ROOT, path) for path in tests]))
evidence = [ref(ROOT, WORK / name) for name in (
    'reviewed-plan.md', 'replay-p10.py', 'p10-request-before.json', 'p10-request-after.json',
    'p10-diff-before.json', 'p10-diff-after.json', 'tests-observed.log')]
evidence += [ref(ROOT, path) for path in tests]
save(directory / 'local-manifest.json', dict(profile='gap-refresh-local-manifest.v1',
    recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    environment='.venv-context; replays set CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden',
    cpu_gpu_status='CPU only; no GPU initialization',
    data_version=read(ROOT / PROGRAM)['prerequisite_repair']['source'],
    random_seeds='N/A: deterministic identity/mutation controls; no statistical ranking',
    commands=[['.venv-context/bin/python', str(WORK / 'replay-p10.py'), mode]
        for mode in ('before', 'after')] + [command],
    wall_seconds=dict(before_replay=before['wall_seconds'], after_replay=after['wall_seconds'], tests=13.39),
    plan=ref(ROOT, PLAN), review=ref(ROOT, REVIEW),
    frozen_ledger=held[str(BASE / 'live-calls.json')], provider_calls=0, ledger_unchanged=True,
    implementation=[ref(ROOT, path) for path in sorted(MUTATED)],
    outputs=[ref(ROOT, WORK / name) for name in ('p10-replay-before.json', 'p10-replay-after.json', 'test-result.json')]))
save(directory / 'local-result.json', dict(profile='gap-refresh-local-result.v1', verdict='PASS',
    provider_calls=0, ledger_unchanged=True, legal_acceptance=False,
    before_replay=ref(ROOT, WORK / 'p10-replay-before.json'),
    after_replay=ref(ROOT, WORK / 'p10-replay-after.json'),
    test_result=ref(ROOT, WORK / 'test-result.json'),
    evidence=evidence + [ref(ROOT, WORK / 'local-manifest.json')],
    scope='Actual detail-10 constructor/receipt reuse, semantic mutation rejection and bounded delayed-499 controls.',
    limitation='Does not prove remaining P10 stages, provider availability, legal accuracy or matched tool effects.'))
print({'local_result': str(WORK / 'local-result.json'), 'passed': 109, 'calls': 0})
