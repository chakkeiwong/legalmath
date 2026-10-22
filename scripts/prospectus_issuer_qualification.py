"""Reviewed source-bound issuer qualification preparation and staged trial."""
from copy import deepcopy
from datetime import datetime, timezone
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile
from scripts.prospectus_default_holder import ROOT, AUTH, read, save, sha, rel, digest, adigest, Authority

PREP = AUTH / 'reviews/issuer-qualification-365'
HERE = AUTH / 'attempts/basf-references/attempt-100'
PLAN = 'docs/plans/prospectus-issuer-qualification-2026-10-20.md'
BASE = AUTH / 'attempts/basf-meanings/attempt-023'
FILES = [PLAN, 'scripts/prospectus_issuer_qualification.py', 'scripts/prospectus_issuer_qualification_worker.py',
    'tests/prospectus_successor/test_issuer_qualification.py',
    'src/legalmath/prospectus/successor/issuer_qualification.py',
    'src/legalmath/prospectus/successor/issuer_qualification_verify.py',
    'src/legalmath/prospectus/successor/service.py', 'src/legalmath/prospectus/successor/conditional_profiles.py']
DEPS = {'source': (), 'tests': (), 'ordinary': ('source',), 'package': (),
    'installed': ('ordinary', 'package'), 'reconcile': (), 'seal': ('reconcile',)}
