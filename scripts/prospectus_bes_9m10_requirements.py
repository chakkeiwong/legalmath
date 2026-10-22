"""Named original-source review; no automatic whole-task acceptance."""
from collections import Counter
from copy import deepcopy
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from scripts.prospectus_default_holder import ROOT, AUTH, read, sha, rel, adigest, Authority

PLAN = 'docs/plans/prospectus-bes-9m10-requirements-2026-10-21.md'
PREP = AUTH / 'reviews/bes-9m10-requirements-382'
BASE = AUTH / 'attempts/source-bes-dep-01'
HERE = BASE / 'attempt-006'
TRANSCRIPT = AUTH / 'reviews/bes-statement-cells-117/printed-cells.tsv'
SELF = rel(Path(__file__))
PDF = '44938fcd6622d7c9ea5466636052a286da42c42cb440cf9f71590fbde71fb841'
PERIODS = {37: ['2009-09-30', '2009-12-31', '2010-09-30'],
           38: ['nine_months_ended_2009-09-30', 'nine_months_ended_2010-09-30']}
WINDOWS = {37: [(350, 435), (435, 490), (490, 550)], 38: [(410, 480), (485, 550)]}
BODY = {37: (168, 730), 38: (227, 670)}


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else encoded(value)).hexdigest()


def same(left, right):
    if encoded(left) != encoded(right):
        raise ValueError('Complete typed values differ')


