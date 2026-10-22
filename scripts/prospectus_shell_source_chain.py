"""Bounded original-source review and source-authority continuation."""
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

PLAN = 'docs/plans/prospectus-shell-source-chain-2026-10-20.md'
PREP = AUTH / 'reviews/shell-source-chain-380'
HERE = AUTH / 'attempts/source-authority/attempt-010'
ORIGINAL = AUTH / 'attempts/finance-conventions/attempt-001'
FINANCE = AUTH / 'attempts/finance-conventions/attempt-013'
SOURCE009 = AUTH / 'attempts/source-authority/attempt-009'
MODULE = 'src/legalmath/prospectus/successor/shell_source_chain.py'
SPEC = 'src/legalmath/prospectus/successor/shell_source_chain_spec.json'
TEST = 'tests/prospectus_successor/test_shell_source_chain.py'
WORKER = 'scripts/prospectus_shell_source_chain_worker.py'
VERIFY = 'scripts/prospectus_shell_source_chain_verify.py'
FILES = [PLAN, rel(Path(__file__)), MODULE, SPEC, TEST, WORKER, VERIFY,
         'src/legalmath/prospectus/successor/service.py',
         'src/legalmath/prospectus/successor/contracts.py']
TESTS = [TEST, 'tests/prospectus_successor/test_acquisition_receipt_integrity.py',
         'tests/prospectus_successor/test_fixed_maturity.py']
CASES = ('global-plain', 'definitive-plain', 'global-principal-only')
DEPS = {'tests': (), 'ordinary': (), 'package': (), 'installed': ('ordinary', 'package'),
        'verify': ('tests', 'ordinary', 'package', 'installed'), 'reconcile': (), 'seal': ('reconcile',)}
CHECKS = ('tests', 'ordinary', 'package', 'installed', 'verify')


def command(name, argv, *, folder=PREP, timeout=20):
    dest = folder / 'commands'
    dest.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    result = None
    error = None
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONDONTWRITEBYTECODE': '1',
           'PYTHONPATH': str(ROOT / 'src') + os.pathsep + str(ROOT), 'PIP_NO_INDEX': '1',
           'PIP_DISABLE_PIP_VERSION_CHECK': '1'}
    try:
        with (dest / (name + '.log')).open('x') as stream:
            result = subprocess.run(argv, cwd=ROOT, env=env, stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=timeout)
        if result.returncode:
            raise RuntimeError('Inspect retained ' + rel(dest / (name + '.log')))
    except Exception as exc:
        error = {'kind': type(exc).__name__, 'reason': str(exc)}
        raise
    finally:
        save(dest / (name + '.json'), {'command': argv, 'cwd': str(ROOT),
             'timeout_seconds': timeout, 'wall_seconds': time.monotonic() - start,
             'exit_code': None if result is None else result.returncode, 'failure': error})


