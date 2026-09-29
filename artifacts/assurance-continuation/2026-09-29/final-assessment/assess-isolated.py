"""Trusted, offline regression of the archived continuation snapshot."""
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ORIGINAL = Path(__file__).resolve().parents[4]
ROOT = Path('/tmp/legalmath-continuation-final-20260929')
OUT = ORIGINAL/'artifacts/assurance-continuation/2026-09-29/final-assessment'
isolation = json.loads((OUT/'isolation-repair/manifest.json').read_text())
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT/'src')]
os.environ.update(PYTHONPATH=str(ROOT/'src'), CUDA_VISIBLE_DEVICES='-1')
import legalmath
import run_assurance_continuation as r
from assurance_continuation_checks import documents, GRANT, baseline
from assurance_successor_audit import journal_receipt
from legalmath.interpretation.assurance.grants import GrantedAllowance

work = r.OUT/'final-assessment/attempt-04'
work.mkdir(parents=True, exist_ok=False)
delivery = OUT/'attempt-04'
delivery.mkdir(exist_ok=False)
started = time.monotonic()
before = r.regression_inputs()
state = r.read(r.OUT/'state.json')
reviewed = r.read(r.OUT/'reviewed-implementation.json')
manifest = {'status':'RUNNING', 'started_at':r.now(), 'snapshot':str(ROOT),
    'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'argv':[sys.executable,*sys.argv], 'script_sha256':r.sha(__file__),
    'python':str(r.PYTHON), 'package_import':legalmath.__file__,
    'PYTHONPATH':os.environ['PYTHONPATH'], 'cpu_only':True,
    'execution_context':'TRUSTED_HOST', 'seed':'N/A: deterministic assessment',
    'inputs':before, 'isolated_material_inputs':isolation['inputs'],
    'isolation_manifest_sha256':r.sha(OUT/'isolation-repair/manifest.json'),
    'plan':'docs/plans/assurance-continuation-final-assessment.md',
    'plan_sha256':r.sha(ROOT/'docs/plans/assurance-continuation-final-assessment.md'),
    'commands':[], 'live_calls':0}


def checkpoint():
    r.save(work/'manifest.json', manifest)
    r.save(delivery/'manifest.json', manifest)


def run(argv, directory, label, **kwargs):
    print('START', label, flush=True)
    try:
        result = r.command(argv, directory, label, **kwargs)
    finally:
        receipt = directory/(label+'-command.json')
        if receipt.exists():
            manifest['commands'].append(r.read(receipt))
            shutil.copy2(receipt, delivery/receipt.name)
        checkpoint()
    print('PASS', label, flush=True)
    return result


checkpoint()
try:
    if not Path(legalmath.__file__).resolve().is_relative_to(ROOT/'src'):
        raise RuntimeError('Imported package is outside the frozen snapshot')
    if any(r.sha(ROOT/p)!=h for p,h in isolation['inputs'].items()):
        raise RuntimeError('Snapshot differs from archived material inputs')
    repairs=isolation['changes']
    allowed_repairs={'scripts/assurance_successor_sources.py',
                     'tests/assurance/test_successor_source_freeze.py'}
    if {p for p in repairs if p in reviewed['inputs']}!=allowed_repairs:
        raise RuntimeError('Unexpected repair scope')
    if any(r.sha(ROOT/p)!=(repairs[p]['after'] if p in repairs else h)
           or (p in repairs and repairs[p]['before']!=h)
           for p,h in reviewed['inputs'].items()):
        raise RuntimeError('Reviewed assurance source changed')
    for phase, attempts in state['phases'].items():
        for ref in attempts:
            if r.sha(ROOT/ref['path'])!=ref['sha256']:
                raise RuntimeError('Changed retained phase manifest')
            m = r.read(ROOT/ref['path'])
            if any(r.sha(ROOT/p)!=h for p,h in m['outputs'].items()):
                raise RuntimeError('Changed retained phase evidence')
    if GrantedAllowance(GRANT).verify()['used']!=500:
        raise RuntimeError('Unexpected frozen allowance')
    _, journal = journal_receipt(r.OUT/'C6/attempt-02/scoped/model/journal.json')
    if any(a['status']=='RESERVED' for a in journal['actions']):
        raise RuntimeError('Incomplete retained live action')
    manifest['baseline_check'] = baseline(work/'baseline-check')
    checkpoint()
    run([str(r.PYTHON), '-m', 'pytest', '-q',
         'tests/assurance/test_successor_source_freeze.py'],
        work, 'portability-repair-preflight', timeout=90)
    run([str(r.PYTHON), '-m', 'pytest', '-q',
         'tests/integration/test_api.py::test_api_evaluation_identity_and_restart'],
        work, 'api-environment-preflight', timeout=90)
    run([str(r.PYTHON), '-m', 'pytest', '-q',
         'tests/assurance/test_proof_carrying_integration.py'],
        work, 'dossier-preflight', timeout=300)
    manifest['documents'] = documents(work, run)
    checkpoint()
    run([str(r.PYTHON), '-m', 'pytest', '-q', '--junitxml='+str(work/'full-regression.xml')],
        work, 'full-regression', timeout=3600)
    tree = ET.parse(work/'full-regression.xml').getroot()
    counts = {k:sum(int(s.get(k,0)) for s in tree.iter('testsuite'))
              for k in ('tests','failures','errors','skipped')}
    manifest['regression'] = counts
    if not counts['tests'] or any(counts[k] for k in ('failures','errors','skipped')):
        raise RuntimeError(str(counts))
    after = r.regression_inputs()
    manifest['input_changes'] = {p:{'before':before.get(p),'after':after.get(p)}
        for p in set(before)|set(after) if before.get(p)!=after.get(p)}
    if manifest['input_changes']:
        raise RuntimeError('Frozen inputs changed during verification')
    if any(r.sha(ROOT/p)!=h for p,h in isolation['inputs'].items()):
        raise RuntimeError('Frozen material input changed')
    export = work/'documents'
    export.mkdir()
    for name in ('monograph.pdf','technical-companion.pdf','process-guide.pdf'):
        shutil.copy2(ROOT/'docs/monograph'/name, export/name)
    manifest['status'] = 'PASSED_ISOLATED_ASSESSMENT_WITH_LIVE_AND_CAPACITY_QUALIFICATIONS'
except BaseException as exc:
    manifest.update(status='FAILED', error=type(exc).__name__, details=str(exc)[:6000])
finally:
    if (work/'full-regression.xml').exists():
        tree = ET.parse(work/'full-regression.xml').getroot()
        manifest['regression'] = {k:sum(int(s.get(k,0)) for s in tree.iter('testsuite'))
                                 for k in ('tests','failures','errors','skipped')}
    manifest.update(finished_at=r.now(), elapsed_seconds=round(time.monotonic()-started,3),
        historical_study_complete=False, master_C7_executed=False,
        legal_correctness='NOT_ESTABLISHED', live_workspace_verified=False)
    manifest['outputs'] = {str(p.relative_to(work)):r.sha(p)
        for p in sorted(work.rglob('*')) if p.is_file() and p.name!='manifest.json'}
    checkpoint()
    shutil.copytree(work, delivery, dirs_exist_ok=True)
    print(manifest['status'], flush=True)
    print(manifest.get('regression'), manifest.get('details',''), flush=True)
if manifest['status']=='FAILED':
    raise SystemExit(1)