def save(path, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
    if len(data) > 1024**2:
        raise ValueError('One-MiB per-output reservation exceeded before write')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def reference(path):
    return {'path': rel(path), 'sha256': sha(path)}


def production():
    return {rel(p): sha(p) for p in (ROOT / 'src/legalmath').rglob('*') if p.is_file()
            and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo')}


def resources(reserve=0):
    start = read(PREP / 'accounting-start.json')
    paths = {p for folder in (PREP, HERE) for p in folder.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / p for p in (PLAN, SELF))
    paths.add(AUTH / 'revisions/0382.json')
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    elapsed = sum(read(p)['wall_seconds'] for p in HERE.glob('commands/*.json'))
    return {'new_bytes': size, 'reserved_bytes': reserve,
        'new_measured_seconds': elapsed, 'new_conservative_control_seconds': 60,
        'known_attempt_and_new_bytes': start['prior_attempt_bytes'] + size,
        'known_recorded_seconds_with_new_allowance': start['prior_recorded_seconds'] + elapsed + 60,
        'older_manual_network_and_support_costs': 'UNKNOWN', 'old_costs_reset': False,
        'execution_allowed': size + reserve < 62 * 1024**2
            and start['prior_attempt_bytes'] + size + reserve < 158 * 1024**2 and elapsed < 240}


def authenticated_baseline():
    events = Authority(ROOT).events()
    bindings = {}
    for number in range(1, 6):
        folder = BASE / ('attempt-' + str(number).zfill(3))
        records = [e for e in events if e.get('attempt') == rel(folder) and 'outputs_sha256' in e]
        assert records and sha(folder / 'outputs.json') == records[-1]['outputs_sha256']
        bindings[rel(folder / 'outputs.json')] = sha(folder / 'outputs.json')
        for name, checksum in read(folder / 'outputs.json').items():
            assert sha(folder / name) == checksum, rel(folder / name)
    return bindings


def prepare():
    old = read(AUTH / 'program.json')
    assert old['revision'] == 381 and not PREP.exists() and not HERE.exists()
    bindings = authenticated_baseline()
    p1 = read(BASE / 'attempt-002/original-P1.json.gz')
    for doc in p1['payload']['request']['bundle']['documents']:
        assert sha(ROOT / doc['path']) == doc['sha256']
        bindings[doc['path']] = doc['sha256']
    # Use each historical work timer once. No total is invented for unmeasured work.
    timers = [BASE / 'attempt-001' / n for n in ('consumer-result.json', 'repair-result.json', 'source-result.json')]
    previous_seconds = sum(read(p)['wall_seconds'] for p in timers)
    for number in range(2, 6):
        path = BASE / ('attempt-' + str(number).zfill(3)) / 'run-manifest.json'
        value = read(path)['wall_seconds']
        previous_seconds += sum(value.values()) if isinstance(value, dict) else value
        timers.append(path)
    prior_bytes = sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    save(PREP / 'accounting-start.json', {'prior_attempt_bytes': prior_bytes,
        'prior_recorded_seconds': previous_seconds, 'timer_sources': [reference(p) for p in timers],
        'older_manual_network_and_support_costs': 'UNKNOWN',
        'program_bytes': (AUTH / 'program.json').stat().st_size,
        'history_names': [p.name for p in (AUTH / 'history').glob('*.json')]})
    names = [PLAN, SELF, rel(TRANSCRIPT), 'scripts/prospectus_default_holder.py',
        'docs/plans/prospectus-source-chain-storage-failure-2026-10-21.md',
        rel(AUTH / 'attempts/source-authority/attempt-011/result.json'),
        rel(AUTH / 'attempts/source-authority/attempt-011/outputs.json')]
    names += [rel(BASE / 'attempt-001' / n) for n in ('release-p37.png', 'release-p38.png',
        'introducer-p37.png', 'release-p1.png', 'IMAGE-REVIEW.md', 'acquisition.json')]
    names += [rel(BASE / 'attempt-002' / n) for n in ('original-P1.json.gz', 'original-P2.json.gz',
        'actual-P3.json.gz', 'actual-P4.json.gz', 'actual-P5.json.gz', 'actual-current-answer-components.json.gz')]
    names += [rel(BASE / 'attempt-005' / n) for n in ('after-products.json.gz', 'answer-reconstruction.json',
        'answer-addition.json', 'matched_consumer.py')]
    names += [rel(p) for p in (BASE / 'attempt-004').glob('control-*.json')]
    names.append(rel(BASE / 'attempt-004/cell-reading.json'))
    origin = next(o for o in old['obligations'] if o['id'] == 'BES-DEP-01')['origin']
    names.append(origin['path'])
    bindings.update({n: sha(ROOT / n) for n in names})
    bindings.update(production())
    save(PREP / 'freeze.json', {'bindings': bindings, 'production': production(),
        'original_requirement': origin, 'check': 'bes-9m10-source-review.v1'})
    attempts = [e['attempt'] for e in Authority(ROOT).events()
                if e['kind'] == 'ADMIT' and e['budget_key'] == 'source-bes-dep-01']
    assert len(attempts) == old['budgets']['source-bes-dep-01']['maximum_new_attempts'] == 5
    new = deepcopy(old)
    new['revision'] = 382
    task = next(t for t in new['tasks'] if t['id'] == 'source-bes-dep-01')
    task.update(dossier=PLAN, pre_admission_review=PLAN,
        reason='Reconcile original9M2010 source requirements with independent full source-map checks and actual current consumers',
        build_criteria_scope=[])
    bounds = {'new_measured_seconds': 240, 'conservative_control_seconds': 60,
        'new_bytes': 64 * 1024**2, 'known_attempt_and_new_bytes': 160 * 1024**2,
        'failure_reserve_bytes': 2 * 1024**2, 'diagnostic_child_seconds': 120,
        'per_stage_output_reserve': 1024**2, 'no_unchanged_retry': True}
    task['requirements_review'] = {'check': 'bes-9m10-source-review.v1',
        'freeze': rel(PREP / 'freeze.json'), 'retained_admissions': attempts, 'bounds': bounds,
        'success_dependencies': {'source': [], 'consumer': []},
        'completion_dependencies': {'reconcile': ['source', 'consumer']}, 'original_task_acceptance': False}
    task['inputs'] = sorted(set(task['inputs']) | set(bindings) | {rel(PREP / 'freeze.json')})
    new['budgets']['source-bes-dep-01']['maximum_new_attempts'] = 6
    routes = read(ROOT / old['continuation_review']['routes'])
    routes['baseline_revision'] = 382
    row = next(r for r in routes['tasks'] if r['task'] == 'source-authority')
    row.update(phase=6, remaining='011 functional tests/workers passed but campaign storage exceeded128MiB incremental and384MiB cumulative; independent verifier blocked.',
        next_action='No further source-authority execution under spent ceiling. Preserve010/011 failures and execute independent source tasks; future source work needs a reviewed resource decision.',
        stop_condition='Known006+storage417642327bytes before bookkeeping exceeds402653184byte ceiling; no retry or reset.')
    row = next(r for r in routes['tasks'] if r['task'] == task['id'])
    row.update(task_sha256=adigest(task), dossier=PLAN, phase=0,
        remaining='Conditional203-cell/304-target integration exists; current source-to-answer correctness and exact original acceptance requirements need named review.',
        next_action='Execute source01 attempt006 source/consumer checks and completion-only original-requirement reconciliation; record/refresh and continue independent original work.',
        stop_condition='6 admissions;240+60s,64MiB new including authority;160MiB known retained plus new;no unchanged retry.')
    save(PREP / 'routes.json', routes)
    new['continuation_review'].update(plan=PLAN, routes=rel(PREP / 'routes.json'))
    new['continuation_review']['bindings'].update({n: sha(ROOT / n) for n in (PLAN, rel(PREP / 'routes.json'), rel(PREP / 'freeze.json'))})
    assert old['obligations'] == new['obligations'] and old['build_contract'] == new['build_contract']
    # Authority proposal/revision are the only large outputs: measure their bytes exactly.
    proposal = (json.dumps(new, ensure_ascii=False, indent=2) + '\n').encode()
    forecast = resources()['new_bytes'] + 2 * len(proposal) + 10 * 1024**2
    assert forecast < 62 * 1024**2 and prior_bytes + forecast < 158 * 1024**2
    with (PREP / 'proposal.json').open('xb') as stream:
        stream.write(proposal)
    save(PREP / 'review.json', {'baseline': adigest(old), 'scope_unchanged': True, 'budget_unchanged': False,
        'changes': ['Retain source-authority011 failed storage campaign and move independent original source01 to frontier',
            'Add named full source-map/current-consumer requirement check; no production or source reinterpretation',
            'Preserve all original obligations, five source01 attempts and resource/failure history'],
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN, 'forecast_new_bytes': forecast,
            'false_positive_prevention': 'Complete comparisons, separately parsed original source and explicit unresolved original acceptance'},
        'evidence_contract': {'question': 'Which original9M2010 source requirements survive actual current consumption?',
            'baseline': 'Source01 attempts002/004/005, original images/304occurrences and203-cell independent transcription',
            'primary': 'All literal/source/period qualifiers and complete actual consumer equality; all actual adverse checks',
            'promotion_veto': ['Lost source/meaning', 'Unexpected complete-answer change', 'Forged consumed reading'],
            'continuation_veto': ['Corrupt originals', 'Invalid authority', 'Spent reviewed bounds'],
            'not_concluded': ['Authenticity', 'Original publication', 'Financial truth', 'Whole task/build']},
        'budget_revision': {'budget_key': 'source-bes-dep-01', 'previous_maximum': 5, 'new_maximum': 6,
            'retained_attempts': attempts, 'reason': 'Named original-requirement reconciliation and current-consumer review after broad service changes',
            'next_discriminating_check': 'Independent source-map validation and exact complete current consumer comparisons',
            'stop_condition': bounds, 'same_scope_authorization': 'User recover and continue original prospectus build'}})
    return {'status': 'PREPARED', 'revision': 382, 'resources': resources()}


def anchor_check(source, units):
    unit = units[source['source_unit']]
    words = [w for w in unit['words'] if source['start'] <= w['start'] and w['end'] <= source['end']]
    assert words and unit['visible'] is True and source['source_sha256'] == unit['source_sha256'] == PDF
    assert source['quote'] == unit['raw'][source['start']:source['end']]
    assert source['page'] == unit['page']
    same(source['word_spans'], [[w['start'], w['end']] for w in words])
    same(source['bbox'], [min(w['bbox'][0] for w in words), min(w['bbox'][1] for w in words),
        max(w['bbox'][2] for w in words), max(w['bbox'][3] for w in words)])
    return unit, words


def check_reading(reading, graph, specs):
    """Independent source/literal check; production only matches protected hashes."""
    units = {u['id']: u for u in graph['units'] if u['document'] == 'bes-release-9m10' and u['page'] in (37, 38)}
    assert len(units) == 304 and reading['source_sha256'] == PDF
    assert len(reading['rows']) == len(specs) == 77
    assert Counter(r['page'] for r in reading['rows']) == {37: 49, 38: 28}
    used = []
    unknown = 0
    for row, spec in zip(reading['rows'], specs):
        page = int(spec['page'])
        assert (row['row_id'], row['page'], row['label']) == (spec['row'], page, spec['label'])
        label, _ = anchor_check(row['label_source'], units)
        assert row['label_source']['quote'] == row['label']
        is_ecb = row['row_id'] == 'ecb_memorandum'
        is_discontinued = row['row_id'] == 'discontinued_memorandum'
        assert row['non_additive'] is (is_ecb or is_discontinued)
        assert row['parent_row'] == ('central_bank_deposits' if is_ecb else 'net_income' if is_discontinued else None)
        assert row['role'] == ('MEMORANDUM_QUANTITY' if is_ecb else 'MEMORANDUM_SIGNED' if is_discontinued else 'REPORTED')
        assert len(row['cells']) == len(PERIODS[page])
        for index, cell in enumerate(row['cells']):
            unit, words = anchor_check(cell['source'], units)
            quote = spec[('first', 'second', 'third')[index]]
            assert cell['source']['quote'] == quote
            assert cell['period'] == PERIODS[page][index] and cell['unit'] == 'EUR_thousands'
            lo, hi = WINDOWS[page][index]
            assert all(lo <= (w['bbox'][0] + w['bbox'][2]) / 2 < hi
                and abs(w['bbox'][1] - label['bbox'][1]) < 2 for w in words)
            literal = ''.join(quote.split())
            if literal == '-':
                assert cell['status'] == 'PRINTED_DASH_UNKNOWN' and cell['value'] is None and cell['magnitude'] is None
                unknown += 1
            else:
                negative = literal.startswith('(') and literal.endswith(')')
                magnitude = int(literal.strip('()'))
                assert type(cell['magnitude']) is int and cell['magnitude'] == magnitude
                if is_ecb:
                    assert negative and cell['value'] is None and cell['status'] == 'MEMORANDUM_MAGNITUDE'
                    assert cell['sign_context'] == 'PARENTHESIZED_SUBSET_NO_ADDITIVE_SIGN_INFERRED'
                else:
                    assert cell['status'] == 'PRINTED_AMOUNT' and type(cell['value']) is int
                    assert cell['value'] == (-magnitude if negative else magnitude)
                    assert cell['sign_context'] == ('PARENTHESIZED_NEGATIVE' if negative else 'POSITIVE_PRINTED')
            used.extend((unit['id'], w['start'], w['end']) for w in words)
    all_tokens = [(u['id'], w['start'], w['end']) for u in units.values()
        if BODY[u['page']][0] <= u['bbox'][1] <= BODY[u['page']][1]
        and u['bbox'][0] >= WINDOWS[u['page']][0][0] for w in u['words']]
    assert len(used) == len(set(used)) == 468 and Counter(used) == Counter(all_tokens)
    assert unknown == 23
    for page, labels in ((37, ['Set, 09', 'Dez, 09', 'Set, 10']), (38, ['Set.09', 'Set.10'])):
        head = reading['headers'][str(page)]
        same(head['periods'], PERIODS[page])
        assert [a['quote'] for a in head['headers']] == labels
        assert len(head['units']) == len(labels) and all(a['quote'] == "(eur '000)" for a in head['units'])
        for source in head['headers'] + head['units']:
            anchor_check(source, units)
    same(reading['source_context'], {'unaudited_source': True,
        'title_difference': {'prospectus': '9H10', 'release': '9M10', 'silently_corrected': False},
        'incorporation_status': 'UNRESOLVED', 'independent_financial_review': False, 'arithmetic_role': 'EXPLANATORY_ONLY'})
    return {'rows': 77, 'cells': 203, 'numeric_tokens': 468, 'target_occurrences': 304, 'unknown_dashes': unknown}


def source_worker():
    graph = read(BASE / 'attempt-002/original-P1.json.gz')['payload']['graph']
    with TRANSCRIPT.open() as stream:
        specs = list(csv.DictReader(stream, delimiter='\t'))
    reading = read(BASE / 'attempt-004/cell-reading.json')
    counts = check_reading(reading, graph, specs)
    controls = []
    for path in sorted((BASE / 'attempt-004').glob('control-*.json')):
        try:
            check_reading(read(path), graph, specs)
        except (AssertionError, ValueError, KeyError) as exc:
            controls.append({'input': reference(path), 'refused': True, 'reason': type(exc).__name__})
        else:
            raise ValueError('Independent checker accepted ' + path.name)
    assert len(controls) == 9
    save(HERE / 'source-check.json', {'status': 'PASS', 'check': 'bes-9m10-source-review.v1',
        'counts': counts, 'controls': controls, 'original_task_acceptance': False,
        'images_reviewed': [reference(BASE / 'attempt-001' / name) for name in ('release-p37.png', 'release-p38.png')]})


def restore_answer():
    folder = BASE / 'attempt-002'
    packet = read(folder / 'actual-current-answer-components.json.gz')
    result = {}
    for key in packet['key_order']:
        if key in packet['inline']:
            result[key] = packet['inline'][key]
        else:
            entry = packet['components'][key]
            path = folder / entry['path']
            assert sha(path) == entry['sha256']
            value = read(path)
            for selector in entry['selector']:
                value = value[selector]
            result[key] = value
    raw = json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
    assert digest(raw) == packet['original_uncompressed_sha256']
    result['assessment_mode'] = 'frozen'
    result['report_sha256'] = digest({k: v for k, v in result.items() if k != 'report_sha256'})
    return result


def first_difference(left, right, path='$'):
    if type(left) is not type(right):
        return {'path': path, 'reason': 'type', 'before': type(left).__name__, 'after': type(right).__name__}
    if isinstance(left, dict):
        if left.keys() != right.keys():
            return {'path': path, 'reason': 'keys', 'missing': sorted(left.keys() - right.keys()), 'added': sorted(right.keys() - left.keys())}
        for key in left:
            found = first_difference(left[key], right[key], path + '/' + str(key))
            if found:
                return found
    elif isinstance(left, list):
        if len(left) != len(right):
            return {'path': path, 'reason': 'length', 'before': len(left), 'after': len(right)}
        for index, (a, b) in enumerate(zip(left, right)):
            found = first_difference(a, b, path + '/' + str(index))
            if found:
                return found
    elif left != right:
        return {'path': path, 'reason': 'value', 'before': str(left)[:300], 'after': str(right)[:300]}
    return None


def consumer_worker():
    from legalmath.prospectus.successor import service
    assert Path(service.__file__).resolve().is_relative_to(ROOT / 'src')
    folder = BASE / 'attempt-002'
    original = {'P1': read(folder / 'original-P1.json.gz'), 'P2': read(folder / 'original-P2.json.gz'),
        **{p: read(folder / ('actual-' + p + '.json.gz')) for p in ('P3', 'P4', 'P5')}}

    def build(p1):
        p2 = service.construction_product(p1, ROOT)
        p3 = service.interpretation_product(p1, p2, original['P3']['payload'].get('interpretation_input'))
        law, finance = original['P4']['payload'], original['P5']['payload']
        return {'P1': p1, 'P2': p2, 'P3': p3,
            'P4': service.law_product(p1, p3, law.get('cases'), law.get('law_input')),
            'P5': service.financial_product(p1, p2, p3, finance.get('cases'), finance.get('scenario_input'))}

    def compare(label, expected, actual):
        found = first_difference(expected, actual)
        if found:
            save(HERE / ('difference-' + label + '.json'), {'first_difference': found,
                'expected_sha256': digest(expected), 'actual_sha256': digest(actual)})
            raise ValueError('Current complete comparison failed: ' + label)

    baseline = build(original['P1'])
    compare('legacy-products', original, baseline)
    answer = service.consume(baseline, ROOT, include_artifacts=True)
    compare('legacy-answer', restore_answer(), answer)
    retained = read(BASE / 'attempt-005/after-products.json.gz')
    current = build(retained['P1'])
    compare('cell-products', retained, current)
    consumed = service.consume(current, ROOT, include_artifacts=True)
    recipe = read(BASE / 'attempt-005/answer-reconstruction.json')
    expected = restore_answer()
    expected.update(recipe['replacements'])
    expected['source_statement_cells'] = read(BASE / 'attempt-005/answer-addition.json')
    assert digest(expected) == recipe['expected_complete_answer_sha256']
    compare('cell-answer', expected, consumed)
    compare('complete-questions', answer['questions'], consumed['questions'])
    assert consumed['questions']['Q3']['status'] == 'PARTIAL'
    assert consumed['independent_legal_acceptance'] is False and consumed['may_execute_transaction'] is False
    controls = []
    for change in ('missing_p2', 'changed_p2', 'missing_p3', 'changed_p3', 'unsupplied'):
        bad = deepcopy(current)
        request = bad['P1']['payload']['request']
        p2, p3 = bad['P2']['payload'], bad['P3']['payload']
        if change == 'missing_p2':
            del p2['source_statement_cells']
        elif change == 'changed_p2':
            p2['source_statement_cells']['reading']['rows'][0]['cells'][0]['value'] += 1
        elif change == 'missing_p3':
            del p3['source_statement_cells_sha256']
        elif change == 'changed_p3':
            p3['source_statement_cells_sha256'] = '0' * 64
        else:
            del request['source_statement_cells']
        b = request['bundle']
        bad['P1'] = service.seal('P1', b, {'request': digest(request)}, bad['P1']['payload'])
        bad['P2'] = service.seal('P2', b, {'P1': bad['P1']['sha256']}, p2)
        bad['P3'] = service.seal('P3', b, {'P1': bad['P1']['sha256'], 'P2': bad['P2']['sha256']}, p3)
        bad['P4'] = service.seal('P4', b, {'P1': bad['P1']['sha256'], 'P3': bad['P3']['sha256']}, bad['P4']['payload'])
        bad['P5'] = service.seal('P5', b, {'P2': bad['P2']['sha256'], 'P3': bad['P3']['sha256']}, bad['P5']['payload'])
        try:
            service.consume(bad, ROOT, include_artifacts=True)
        except ValueError as exc:
            assert 'Consumed statement cells' in str(exc)
            controls.append({'id': change, 'refused': True, 'reason': str(exc), 'input_sha256': digest(bad),
                'reconstruction': 'consumer_worker named change from retained005 after-products; reseal all phase hashes'})
        else:
            raise ValueError('Accepted resealed statement evidence: ' + change)
    imports = {name: m.__file__ for name, m in sys.modules.items()
        if name.startswith('legalmath') and getattr(m, '__file__', None)}
    assert all(Path(p).resolve().is_relative_to(ROOT / 'src') for p in imports.values())
    save(HERE / 'consumer-check.json', {'status': 'PASS', 'complete_legacy_and_cell_products_equal': True,
        'complete_legacy_and_cell_answers_equal': True, 'baseline_answer_sha256': digest(answer),
        'cell_answer_sha256': digest(consumed), 'controls': controls, 'imports': imports,
        'legacy_answer_recipe': reference(folder / 'actual-current-answer-components.json.gz'),
        'cell_answer_recipe': reference(BASE / 'attempt-005/answer-reconstruction.json'),
        'cell_products': reference(BASE / 'attempt-005/after-products.json.gz'),
        'native_extraction': False, 'installed_revalidation': False, 'whole_task_complete': False})


def frozen():
    admission = read(HERE / 'admission.json')
    assert adigest(read(AUTH / 'program.json')) == admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec']) == admission['binding']
    for name, checksum in read(PREP / 'freeze.json')['bindings'].items():
        assert sha(ROOT / name) == checksum, name


def stage(name):
    assert name in ('source', 'consumer') and not (HERE / 'stages' / name).exists()
    frozen()
    assert resources(1024**2)['execution_allowed'], 'Diagnostic reservation exhausted before launch'
    folder = HERE / 'stages' / name
    save(folder / 'started.json', {'pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat()})
    command = [str(ROOT / '.venv/bin/python'), '-B', '-m', 'scripts.prospectus_bes_9m10_requirements', 'worker-' + name]
    tick = time.monotonic()
    result = None
    error = None
    try:
        (HERE / 'commands').mkdir(exist_ok=True)
        with (HERE / 'commands' / (name + '.log')).open('x') as stream:
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=120,
                env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONDONTWRITEBYTECODE': '1',
                    'PYTHONPATH': str(ROOT / 'src') + os.pathsep + str(ROOT)})
        assert result.returncode == 0, 'Inspect retained ' + name + '.log'
        frozen()
    except Exception as exc:
        error = {'type': type(exc).__name__, 'reason': str(exc)}
    save(HERE / 'commands' / (name + '.json'), {'command': command, 'wall_seconds': time.monotonic() - tick,
        'exit_code': None if result is None else result.returncode, 'error': error})
    if error is None and not resources()['execution_allowed']:
        error = {'type': 'ResourceLimit', 'reason': 'Post-command resource check failed'}
    save(folder / 'result.json', {'status': 'FAIL' if error else 'PASS', 'error': error})
    return {'stage': name, 'status': 'FAIL' if error else 'PASS', 'resources': resources()}


def reconcile():
    # Completion-only evidence is writable even if experiment reservations failed.
    outcomes = {n: read(HERE / 'stages' / n / 'result.json')['status'] for n in ('source', 'consumer')}
    passed = all(v == 'PASS' for v in outcomes.values())
    ledger = [
        {'requirement': 'Retained release and prospectus exact bytes', 'status': 'VERIFIED_INPUTS', 'evidence': rel(PREP / 'freeze.json')},
        {'requirement': 'Issuer/date/statement-scope match with9H10/9M10 difference', 'status': 'DISCLOSED_SOURCE_READING', 'evidence': rel(BASE / 'attempt-001/IMAGE-REVIEW.md')},
        {'requirement': 'Complete304target units and203cells, periods/units/unknowns', 'status': outcomes['source'], 'evidence': rel(HERE / 'source-check.json')},
        {'requirement': 'Actual current product/answer use and resealed forgery refusal', 'status': outcomes['consumer'], 'evidence': rel(HERE / 'consumer-check.json')},
        {'requirement': 'Exact publication date and historical availability at3November2010', 'status': 'NOT_ESTABLISHED', 'evidence': rel(BASE / 'attempt-001/RESULT.md')},
        {'requirement': 'Source authenticity and final legal incorporation in full instrument', 'status': 'NOT_ESTABLISHED', 'evidence': rel(BASE / 'attempt-005/RESULT.md')},
        {'requirement': 'General automatic table parsing or financial-statement truth', 'status': 'NOT_ESTABLISHED', 'evidence': rel(BASE / 'attempt-005/RESULT.md')},
    ]
    save(HERE / 'requirements.json', {'check': 'bes-9m10-source-review.v1', 'rows': ledger,
        'conditional_source_map_and_consumption_passed': passed, 'original_task_acceptance': False,
        'external_adviser_opinion_required': False})
    with (HERE / 'RESULT.md').open('x') as stream:
        stream.write(f'''# Original nine-month source requirements

The named source/consumer check {'passed' if passed else 'failed'}: {outcomes}.
The ledger in requirements.json distinguishes actual code/source coverage from
unproved historical and legal facts. Complete prior answers are reconstructed
from authenticated original components; no large product snapshots are copied.

The source reading preserves all203cells,77rows,304target occurrences and the
three stock dates/two income periods. Unknown dashes remain unknown, and the
ECB and discontinued-operation rows remain non-additive. These are conditional
interpretations of the supplied source, not an audit of the Bank's accounts.
The source check and actual consumer each retain their executed adverse cases.
See their status above before relying on the intended criteria.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| {'Retain named conditional evidence' if passed else 'Retain diagnosed current gap'} | Independent full source-map and complete current-answer equality: {passed} | Individual stage records | Historical authenticity/publication and full legal incorporation | Record/refresh; select a distinct uncovered original requirement or independent source task | Whole source task/build or financial truth |

Original-task acceptance remains false. The2011archive capture does not prove
availability at3November2010. The disclosed9H10/9M10 difference cannot be erased
by matching table values. No new package trial, installed validation, extraction
or external opinion occurred. All five previous admissions and failures survive.

Post-run red-team: agreeing with a retained transcription cannot establish the
truth of accounts or unrestricted source reading. The source anchors and complete
comparators can expose a changed literal, scope or answer, while a contrary
original source would require substantive reinterpretation. No stochastic ranking.
''')
    save(HERE / 'result.json', {'task': 'source-bes-dep-01', 'status': 'PASS' if passed else 'FAIL',
        'check': 'bes-9m10-source-review.v1', 'whole_task_complete': False, 'whole_program_complete': False,
        'build_criteria_claimed': [], 'stages': outcomes, 'resources': resources(),
        'original_task_acceptance': False, 'external_adviser_opinion_required': False})
    save(HERE / 'run-manifest.json', {'git_commit': read(HERE / 'admission.json')['git_commit'],
        'commands': [read(p) for p in sorted((HERE / 'commands').glob('*.json'))],
        'environment': str(ROOT / '.venv/bin/python'), 'cpu_gpu': 'CPU; GPU intentionally hidden',
        'seeds': 'N/A deterministic', 'data_version': sha(PREP / 'freeze.json'),
        'plan': PLAN, 'result': rel(HERE / 'RESULT.md'), 'resources': resources()})
    save(HERE / 'outputs.json', {str(p.relative_to(HERE)): sha(p) for p in HERE.rglob('*')
        if p.is_file() and '__pycache__' not in p.parts})
    return {'status': 'SEALED', 'candidate_passed': passed, 'resources': resources()}


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'prepare':
        output = prepare()
    elif action.startswith('worker-'):
        def forbidden(*args, **kwargs):
            raise RuntimeError('No native child allowed in retained-source review')
        subprocess.Popen = forbidden
        {'worker-source': source_worker, 'worker-consumer': consumer_worker}[action]()
        output = {'status': 'PASS', 'worker': action}
    elif action == 'reconcile':
        output = reconcile()
    else:
        output = stage(action)
    print(json.dumps(output))
