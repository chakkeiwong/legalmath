"""Test installed bytes, then refresh the current mission without live calls."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = Path('/home/chakwong/python/legalmath')
WORK = ROOT / 'artifacts/legal-mission-control/2026-10-26/baselines-corpus-deployment'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
os.chdir(ROOT)

def verify():
    journal = json.loads((WORK / 'registration.json').read_text())
    assert journal['status'] == 'COMMITTED'
    for row in journal['writes']:
        assert hashlib.sha256((ROOT / row['path']).read_bytes()).hexdigest() == row['replacement']['sha256'], row['path']
    from legalmath.interpretation.assurance import corpus_review
    assert Path(corpus_review.__file__).resolve() == ROOT / 'src/legalmath/interpretation/assurance/corpus_review.py'
    import pytest
    tests = ['tests/assurance/test_baseline_corpus_repairs.py',
        'tests/assurance/test_corpus_passage_attribution.py', 'tests/assurance/test_context_exact_references.py',
        'tests/assurance/test_context_need_disposition.py', 'tests/assurance/test_downstream_capacity.py',
        'tests/assurance/test_requirement_correction.py', 'tests/assurance/test_source_review_repair.py',
        'tests/tooling/test_baseline_corpus_deployment.py']
    return pytest.main([*tests, '-q', '--junitxml=' + str(WORK / 'tests-installed.xml')])

def refresh():
    command = ['.venv/bin/python', 'scripts/legal_mission_control.py', 'refresh']
    start = time.monotonic()
    at = datetime.now(timezone.utc).isoformat()
    with (WORK / 'mission-refresh.json').open('w') as out, (WORK / 'mission-refresh.stderr').open('w') as err:
        result = subprocess.run(command, cwd=ROOT, stdout=out, stderr=err)
    receipt = dict(command=command, started_at_utc=at,
        finished_at_utc=datetime.now(timezone.utc).isoformat(), wall_seconds=time.monotonic() - start,
        exit_code=result.returncode)
    (WORK / 'mission-refresh-command.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
    return result.returncode

def provider():
    from scripts.legal_integration_campaign import provider as configured_provider
    from scripts.legal_integration_master import BASE
    from legalmath.errors import LegalMathError
    service = configured_provider()
    path = ROOT / BASE / 'live-calls.json'
    before = path.read_bytes()
    ledger = service.check()
    binding = json.loads((ROOT / BASE / 'current-binding.json').read_text())
    assert len(ledger['calls']) == 6471 and ledger['maximum'] == 8100
    assert service.allowance.service_scope()[0] == binding['phase_service_scope']
    service.allowance.expected = 'installed-deployment-must-not-dispatch'
    try:
        service.allowance.reserve(service.allowance.expected)
    except LegalMathError as exc:
        assert exc.code == 'E_AUTHORITY' and 'reviewed live continuation' in exc.details
    else:
        raise AssertionError('Installed activation hold failed')
    assert path.read_bytes() == before
    result = dict(verdict='PASS', actual_installed_binding=True, calls=6471,
        provider_calls=0, activation_hold='VERIFIED', inherited_scope='VERIFIED',
        at_utc=datetime.now(timezone.utc).isoformat())
    (WORK / 'provider-installed.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['verify', 'refresh', 'provider'])
    raise SystemExit(globals()[parser.parse_args().action]())
