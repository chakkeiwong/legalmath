"""Retain bounded local validation before adoption. Does not call a provider."""
from pathlib import Path
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from scripts.legal_mission_execution import read, save, ref, require
from scripts.legal_integration_delayed_service import WORK, BASE, PLAN, REVIEW

tests = ['tests/assurance/test_delayed_service_recovery.py',
    'tests/tooling/test_delayed_service_registration.py',
    'tests/assurance/test_service_continuation.py', 'tests/assurance/test_retry_delay_persistence.py',
    'tests/assurance/test_execution_recovery.py', 'tests/assurance/test_phased_admission.py',
    'tests/assurance/test_local_refresh_boundaries.py',
    'tests/tooling/test_local_refresh_registration.py', 'tests/tooling/test_local_refresh_views.py',
    'tests/tooling/test_repair_execution.py', 'tests/tooling/test_legal_mission_execution.py',
    'tests/tooling/test_legal_mission_control.py']
command = ['.venv-context/bin/python', '-m', 'pytest', '-q', *tests]
before = ref(ROOT, BASE / 'live-calls.json')
started = datetime.now(timezone.utc).isoformat()
begin = time.monotonic()
with (ROOT / WORK / 'tests.log').open('w') as output:
    result = subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
unchanged = ref(ROOT, BASE / 'live-calls.json') == before
manifest = dict(command=command, commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    environment='.venv-context; CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden',
    started_at_utc=started, wall_seconds=round(time.monotonic() - begin, 3),
    random_seeds='N/A: deterministic engineering regression', data_version='frozen delayed-service baseline',
    plan=str(PLAN), review=str(REVIEW), exit_code=result.returncode, provider_calls=0,
    ledger_before=before, ledger_unchanged=unchanged, log=ref(ROOT, WORK / 'tests.log'))
save(ROOT / WORK / 'test-manifest.json', manifest)
require(result.returncode == 0 and unchanged, 'Delayed service regression failed; inspect tests.log')
save(ROOT / WORK / 'local-result.json', dict(verdict='PASS', provider_calls=0, ledger_unchanged=True,
    legal_acceptance=False, evidence=[ref(ROOT, WORK / 'test-manifest.json'), ref(ROOT, WORK / 'tests.log')]
        + [ref(ROOT, name) for name in tests],
    decision='Hourly retry engineering checks pass; actual service and legal answer quality remain untested.'))
print((ROOT / WORK / 'tests.log').read_text()[-2000:])
