"""Retain focused local checks with the exact implementation and environment."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import sys, time, subprocess, json
from pathlib import Path
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from scripts.legal_integration_synthesis_resolution import WORK, IMPLEMENTATION
from scripts.legal_mission_execution import ref, save
RESULTS = WORK/'validation-2'
(ROOT/RESULTS).mkdir(parents=True, exist_ok=True)
TESTS = [
    'tests/assurance/test_synthesis_successor.py',
    'tests/assurance/test_synthesis_catalog.py',
    'tests/assurance/test_synthesis_lineage.py',
    'tests/assurance/test_downstream_capacity.py',
    'tests/assurance/test_downstream_replay_order.py',
    'tests/assurance/test_phased_phase.py',
    'tests/assurance/test_phased_product.py',
    'tests/assurance/test_failure_recovery.py',
    'tests/assurance/test_terminal_cancellation_recovery.py',
    'tests/tooling/test_synthesis_resolution_registration.py',
]
command = [sys.executable, '-m', 'pytest', '-q', '--tb=short', *TESTS]
started = time.monotonic()
result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
(ROOT/RESULTS/'tests.stdout').write_text(result.stdout)
(ROOT/RESULTS/'tests.stderr').write_text(result.stderr)
value = dict(verdict='PASS' if result.returncode == 0 else 'FAIL', command=command,
    exit_code=result.returncode, wall_seconds=time.monotonic()-started,
    environment='.venv-context', gpu='Intentionally hidden with CUDA_VISIBLE_DEVICES=-1',
    seeds='N/A: deterministic engineering checks', provider_calls=0,
    implementation={p:ref(ROOT,p) for p in sorted(IMPLEMENTATION)},
    tests={p:ref(ROOT,p) for p in TESTS}, stdout=ref(ROOT,RESULTS/'tests.stdout'),
    stderr=ref(ROOT,RESULTS/'tests.stderr'), legal_acceptance=False)
save(ROOT/RESULTS/'tests.json', value)
print(result.stdout)
if result.stderr: print(result.stderr)
raise SystemExit(result.returncode)
