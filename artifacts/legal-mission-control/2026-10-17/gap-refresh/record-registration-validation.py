"""Record focused registration validation without touching the provider."""
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import time
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from scripts.legal_mission_execution import read, save, ref, require
from scripts.legal_integration_gap_refresh import WORK, REVIEW

DIRECTORY = ROOT / WORK / 'registration-validation'
DIRECTORY.mkdir(parents=True, exist_ok=True)
COMMAND = [
    '.venv-context/bin/python', '-m', 'pytest', '-q',
    'tests/tooling/test_gap_refresh_registration.py',
    'tests/tooling/test_delayed_service_registration.py',
    'tests/assurance/test_completed_account_constructor.py',
    'tests/assurance/test_completed_account_receipt.py',
    'tests/assurance/test_terminal_cancellation_recovery.py',
    'tests/assurance/test_delayed_service_recovery.py',
    'tests/assurance/test_service_continuation.py',
]
started = time.monotonic()
completed = subprocess.run(COMMAND, cwd=ROOT, text=True, capture_output=True)
elapsed = round(time.monotonic() - started, 2)
log = DIRECTORY / 'tests.log'
log.write_text(completed.stdout + completed.stderr)
require(completed.returncode == 0 and '110 passed' in completed.stdout,
    'Focused registration validation did not pass 110 tests')

tests = [ref(ROOT, path) for path in (
    'tests/tooling/test_gap_refresh_registration.py',
    'tests/tooling/test_delayed_service_registration.py',
    'tests/assurance/test_completed_account_constructor.py',
    'tests/assurance/test_completed_account_receipt.py',
    'tests/assurance/test_terminal_cancellation_recovery.py',
    'tests/assurance/test_delayed_service_recovery.py',
    'tests/assurance/test_service_continuation.py',
)]
test_result = DIRECTORY / 'test-result.json'
save(test_result, dict(profile='gap-refresh-registration-validation.v1',
    command=COMMAND, exit_code=completed.returncode, passed=110, wall_seconds=elapsed,
    inherited_archive_aliases_composed=True, conflicting_aliases_rejected=True,
    semantic_mutations_rejected=True, delayed_499_controls_passed=True,
    provider_calls=0, log=ref(ROOT, log), tests=tests,
    observed_output=completed.stdout.strip()))

prior = read(ROOT / WORK / 'local-result.json')
result_path = ROOT / WORK / 'local-result-registration.json'
save(result_path, dict(profile='gap-refresh-registration-result.v1', verdict='PASS',
    provider_calls=0, ledger_unchanged=True, legal_acceptance=False,
    before_replay=prior['before_replay'], after_replay=prior['after_replay'],
    test_result=ref(ROOT, test_result),
    evidence=[ref(ROOT, WORK / 'local-result.json'), ref(ROOT, REVIEW),
        ref(ROOT, WORK / 'local-manifest.json'), ref(ROOT, log), ref(ROOT, test_result),
        *tests, ref(ROOT, 'scripts/legal_mission_execution.py'),
        ref(ROOT, 'scripts/legal_integration_delayed_service.py')],
    registration_integrity='Nested historical aliases are composed by exact path and SHA-256; conflicts are refused.',
    limitations=prior['limitation'], recorded_at_utc=datetime.now(timezone.utc).isoformat()))
print({'result': str(result_path.relative_to(ROOT)), 'passed': 110,
    'wall_seconds': elapsed, 'provider_calls': 0})