CHECKS = ('source', 'tests', 'ordinary', 'package', 'installed')


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    timed = [PREP / 'development.json', PREP / 'preparation-result.json']
    timed += list(HERE.glob('stages/*/result.json')) + list(HERE.glob('stages/*/failure.json'))
    seconds = extra + sum(read(p).get('wall_seconds', 0) for p in timed if p.exists())
    files = {p for d in (PREP, HERE) for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    files.update(ROOT / n for n in FILES); files.add(AUTH / 'revisions/0365.json')
    files.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in files if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    total = start['prior']['combined_accounted_seconds'] + seconds + 120
    combined = start['prior']['combined_bytes'] + size
    assert seconds < 1000 and size < 176 * 1024**2, 'Incremental trial ceiling'
    assert total < 28000 and combined < 4348 * 1024**2, 'Cumulative trial ceiling'
    return {'combined_accounted_seconds': total, 'combined_bytes': combined,
        'new_measured_seconds': seconds, 'new_conservative_other_seconds': 120, 'new_bytes': size,
        'old_costs_reset': False, 'manual_earlier_time': 'UNKNOWN', 'seal_reserve_bytes': 4 * 1024**2}


def prepare():
    started = time.monotonic()
    from legalmath.prospectus.successor import issuer_qualification as model
    from legalmath.prospectus.successor.issuer_qualification_verify import qualification
    reproduction = read(PREP / 'reproduction.json'); assert not reproduction['optional_argument_exists']
    for name, checksum in read(BASE / 'outputs.json').items(): assert sha(BASE / name) == checksum, name
    manifest = read(ROOT / reproduction['products'])['products']
    for row in manifest.values(): assert sha(ROOT / row['path']) == row['sha256']
    products = {k: read(ROOT / r['path']) for k, r in manifest.items()}
    ordinary = read(ROOT / reproduction['baseline'])
    rows = [{'id': 'all-open', 'base_case': 'all-open', 'qualification': dict.fromkeys(model.FACTS)}]
    expected = {'all-open': 'UNKNOWN'}
    examples = [
        ('german-domestic', 'GERMANY', 'ONLY_GERMANY_ORGANISED', None, 'YES'),
        ('german-excluded', 'GERMANY', 'ONLY_OTHER_EU_EEA', True, 'NO'),
        ('german-no-foreign-duty', 'GERMANY', 'ONLY_OTHER_EU_EEA', False, 'YES'),
        ('foreign-duty-open', 'GERMANY', 'ONLY_OTHER_EU_EEA', None, 'UNKNOWN'),
        ('german-mixed-admission', 'GERMANY', 'NEITHER_EXCLUSIVE', None, 'YES'),
        ('other-home-german-only', 'OTHER_EU_EEA', 'ONLY_GERMANY_ORGANISED', None, 'YES'),
        ('other-home-mixed', 'OTHER_EU_EEA', 'NEITHER_EXCLUSIVE', False, 'NO'),
        ('neither-home', 'NEITHER', None, None, 'NO'),
        ('home-open', None, 'ONLY_GERMANY_ORGANISED', False, 'UNKNOWN'),
        ('home-conflict', 'conflict', 'ONLY_GERMANY_ORGANISED', False, 'CONFLICT'),
        ('admission-conflict', 'GERMANY', 'conflict', False, 'CONFLICT'),
        ('foreign-duty-conflict', 'GERMANY', 'ONLY_OTHER_EU_EEA', 'conflict', 'CONFLICT'),
    ]
    for name, h, a, d, status in examples:
        rows.append({'id': name, 'base_case': 'complete-statutory-route',
            'qualification': dict(zip(model.FACTS, (h, a, d)))})
        expected[name] = status
    for base in ('interpretations-diverge', 'implementing_rules_satisfied-None',
                 'conventional-route-unknown-statute', 'website-still-open'):
        for suffix, duty, status in (('included', False, 'YES'), ('excluded', True, 'NO')):
            name = base + '-' + suffix
            rows.append({'id': name, 'base_case': base, 'qualification':
                dict(zip(model.FACTS, ('GERMANY', 'ONLY_OTHER_EU_EEA', duty)))})
            expected[name] = status
    for row in rows: assert qualification(row['qualification'])['status'] == expected[row['id']]
    profile = {'version': model.VERSION, 'products_sha256': digest(products),
        'ordinary_answer_sha256': digest(ordinary), 'context': model.source_context(ordinary, ROOT), 'scenarios': rows}
    save(PREP / 'profile.json', profile); save(PREP / 'expected.json', {'qualification': expected, 'candidate_derived': False})
    options = read(ROOT / reproduction['profiles'])
    options['profiles'].append({'name': 'issuer_qualification', 'path': rel(PREP / 'profile.json'),
        'file_sha256': sha(PREP / 'profile.json'), 'profile_sha256': digest(profile)})
    save(PREP / 'profiles.json', options)
    source_paths = [ROOT / reproduction[n] for n in ('baseline', 'products', 'profiles')] + [BASE / 'outputs.json']
    source_paths += [ROOT / row['path'] for row in manifest.values()]
    source_paths += [ROOT / row['path'] for row in options['profiles']]
    source_paths += [ROOT / name for name in reproduction['source_files']]
    save(PREP / 'source-bindings.json', {rel(p): sha(p) for p in source_paths})
    save(PREP / 'preparation-result.json', {'status': 'PASS', 'scenarios': len(rows), 'wall_seconds': time.monotonic() - started})
    return {'status': 'PASS', 'scenarios': len(rows), 'resources': costs()}


def proposal():
    program = read(AUTH / 'program.json'); assert program['revision'] == 364 and not HERE.exists()
    attempts = [e['attempt'] for e in Authority(ROOT).events() if e['kind'] == 'ADMIT' and e.get('budget_key') == 'basf-references']
    assert len(attempts) == 99
    production = {rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}
    bindings = {n: sha(ROOT / n) for n in FILES}
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    bindings.update(production); bindings.update(read(PREP / 'source-bindings.json'))
    save(PREP / 'freeze.json', {'bindings': bindings, 'production': production})
    new = deepcopy(program); new['revision'] = 365
    task = next(t for t in new['tasks'] if t['id'] == 'basf-references')
    task.update(dossier=PLAN, pre_admission_review=PLAN, timeout_seconds=380,
        reason='Expose current section2(14) issuer routes and exceptions through existing publication consumer',
        issuer_qualification_continuation={'review': rel(PREP), 'original_task_complete': False,
            'new_seconds': 1000, 'conservative_other_seconds': 120, 'new_bytes': 180 * 1024**2,
            'cumulative_seconds': 28000, 'cumulative_bytes': 4352 * 1024**2}, build_criteria_scope=[])
    task['inputs'] = list(dict.fromkeys(task['inputs'] + list(bindings) + [rel(PREP / 'freeze.json')]))
    new['budgets']['basf-references']['maximum_new_attempts'] = 100
    routes = read(ROOT / program['continuation_review']['routes']); routes['baseline_revision'] = 365
    for row in routes['tasks']:
        if row['task'] == 'basf-references':
            row.update(dossier=PLAN, task_sha256=adigest(task),
                next_action='Verify explicit issuer prerequisites in complete ordinary and installed answers; retain source gaps',
                stop_condition='100 admissions;1000+120s/180MiB new;28000s/4352MiB cumulative;no unchanged retry')
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    new['continuation_review']['bindings'].update({n: sha(ROOT / n) for n in (PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'))})
    review = {'baseline': adigest(program), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Source-bound issuer qualification feeds existing publication analysis', 'Finite budget extension with all old costs retained'],
        'skeptical_audit': {'verdict': 'PASS', 'review': PLAN, 'existing_bundled_premise_declared_wrong': False},
        'evidence_contract': {'primary': 'Complete preceding answer preserved and independently checked issuer/publication decisions in ordinary and installed CLI',
            'promotion_veto': ['Wrong result', 'Lost uncertainty/source', 'Changed prior answer', 'Permissive corruption control', 'Wrong imports'],
            'continuation_veto': ['Invalid authority', 'Corrupt shared evidence', 'Exhausted bounds'],
            'explanatory_only': ['Counts', 'Time', 'Smoke checks'],
            'not_concluded': ['Actual issuer status', 'Historical law', 'Exhaustive legal interpretation', 'Whole build']},
        'budget_revision': {'budget_key': 'basf-references', 'previous_maximum': 99, 'new_maximum': 100,
            'retained_attempts': attempts, 'reason': 'Distinct reproduced conditional prerequisite capability with real consumer validation',
            'next_discriminating_check': 'Source exception changes downstream answer while prior complete answer remains unchanged',
            'stop_condition': '1000+120s/180MiB new;28000s/4352MiB cumulative;380s consumers;120s other children',
            'same_scope_authorization': 'User authorized internally proved general build and continuation; no new live call'}}
    save(PREP / 'proposal.json', new); save(PREP / 'review.json', review)
    return {'status': 'PASS', 'revision': 365, 'frozen_files': len(bindings), 'resources': costs()}


def frozen():
    admission = read(HERE / 'admission.json')
    assert adigest(read(AUTH / 'program.json')) == admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec']) == admission['binding']
    for name, checksum in read(PREP / 'freeze.json')['bindings'].items(): assert sha(ROOT / name) == checksum, name


def execute(name, argv, timeout=120, cwd=ROOT):
    folder = HERE / 'commands'; folder.mkdir(exist_ok=True); started = time.monotonic()
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONPATH': str(ROOT / 'src'),
        'PYTHONDONTWRITEBYTECODE': '1', 'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1'}
    result = None; error = None
    try:
        with (folder / (name + '.log')).open('x') as output:
            result = subprocess.run(argv, cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=timeout)
        assert result.returncode == 0, 'Inspect retained ' + name + '.log'
    except Exception as exc:
        error = {'type': type(exc).__name__, 'message': str(exc)}; raise
    finally:
        save(folder / (name + '.json'), {'command': argv, 'cwd': str(cwd), 'timeout_seconds': timeout,
            'wall_seconds': time.monotonic() - started, 'exit_code': result.returncode if result else None, 'failure': error})


def source():
    from legalmath.prospectus.successor import issuer_qualification as model
    from legalmath.prospectus.successor.issuer_qualification_verify import verify_answer
    request = read(PREP / 'reproduction.json')
    products = {k: read(ROOT / r['path']) for k, r in read(ROOT / request['products'])['products'].items()}
    ordinary = read(ROOT / request['baseline']); profile = read(PREP / 'profile.json')
    body = {k: v for k, v in ordinary.items() if k != 'report_sha256'}
    body.update(model.evaluate(products, ordinary, profile, ROOT, expected_profile_sha256=digest(profile)))
    check = verify_answer({**body, 'report_sha256': digest(body)}, ordinary, profile, expected_profile_sha256=digest(profile))
    controls = []
    for kind in ('source-copy', 'product-pin'):
        altered = deepcopy(profile)
        if kind == 'source-copy': altered['context']['complete_current_section2'] += ' changed'
        else: altered['products_sha256'] = '0' * 64
        try: model.evaluate(products, ordinary, altered, ROOT, expected_profile_sha256=digest(altered))
        except ValueError as error: controls.append({'kind': kind, 'reason': str(error)})
        else: raise AssertionError('Corrupt source/profile accepted')
    before = ast.parse((PREP / 'baseline/service.py').read_text())
    after = ast.parse((ROOT / 'src/legalmath/prospectus/successor/service.py').read_text())
    funcs = lambda tree: {n.name: ast.dump(n) for n in tree.body if isinstance(n, ast.FunctionDef)}
    a, b = funcs(before), funcs(after); assert a.keys() == b.keys() and all(a[k] == b[k] for k in a if k != 'consume')
    save(HERE / 'source-verification.json', {**check, 'controls': controls, 'actual_cli': False})
    return {'status': 'PASS', **check, 'source_controls': len(controls)}


def tests():
    execute('tests', [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q',
        'tests/prospectus_successor/test_issuer_qualification.py', 'tests/prospectus_successor/test_conditional_profiles_cli.py',
        '--junitxml=' + str(HERE / 'tests.xml')])
    import xml.etree.ElementTree as ET
    suites = ET.parse(HERE / 'tests.xml').getroot(); assert not any(int(s.get('errors', 0)) or int(s.get('failures', 0)) for s in suites)
    return {'status': 'PASS', 'tests': sum(int(s.get('tests', 0)) for s in suites)}


def ordinary():
    execute('ordinary', [str(ROOT / '.venv/bin/python'), '-B', str(ROOT / 'scripts/prospectus_issuer_qualification_worker.py'),
        str(ROOT), str(PREP), str(HERE), 'ordinary'], 380)
    return {'status': 'PASS', **read(HERE / 'ordinary-verification.json')}


def package():
    folder = HERE / 'package-source'; folder.mkdir()
    shutil.copyfile(ROOT / 'pyproject.toml', folder / 'pyproject.toml')
    shutil.copytree(ROOT / 'src', folder / 'src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info'))
    python = read(BASE / 'package.json')['python']
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
    execute('installed', [read(HERE / 'package.json')['python'], '-I', '-B',
        str(ROOT / 'scripts/prospectus_issuer_qualification_worker.py'), str(ROOT), str(PREP), str(HERE), 'installed'], 380, HERE)
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
    save(HERE / 'original-requirements.json', {'original_task_complete': False,
        'remaining': ['Historical law/application', 'Election effectiveness and missing sections4/5',
            'Implementing ordinance', 'Original onward reference/source coverage', 'Actual issuer facts after build'],
        'outcomes': {s: outcome[s] for s in CHECKS}, 'external_adviser_opinion_required': False})
    return {'status': 'PASS', 'candidate_passed': all(outcome[s] == 'PASS' for s in CHECKS)}


def seal():
    outcome = states()['stages']; assert (HERE / 'RESULT.md').is_file()
    result = {'status': 'PASS' if all(outcome[s] == 'PASS' for s in CHECKS) else 'FAIL',
        'task': 'basf-references', 'original_task_complete': False,
        'result_kind': 'CONDITIONAL_ISSUER_QUALIFICATION_PUBLICATION_INTEGRATION', 'resources': costs(),
        'checks': {s: outcome[s] for s in CHECKS},
        'next_action': 'Review remaining original references and source-authority gaps; keep historical and missing source conditions open'}
    save(HERE / 'result.json', result)
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(p) for p in sorted((HERE / 'commands').glob('*.json'))],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU;GPU intentionally hidden',
        'seeds': 'N/A deterministic categorical enumeration', 'data_version': sha(PREP / 'source-bindings.json'),
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
