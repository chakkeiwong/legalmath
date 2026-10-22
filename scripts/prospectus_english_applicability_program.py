"""Bounded source09 heading repair; original annual interpretation stays open."""
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
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
SOURCE = AUTH / 'attempts/source-bes-dep-09'
PREP = AUTH / 'reviews/english-applicability-439'
WORK = ROOT / '.localresources/prospectus-preparation/english-applicability'
PROBE = ROOT / '.localresources/prospectus-preparation/annual-scope-review-recovery'
FAILED = ROOT / '.localresources/prospectus-preparation/annual-scope-review'
HERE = SOURCE / 'attempt-015'
TASK = 'source-bes-dep-09'
SELF = 'scripts/prospectus_english_applicability_program.py'
PLAN = 'docs/plans/prospectus-english-report-applicability-2026-10-22.md'
TEST = 'tests/prospectus_successor/test_english_report_applicability.py'
CHANGE = 'prospectus/successor/english_report_context.py'
TESTS = [TEST, 'tests/prospectus_successor/test_english_report_context.py',
         'tests/prospectus_successor/test_english_2010_reports.py',
         'tests/prospectus_successor/test_report_scope.py']
SUPPORT = [SELF, PLAN, *TESTS, 'scripts/prospectus_annual_scope_probe.py',
           '.localresources/prospectus-preparation/english-applicability-preflight-failure.json',
           '.localresources/prospectus-preparation/english-applicability-runtime-format-failure.json',
           'docs/plans/prospectus-annual-scope-review-2026-10-22.md',
           'scripts/prospectus_2010_capital_product_cases.py',
           'scripts/prospectus_2010_annual_cases.py', 'pyproject.toml']
LIMITS = {'new_bytes': 192 * 1024**2, 'cumulative_bytes': 448 * 1024**2,
          'reserve_bytes': 2 * 1024**2, 'new_seconds': 337.098758,
          'cumulative_seconds': 1960, 'process_seconds': 90,
          'record_reserve_seconds': 15, 'unchanged_retries': 0, 'changed_recoveries': 1}
PRIOR_BYTES = 224145462
PRIOR_SECONDS = 1576.1191290449352


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    path = Path(path)
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def rel(path):
    return str(Path(path).relative_to(ROOT))