def authenticated(path, folder):
    assert sha(path) == read(folder / 'outputs.json')[str(path.relative_to(folder))], rel(path)
    return read(path)


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    # Command receipts account for every subprocess, including a failed child.
    records = list(PREP.glob('commands/*.json')) + list(HERE.glob('commands/*.json'))
    measured = extra + sum(read(p)['wall_seconds'] for p in records)
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / n for n in FILES)
    paths.add(AUTH / 'revisions/0380.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    total = start['prior_seconds'] + measured + 60
    combined = start['prior_bytes'] + size
    assert measured < 300 and total < 1900, 'Source-chain cumulative time exhausted'
    assert size < 124 * 1024**2 and combined < 380 * 1024**2, 'Source-chain cumulative storage exhausted'
    return {'new_measured_seconds': measured, 'new_conservative_other_seconds': 60,
            'new_bytes': size, 'known006plus_accounted_seconds': total,
            'known006plus_bytes': combined, 'earlier_and_manual_costs': 'UNKNOWN',
            'old_costs_reset': False, 'seal_reserve_bytes': 4 * 1024**2}


def development(label):
    command(label, [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q', TEST,
                    '--junitxml=' + str(PREP / (label + '.xml'))], timeout=60)
    return {'status': 'PASS', 'resources': costs()}


def prepare():
    start = time.monotonic()
    old = read(AUTH / 'program.json')
    assert old['revision'] == 379 and not HERE.exists()
    assert read(PREP / 'commands/development-initial.json')['exit_code'] == 0
    assert read(PREP / 'commands/development-evidence.json')['exit_code'] == 0
    assert (PREP / 'SOURCE-REVIEW.md').exists()
    authority = Authority(ROOT)
    attempts = [e['attempt'] for e in authority.events()
                if e['kind'] == 'ADMIT' and e['budget_key'] == 'source-authority']
    assert len(attempts) == old['budgets']['source-authority']['maximum_new_attempts'] == 9
    inputs = read(PREP / 'source-bindings.json')
    for folder in (ORIGINAL, FINANCE, SOURCE009):
        events = [e for e in authority.events() if e.get('attempt') == rel(folder) and 'outputs_sha256' in e]
        assert events and sha(folder / 'outputs.json') == events[-1]['outputs_sha256']
        inputs[rel(folder / 'outputs.json')] = sha(folder / 'outputs.json')
    for name in CASES:
        packet = AUTH / 'reviews/shell-maturity-361' / (name + '-packet.json.gz')
        assert sha(packet) == read(AUTH / 'reviews/fixed-finance-377/freeze-379.json')['bindings'][rel(packet)]
        inputs[rel(packet)] = sha(packet)
        for kind in ('answer', 'P5'):
            path = FINANCE / 'ordinary' / (name + '-' + kind + '.json.gz')
            value = authenticated(path, FINANCE)
            inputs[rel(path)] = sha(path)
            if kind == 'answer':
                assert 'contract_source_chain' not in value and value['questions']['Q1']['status'] == 'UNKNOWN'
    save(PREP / 'input-bindings.json', inputs)
    save(PREP / 'cases.json', list(CASES))
    save(PREP / 'gap-evidence.json', {'status': 'SOURCE_CHAIN_REPORT_ABSENT',
        'complete_answer_keys': sorted(read(FINANCE / 'ordinary/global-plain-answer.json.gz')),
        'baseline': rel(FINANCE), 'original_sources': rel(ORIGINAL),
        'question_1': 'UNKNOWN', 'finance_status': 'CONDITIONAL',
        'source_reading': rel(PREP / 'SOURCE-REVIEW.md'), 'whole_task_complete': False})
    save(PREP / 'config.json', {'package_python': read(FINANCE / 'package.json')['python']})
    production = {str(p.relative_to(ROOT / 'src/legalmath')): sha(p)
                  for p in (ROOT / 'src/legalmath').rglob('*') if p.is_file()
                  and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}
    prior_map = read(PREP / 'baseline/production.json')
    changes = {n for n, checksum in prior_map.items() if sha(ROOT / n) != checksum}
    assert changes == {'src/legalmath/prospectus/successor/service.py',
                       'src/legalmath/prospectus/successor/contracts.py'}
    assert set(production) - {str(Path(n).relative_to('src/legalmath')) for n in prior_map} == {
        'prospectus/successor/shell_source_chain.py'}
    bindings = {n: sha(ROOT / n) for n in FILES + TESTS + ['pyproject.toml', 'scripts/prospectus_default_holder.py']}
    bindings.update({'src/legalmath/' + n: h for n, h in production.items()})
    bindings.update(inputs)
    bindings.update({rel(p): sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    save(PREP / 'freeze.json', {'bindings': bindings, 'production': production,
         'skeptical_audit': 'PASS: original-source scope, exact baseline preservation, dated trustee contexts, limited precedence and no authenticity promotion',
         'prepared_seconds': time.monotonic() - start})
    new = deepcopy(old)
    new['revision'] = 380
    task = next(t for t in new['tasks'] if t['id'] == 'source-authority')
    task.update(dossier=PLAN, pre_admission_review=rel(PREP / 'SOURCE-REVIEW.md'),
        reason='Carry the reviewed Shell contractual source chain and unresolved agreement/history limits into P2 and the final answer',
        build_criteria_scope=[])
    task['shell_source_chain'] = {'version': 'shell-contract-source-chain.v1',
        'review': rel(PREP), 'freeze': rel(PREP / 'freeze.json'), 'retained_admissions': attempts,
        'whole_task_complete': False, 'automatic_retry': False, 'stage_dependencies': DEPS,
        'completion_dependencies': {'reconcile': list(CHECKS)},
        'bounds': {'new_measured_seconds': 300, 'conservative_control_seconds': 60,
                   'known006plus_seconds': 1900, 'new_bytes': 128 * 1024**2,
                   'known006plus_bytes': 384 * 1024**2, 'seal_reserve_bytes': 4 * 1024**2,
                   'renders': 5, 'consumers_seconds': 90, 'other_child_seconds': 60}}
    task['inputs'] = sorted(set(task['inputs']) | set(bindings) | {rel(PREP / 'freeze.json')})
    new['budgets']['source-authority']['maximum_new_attempts'] = 10
    routes = read(ROOT / old['continuation_review']['routes'])
    routes['baseline_revision'] = 380
    row = next(r for r in routes['tasks'] if r['task'] == 'source-authority')
    row.update(task_sha256=adigest(task), dossier=PLAN,
        remaining='009 byte-integrity repair is retained. The original Shell final/base source relationship and onward agreement limits are absent from the answer.',
        next_action='Execute source-authority010 once; retain exact source history and conditional financial preservation; record/refresh and continue original source work.',
        stop_condition='10 admissions;300+60s/128MiB new;known006+1900s/384MiB;no unchanged retry')
    row = next(r for r in routes['tasks'] if r['task'] == 'finance-conventions')
    row.update(remaining='013 sealed and recorded: current ordinary/installed supported finance passes; source applicability and original wider requirements remain open.',
        next_action='Preserve013. Resolve original source construction and applicability with contextual evidence; do not repeat fraction comparisons or relabel UNKNOWN roles.')
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    new['continuation_review']['bindings'].update({n: sha(ROOT / n) for n in
        (PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'), rel(PREP / 'SOURCE-REVIEW.md'))})
    assert old['obligations'] == new['obligations'] and old['build_contract'] == new['build_contract']
    forecast = costs()['new_bytes'] + 2 * len(json.dumps(new, indent=2, ensure_ascii=False).encode()) + 70 * 1024**2
    assert forecast < 124 * 1024**2, 'Preparation/package storage reservation exceeds bound'
    save(PREP / 'proposal.json', new)
    save(PREP / 'review.json', {'baseline': adigest(old), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Add one original-source relationship report through normal P2 and the final consumer',
                    'Retain dated trustee contexts, limited precedence, missing agreement content and historical unknowns',
                    'Preserve finance013, source-authority001–009, every original obligation and all cumulative costs'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'source_review': rel(PREP / 'SOURCE-REVIEW.md'),
                            'development_result': rel(PREP / 'commands/development-evidence.json'),
                            'forecast_new_bytes': forecast},
        'evidence_contract': {'question': 'Can actual current answers explain the original contractual source chain without promoting source authenticity or financial applicability?',
            'baseline': 'Complete finance013 answers/P5 and original001 source graph/PDFs',
            'primary': 'Complete source groups and independently checked dated relationships; exact financial/assembly preservation and installed equality',
            'promotion_veto': ['Wrong edition/date/actor', 'Lost source qualifier', 'Rehashed report forgery accepted', 'Lost legacy answer', 'Wrong installed origin'],
            'continuation_veto': ['Corrupt original evidence', 'Invalid authority', '1900s/384MiB known006+ exhausted'],
            'explanatory_only': ['Counts', 'Time', 'Storage'],
            'not_concluded': ['Authenticity', 'First publication', 'Actual trustee succession', 'Operative source roles', 'Whole task/build']},
        'budget_revision': {'budget_key': 'source-authority', 'previous_maximum': 9, 'new_maximum': 10,
            'retained_attempts': attempts, 'reason': 'Distinct original contractual-source identity/history gap after009 receipt repair and013 conditional finance',
            'next_discriminating_check': 'Source-qualified actual P2/final explanation with rehashed adverse controls and unchanged conditional arithmetic',
            'stop_condition': task['shell_source_chain']['bounds'],
            'same_scope_authorization': 'User recover and continue the general prospectus build'}})
    return {'status': 'PASS', 'revision': 380, 'resources': costs()}


def frozen():
    admission = read(HERE / 'admission.json')
    assert adigest(read(AUTH / 'program.json')) == admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec']) == admission['binding']
    for name, checksum in read(PREP / 'freeze.json')['bindings'].items():
        assert sha(ROOT / name) == checksum, name


def tests():
    command('tests', [str(ROOT / '.venv/bin/python'), '-m', 'pytest', '-q', *TESTS,
                     '--junitxml=' + str(HERE / 'tests.xml')], folder=HERE, timeout=60)
    from legalmath.prospectus.execution_acceptance import checked_tests
    return {'status': 'PASS', 'tests': checked_tests(HERE / 'tests.xml', 1)}


def ordinary():
    command('ordinary', [str(ROOT / '.venv/bin/python'), '-B', str(ROOT / WORKER),
                         str(ROOT), str(HERE), 'ordinary'], folder=HERE, timeout=90)
    return {'status': 'PASS', 'cases': len(read(HERE / 'ordinary-summary.json')['cases'])}


def package():
    source = HERE / 'package-source'
    source.mkdir()
    shutil.copyfile(ROOT / 'pyproject.toml', source / 'pyproject.toml')
    shutil.copytree(ROOT / 'src', source / 'src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo', '*.egg-info'))
    python = read(PREP / 'config.json')['package_python']
    command('wheel', [python, '-I', '-B', '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation',
                      '--no-index', '--wheel-dir', str(HERE / 'wheel'), str(source)], folder=HERE, timeout=60)
    wheels = list((HERE / 'wheel').glob('*.whl'))
    assert len(wheels) == 1
    expected = read(PREP / 'freeze.json')['production']
    with zipfile.ZipFile(wheels[0]) as archive:
        actual = {n.removeprefix('legalmath/'): digest(archive.read(n)) for n in archive.namelist()
                  if n.startswith('legalmath/') and not n.endswith('/')}
    assert actual == expected
    command('install', [python, '-I', '-B', '-m', 'pip', 'install', '--no-index', '--no-deps', '--no-compile',
                        '--target', str(HERE / 'installed'), str(wheels[0])], folder=HERE, timeout=60)
    installed = HERE / 'installed/legalmath'
    assert {str(p.relative_to(installed)): sha(p) for p in installed.rglob('*') if p.is_file()} == expected
    save(HERE / 'package.json', {'python': python, 'files': expected, 'wheel_sha256': sha(wheels[0])})
    return {'status': 'PASS', 'source_matched_files': len(expected)}


def installed():
    command('installed', [read(HERE / 'package.json')['python'], '-I', '-B', str(ROOT / WORKER),
                          str(ROOT), str(HERE), 'installed'], folder=HERE, timeout=90)
    return {'status': 'PASS', 'cases': len(read(HERE / 'installed-summary.json')['cases'])}


def verify():
    command('verify', [str(ROOT / '.venv/bin/python'), '-B', '-m',
                      'scripts.prospectus_shell_source_chain_verify', str(HERE)], folder=HERE, timeout=60)
    return read(HERE / 'verification.json')


def status():
    states = {}
    for name, deps in DEPS.items():
        folder = HERE / 'stages' / name
        if (folder / 'failure.json').exists():
            states[name] = 'FAIL'
        elif (folder / 'result.json').exists():
            states[name] = read(folder / 'result.json')['status']
        elif (folder / 'started.json').exists():
            states[name] = 'INTERRUPTED_OR_RUNNING'
        elif any(states.get(d) in ('FAIL', 'BLOCKED') for d in deps):
            states[name] = 'BLOCKED'
        else:
            states[name] = 'PENDING'
    ready = [n for n, deps in DEPS.items() if states[n] == 'PENDING' and all(states[d] == 'PASS' for d in deps)]
    if not all(states[n] in ('PASS', 'FAIL', 'BLOCKED') for n in CHECKS):
        ready = [n for n in ready if n not in ('reconcile', 'seal')]
    return {'stages': states, 'ready': ready, 'whole_build_complete': False}


def reconcile():
    outcomes = {n: status()['stages'][n] for n in CHECKS}
    passed = all(v == 'PASS' for v in outcomes.values())
    save(HERE / 'original-requirements.json', {'candidate_passed': passed, 'checks': outcomes,
        'original_task_complete': False, 'original_obligations': ['G01', 'G20'],
        'remaining': ['Original authenticity/publication and historical availability',
                      'Executed agreement/amendment/succession evidence', 'Complete source construction'],
        'external_adviser_opinion_required': False})
    with (HERE / 'RESULT.md').open('x') as stream:
        stream.write(f'''# Shell contractual source chain

The current candidate {'passed' if passed else 'failed'} the required stages:
{outcomes}. Actual commands, full products and answers, adverse inputs and
resource records are retained. Finance013 and source-authority001–009 remain
immutable. Whole source-authority and general-build completion remain false.

The named source reading distinguishes the final terms/memorandum printed
reference, the restricted agreement-precedence rule, and the differently dated
trustee descriptions. A successor definition does not prove an actual succession.
The original executed agreements, authenticity and first publication remain
unestablished. UNKNOWN assembly roles and conditional cash flows are preserved.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| {'Retain source-chain integration' if passed else 'Retain candidate failure'} | Complete source-qualified report, ordinary/installed equality, unchanged questions/assembly: {passed} | See individual stage receipts | Authenticity, executed agreements and source applicability | Record/refresh; continue original source construction | Whole task/build or actual trustee succession |

Post-run red-team: the reading is a named, exposed source interpretation. Exact
byte/anchor checks do not prove completeness of legal construction or authenticity.
A conflicting original, a lost condition, a forged consumed review or changed
financial result would invalidate the relevant result. This package addresses our
missing downstream explanation, with no evidence of a third-party package defect.
There is no stochastic ranking or new automatic default.
''')
    return {'status': 'PASS', 'candidate_passed': passed}


def seal():
    outcomes = {n: status()['stages'][n] for n in CHECKS}
    passed = all(v == 'PASS' for v in outcomes.values())
    resources = costs()
    save(HERE / 'result.json', {'status': 'PASS' if passed else 'FAIL', 'task': 'source-authority',
         'classification': 'NAMED_CONDITIONAL_SOURCE_CHAIN', 'whole_task_complete': False,
         'whole_program_complete': False, 'build_criteria_claimed': [], 'checks': outcomes, 'resources': resources})
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
         'commands': [read(p) for p in sorted((HERE / 'commands').glob('*.json'))],
         'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; GPU intentionally hidden',
         'seeds': 'N/A deterministic', 'data_version': sha(PREP / 'source-bindings.json'),
         'plan': PLAN, 'result': rel(HERE / 'RESULT.md'), 'resources': resources})
    return {'status': 'PASS', 'candidate_status': 'PASS' if passed else 'FAIL', 'resources': resources}


def stage(name):
    assert name in status()['ready'], 'Stage not ready; inspect retained state'
    frozen()
    costs()
    start = time.monotonic()
    folder = HERE / 'stages' / name
    save(folder / 'started.json', {'command': sys.argv, 'pid': os.getpid(),
         'started_at': datetime.now(timezone.utc).isoformat()})
    try:
        result = globals()[name]()
        frozen()
        costs()
        save(folder / 'result.json', {**result, 'wall_seconds': time.monotonic() - start})
    except Exception as exc:
        save(folder / 'failure.json', {'status': 'FAIL', 'type': type(exc).__name__,
             'reason': str(exc), 'wall_seconds': time.monotonic() - start})
        raise
    if name == 'seal':
        save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts})
    return {'result': result, 'frontier': status()}


