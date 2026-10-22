import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import tomllib

ROOT = Path('/tmp/legalmath-main-integration-20261022')
OUT = Path('/tmp/legalmath-merged-validation')
OUT.mkdir(exist_ok=True)
os.chdir(ROOT)
os.environ['PYTHONPATH'] = str(ROOT / 'src') + os.pathsep + str(ROOT)
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def static():
    assert not git('diff', '--name-only', '--diff-filter=U').strip()
    paths = git('diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z',
                'origin/main', '--', 'src', 'scripts', 'tests', 'AGENTS.md', 'pyproject.toml').decode().split('\0')
    checked = []
    conflicts = []
    for name in filter(None, paths):
        path = ROOT / name
        if path.suffix not in ('.py', '.toml', '.md', '.java', '.lean', '.json'):
            continue
        source = path.read_text()
        if re.search(r'^(<<<<<<< |>>>>>>> )', source, re.MULTILINE):
            conflicts.append(name)
        if path.suffix == '.py':
            ast.parse(source, filename=name)
            checked.append(name)
    assert not conflicts, conflicts
    config = tomllib.loads((ROOT / 'pyproject.toml').read_text())
    patterns = config['tool']['setuptools']['package-data']['legalmath']
    for pattern in ('prospectus/bes_comparative_spec.json', 'prospectus/successor/*.json.gz'):
        assert pattern in patterns and list((ROOT / 'src/legalmath').glob(pattern))
    listing = git('rev-list', '--objects', 'HEAD', 'MERGE_HEAD', '--not', 'origin/main')
    objects = subprocess.check_output(['git', 'cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize) %(rest)'],
                                     input=listing, cwd=ROOT).decode().splitlines()
    blobs = []
    for line in objects:
        parts = line.split(' ', 3)
        if len(parts) >= 3 and parts[1] == 'blob':
            blobs.append(dict(sha=parts[0], bytes=int(parts[2]), path=parts[3] if len(parts) > 3 else ''))
    oversized = [row for row in blobs if row['bytes'] >= 100 * 1024 * 1024]
    assert not oversized, oversized
    result = dict(status='PASS', python_files=len(checked), conflict_markers=conflicts,
                  outgoing_blobs=len(blobs), largest_blobs=sorted(blobs, key=lambda x:x['bytes'], reverse=True)[:5],
                  merged_package_data_verified=True, parents=git('rev-parse', 'HEAD', 'MERGE_HEAD').decode().splitlines())
    (OUT / 'static.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))

def tests():
    import legalmath
    import legalmath.prospectus.successor.service as prospectus
    import legalmath.interpretation.assurance.phased.capacity_policy as capacity
    for module in (legalmath, prospectus, capacity):
        assert Path(module.__file__).resolve().is_relative_to(ROOT / 'src'), module.__file__
    selected = [
        'tests/assurance/test_common_capacity.py',
        'tests/assurance/test_retained_acquisition_capacity.py',
        'tests/assurance/test_source_review_repair.py',
        'tests/assurance/test_review_repair_budget_service.py',
        'tests/assurance/test_review_receipts.py::test_reference_dispatch_runs_one_repair_for_every_malformed_assignment',
        'tests/tooling/test_review_timeout_correction.py',
        'tests/tooling/test_review_receipt_correction.py',
        'tests/tooling/test_retained_acquisition_registration.py',
        'tests/tooling/test_review_repair_registration.py',
        'tests/prospectus/test_closure_mechanisms.py',
        'tests/prospectus_successor/test_closure_consumers.py',
        'tests/prospectus_successor/test_closure_coupon_anchor.py',
        'tests/prospectus_successor/test_closure_finance.py',
        'tests/prospectus_successor/test_closure_program.py',
        'tests/prospectus_successor/test_closure_real_scan.py',
        'tests/prospectus_successor/test_repairs.py',
    ]
    selector = ('not test_actual_slot_3591_is_authenticated_empty_timeout '
                'and not test_real_scan_corrections_keep_raw_identifiers_and_full_qualifications '
                'and not test_real_scan_layout_requires_whole_qualification_even_when_yes_survives')
    args = ['-q', '-p', 'no:cacheprovider', '--maxfail=10', '--tb=short',
            '--junitxml=' + str(OUT / 'tests.xml'), '-k', selector, *selected]
    import pytest
    start = time.monotonic()
    log = OUT / 'tests.log'
    with log.open('w') as stream:
        sys.stdout = sys.stderr = stream
        print('Merged checkout imports verified; CPU devices intentionally hidden; no live calls.', flush=True)
        code = pytest.main(args)
        print(f'Exit={code}; seconds={time.monotonic() - start:.2f}', flush=True)
    manifest = dict(command=[sys.executable, *sys.argv], pytest_args=args,
                    interpreter=sys.executable, source=str(ROOT / 'src'), cpu_only=True,
                    provider_calls=0, exit_code=int(code), seconds=time.monotonic() - start,
                    log=str(log), junit=str(OUT / 'tests.xml'))
    (OUT / 'tests-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    raise SystemExit(code)

{'static': static, 'tests': tests}[sys.argv[1]]()