def save(path, value):
    path = Path(path)
    data = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
    if path.suffix == '.gz':
        data = gzip.compress(data, mtime=0)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def inventory(folder):
    return {str(p.relative_to(folder)): sha(p) for p in sorted(folder.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def authority():
    sys.path.insert(0, str(ROOT / 'src'))
    from legalmath.prospectus.execution_authority import Authority
    return Authority(ROOT)


def check_runtime(runtime, expected):
    env = Path(runtime['package_python']).parent.parent
    actual = inventory(env)
    actual['resolved-interpreter'] = sha((env / 'bin/python').resolve())
    require(actual == expected, 'Frozen offline runtime changed')


def prepare():
    a = authority()
    program, _, _ = a.spec()
    require(program['revision'] == 438 and not a.status()['running'], 'Idle438required')
    require(not PREP.exists() and not WORK.exists() and not HERE.exists(), 'No repeated preparation')
    witness = read(PROBE / 'result.json')
    require(witness['status'] == 'DEFECT_REPRODUCED' and witness['false_support_cases'] == 6,
            'Six actual false-support findings required')
    event = next(e for e in reversed(a.events()) if e.get('attempt') == rel(SOURCE / 'attempt-014'))
    require(event['kind'] == 'RECORD' and a.retained_evidence_valid(event), 'Intact recorded014required')
    runtime = read(AUTH / 'reviews/q1-scope-437/freeze.json')['runtime']
    runtime_files = read(AUTH / 'reviews/component-438/frozen.json')['runtime_files']
    check_runtime(runtime, runtime_files)
    save(PREP / 'baseline.json', {'production': inventory(ROOT / 'src/legalmath'),
        'runtime': runtime, 'runtime_files': runtime_files,
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')],
        'program_bytes': (AUTH / 'program.json').stat().st_size,
        'prior_event': event['sha256'], 'prior_outputs_sha256': event['outputs_sha256'],
        'previous_bytes': PRIOR_BYTES, 'previous_seconds': PRIOR_SECONDS,
        'review_seconds': witness['seconds'] + read(FAILED / 'failure.json')['seconds']})
    shutil.copytree(ROOT / 'src/legalmath', WORK / 'candidate/src/legalmath',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    return {'status': 'PREPARED', 'baseline_revision': 438}


def costs():
    start = read(PREP / 'baseline.json')
    paths = {p for d in (WORK, PREP, HERE, PROBE, FAILED) if d.exists()
             for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / p for p in SUPPORT)
    paths.add(ROOT / 'src/legalmath' / CHANGE)
    paths.add(AUTH / 'revisions/0439.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.is_file())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    seconds = sum(read(p)['seconds'] for folder in (PREP, HERE)
                  for p in folder.glob('commands/*.json') if 'seconds' in read(p))
    seconds += 180  # Two retained preflight allocations; actual durations unavailable.
    cumulative_seconds = PRIOR_SECONDS + start['review_seconds'] + seconds
    return {'new_bytes': size, 'cumulative_bytes': PRIOR_BYTES + size,
            'new_measured_seconds': seconds - 180, 'new_charged_seconds': seconds,
            'review_measured_seconds': start['review_seconds'],
            'cumulative_measured_seconds': cumulative_seconds - 180,
            'cumulative_charged_seconds': cumulative_seconds,
            'unmeasured_preflight_charge_seconds': 180,
            'manual_time': 'UNKNOWN; startup/final-receipt exclusions preserved', 'limits': LIMITS,
            'allowed': size + LIMITS['reserve_bytes'] < LIMITS['new_bytes'] and
            PRIOR_BYTES + size + LIMITS['reserve_bytes'] < LIMITS['cumulative_bytes'] and
            seconds < LIMITS['new_seconds'] and cumulative_seconds < LIMITS['cumulative_seconds']}


def command(name, argv, folder, seconds=90, record=False):
    usage = costs()
    reserve = 0 if record else LIMITS['record_reserve_seconds']
    require(usage['allowed'] and usage['new_charged_seconds'] + seconds + reserve <= LIMITS['new_seconds'] and
            usage['cumulative_charged_seconds'] + seconds + reserve <= LIMITS['cumulative_seconds'],
            'Command would spend reserved recording/resource allowance')
    env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONPATH': '',
           'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1',
           'PIP_NO_INDEX': '1', 'PIP_NO_CACHE_DIR': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1',
           'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'}
    folder.mkdir(parents=True, exist_ok=True)
    tick = time.monotonic()
    with (folder / (name + '.log')).open('x') as log:
        child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        save(folder / (name + '-started.json'), {'argv': argv, 'pid': child.pid, 'time_ns': time.time_ns()})
        try:
            code = child.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
            code = -1
    save(folder / (name + '.json'), {'argv': argv, 'exit_code': code, 'seconds': time.monotonic() - tick,
        'environment': {k: env[k] for k in ('CUDA_VISIBLE_DEVICES', 'PYTHONPATH', 'PIP_NO_INDEX')}})
    require(code == 0, 'Inspect retained ' + name + ' failure; no retry authorized')
    require(costs()['allowed'], 'Post-command resource ceiling')


def products(service, packet):
    p1, p2 = packet['P1'], packet['P2']
    p3 = service.interpretation_product(p1, p2, {'source_report_scope': packet['scope']})
    return {'P1': p1, 'P2': p2, 'P3': p3, 'P4': service.law_product(p1, p3),
            'P5': service.financial_product(p1, p2, p3)}


def annual(service, digest):
    from scripts.prospectus_2010_capital_product_cases import configure, original
    from scripts.prospectus_2010_annual_cases import reseal
    configure(ROOT, SOURCE / 'attempt-012')
    ps = original()
    delta = read(SOURCE / 'attempt-012/after-delta.json.gz')
    for phase, addition in delta['payload_additions'].items():
        target = ps[phase]['payload']['request'] if phase == 'P1' else ps[phase]['payload']
        require(not set(target) & set(addition), 'Existing annual addition')
        target.update(addition)
    reseal(ps)
    require({k: v['sha256'] for k, v in ps.items()} == delta['expected_hashes'], 'Original012products differ')
    ref = read(SOURCE / 'attempt-012/answer-delta.json.gz')
    base = ROOT / ref['baseline']['path']
    require(sha(base) == ref['baseline']['file_sha256'], 'Original answer baseline changed')
    expected = {**read(base), **ref['replacements']}
    require(digest(expected) == ref['answer_sha256'], 'Original full answer identity differs')
    answer = service.consume(ps, ROOT, mode='frozen', include_artifacts=True)
    require(answer == expected, 'Complete original annual answer differs')
    return answer, expected, ps, ref


def check_original(answer, expected):
    require(answer == expected, 'Original financial/report meanings changed')
    require(answer['questions']['Q3']['status'] == 'PARTIAL' and not answer['may_execute_transaction'] and
            not answer['independent_legal_acceptance'], 'Unsupported legal promotion')
    cells = answer['source_statement_cells']
    require(not cells['source_context']['all_notes_read'], 'Missing notes promoted')
    require(len([d for d in answer['dependencies'] if d['status'] == 'UNRESOLVED']) >= 14,
            'Original unresolved dependencies lost')


def check_changed(answer, before):
    report, = answer['source_reports']
    require(report['status'] == 'INCOMPLETE_SOURCE_READING' and
            report['english_report_context']['status'] == 'UNRECOGNIZED_OR_CHANGED_SOURCE_READING',
            'Changed report bypasses context')
    require('SUPPLIED_SOURCE_SUPPORT' not in report['use_assessment'].values(), 'False source support remains')
    require(report['facts'] == before['source_reports'][0]['facts'], 'Supplied facts changed')
    skip = {'source_reports', 'report_sha256', 'consumed_products'}
    require({k: v for k, v in answer.items() if k not in skip} ==
            {k: v for k, v in before.items() if k not in skip}, 'Unaffected answer changed')


def changed_values(before, after, path=()):
    if before == after:
        return []
    if isinstance(before, dict) and isinstance(after, dict) and before.keys() == after.keys():
        return [r for k in before for r in changed_values(before[k], after[k], path + (k,))]
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return [r for i, v in enumerate(before) for r in changed_values(v, after[i], path + (i,))]
    return [{'path': list(path), 'value': after}]


def answer_delta(before, answer):
    if before == answer:
        return []
    changes = changed_values(before, answer)
    restored = deepcopy(before)
    for row in changes:
        require(row['path'], 'Whole answer replacement not allowed')
        obj = restored
        for key in row['path'][:-1]:
            obj = obj[key]
        obj[row['path'][-1]] = row['value']
    require(restored == answer, 'Answer delta does not fully reconstruct')
    return changes


def worker(kind):
    is_candidate = kind in ('candidate', 'candidate-recovery')
    target = WORK / 'candidate/src' if is_candidate else HERE / 'installed-package' if kind == 'installed' else ROOT / 'src'
    sys.path.insert(0, str(target))
    from legalmath.prospectus.successor import service
    from legalmath.prospectus.successor.contracts import digest
    folder = WORK / (kind + '-result') if is_candidate else HERE / (kind + '-result')
    folder.mkdir(parents=True, exist_ok=False)
    answer, expected, ps, ref = annual(service, digest)
    check_original(answer, expected)
    original_hash = digest(answer)
    save(folder / 'annual-answer-delta.json.gz', {
        'baseline': {'path': rel(SOURCE / 'attempt-012/answer-delta.json.gz'),
                     'sha256': sha(SOURCE / 'attempt-012/answer-delta.json.gz')},
        'actual_answer_sha256': original_hash, 'changes': answer_delta(expected, answer),
        'complete_reconstruction_equal': True})
    coverage = read(PROBE / 'coverage.json')
    selected = set(answer['source_statement_cells']['source_context']['source_pages'])
    required = set([92, 94, 96, 190, 191]) | set(range(97, 188))
    require(coverage['required_pages'] == sorted(required) and
            coverage['uninterpreted_required_pages'] == sorted(required - selected - {190, 191}),
            'Original96page scope or missing-page bound changed')
    original_ids = {d['id'] for d in ps['P1']['payload']['request']['bundle']['dependencies']}
    deps = {d['id']: d for d in answer['dependencies']}
    require(len(original_ids) == 14 and all(deps[k]['status'] == 'UNRESOLVED' for k in original_ids),
            'Original dependency identities changed')
    save(folder / 'coverage.json', coverage)
    # Each mutant changes the actual original answer, never an expected fixture.
    caught = []
    for label in ('erased-qualification', 'changed-cell', 'erased-unknown', 'false-completion'):
        mutant = dict(answer)
        key = 'source_reports' if label == 'erased-qualification' else 'source_statement_cells'
        mutant[key] = deepcopy(answer[key])
        if label == 'erased-qualification':
            mutant['source_reports'][1]['facts']['conclusion']['spans'] = []
        elif label == 'false-completion':
            mutant['source_statement_cells']['source_context']['all_notes_read'] = True
        else:
            tables = mutant['source_statement_cells']['primary_statements']['profile']['reading']['tables']
            cells = [c for table in tables.values() for row in table['rows'] for c in row['cells']]
            cell = next(c for c in cells if c.get('value') is not None) if label == 'changed-cell' else next(c for c in cells if c.get('value') is None)
            cell['value'] = cell['value'] + 1 if label == 'changed-cell' else 0
        try:
            check_original(mutant, expected)
        except ValueError:
            caught.append(label)
        else:
            raise ValueError('Permissive original checker: ' + label)
    del ps, expected, answer
    rows, representative = [], None
    for path in sorted((PROBE / 'packets').glob('*.json.gz')):
        packet = read(path)
        try:
            actual = service.consume(products(service, packet), ROOT, mode='current', include_artifacts=True)
        except ValueError as error:
            require(packet.get('error') == str(error), 'Unexpected actual-consumer refusal')
            rows.append({'case': path.stem, 'refused': True, 'reason': str(error)})
            continue
        require('answer' in packet, 'Previously refused case became accepted')
        if packet['variant'] == 'paraphrased-title':
            check_changed(actual, packet['answer'])
            representative = (actual, packet['answer'])
        else:
            require(actual == packet['answer'], 'Previously safe exact-title answer changed')
        save(folder / 'answers' / path.name, {
            'baseline': {'path': rel(path), 'sha256': sha(path), 'field': 'answer'},
            'actual_answer_sha256': digest(actual), 'changes': answer_delta(packet['answer'], actual),
            'complete_reconstruction_equal': True})
        rows.append({'case': path.stem, 'refused': False, 'status': actual['source_reports'][0]['status'],
                     'answer_sha256': digest(actual), 'false_support': False,
                     'changed_heading': packet['variant'] == 'paraphrased-title'})
    require(len(rows) == 12 and sum(r.get('changed_heading', False) for r in rows) == 6,
            'Original12case denominator changed')
    actual, before = representative
    for label in ('reintroduced-support', 'changed-question'):
        mutant = deepcopy(actual)
        if label == 'reintroduced-support':
            key = next(iter(mutant['source_reports'][0]['use_assessment']))
            mutant['source_reports'][0]['use_assessment'][key] = 'SUPPLIED_SOURCE_SUPPORT'
        else:
            mutant['questions']['Q3']['status'] = 'SUPPORTED'
        try:
            check_changed(mutant, before)
        except ValueError:
            caught.append(label)
        else:
            raise ValueError('Permissive changed-answer checker: ' + label)
    result = {'status': 'PASS', 'whole_original_answer_sha256': original_hash, 'cases': rows,
              'false_support_cases_withheld': 6, 'original_safe_cases_preserved': 6,
              'adverse_answer_checks': caught, 'missing_required_pages_at_least': 82,
              'original_dependencies_unresolved': 14, 'task_complete': False}
    origins = {}
    for name, module in sorted(sys.modules.items()):
        if name == 'legalmath' or name.startswith('legalmath.'):
            filename = getattr(module, '__file__', None)
            if filename:
                path = Path(filename).resolve()
                require(path.is_relative_to((target / 'legalmath').resolve()), 'Wrong import origin: ' + name)
                origins[name] = {'path': str(path), 'sha256': sha(path)}
    require(sys.flags.isolated == 1, 'Worker must be isolated')
    if not is_candidate:
        require(result == read(WORK / 'candidate-recovery-result/result.json'), 'Current/installed result differs')
    save(folder / 'imports.json', {'modules': origins, 'executable': sys.executable, 'isolated': True})
    save(folder / 'result.json', result)
    return {'status': 'PASS', 'kind': kind, 'imports': len(origins)}


def trial():
    code = ('import sys; from pathlib import Path; r=Path.cwd(); '
            'sys.path[:0]=[str(r/".localresources/prospectus-preparation/english-applicability/candidate/src"),str(r)]; '
            'import pytest; raise SystemExit(pytest.main(' + repr(['-q', '-p', 'no:cacheprovider', *TESTS,
            '--junitxml=' + str(WORK / 'tests.xml')]) + '))')
    command('tests', [str(ROOT / '.venv/bin/python'), '-I', '-B', '-c', code], PREP / 'commands', 60)
    command('candidate', [str(ROOT / '.venv/bin/python'), '-I', '-B', str(ROOT / SELF), 'worker', '--kind', 'candidate'], PREP / 'commands', 45)
    return {'status': 'PASS', 'costs': costs()}


def recovery():
    require(read(PREP / 'commands/candidate.json')['exit_code'] == 1 and
            "KeyError: 'rows'" in (PREP / 'commands/candidate.log').read_text(), 'Expected retained harness failure required')
    command('candidate-recovery', [str(ROOT / '.venv/bin/python'), '-I', '-B', str(ROOT / SELF),
                                  'worker', '--kind', 'candidate-recovery'], PREP / 'commands', 30)
    return {'status': 'PASS', 'changed_recovery_consumed': True, 'costs': costs()}


def freeze():
    a = authority()
    from legalmath.prospectus.execution_authority import digest
    old, _, _ = a.spec()
    latest = {e['task']: e for e in a.events() if e.get('task')}
    require(old['revision'] == 438 and all(e['kind'] not in ('ADMIT', 'LAUNCH', 'START') for e in latest.values()), 'Idle438required')
    require(all(read(PREP / 'commands' / (n + '.json'))['exit_code'] == 0 for n in ('tests', 'candidate-recovery')), 'Passing candidate required')
    baseline = read(PREP / 'baseline.json')
    candidate = inventory(WORK / 'candidate/src/legalmath')
    require(inventory(ROOT / 'src/legalmath') == baseline['production'], 'Baseline changed')
    require({n for n in candidate if candidate[n] != baseline['production'].get(n)} == {CHANGE} and
            candidate.keys() == baseline['production'].keys(), 'Only declared production module may change')
    evidence = {p: sha(ROOT / p) for p in SUPPORT}
    evidence[rel(PREP / 'failed-candidate-method.py')] = sha(PREP / 'failed-candidate-method.py')
    evidence.update({rel(p): sha(p) for p in (PREP / 'commands').glob('*') if p.is_file()})
    for folder in (WORK, PROBE, FAILED, SOURCE / 'attempt-002', SOURCE / 'attempt-003', SOURCE / 'attempt-012', SOURCE / 'attempt-014'):
        # Keep historical evidence identity without repeatedly expanding package copies.
        selected = [folder / 'outputs.json'] if (folder / 'outputs.json').exists() else list(folder.rglob('*'))
        evidence.update({rel(p): sha(p) for p in selected if p.is_file() and '__pycache__' not in p.parts})
    evidence.update({'src/legalmath/' + n: h for n, h in candidate.items()})
    save(PREP / 'freeze.json', {'evidence': evidence, 'candidate': candidate, 'baseline': baseline['production'],
                              'runtime': baseline['runtime'], 'limits': LIMITS})
    proposal = deepcopy(old)
    proposal['revision'] = 439
    task = next(t for t in proposal['tasks'] if t['id'] == TASK)
    task.update(dossier=PLAN, pre_admission_review=PLAN, english_applicability_review=rel(PREP / 'freeze.json'),
                reason='Withhold six reproduced false report-support findings while preserving complete original annual answer')
    task['inputs'] = sorted(set(task['inputs']) | set(evidence) | {rel(PREP / 'freeze.json'), rel(PREP / 'baseline.json')})
    attempts = [e['attempt'] for e in a.events() if e['kind'] == 'ADMIT' and e['budget_key'] == TASK]
    require(len(attempts) == old['budgets'][TASK]['maximum_new_attempts'] == 14, 'Retain14original admissions')
    proposal['budgets'][TASK]['maximum_new_attempts'] = 15
    routes = read(ROOT / old['continuation_review']['routes'])
    routes['baseline_revision'] = 439
    for row in routes['tasks']:
        if row['task'] == TASK:
            row.update(task_sha256=digest(task), dossier=PLAN, phase=0,
                remaining='At least82of96required annual pages lack interpreted readings; finite report repair does not complete source09.',
                next_action='Complete heading repair, then inspect missing original note content and design the next substantive source reading within remaining cumulative limits.',
                stop_condition='Admission015; changed harness recovery consumed; no further retry;337.098758new/1960cumulative seconds;192MiBnew/448MiBcumulative.')
        elif row['task'] == 'source-bes-dep-05':
            row.update(phase=3, remaining='438accepted individual-unit-conflict on its exact package; production change makes current inventory binding stale.',
                next_action='Preserve438as historical evidence; batch finite-criterion refresh after substantive source changes.')
    save(PREP / 'routes.json', routes)
    proposal['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    if 'src/legalmath/' + CHANGE in proposal['continuation_review']['bindings']:
        proposal['continuation_review']['bindings']['src/legalmath/' + CHANGE] = candidate[CHANGE]
    proposal['continuation_review']['bindings'].update({p: sha(ROOT / p) for p in (SELF, PLAN, rel(PREP / 'freeze.json'), rel(PREP / 'routes.json'))})
    save(PREP / 'proposal.json', proposal)
    save(PREP / 'review.json', {'baseline': digest(old), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Finite conservative heading guard for actual false-support cases', 'Original scope and history preserved'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'candidate': rel(WORK / 'candidate-recovery-result/result.json'),
            'baseline': 'complete012answer, verified014and retained438review', 'production_changes': [CHANGE]},
        'evidence_contract': {'primary': 'Six false findings withheld; six safe cases and full annual answer preserved',
            'promotion_veto': ['Meaning/source/import mismatch', 'Unsupported completion'],
            'continuation_veto': ['Invalid authority', 'Corrupt common evidence', 'Resource limit'],
            'explanatory': ['Test counts', 'Runtime'], 'not_concluded': ['General report recognition', 'Legal truth', 'Whole task complete']},
        'budget_revision': {'budget_key': TASK, 'previous_maximum': 14, 'new_maximum': 15, 'retained_attempts': attempts,
            'reason': 'Distinct actual-consumer applicability defect; honest current-package build requires cumulative storage220to448MiB',
            'next_discriminating_check': 'Fresh ordinary and installed complete original answer and12retained consumer cases',
            'stop_condition': LIMITS, 'same_scope_authorization': 'Recover and continue original prospectus build; no external action'}})
    package_bytes = sum((ROOT / 'src/legalmath' / n).stat().st_size for n in candidate)
    forecast = costs()['new_bytes'] + 4 * (PREP / 'proposal.json').stat().st_size + 4 * package_bytes + 16 * 1024**2
    require(forecast + LIMITS['reserve_bytes'] < LIMITS['new_bytes'] and
            PRIOR_BYTES + forecast + LIMITS['reserve_bytes'] < LIMITS['cumulative_bytes'], 'Final storage forecast exceeds reviewed bound')
    save(PREP / 'forecast.json', {'new_bytes': forecast, 'cumulative_bytes': PRIOR_BYTES + forecast,
        'accepted_revision_admission_build_install_wheel_manifests_record_included': True})
    return {'status': 'FROZEN', 'forecast_new_bytes': forecast}


def cutover():
    a = authority()
    from legalmath.prospectus.execution_authority import digest
    freeze = read(PREP / 'freeze.json')
    require(digest(a.spec()[0]) == read(PREP / 'review.json')['baseline'], 'Baseline revision changed')
    require(inventory(ROOT / 'src/legalmath') == freeze['baseline'], 'Production changed')
    shutil.copyfile(WORK / 'candidate/src/legalmath' / CHANGE, ROOT / 'src/legalmath' / CHANGE)
    require(inventory(ROOT / 'src/legalmath') == freeze['candidate'], 'Cutover differs')
    save(PREP / 'cutover.json', {'changed': [CHANGE], 'revision_required': 439})
    return {'status': 'CUTOVER_COMPLETE_REVISION_REQUIRED'}


def admitted():
    a = authority()
    p, tasks, _ = a.spec()
    require(p['revision'] == 439 and read(HERE / 'admission.json')['binding'] == a.binding(tasks[TASK]), 'Current439admission required')
    require(next(e for e in reversed(a.events()) if e.get('task') == TASK)['kind'] == 'ADMIT', 'Attempt already terminal')
    require(not (HERE / 'outputs.json').exists(), 'Attempt already sealed')


def stage(kind):
    admitted()
    freeze = read(PREP / 'freeze.json')
    if kind == 'package':
        source = HERE / 'package-source'
        source.mkdir()
        shutil.copyfile(ROOT / 'pyproject.toml', source / 'pyproject.toml')
        shutil.copytree(ROOT / 'src', source / 'src', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info'))
        python = freeze['runtime']['package_python']
        command('wheel', [python, '-I', '-B', '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation', '--no-index',
                          '--wheel-dir', str(HERE / 'wheel'), str(source)], HERE / 'commands', 20)
        wheel, = (HERE / 'wheel').glob('*.whl')
        with zipfile.ZipFile(wheel) as archive:
            files = {n.removeprefix('legalmath/'): hashlib.sha256(archive.read(n)).hexdigest()
                     for n in archive.namelist() if n.startswith('legalmath/') and not n.endswith('/')}
        require(files == freeze['candidate'], 'Wheel differs from reviewed production')
        command('install', [python, '-I', '-B', '-m', 'pip', 'install', '--no-index', '--no-deps', '--no-compile',
                            '--target', str(HERE / 'installed-package'), str(wheel)], HERE / 'commands', 20)
        require(inventory(HERE / 'installed-package/legalmath') == files, 'Installed package differs')
        save(HERE / 'package.json', {'status': 'PASS', 'files': files, 'wheel': {'path': rel(wheel), 'sha256': sha(wheel)}})
    else:
        if kind == 'installed':
            require(read(HERE / 'package.json')['status'] == 'PASS', 'Installed package required')
        python = freeze['runtime']['package_python' if kind == 'installed' else 'ordinary_python']
        command(kind, [python, '-I', '-B', str(ROOT / SELF), 'worker', '--kind', kind], HERE / 'commands', 30)
    return {'status': 'PASS', 'stage': kind, 'costs': costs()}


def seal():
    admitted()
    freeze = read(PREP / 'freeze.json')
    require(all(sha(ROOT / p) == h for p, h in freeze['evidence'].items()), 'Frozen evidence changed')
    baseline = read(PREP / 'baseline.json')
    check_runtime(baseline['runtime'], baseline['runtime_files'])
    require(inventory(ROOT / 'src/legalmath') == freeze['candidate'] == inventory(HERE / 'installed-package/legalmath'), 'Package changed')
    require(read(HERE / 'ordinary-result/result.json') == read(HERE / 'installed-result/result.json'), 'Actual consumers differ')
    a = authority()
    event = next(e for e in a.events() if e['sha256'] == baseline['prior_event'])
    require(a.retained_evidence_valid(event), 'Sealed014changed')
    require((HERE / 'RESULT.md').is_file(), 'Substantive result note required')
    usage = costs()
    save(HERE / 'result.json', {'task': TASK, 'status': 'PASS', 'task_complete': False,
        'whole_program_complete': False, 'costs': usage, 'plan': PLAN})
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [rel(p) for p in (HERE / 'commands').glob('*.json')],
        'preparation_commands': [rel(p) for p in (PREP / 'commands').glob('*.json')],
        'environment': freeze['runtime'], 'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1',
        'data_version': rel(PREP / 'freeze.json'), 'random_seeds': 'N/A deterministic',
        'wall_seconds': usage['new_measured_seconds'], 'plan': PLAN, 'result': rel(HERE / 'RESULT.md')})
    outputs = {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    require(costs()['new_bytes'] + len(json.dumps(outputs).encode()) + 1024**2 + LIMITS['reserve_bytes'] < LIMITS['new_bytes'], 'Final manifest reserve')
    save(HERE / 'outputs.json', outputs)
    require(costs()['allowed'], 'Post-seal ceiling')
    return {'status': 'SEALED', 'costs': costs()}


def record():
    command('authority-record', [str(ROOT / '.venv/bin/python'), '-B', '-m', 'scripts.prospectus_control',
                                'record', '--attempt', rel(HERE)], PREP / 'commands', 15, record=True)
    a = authority()
    event = next(e for e in reversed(a.events()) if e.get('attempt') == rel(HERE))
    require(event['kind'] == 'RECORD' and a.retained_evidence_valid(event), 'Partial result not intact/recorded')
    save(PREP / 'post-record.json', {'event': event, 'costs': costs(), 'task_complete': False})
    return {'status': 'RECORDED', 'costs': costs()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'trial', 'recovery', 'worker', 'freeze', 'cutover', 'stage', 'seal', 'record', 'costs'])
    parser.add_argument('--kind', choices=['candidate', 'candidate-recovery', 'ordinary', 'package', 'installed'])
    args = parser.parse_args()
    started = time.monotonic()
    result = worker(args.kind) if args.action == 'worker' else stage(args.kind) if args.action == 'stage' else globals()[args.action]()
    if args.action in ('prepare', 'freeze', 'cutover', 'seal'):
        save(PREP / 'commands' / (args.action + '.json'), {'seconds': time.monotonic() - started,
             'action': args.action, 'argv': sys.argv, 'environment': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1'})
    print(json.dumps(result), flush=True)