def sources():
    start = time.monotonic()
    assert read(AUTH / 'program.json')['revision'] == 379
    p1 = authenticated(ORIGINAL / 'source-P1.json.gz', ORIGINAL)
    result = authenticated(FINANCE / 'result.json', FINANCE)
    assert result['status'] == 'PASS' and result['whole_task_complete'] is False
    old_cost = authenticated(SOURCE009 / 'result.json', SOURCE009)['resources']
    save(PREP / 'accounting-start.json', {
        'prior_seconds': old_cost['known006plus_accounted_seconds'],
        'prior_bytes': old_cost['known006plus_bytes'],
        'program_bytes': (AUTH / 'program.json').stat().st_size,
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
        'started_at': datetime.now(timezone.utc).isoformat(),
        'earlier_and_manual_costs': 'UNKNOWN'})
    graph = p1['payload']['graph']
    units = {u['id']: u for u in graph['units']}
    from legalmath.prospectus.successor.occurrences import anchor
    ranges = {
        'final_identity_and_reference': [('shell-2030-final', 1, 25, 39)],
        'base_identity': [('shell-2020-base', 1, 0, 11), ('shell-2020-base', 1, 42, 42)],
        'note_form_and_fixed_selection': [('shell-2030-final', 2, 19, 45)],
        'redemption_and_payment_selection': [('shell-2030-final', 3, 15, 43)],
        'conditions_and_agreements': [('shell-2020-base', 33, 0, 48)],
        'agreement_access_and_precedence': [('shell-2020-base', 34, 8, 22)],
        'programme_trustee': [('shell-2020-base', 26, 15, 18)],
        'global_recipient': [('shell-2020-base', 50, 8, 18)],
    }
    groups = {key: [anchor(units[f'{doc}:p{page}:l{line}'])
                    for doc, page, lo, hi in spans for line in range(lo, hi + 1)]
              for key, spans in ranges.items()}
    docs = [d for d in p1['payload']['request']['bundle']['documents'] if d['id'] != 'hypotheses']
    bindings = {rel(ORIGINAL / 'source-P1.json.gz'): sha(ORIGINAL / 'source-P1.json.gz'),
                rel(ORIGINAL / 'outputs.json'): sha(ORIGINAL / 'outputs.json'),
                rel(FINANCE / 'outputs.json'): sha(FINANCE / 'outputs.json')}
    for doc in docs:
        assert sha(ROOT / doc['path']) == doc['sha256']
        bindings[doc['path']] = doc['sha256']
    spec = {'version': 'shell-contract-source-chain.v1', 'instrument_id': graph['instrument_id'],
            'documents': [{k: d[k] for k in ('id', 'path', 'sha256', 'document_date')} for d in docs],
            'groups': groups}
    save(PREP / 'source-spec.json', spec)
    images = PREP / 'images'
    images.mkdir()
    for doc_id, pages in (('shell-2030-final', (1,)), ('shell-2020-base', (1, 26, 33, 34))):
        doc = next(d for d in docs if d['id'] == doc_id)
        for page in pages:
            stem = images / (doc_id + '-' + str(page))
            command('render-' + doc_id + '-' + str(page),
                    ['pdftoppm', '-f', str(page), '-l', str(page), '-scale-to', '1600',
                     '-png', '-singlefile', doc['path'], rel(stem)])
            bindings[rel(stem.with_suffix('.png'))] = sha(stem.with_suffix('.png'))
    for folder, name in ((ORIGINAL, 'images/final-2.png'), (ORIGINAL, 'images/final-3.png'),
                         (AUTH / 'reviews/shell-maturity-361', 'images/base-50.png')):
        path = folder / name
        if folder == ORIGINAL:
            assert sha(path) == read(ORIGINAL / 'outputs.json')[name]
        else:
            freeze = read(AUTH / 'reviews/fixed-finance-377/freeze-379.json')['bindings']
            assert sha(path) == freeze[rel(path)]
        bindings[rel(path)] = sha(path)
    save(PREP / 'source-bindings.json', bindings)
    save(PREP / 'sources-result.json', {'status': 'PASS', 'groups': list(groups),
         'render_starts': 5, 'retained_images': 3, 'original_extraction_reused': True,
         'wall_seconds': time.monotonic() - start, 'visual_review_complete': False})
    return {'status': 'PASS', 'groups': len(groups), 'render_starts': 5}


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'sources':
        output = sources()
    elif action.startswith('development-'):
        output = development(action)
    elif action == 'prepare':
        output = prepare()
    elif action == 'status':
        output = status()
    elif action in DEPS:
        output = stage(action)
    else:
        raise SystemExit('Unsupported action ' + action)
    print(json.dumps(output))
