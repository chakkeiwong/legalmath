"""Retain the actual final frontier and completed deployment checks."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
from xml.etree import ElementTree as ET

ROOT = Path('/home/chakwong/python/legalmath')
WORK = ROOT / 'artifacts/legal-mission-control/2026-10-26/baselines-corpus-deployment'
def read(name):
    return json.loads((WORK / name).read_text())
def ref(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(path.read_bytes()).hexdigest())

assert read('mission-refresh-command.json')['exit_code'] == 0
refresh = read('mission-refresh.json')
assert refresh['status']['mission'] == 'OPEN'
suite = ET.parse(WORK / 'tests-installed.xml').getroot()
assert len(list(suite.iter('testcase'))) == 145
assert not list(suite.iter('failure')) and not list(suite.iter('error'))
assert read('provider-installed.json')['verdict'] == 'PASS'
assert read('registration.json')['status'] == 'COMMITTED'
master = refresh['status']['integration_master']
state = json.loads((ROOT / 'artifacts/legal-mission-control/2026-10-13/master/execution-state.json').read_text())
program = json.loads((ROOT / 'docs/implementation/legal-mission-control/integration-master.json').read_text())
task_index = {t['id']: t for t in program['tasks']}
ready = master['ready']
assert not [tid for tid in ready if task_index[tid]['executor'] == 'command']
outcome = dict(profile='verified-local-baseline-corpus-deployment.v1',
    recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    status='DEPLOYED_AND_VERIFIED_LOCAL', live_activation='HELD',
    integration_complete=False, provider_calls=0, installed_tests=145,
    source_attribution_selections=read('corpus-attribution-hardened.json')['total_actual_passages'],
    mission_refresh='PASS', graph_frontier=master['execution'], graph_ready=ready,
    authorized_ready_live_work=[],
    ready_work_limitation='All graph-ready owners require service; 288/288 replacements spent and the reviewed local installation holds live reservation. No ready local command remains.',
    calls=6471, call_ceiling=8100, service_replacements=288, service_replacement_ceiling=288,
    deadline_utc=program['deadline_utc'],
    retained_owners={tid:dict(status=state['tasks'][tid]['status'], attempts=len(state['tasks'][tid]['attempts']),
        maximum_attempts=task_index[tid]['maximum_attempts']) for tid in
        ('baseline-p14', 'baseline-gatecoin', 'corpus-qualification', 'tool-gatecoin-bm25')},
    evidence=[ref(WORK / p) for p in ('deployment-result.json', 'registration-check.json',
        'tests-installed.xml', 'provider-installed.json', 'installed-integrity.json',
        'corpus-attribution-hardened.json', 'mission-refresh-command.json', 'mission-refresh.json')],
    legal_acceptance=False)
(WORK / 'final-result.json').write_text(json.dumps(outcome, indent=2) + '\n')
manifest = dict(profile='baseline-corpus-deployment-final-manifest.v1',
    git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    baseline='Dirty worktree recorded in baseline.json; exact installed bytes recorded in registration.json.',
    environment='.venv-context and .venv; explicit repository source imports',
    cpu_gpu='CPU-only; no GPU use', seeds='N/A deterministic engineering checks',
    plan=ref(ROOT / 'docs/plans/legal-baseline-corpus-local-deployment-2026-10-26.md'),
    result=ref(WORK / 'final-result.json'),
    commands=[
        '.venv-context/bin/python artifacts/legal-mission-control/2026-10-26/baselines-corpus-deployment/deploy.py ' + action
        for action in ('prepare', 'tests', 'stage', 'validate', 'commit')] + [
        '.venv-context/bin/python artifacts/legal-mission-control/2026-10-26/baselines-corpus-deployment/' + command
        for command in ('seal_validation.py', 'verify_installed.py verify', 'verify_installed.py provider', 'verify_installed.py refresh')],
    wall_time=dict(installed_tests_seconds=float(next(suite.iter('testsuite')).get('time')),
        final_refresh_seconds=read('mission-refresh-command.json')['wall_seconds'],
        whole_package='Not separately instrumented; timestamps retained. No performance claim.'),
    provider_calls=0,
    scripts=[ref(WORK / name) for name in ('deploy.py', 'seal_validation.py', 'verify_installed.py', 'finalize.py')])
(WORK / 'run-manifest-final.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({k:outcome[k] for k in ('status','mission_refresh','installed_tests','graph_frontier',
    'live_activation','integration_complete','provider_calls','retained_owners')}, indent=2))
