"""Bounded downstream receipt repair; original source-authority history retained."""
import ast
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile
from scripts.prospectus_default_holder import ROOT, AUTH, read, save, sha, rel, digest, adigest, Authority

PREP = AUTH / 'reviews/acquisition-receipt-366'
HERE = AUTH / 'attempts/source-authority/attempt-009'
BASE = AUTH / 'attempts/basf-references/attempt-100'
PLAN = 'docs/plans/prospectus-acquisition-receipt-integrity-2026-10-20.md'
FILES = [PLAN, 'scripts/prospectus_acquisition_receipt.py', 'scripts/prospectus_acquisition_receipt_worker.py',
    'src/legalmath/prospectus/successor/source_graph.py', 'src/legalmath/prospectus/successor/service.py',
    'tests/prospectus_successor/test_acquisition_receipt_integrity.py']
TESTS = ['tests/prospectus_successor/' + n for n in ('test_acquisition_receipt_integrity.py',
    'test_document_time_validation.py', 'test_archive_observations.py', 'test_conditional_profiles_cli.py')]
DEPS = {'tests': (), 'ordinary': (), 'package': (), 'installed': ('ordinary', 'package'),
        'reconcile': (), 'seal': ('reconcile',)}
CHECKS = ('tests', 'ordinary', 'package', 'installed')


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    timed = [PREP / n for n in ('reproduction.json', 'development.json', 'preparation-result.json')]
    timed += list(HERE.glob('stages/*/result.json')) + list(HERE.glob('stages/*/failure.json'))
    seconds = extra + sum(read(p).get('wall_seconds', 0) for p in timed if p.exists())
    files = {p for d in (PREP, HERE) for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    files.update(ROOT / n for n in FILES); files.add(AUTH / 'revisions/0366.json')
    files.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in files if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    total = start['known006plus_seconds'] + seconds + 120
    combined = start['known006plus_bytes'] + size
    assert seconds < 900 and size < 156 * 1024**2, 'Incremental trial ceiling'
    assert total < 1900 and combined < 380 * 1024**2, 'Known cumulative trial ceiling'
    return {'known006plus_accounted_seconds': total, 'known006plus_bytes': combined,
        'new_measured_seconds': seconds, 'new_conservative_other_seconds': 120, 'new_bytes': size,
        'earlier_and_manual_costs': 'UNKNOWN', 'old_costs_reset': False, 'seal_reserve_bytes': 4 * 1024**2}


def prepare():
    started = time.monotonic(); assert read(PREP / 'reproduction.json')['status'] == 'REPRODUCED'
    assert read(PREP / 'development.json')['exit_code'] == 0
    for name, checksum in read(BASE / 'outputs.json').items(): assert sha(BASE / name) == checksum, name
    previous = read(AUTH / 'reviews/issuer-qualification-365/reproduction.json')
    products_path = previous['products']; manifest = read(ROOT / products_path)['products']
    p1 = read(ROOT / manifest['P1']['path']); documents = p1['payload']['request']['bundle']['documents']
    receipts = {d['acquisition']['path']: d['acquisition']['sha256'] for d in documents if d.get('acquisition')}
    assert len(receipts) == 4
    for path, checksum in receipts.items(): assert sha(ROOT / path) == checksum
    from legalmath.prospectus.successor import source_graph
    assert all(source_graph.acquisition_status(d, ROOT) == 'BYTES_BOUND; AUTHENTICITY_REQUIRES_REVIEW' for d in documents)
    config = {'products': products_path, 'profiles': 'docs/implementation/prospectus-execution-authority/reviews/issuer-qualification-365/profiles.json',
        'baseline': rel(BASE / 'ordinary-answer.json.gz'), 'receipts': receipts, 'package_python': read(BASE / 'package.json')['python']}
    save(PREP / 'config.json', config)
    sources = read(AUTH / 'reviews/issuer-qualification-365/source-bindings.json'); sources.update(receipts)
    sources.update({rel(BASE / n): sha(BASE / n) for n in ('ordinary-answer.json.gz', 'outputs.json', 'package.json')})
    sources[config['profiles']] = sha(ROOT / config['profiles'])
    for path, checksum in sources.items(): assert sha(ROOT / path) == checksum, path
    save(PREP / 'source-bindings.json', sources)
    def functions(path):
        return {n.name: ast.dump(n) for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef)}
    changes = {}
    for name, permitted in [('source_graph.py', {'build', 'acquisition_status'}), ('service.py', {'construction_product', 'consume'})]:
        old = functions(PREP / 'baseline' / name); new = functions(ROOT / 'src/legalmath/prospectus/successor' / name)
        changed = {n for n in old.keys() | new.keys() if old.get(n) != new.get(n)}
        assert changed <= permitted; changes[name] = sorted(changed)
    save(PREP / 'preparation-result.json', {'status': 'PASS', 'receipts': len(receipts),
        'changed_functions': changes, 'wall_seconds': time.monotonic() - started})
    assert time.monotonic() - started < 60
    return {'status': 'PASS', 'receipts': len(receipts), 'resources': costs()}


