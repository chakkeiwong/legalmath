"""Retain actual local evidence only after the production replay completes."""
from datetime import datetime, timezone
from pathlib import Path
from hashlib import sha256
import json
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[4]
WORK = Path('artifacts/legal-mission-control/2026-10-21/review-repair')
PLAN = Path('docs/plans/legal-review-repair-2026-10-21.md')

def read(path):
    return json.loads((ROOT/path).read_text())

def ref(path):
    return dict(path=str(path), sha256=sha256((ROOT/path).read_bytes()).hexdigest())

def save(path, value):
    (ROOT/path).write_text(json.dumps(value, indent=2)+'\n')

baseline = read(WORK/'baseline.json')
prior = next(row['archive'] for row in baseline['archived']
    if row['previous']['path'] == 'artifacts/legal-mission-control/2026-10-13/master/live-calls.json')
assert ref(Path('artifacts/legal-mission-control/2026-10-13/master/live-calls.json'))['sha256'] == prior['sha256']
replay = read(WORK/'production-replay.json')
assert replay['verdict'] == 'PASS' and replay['provider_calls'] == 0 and replay['ledger_unchanged']
assert replay['current_production_entry'] and not replay['actual_live_admission'] and not replay['legal_acceptance']
assert set(replay['questions']) == {'p10','p14','evidence','gatecoin'}
assert all(row['route_completed'] for row in replay['questions'].values())
assert all(replay['questions'][q]['original_answer_unchanged'] for q in ('p14','gatecoin'))
suites = list(ET.parse(ROOT/WORK/'tests.xml').getroot().iter('testsuite'))
tests = sum(int(row.get('tests','0')) for row in suites)
assert tests == 160
assert all(int(row.get(key,'0')) == 0 for row in suites for key in ('errors','failures','skipped'))
test_files = [
    'tests/assurance/test_source_review_repair.py',
    'tests/assurance/test_review_repair_budget_service.py',
    'tests/assurance/test_phased_product.py',
    'tests/assurance/test_requirement_correction.py',
    'tests/assurance/test_common_capacity.py',
    'tests/assurance/test_downstream_capacity.py',
    'tests/assurance/test_response_schema_continuation.py',
    'tests/assurance/test_delayed_service_recovery.py',
    'tests/assurance/test_service_continuation.py',
    'tests/tooling/test_review_repair_registration.py',
    'tests/tooling/test_legal_mission_execution.py',
    'tests/tooling/test_outage_refresh_continuation.py',
    'tests/tooling/test_settled_recovery_registration.py',
]
manifest = dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    uncommitted_implementation=True, environment='.venv-context/bin/python',
    cpu_gpu='CPU only; CUDA_VISIBLE_DEVICES=-1 intentionally hides GPU devices', random_seeds='N/A: deterministic offline validation',
    data_version=ref(WORK/'baseline.json'), plan=ref(PLAN),
    implementation={p:ref(Path(p)) for p in read(WORK/'implementation-files.json')},
    test_sources={p:ref(Path(p)) for p in test_files},
    commands=[dict(argv=['.venv-context/bin/python','-m','pytest','-q',*test_files,
        '--junitxml='+str(WORK/'tests.xml')],env={'CUDA_VISIBLE_DEVICES':'-1'},
        junit_suite_seconds=sum(float(row.get('time','0')) for row in suites),
        tests=tests,exit_code=0,output=ref(WORK/'tests.xml')),
        dict(argv=['.venv-context/bin/python','scripts/legal_review_repair_replay.py'],
        env={'CUDA_VISIBLE_DEVICES':'-1'},wall_seconds=replay['wall_seconds'],exit_code=0,
        output=ref(WORK/'production-replay.json'))],
    other_evidence=[ref(WORK/'packing-census.json'),ref(WORK/'budget.json'),ref(WORK/'handover.json'),
        ref(WORK/'terminal-receipt-replay.json')],
    result_file=str(WORK/'local-result.json'),provider_calls=0,legal_acceptance=False)
save(WORK/'run-manifest.json',manifest)
result = dict(verdict='PASS',provider_calls=0,ledger_unchanged=True,legal_acceptance=False,
    engineering_scope='Current production-entry capacity, exact reuse, typed review repair, independent corrections, finite recovery and protected branch budgets',
    tests=tests,review='Skeptical audit passed for bounded adoption; no claim of full legal or tool acceptance',
    missing_model_work={q:len(v['missing_model_requests']) for q,v in replay['questions'].items()},
    evidence=[ref(WORK/p) for p in ('tests.xml','production-replay.json','packing-census.json','budget.json',
        'run-manifest.json','handover.json','terminal-receipt-replay.json')])
save(WORK/'local-result.json',result)
print(json.dumps(dict(verdict='PASS',tests=tests,provider_calls=0,missing_model_work=result['missing_model_work'])))
