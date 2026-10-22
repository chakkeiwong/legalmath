"""Prepare and exercise the optional annual accounting-note reading."""
import argparse
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from scripts.prospectus_annual_basis_source import AUTH, SOURCE, WORK, PLAN, read, sha, save
from scripts.prospectus_annual_basis_reading import PROFILE, NEW_PAGES, combine
from scripts.prospectus_annual_basis_checks import check, mutations, require

PREP = AUTH / 'reviews/annual-basis-440'
HERE = SOURCE / 'attempt-016'
SELF = 'scripts/prospectus_annual_basis_program.py'
READING = 'scripts/prospectus_annual_basis_reading.py'
CHECKS = 'scripts/prospectus_annual_basis_checks.py'
TEST = 'tests/prospectus_successor/test_annual_basis_estimates.py'
FIXTURE = 'tests/prospectus_successor/fixtures/bes_annual2010_statement_cells_v3.json.gz'
CHANGE = 'prospectus/successor/statement_cells.py'
OLD_FIXTURE = 'tests/prospectus_successor/fixtures/bes_annual2010_statement_cells_v2.json.gz'


def inventory(folder):
    return {str(p.relative_to(folder)): sha(p) for p in sorted(folder.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def candidate():
    start = time.monotonic()
    require(not PREP.exists() and not (WORK / 'candidate').exists(), 'No repeated candidate preparation')
    require(read(AUTH / 'program.json')['revision'] == 439, 'Current439required')
    prepared = read(WORK / 'preparation.json')
    require(sha(ROOT / PLAN) == prepared['plan_sha256'], 'Source-review plan changed')
    graph = read(SOURCE / 'attempt-002/original-P1.json.gz')['payload']['graph']
    old = read(ROOT / OLD_FIXTURE)
    reference = read(SOURCE / 'attempt-012/after-delta.json.gz')['payload_additions']['P1']['source_statement_cells']
    require(old['reading'] == reference['reading'], 'Original fixture differs from consumed012reading')
    combined = combine(old['reading'], graph)
    check(combined['basis_estimates_pronouncements'], graph)
    pages = combined['source_context']['source_pages']
    selected = sorted([u for u in graph['units'] if u['document'] == 'bes-2010-en' and u['page'] in pages],
                      key=lambda u: (u['page'], u['order'], u['id']))
    entry = {'document': 'bes-2010-en', 'source': prepared['pdf_sha256'], 'reading': fingerprint(combined),
             'pages_digest': fingerprint(selected), 'pages': pages, 'occurrences': len(selected),
             'reading_fields': ['primary_statements', 'eps_cash_notes', 'capital_notes', 'basis_estimates_pronouncements']}
    save(ROOT / FIXTURE, {'graph': {'units': selected}, 'reading': combined})
    baseline = inventory(ROOT / 'src/legalmath')
    shutil.copytree(ROOT / 'src/legalmath', WORK / 'candidate/src/legalmath',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    target = WORK / 'candidate/src/legalmath' / CHANGE
    body = target.read_text()
    require(body.count('PROFILES = {\n') == 1 and PROFILE not in body, 'Unexpected profile insertion point')
    target.write_text(body.replace('PROFILES = {\n', 'PROFILES = {\n    ' + repr(PROFILE) + ': ' + repr(entry) + ',\n', 1))
    save(PREP / 'candidate.json', {'status': 'PREPARED', 'baseline': baseline, 'candidate': inventory(WORK / 'candidate/src/legalmath'),
        'profile': entry, 'source_plan': PLAN, 'fixture': FIXTURE, 'fixture_sha256': sha(ROOT / FIXTURE),
        'source_preparation_sha256': sha(WORK / 'preparation.json'), 'old_fixture_sha256': sha(ROOT / OLD_FIXTURE),
        'prior_charged_seconds': prepared['prior_charged_seconds'], 'seconds': time.monotonic() - start})
    return {'status': 'CANDIDATE_PREPARED', 'source_occurrences': len(selected), 'source_pages': pages}


def costs():
    prepared = read(WORK / 'preparation.json')
    seconds = prepared['seconds']
    seconds += sum(read(p)['seconds'] for p in WORK.glob('render-*.json'))
    if (PREP / 'candidate.json').exists():
        seconds += read(PREP / 'candidate.json')['seconds']
    seconds += sum(read(p)['seconds'] for folder in (PREP, HERE) for p in folder.glob('commands/*.json') if 'seconds' in read(p))
    files = {p for folder in (WORK, PREP, HERE) if folder.exists() for p in folder.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    files.update(ROOT / n for n in (SELF, READING, CHECKS, TEST, FIXTURE, PLAN, 'scripts/prospectus_annual_basis_source.py'))
    size = sum(p.stat().st_size for p in files if p.is_file())
    return {'new_seconds': seconds, 'cumulative_charged_seconds': prepared['prior_charged_seconds'] + seconds,
            'new_bytes': size, 'cumulative_bytes': prepared['prior_bytes'] + size,
            'allowed': seconds < 600 and prepared['prior_charged_seconds'] + seconds < 2560 and
            size + 2 * 1024**2 < 128 * 1024**2 and prepared['prior_bytes'] + size + 2 * 1024**2 < 448 * 1024**2}


def command(name, argv, folder, limit=60):
    state = costs()
    require(state['allowed'] and state['new_seconds'] + limit < 600 and
            state['cumulative_charged_seconds'] + limit < 2560, 'Substantive resource ceiling')
    folder.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONPATH': '', 'PYTHONNOUSERSITE': '1',
           'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'PIP_NO_INDEX': '1',
           'PIP_NO_CACHE_DIR': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1'}
    started = time.monotonic()
    with (folder / (name + '.log')).open('x') as log:
        child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        save(folder / (name + '-started.json'), {'argv': argv, 'pid': child.pid, 'time_ns': time.time_ns()})
        try:
            code = child.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
            code = -1
    save(folder / (name + '.json'), {'argv': argv, 'exit_code': code, 'seconds': time.monotonic() - started,
                                  'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1'})
    require(code == 0, 'Inspect retained ' + name + ' failure before any reviewed recovery')
    require(costs()['allowed'], 'Post-command resource ceiling')


def trial():
    code = ('import sys; from pathlib import Path; r=Path.cwd(); '
            'sys.path[:0]=[str(r/".localresources/prospectus-preparation/annual-basis/candidate/src"),str(r)]; '
            'import pytest; raise SystemExit(pytest.main(' + repr(['-q', '-p', 'no:cacheprovider', TEST,
              'tests/prospectus_successor/test_statement_cells.py',
              'tests/prospectus_successor/test_english_report_applicability.py',
              '--junitxml=' + str(WORK / 'tests.xml')]) + '))')
    command('tests', [str(ROOT / '.venv/bin/python'), '-I', '-B', '-c', code], PREP / 'commands')
    command('candidate', [str(ROOT / '.venv/bin/python'), '-I', '-B', str(ROOT / SELF), 'worker', '--kind', 'candidate'], PREP / 'commands')
    return {'status': 'PASS', 'costs': costs()}


def worker(kind, part='all'):
    is_candidate = kind in ('candidate', 'candidate-recovery')
    target = WORK / 'candidate/src' if is_candidate else HERE / 'installed-package' if kind == 'installed' else ROOT / 'src'
    sys.path.insert(0, str(target))
    from legalmath.prospectus.successor import service, statement_cells
    from legalmath.prospectus.successor.contracts import digest
    from scripts import prospectus_english_applicability_program as earlier
    from scripts.prospectus_2010_capital_product_cases import p1_from, rebuild, configure
    configure(ROOT, SOURCE / 'attempt-012')
    folder = WORK / (kind + '-' + part) if is_candidate else HERE / (kind + '-' + part)
    folder.mkdir(parents=True, exist_ok=False)
    if part != 'answer':
        return controls(service, statement_cells, digest, p1_from, kind, part, folder, target)
    before, expected, ps, ref = earlier.annual(service, digest)
    earlier.check_original(before, expected)
    before_hash = digest(before)
    require(before_hash == read(SOURCE / 'attempt-015/ordinary-result/result.json')['whole_original_answer_sha256'], 'Complete015baseline changed')
    del expected
    fixture = read(ROOT / FIXTURE)
    req = deepcopy(ps['P1']['payload']['request'])
    graph = ps['P1']['payload']['graph']
    req['source_statement_cells'] = {**req['source_statement_cells'], 'profile': PROFILE, 'reading': fixture['reading'],
        'review': {'kind': 'DEVELOPMENT', 'reviewer': 'retained annual source review',
                   'reason': 'Preserve primary/EPS/cash/capital readings; add attributed Note2.1, Note3 and Note46 meanings'}}
    supplied = req['source_statement_cells']
    built = rebuild(ps, p1_from(req, graph))
    answer = service.consume(built, ROOT, mode='frozen', include_artifacts=True)
    changed_keys = {'source_statement_cells', 'request_sha256', 'report_sha256', 'consumed_products'}
    require({k: v for k, v in answer.items() if k not in changed_keys} ==
            {k: v for k, v in before.items() if k not in changed_keys}, 'Unrelated complete annual answer changed')
    old_cells = before['source_statement_cells']
    cells = answer['source_statement_cells']
    for key in ('primary_statements', 'eps_cash_notes', 'capital_notes'):
        require(cells[key] == old_cells[key], 'Old financial meaning changed: ' + key)
    require(cells['basis_estimates_pronouncements'] == fixture['reading']['basis_estimates_pronouncements'], 'New source meanings not consumed')
    meaning_proof = check(cells['basis_estimates_pronouncements'], graph)
    require(cells['source_context']['all_notes_read'] is False and
            not answer['independent_legal_acceptance'] and not answer['may_execute_transaction'] and
            answer['questions']['Q3']['status'] == 'PARTIAL', 'Unsupported whole-task/transaction promotion')
    del built
    changes = earlier.answer_delta(before, answer)
    save(folder / 'answer-delta.json.gz', {'baseline': {'path': str((SOURCE / 'attempt-012/answer-delta.json.gz').relative_to(ROOT)),
        'sha256': sha(SOURCE / 'attempt-012/answer-delta.json.gz')}, 'original_answer_sha256': before_hash,
        'actual_answer_sha256': digest(answer), 'changes': changes, 'complete_reconstruction_equal': True})
    actual_hash = digest(answer)
    save(folder / 'request.json.gz', req)
    save(folder / 'source-reference.json', {'path': str((SOURCE / 'attempt-002/original-P1.json.gz').relative_to(ROOT)),
                                          'sha256': sha(SOURCE / 'attempt-002/original-P1.json.gz')})
    result = {'status': 'PASS', 'original_annual_answer_sha256': before_hash,
              'optional_annual_answer_sha256': actual_hash, 'meaning_proof': meaning_proof,
              'all_notes_read': False, 'task_complete': False}
    if kind == 'candidate-recovery':
        require(read(WORK / 'candidate-result/answer-delta.json.gz') == read(folder / 'answer-delta.json.gz'),
                'Recovered complete answer differs from interrupted answer')
    finish(result, folder, target, kind, part)
    return {'status': 'PASS', 'worker': kind, 'part': part}


def finish(result, folder, target, kind, part):
    origins = {}
    for name, module in sys.modules.copy().items():
        filename = getattr(module, '__file__', None)
        if filename and (name == 'legalmath' or name.startswith('legalmath.')):
            path = Path(filename).resolve()
            require(path.is_relative_to((target / 'legalmath').resolve()), 'Wrong project import: ' + name)
            origins[name] = {'path': str(path), 'sha256': sha(path)}
    require(sys.flags.isolated == 1, 'Isolated interpreter required')
    if kind != 'candidate-recovery':
        require(result == read(WORK / ('candidate-recovery-' + part) / 'result.json'), 'Candidate/current/installed result differs')
    save(folder / 'result.json', result)
    save(folder / 'imports.json', {'modules': origins, 'executable': sys.executable, 'isolated': True})


def controls(service, statement_cells, digest, p1_from, kind, part, folder, target):
    from scripts import prospectus_english_applicability_program as earlier
    base = WORK / 'candidate-recovery-answer' if kind == 'candidate-recovery' else HERE / (kind + '-answer')
    require(read(base / 'result.json')['status'] == 'PASS', 'Matched answer required first')
    reference = read(base / 'source-reference.json')
    require(sha(ROOT / reference['path']) == reference['sha256'], 'Original whole source changed')
    graph = read(ROOT / reference['path'])['payload']['graph']
    req = read(base / 'request.json.gz')
    supplied = req['source_statement_cells']
    fixture = read(ROOT / FIXTURE)
    caught, public = [], []
    for name, altered in mutations(fixture['reading']['basis_estimates_pronouncements']):
        public_names = {'public-a': 'ifric12-date', 'public-b': 'ifrs9-adoption', 'public-c': 'lost-ifric18-body'}
        if part not in ('controls',) and public_names.get(part) != name:
            continue
        try:
            check(altered, graph)
        except ValueError:
            pass
        else:
            raise ValueError('Semantic checker accepted ' + name)
        bad = deepcopy(supplied)
        bad['reading']['basis_estimates_pronouncements'] = altered
        try:
            statement_cells.admit(graph, bad)
        except ValueError as exc:
            require('reading differs' in str(exc), 'Wrong refusal for ' + name)
            caught.append(name)
        else:
            raise ValueError('Production accepted altered meaning ' + name)
        if part in public_names:
            changed_request = deepcopy(req)
            changed_request['source_statement_cells'] = bad
            try:
                service.construction_product(p1_from(changed_request, graph), ROOT)
            except ValueError as exc:
                require('reading differs' in str(exc), 'Wrong public refusal for ' + name)
                public.append(name)
            else:
                raise ValueError('Actual construction accepted ' + name)
    if part != 'english':
        result = {'status': 'PASS', 'semantic_mutations_refused': caught, 'public_construction_refusals': public}
        finish(result, folder, target, kind, part)
        return {'status': 'PASS', 'worker': kind, 'part': part, 'controls': len(caught)}
    del graph, req, supplied
    earlier_cases = read(SOURCE / 'attempt-015/ordinary-result/result.json')['cases']
    english = []
    for path in sorted((earlier.PROBE / 'packets').glob('*.json.gz')):
        packet = read(path)
        prior = next(r for r in earlier_cases if r['case'] == path.stem)
        try:
            actual = service.consume(earlier.products(service, packet), ROOT, mode='current', include_artifacts=True)
        except ValueError as exc:
            require(prior['refused'] and prior['reason'] == str(exc), 'English refusal changed')
            english.append({'case': path.stem, 'refused': True})
        else:
            require(not prior['refused'] and digest(actual) == prior['answer_sha256'], 'Complete439English answer changed')
            english.append({'case': path.stem, 'refused': False, 'answer_sha256': digest(actual)})
    result = {'status': 'PASS', 'english_regressions': english}
    finish(result, folder, target, kind, part)
    return {'status': 'PASS', 'worker': kind, 'part': part, 'cases': len(english)}


def recovery(part):
    require(read(PREP / 'commands/candidate.json')['exit_code'] == -1, 'Retained timeout required')
    command('candidate-recovery-' + part, [str(ROOT / '.venv/bin/python'), '-I', '-B', str(ROOT / SELF),
        'worker', '--kind', 'candidate-recovery', '--part', part], PREP / 'commands')
    return {'status': 'PASS', 'part': part, 'costs': costs()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['candidate', 'trial', 'recovery', 'worker', 'costs'])
    parser.add_argument('--kind', choices=['candidate', 'candidate-recovery', 'ordinary', 'installed'])
    parser.add_argument('--part', choices=['answer', 'controls', 'public-a', 'public-b', 'public-c', 'english'])
    args = parser.parse_args()
    result = worker(args.kind, args.part) if args.action == 'worker' else recovery(args.part) if args.action == 'recovery' else globals()[args.action]()
    print(json.dumps(result), flush=True)