def proposal():
    program = read(AUTH / 'program.json'); assert program['revision'] == 365 and not HERE.exists()
    attempts = [e['attempt'] for e in Authority(ROOT).events() if e['kind'] == 'ADMIT' and e.get('budget_key') == 'source-authority']
    assert len(attempts) == 8
    production = {rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}
    bindings = {n: sha(ROOT / n) for n in FILES + TESTS}
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    bindings.update(production); bindings.update(read(PREP / 'source-bindings.json'))
    save(PREP / 'freeze.json', {'bindings': bindings, 'production': production})
    new = deepcopy(program); new['revision'] = 366
    task = next(t for t in new['tasks'] if t['id'] == 'source-authority')
    task.update(dossier=PLAN, pre_admission_review=PLAN, timeout_seconds=380,
        reason='Repair reproduced stale acquisition receipt acceptance in construction and frozen consumer',
        acquisition_receipt_repair={'review': rel(PREP), 'original_task_complete': False,
            'new_seconds': 900, 'conservative_other_seconds': 120, 'new_bytes': 160 * 1024**2,
            'known006plus_seconds': 1900, 'known006plus_bytes': 384 * 1024**2, 'earlier_costs': 'UNKNOWN'})
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json')]))
    new['budgets']['source-authority']['maximum_new_attempts'] = 9
    routes = read(ROOT / program['continuation_review']['routes']); routes['baseline_revision'] = 366
    for row in routes['tasks']:
        if row['task'] == 'source-authority':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Verify downstream receipt repair and unchanged complete answers; reconcile missing publication/authenticity sources',
                stop_condition='9 admissions;900+120s/160MiB new;1900s/384MiB known006+;no archive harness or unchanged retry')
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    new['continuation_review']['bindings'].update({n: sha(ROOT / n) for n in (PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'))})
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Recheck supplied receipt bytes at two actual downstream boundaries', 'Preserve complete100 answer and known cumulative costs'],
        'skeptical_audit': {'verdict': 'PASS', 'review': PLAN, 'reproduction': rel(PREP / 'reproduction.json'),
            'archive_harness_retry': False, 'source_authenticity_claim': False},
        'evidence_contract': {'primary': 'Actual changed/missing receipt refusals and exact complete ordinary/installed baseline equality',
            'promotion_veto': ['Permissive stale receipt', 'Changed valid answer', 'Wrong source/import', 'Frozen extraction rerun'],
            'continuation_veto': ['Invalid authority', 'Corrupt shared evidence', 'Exhausted bounds'],
            'explanatory_only': ['Counts', 'Time'], 'not_concluded': ['Source authenticity', 'Publication date', 'Whole task/build']},
        'budget_revision': {'budget_key': 'source-authority', 'previous_maximum': 8, 'new_maximum': 9,
            'retained_attempts': attempts, 'reason': 'Distinct reproduced downstream receipt integrity defect',
            'next_discriminating_check': 'Changed receipt rejected while original complete100 answer stays equal in both runtimes',
            'stop_condition': '900+120s/160MiB new;1900s/384MiB known006+;380s consumers;no unchanged retry',
            'same_scope_authorization': 'User authorized repair and continued general build; no external call or branch action'}}
    save(PREP / 'proposal.json', new); save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 366, 'frozen_files': len(bindings), 'resources': costs()}


def frozen():
    admission = read(HERE / 'admission.json')
    assert adigest(read(AUTH / 'program.json')) == admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec']) == admission['binding']
    for name, checksum in read(PREP / 'freeze.json')['bindings'].items(): assert sha(ROOT / name) == checksum, name


def execute(name, argv, timeout=120, cwd=ROOT):
    folder = HERE / 'commands'; folder.mkdir(exist_ok=True); started = time.monotonic()
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONPATH': str(ROOT / 'src'),
        'PYTHONDONTWRITEBYTECODE': '1', 'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1'}
    result = None; failure = None
    try:
        with (folder / (name + '.log')).open('x') as output:
            result = subprocess.run(argv, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
        assert result.returncode == 0, 'Inspect retained ' + name + '.log'
    except Exception as exc:
        failure = {'kind': type(exc).__name__, 'error': str(exc)}; raise
    finally:
        save(folder / (name + '.json'), {'command': argv, 'cwd': str(cwd), 'timeout_seconds': timeout,
            'wall_seconds': time.monotonic() - started, 'exit_code': result.returncode if result else None, 'failure': failure})


def tests():
    execute('tests', [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q', *TESTS, '--junitxml=' + str(HERE / 'tests.xml')])
    import xml.etree.ElementTree as ET
    suites = list(ET.parse(HERE / 'tests.xml').getroot().iter('testsuite'))
    assert not any(int(s.get('failures', 0)) or int(s.get('errors', 0)) or int(s.get('skipped', 0)) for s in suites)
    return {'status': 'PASS', 'tests': sum(int(s.get('tests', 0)) for s in suites)}


def ordinary():
    execute('ordinary', [str(ROOT / '.venv/bin/python'), '-B', str(ROOT / 'scripts/prospectus_acquisition_receipt_worker.py'),
        str(ROOT), str(PREP), str(HERE), 'ordinary'], 380)
    return {'status': 'PASS', **read(HERE / 'ordinary-verification.json')}


def package():
    folder = HERE / 'package-source'; folder.mkdir()
    shutil.copyfile(ROOT / 'pyproject.toml', folder / 'pyproject.toml')
    shutil.copytree(ROOT / 'src', folder / 'src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info'))
    python = read(PREP / 'config.json')['package_python']
    execute('wheel', [python, '-I', '-B', '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation',
        '--no-index', '--wheel-dir', str(HERE / 'wheel'), str(folder)])
    wheels = list((HERE / 'wheel').glob('*.whl')); assert len(wheels) == 1
    expected = {str(Path(n).relative_to('src/legalmath')): h for n, h in read(PREP / 'freeze.json')['production'].items()}
    with zipfile.ZipFile(wheels[0]) as archive:
        actual = {n.removeprefix('legalmath/'): digest(archive.read(n)) for n in archive.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
    assert actual == expected
    execute('install', [python, '-I', '-B', '-m', 'pip', 'install', '--no-index', '--no-deps', '--no-compile',
        '--target', str(HERE / 'installed'), str(wheels[0])])
    assert {str(p.relative_to(HERE / 'installed/legalmath')): sha(p) for p in (HERE / 'installed/legalmath').rglob('*') if p.is_file()} == expected
    save(HERE / 'package.json', {'python': python, 'files': expected, 'wheel_sha256': sha(wheels[0])})
    return {'status': 'PASS', 'source_matched_files': len(expected)}


def installed():
    execute('installed', [read(HERE / 'package.json')['python'], '-I', '-B', str(ROOT / 'scripts/prospectus_acquisition_receipt_worker.py'),
        str(ROOT), str(PREP), str(HERE), 'installed'], 380, HERE)
    return {'status': 'PASS', **read(HERE / 'installed-verification.json')}


def states():
    result = {}
    for stage in DEPS:
        folder = HERE / 'stages' / stage
        if (folder / 'result.json').exists(): result[stage] = read(folder / 'result.json')['status']
        elif (folder / 'failure.json').exists(): result[stage] = 'FAIL'
        elif (folder / 'started.json').exists(): result[stage] = 'INTERRUPTED_OR_RUNNING'
        elif any(result.get(d) in ('FAIL', 'BLOCKED') for d in DEPS[stage]): result[stage] = 'BLOCKED'
        else: result[stage] = 'PENDING'
    ready = [s for s in DEPS if result[s] == 'PENDING' and all(result[d] == 'PASS' for d in DEPS[s])]
    if not all(result[s] in ('PASS', 'FAIL', 'BLOCKED') for s in CHECKS): ready = [s for s in ready if s not in ('reconcile', 'seal')]
    return {'stages': result, 'ready': ready, 'whole_build_complete': False}


def reconcile():
    outcome = states()['stages']
    save(HERE / 'original-requirements.json', {'original_task_complete': False, 'obligations': ['G01', 'G20'],
        'remaining': ['Original publication date evidence', 'Edition/source authenticity',
            'Historical legal availability', 'Current final native/recovery acceptance after stabilization'],
        'outcomes': {s: outcome[s] for s in CHECKS}, 'external_adviser_opinion_required': False, 'archive_harness_retried': False})
    return {'status': 'PASS', 'candidate_passed': all(outcome[s] == 'PASS' for s in CHECKS)}


def seal():
    outcome = states()['stages']; assert (HERE / 'RESULT.md').is_file()
    result = {'status': 'PASS' if all(outcome[s] == 'PASS' for s in CHECKS) else 'FAIL',
        'task': 'source-authority', 'original_task_complete': False,
        'result_kind': 'DOWNSTREAM_ACQUISITION_RECEIPT_INTEGRITY', 'resources': costs(),
        'checks': {s: outcome[s] for s in CHECKS},
        'next_action': 'Continue original source-authority/acceptance reconciliation; receipt integrity is not authenticity'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(p) for p in sorted((HERE / 'commands').glob('*.json'))],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU;GPU intentionally hidden',
        'seeds': 'N/A deterministic integrity controls', 'data_version': sha(PREP / 'source-bindings.json'),
        'plan': PLAN, 'result': rel(HERE / 'result.json'), 'resource_accounting': costs()})
    return result


def main():
    action = sys.argv[1]
    if action in ('prepare', 'proposal', 'status'): return states() if action == 'status' else globals()[action]()
    assert action in states()['ready'], 'Stage not ready; inspect retained worker/result'
    frozen(); costs(); started = time.monotonic(); folder = HERE / 'stages' / action
    save(folder / 'started.json', {'command': sys.argv, 'pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat()})
    try:
        result = globals()[action](); frozen(); costs(time.monotonic() - started)
        save(folder / 'result.json', {**result, 'wall_seconds': time.monotonic() - started})
    except Exception as error:
        save(folder / 'failure.json', {'status': 'FAIL', 'kind': type(error).__name__, 'error': str(error), 'wall_seconds': time.monotonic() - started}); raise
    if action == 'seal':
        save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
            if p.is_file() and p.name not in ('admission.json', 'outputs.json') and '__pycache__' not in p.parts
            and not any(n in p.parts for n in ('installed', 'package-source'))})
    return {'status': result['status'], 'stage': action, 'frontier': states(), 'resources': costs()}


if __name__ == '__main__': print(json.dumps(main()))
