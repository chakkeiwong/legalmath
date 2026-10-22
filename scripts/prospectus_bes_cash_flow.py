"""Bounded same-task BES cash-flow integration through the normal frozen consumer."""
import argparse
from copy import deepcopy
import gzip
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
from legalmath.prospectus.execution_authority import Authority, REL, file_hash, read, write, digest as authority_digest
from legalmath.prospectus.successor import bes_cash_flow as production, service
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor
from scripts.prospectus_bes_cash_flow_oracle import verify_review, require

SOURCE = REL + '/attempts/source-bes-dep-07'
NORMAL = SOURCE + '/attempt-003'
PRIOR = SOURCE + '/attempt-008'
REVIEW = REL + '/reviews/bes-cash-flow-210'
PLAN = 'docs/plans/prospectus-bes-cash-flow-integration-2026-10-17.md'
MASTER = 'docs/plans/prospectus-general-build-2026-10-17.md'
FIXTURE = 'tests/prospectus_successor/fixtures/bes_cash_flow.json.gz'
TESTS = ('tests/prospectus_successor/test_bes_cash_flow.py',
         'tests/prospectus_successor/test_source_discrepancies.py',
         'tests/prospectus/test_build_contract.py', 'tests/prospectus/test_execution_authority.py')
METHODS = ('scripts/prospectus_bes_cash_flow.py', 'scripts/prospectus_bes_cash_flow_oracle.py',
           'scripts/prospectus_bes_cash_flow_prepare.py',
           'src/legalmath/prospectus/successor/bes_cash_flow.py',
           'src/legalmath/prospectus/successor/service.py',
           'src/legalmath/prospectus/successor/contracts.py',
           'src/legalmath/prospectus/build_contract.py', FIXTURE, *TESTS)
SELECTOR = {'version': 'bes-cash-flow.v1', 'new_seconds': 240, 'preparation_seconds': 60,
            'validation_seconds': 60, 'combined003_onward_seconds': 1320,
            'new_bytes': 32 * 1024**2, 'combined003_onward_bytes': 200 * 1024**2,
            'reserve_bytes': 262144, 'new_extraction_OCR_network_models_installs_GPU': 0,
            'current_reextraction_claimed': False}
PROFILE_CONTROLS = ('version', 'graph', 'edition', 'document', 'language', 'context', 'unit', 'year',
                    'row-label', 'row-cell', 'omit-component', 'duplicate-column', 'abbreviation',
                    'boolean-position', 'malformed-anchor', 'blank-zero', 'absence-zero', 'resolved-amount',
                    'controlling-edition', 'accounting-cause', 'authority', 'image-page', 'review')
OUTPUT_CONTROLS = ('residual', 'component-sum', 'dash-zero', 'blank-zero', 'absent-zero',
                   'missing-relation', 'year', 'unit', 'cell', 'boolean-amount', 'row-source',
                   'context', 'comparison', 'correction', 'edition', 'cause', 'authority', 'prose')


def load(path):
    with gzip.open(path, 'rt') as stream:
        return json.load(stream)


def compressed(path, value):
    data = gzip.compress(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode(), mtime=0)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def make_profile(root, graph):
    units = {u['id']: u for u in graph['units']}
    old = load(root / PRIOR / 'profile.json.gz')
    editions = []
    for lang in ('en', 'pt'):
        def a(page, n):
            return anchor(units[f'bes-2008-{lang}:p{page}:l{n}'])
        rows = {name: {'label': a(170, label), 'cells': [a(170, x), a(170, y)]}
                for name, (label, x, y, _) in production.LAYOUT[lang].items()}
        image, = [i for i in old['images'] if i['document'] == 'bes-2008-' + lang and i['page'] == 170]
        editions.append({'language': lang, 'document': 'bes-2008-' + lang,
            'source_sha256': a(170, 0)['source_sha256'],
            'context': {'individual': a(165, 1), 'title': a(170, 0), 'unit': a(170, 1),
                        'years': [a(170, 4), a(170, 5)]},
            'rows': rows, 'image': image,
            'capital_increase': {'status': 'SUPPLIED_VISUAL_BLANKS', 'label': a(170, 94)} if lang == 'en'
                                else {'status': 'ABSENT_IN_SUPPLIED_READING'}})
    return {'version': production.PROFILE, 'graph_sha256': digest(graph),
            'review': {'kind': 'DEVELOPMENT', 'reviewer': 'source-bound supplied reading',
                       'reason': 'Retain both original individual statements and unknowns; finite arithmetic, no correction or edition priority'},
            'editions': editions}


def small_fixture(root):
    units = load(root / PRIOR / 'source-units.json.gz')
    identifiers = set()
    for lang, rows in production.LAYOUT.items():
        identifiers.add(f'bes-2008-{lang}:p165:l1')
        identifiers.update(f'bes-2008-{lang}:p170:l{n}' for n in (0, 1, 4, 5))
        for label, first, second, _ in rows.values():
            identifiers.update(f'bes-2008-{lang}:p170:l{n}' for n in (label, first, second))
    identifiers.add('bes-2008-en:p170:l94')
    graph = {'units': [u for u in units if u['id'] in identifiers]}
    return {'graph': graph, 'profile': make_profile(root, graph),
            'original_reading': load(root / PRIOR / 'profile.json.gz')['reading'], 'original_units': units}


def products(root):
    result = load(root / NORMAL / 'candidate-P2-P5.json.gz')
    original = load(root / NORMAL / 'original-P1.json.gz')
    request = deepcopy(original['payload']['request'])
    request['source_report_readings'] = read(root / NORMAL / 'reading-input.json')
    result['P1'] = service.seal('P1', request['bundle'], {'request': digest(request)},
                                {'request': request, 'graph': original['payload']['graph']})
    # Reconstruct the historical selected request, never alter saved child links.
    for phase, parents in (('P2',('P1',)),('P3',('P1','P2')),('P4',('P1','P3')),('P5',('P2','P3'))):
        service.verify(result[phase],phase,request['bundle'],{k:result[k]['sha256'] for k in parents})
    return {k: result[k] for k in ('P1', 'P2', 'P3', 'P4', 'P5')}


def updated(original, profile):
    p1, p2 = original['P1'], original['P2']
    supplied = {**(original['P3']['payload'].get('interpretation_input') or {}), 'source_cash_flow': profile}
    p3 = service.interpretation_product(p1, p2, supplied)
    previous = original['P3']['payload']
    comparable = {**p3['payload'], 'interpretation_input': previous.get('interpretation_input')}
    del comparable['source_cash_flow']
    require(digest(comparable) == digest(previous), 'Unrelated interpretation changed during integration')
    p4_input, p5_input = original['P4']['payload'], original['P5']['payload']
    p4 = service.law_product(p1, p3, p4_input.get('cases'), p4_input.get('law_input'))
    p5 = service.financial_product(p1, p2, p3, p5_input.get('cases'), p5_input.get('scenario_input'))
    require(digest(p4['payload']) == digest(p4_input) and digest(p5['payload']) == digest(p5_input),
            'Unrelated law/financial result changed')
    return {**original, 'P3': p3, 'P4': p4, 'P5': p5}


def verify_answer(actual, baseline, revised):
    require(set(actual) == set(baseline) | {production.ADDED}, 'Complete answer coverage changed')
    prior = {k: actual[k] for k in baseline}
    for k in ('consumed_products', 'report_sha256'):
        prior[k] = baseline[k]
    require(digest(prior) == digest(baseline), 'Unrelated complete baseline answer changed')
    require(actual['consumed_products'] == {k: revised[k]['sha256'] for k in revised}, 'Consumed product identity differs')
    require(actual['report_sha256'] == digest({k: v for k, v in actual.items() if k != 'report_sha256'}), 'Report identity differs')
    require(actual['questions']['Q3']['status'] == 'PARTIAL' and actual['may_execute_transaction'] is False,
            'Unresolved answer promoted')
    return True


def reconstruct(root, path):
    spec = read(root / path)
    def chunk(reference):
        file = root / reference['path']
        require(file_hash(file) == reference['file_sha256'], 'Prior compressed answer changed')
        value = load(file)
        require(authority_digest(value) == reference['content_sha256'], 'Prior answer content changed')
        return value
    if 'predecessor' in spec:
        prior = spec['predecessor']
        require(file_hash(root / prior['path']) == prior['sha256'], 'Prior composition changed')
        base = reconstruct(root, prior['path'])
        require(authority_digest(base) == spec['baseline_content_sha256'], 'Prior composed baseline changed')
    else:
        base = chunk(spec['baseline'])
    overlay = chunk(spec['overlay'])
    require(not set(base) & set(overlay), 'Prior composition keys collide')
    result = {**base, **overlay}
    require(authority_digest(result) == spec['complete_composed_answer_sha256'], 'Complete retained answer changed')
    return result


def profile_mutation(profile, name):
    p = deepcopy(profile)
    e = p['editions'][0]
    if name == 'version': p['version'] = 'general-table-discovery'
    elif name == 'graph': p['graph_sha256'] = '0' * 64
    elif name == 'edition': e['source_sha256'] = '0' * 64
    elif name == 'document': e['document'] = 'bes-2008-consolidated'
    elif name == 'language': e['language'] = 'pt'
    elif name in ('context', 'unit', 'year'):
        if name == 'context': e['context']['individual'] = deepcopy(e['context']['title'])
        elif name == 'unit': e['context']['unit'] = deepcopy(e['context']['title'])
        else: e['context']['years'].reverse()
    elif name == 'row-label': e['rows']['investing']['label'] = deepcopy(e['rows']['operating']['label'])
    elif name == 'row-cell': e['rows']['investing']['cells'] = deepcopy(e['rows']['operating']['cells'])
    elif name == 'omit-component': del e['rows']['HTM']
    elif name == 'duplicate-column': e['rows']['buy_AFS']['cells'][1] = deepcopy(e['rows']['buy_AFS']['cells'][0])
    elif name == 'abbreviation': e['rows']['investing']['label']['end'] -= 1
    elif name == 'boolean-position': e['rows']['investing']['label']['start'] = False
    elif name == 'malformed-anchor': e['rows']['investing']['label'] = []
    elif name == 'blank-zero': e['capital_increase']['status'] = 'ZERO'
    elif name == 'absence-zero': p['editions'][1]['capital_increase']['status'] = 'ZERO'
    elif name == 'image-page': e['image']['page'] = 74
    elif name == 'review': p['review']['reason'] = ''
    else: p[name.replace('-', '_')] = True
    return p


def output_mutation(actual, name):
    result = deepcopy(actual)
    e = result['editions'][0]
    if name == 'residual': e['relations'][0]['residual'] = 0
    elif name == 'component-sum': e['relations'][0]['component_sum'] = -4041758
    elif name == 'dash-zero':
        e['rows']['merger_BESSA']['cells']['2008'].update(value=0, status='SOURCE_NUMBER')
        e['relations'][1].update(status='COMPLETE_EQUALITY', residual=-40, unknown_terms=[])
    elif name == 'blank-zero': e['capital_increase']['cells']['2008']['value'] = 0
    elif name == 'absent-zero': result['editions'][1]['capital_increase']['cells'] = {'2008': 0}
    elif name == 'missing-relation': e['relations'].pop()
    elif name == 'year': e['relations'][0]['year'] = '2007'
    elif name == 'unit': e['relations'][0]['unit'] = 'EUR millions'
    elif name == 'cell': e['rows']['buy_AFS']['cells']['2008']['value'] *= -1
    elif name == 'boolean-amount': e['rows']['sell_fixed']['cells']['2008']['value'] = True
    elif name == 'row-source': e['rows']['investing']['cells']['2008']['source']['unit'] = 'bes-2008-en:p74:l91'
    elif name == 'context': e['context']['unit']['quote'] = 'millions of euro'
    elif name == 'comparison': result['bilingual_comparisons'][16]['difference_en_minus_pt'] = 0
    elif name == 'correction': result['official_correction_established'] = True
    elif name == 'edition': result['controlling_edition'] = 'pt'
    elif name == 'cause': result['accounting_cause'] = 'translation error'
    elif name == 'authority': result['may_execute_transaction'] = True
    elif name == 'prose': result['explanation'] = 'The Portuguese edition controls and fixes the amount.'
    return result


def reject_altered_outputs(actual, verifier):
    rows = []
    for name in OUTPUT_CONTROLS:
        try:
            verifier(output_mutation(actual, name))
        except ValueError:
            rows.append({'mutation': 'resealed-output:' + name, 'rejected': True})
        else:
            raise ValueError('Incorrect output accepted by separate checker: ' + name)
    return rows


def controls(root, fixture):
    graph, profile = fixture['graph'], fixture['profile']
    actual = production.admit(graph, profile)
    oracle = lambda a: verify_review(a, profile, graph, fixture['original_reading'], fixture['original_units'])
    rows = []
    for name in PROFILE_CONTROLS:
        try:
            production.admit(graph, profile_mutation(profile, name))
        except ValueError:
            rows.append({'mutation': 'repinned-profile:' + name, 'rejected': True})
        else:
            raise ValueError('Invalid supplied profile accepted: ' + name)
    rows.extend(reject_altered_outputs(actual, oracle))
    permissive_detected = False
    try:
        reject_altered_outputs(actual, lambda _: True)
    except ValueError as exc:
        permissive_detected = str(exc).startswith('Incorrect output accepted by separate checker:')
    require(permissive_detected, 'Verifier acceptor control failed')
    image_case = deepcopy(actual)
    image_case['editions'][0]['image']['sha256'] = '0' * 64
    try:
        production.validate_images(image_case, root)
    except ValueError:
        rows.append({'mutation': 'image-bytes', 'rejected': True})
    else:
        raise ValueError('Changed image accepted')
    return {'controls': rows, 'permissive_checker_detected': permissive_detected,
            'dash_as_zero_detected': True}


def storage(root, attempt, enforce=True):
    # Reuse the historical accounting sets, without running its worker or altering evidence.
    from scripts.prospectus_2008_individual import storage as previous_storage
    prior = previous_storage()['combined_bytes']
    support = {root / n for n in (*METHODS, PLAN, MASTER)}
    support |= {p for p in (root / REVIEW).rglob('*') if p.is_file()}
    support |= {p for n in (208,209) for p in (root / REL / ('reviews/bes-cash-flow-'+str(n))).rglob('*') if p.is_file()}
    support |= {p for p in (root / SOURCE / 'attempt-009').rglob('*') if p.is_file()}
    support |= {p for p in attempt.rglob('*') if p.is_file()}
    support |= {root / REL / 'proposals' / ('bes-cash-flow-' + str(n) + suffix)
                for n in (208, 209, 210) for suffix in ('.json', '-review.json')}
    current = sum(p.stat().st_size for p in support if p.is_file())
    if enforce:
        require(current < SELECTOR['new_bytes'] - SELECTOR['reserve_bytes']
                and current + prior < SELECTOR['combined003_onward_bytes'] - SELECTOR['reserve_bytes'], 'Cumulative storage ceiling')
    return {'historical_bytes': prior, 'new_bytes': current, 'combined_bytes': current + prior,
            'failure_reserve_bytes': SELECTOR['reserve_bytes']}


def frozen_inputs(root):
    frozen = read(root / REVIEW / 'frozen.json')
    require(frozen['selector'] == SELECTOR, 'Frozen resource/scope selector changed')
    require(frozen['methods'] == {n: file_hash(root / n) for n in METHODS}, 'Reviewed methods changed')
    require(frozen['inputs'] == {n: file_hash(root / n) for n in frozen['inputs']}, 'Original source/baseline/image changed')
    fixture = load(root / FIXTURE)
    require(digest(fixture['original_units']) == digest(load(root / PRIOR / 'source-units.json.gz'))
            and digest(fixture['original_reading']) == digest(load(root / PRIOR / 'profile.json.gz')['reading']),
            'Independent fixture differs from retained original reading')
    return frozen


def run(root, attempt):
    frozen_inputs(root)
    ps = products(root)
    graph = ps['P1']['payload']['graph']
    profile = read(root / REVIEW / 'profile.json')
    require(digest(profile) == digest(make_profile(root, graph)), 'Frozen reviewed profile changed')
    baseline = load(root / NORMAL / 'candidate-answer.json.gz')
    off = service.consume(ps, root, mode='frozen', include_artifacts=True)
    require(digest(off) == digest(baseline), 'Actual normal unconfigured consumer differs from full baseline')
    del off
    revised = updated(ps, profile)
    actual = service.consume(revised, root, mode='frozen', include_artifacts=True)
    verify_answer(actual, baseline, revised)
    fixture = load(root / FIXTURE)
    checked = verify_review(actual[production.ADDED], profile, graph, fixture['original_reading'], fixture['original_units'], root)
    adverse = controls(root, fixture)
    delta = {production.ADDED: actual[production.ADDED], 'consumed_products': actual['consumed_products'],
             'report_sha256': actual['report_sha256']}
    compressed(attempt / 'normal-answer-delta.json.gz', delta)
    normal_hash = digest(actual)
    del actual, baseline, ps, revised, graph
    later = reconstruct(root, PRIOR + '/answer-composition.json')
    require(production.ADDED not in later, 'New explanation collides with a prior result')
    before_hash = digest(later)
    combined = {**later, production.ADDED: delta[production.ADDED]}
    require(digest({k: combined[k] for k in later}) == before_hash, 'Earlier complete composition changed')
    write(attempt / 'composition.json', {'normal_baseline': NORMAL + '/candidate-answer.json.gz',
        'normal_baseline_file_sha256': file_hash(root / NORMAL / 'candidate-answer.json.gz'),
        'normal_delta': 'normal-answer-delta.json.gz', 'normal_answer_sha256': normal_hash,
        'prior_composition': PRIOR + '/answer-composition.json',
        'prior_composition_file_sha256': file_hash(root / PRIOR / 'answer-composition.json'),
        'prior_answer_sha256': before_hash, 'complete_composed_answer_sha256': digest(combined),
        'complete_prior_answer_preserved': True, 'new_fields': [production.ADDED],
        'normal_product_hash_changes_apply_to': 'normal consumer only; previous supplied compositions remain immutable',
        'large_answer_copies': 0}, exclusive=True)
    write(attempt / 'verification.json', checked, exclusive=True)
    write(attempt / 'controls.json', adverse, exclusive=True)
    write(attempt / 'profile.json', profile, exclusive=True)
    return {**checked, 'mutations_rejected': len(adverse['controls']), 'normal_consumer_on_off_checked': True,
            'complete_prior_answer_preserved': True, 'frozen_consumer_integrated': True,
            'current_reextraction_checked': False, 'whole_build_complete': False}


def validate_submission(root, attempt, task):
    from legalmath.prospectus.execution_acceptance import checked_tests
    start = time.monotonic()
    root, attempt = Path(root), Path(attempt)
    require(task['id'] == 'source-bes-dep-07' and task.get('cash_flow_integration') == SELECTOR,
            'Cash-flow criterion outside reviewed same task')
    checked_tests(attempt / 'tests.xml', 182)
    frozen = frozen_inputs(root)
    manifest, result = read(attempt / 'run-manifest.json'), read(attempt / 'result.json')
    require(manifest['methods'] == {n: file_hash(root / n) for n in METHODS}, 'Frozen methods changed')
    require(set(METHODS) | set(frozen['inputs']) | {REVIEW + '/profile.json', REVIEW + '/frozen.json'}
            <= set(task['inputs']), 'Unbound methods/profile/original sources')
    require(result['status'] == 'PASS' and result['whole_program_complete'] is False
            and result['task_complete'] is False and result['scope'] == 'CONDITIONAL_BES_INDIVIDUAL_CASH_FLOW'
            and manifest['status'] == 'PASS', 'Invalid retained result')
    require(manifest['data_version'] == frozen['inputs'] and manifest['accounting'] == SELECTOR
            and manifest['environment']['service_module'] == str(root / 'src/legalmath/prospectus/successor/service.py')
            and manifest['preparation_seconds'] == read(root / REVIEW / 'preparation.json')['seconds']
            and 0 <= manifest['preparation_seconds'] <= SELECTOR['preparation_seconds']
            and manifest['historical_seconds'] == 948.8160658078269
            and manifest['previous_failed_seconds'] == read(root / SOURCE / 'attempt-009/run-manifest.json')['wall_seconds']
            and manifest['plan'] == PLAN, 'Retained environment, source or resource claim differs')
    ps = products(root)
    profile = read(attempt / 'profile.json')
    require(digest(profile) == digest(read(root / REVIEW / 'profile.json'))
            == digest(make_profile(root, ps['P1']['payload']['graph'])), 'Retained source profile changed')
    baseline = load(root / NORMAL / 'candidate-answer.json.gz')
    delta = load(attempt / 'normal-answer-delta.json.gz')
    revised = updated(ps, profile)
    actual = service.consume(revised, root, mode='frozen', include_artifacts=True)
    verify_answer(actual, baseline, revised)
    require(digest({**baseline, **delta}) == digest(actual), 'Retained delta is not the normal answer')
    fixture = load(root / FIXTURE)
    check = verify_review(delta[production.ADDED], profile, ps['P1']['payload']['graph'],
                          fixture['original_reading'], fixture['original_units'], root)
    require(read(attempt / 'verification.json') == check and read(attempt / 'controls.json') == controls(root, fixture),
            'Independent retained evidence differs')
    spec = read(attempt / 'composition.json')
    require(spec['normal_answer_sha256'] == digest(actual) and spec['normal_baseline'] == NORMAL + '/candidate-answer.json.gz'
            and spec['normal_baseline_file_sha256'] == file_hash(root / spec['normal_baseline'])
            and spec['prior_composition'] == PRIOR + '/answer-composition.json'
            and spec['prior_composition_file_sha256'] == file_hash(root / spec['prior_composition'])
            and spec['complete_prior_answer_preserved'] is True and spec['large_answer_copies'] == 0,
            'Normal answer composition differs')
    del actual, baseline, ps, revised
    prior = reconstruct(root, spec['prior_composition'])
    require(digest(prior) == spec['prior_answer_sha256']
            and digest({**prior, production.ADDED: delta[production.ADDED]}) == spec['complete_composed_answer_sha256'],
            'Complete later evidence differs')
    elapsed = time.monotonic() - start
    charged = manifest['wall_seconds'] + manifest['preparation_seconds'] + manifest['previous_failed_seconds'] + elapsed
    require(elapsed <= SELECTOR['validation_seconds'] and charged <= SELECTOR['new_seconds']
            and manifest['historical_seconds'] + charged <= SELECTOR['combined003_onward_seconds'],
            'Cumulative command/acceptance-validation time ceiling')
    storage(root, attempt)
    print(json.dumps({'stage': 'acceptance-validation', 'seconds': elapsed, 'charged_new_seconds': charged,
                      'historical_plus_charged_seconds': manifest['historical_seconds'] + charged}), flush=True)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', required=True)
    args = parser.parse_args()
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    authority = Authority(ROOT)
    attempt = authority.path(args.attempt)
    admission = read(attempt / 'admission.json')
    active_program, active_tasks, _ = authority.spec()
    latest = next(e for e in reversed(authority.events()) if e.get('task') == 'source-bes-dep-07')
    require(admission['task'] == 'source-bes-dep-07' and admission['binding'] == authority.binding(admission['task_spec'])
            and admission['task_spec'].get('cash_flow_integration') == SELECTOR
            and admission['task_spec'] == active_tasks['source-bes-dep-07']
            and admission['program_sha256'] == authority_digest(active_program)
            and latest['kind'] == 'ADMIT' and latest['attempt'] == args.attempt
            and latest['admission_sha256'] == file_hash(attempt / 'admission.json'), 'Unchanged reviewed admission required')
    require(not (attempt / 'started.json').exists(), 'Do not duplicate an already started package')
    frozen = frozen_inputs(ROOT)
    start = time.monotonic()
    preparation = read(ROOT / REVIEW / 'preparation.json')['seconds']
    previous_failed = read(ROOT / SOURCE / 'attempt-009/run-manifest.json')['wall_seconds']
    require(preparation <= SELECTOR['preparation_seconds'], 'Preparation allowance exhausted')
    def expired(_a, _b): raise TimeoutError('Reviewed cash-flow package ceiling')
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(int(SELECTOR['new_seconds'] - preparation - previous_failed - SELECTOR['validation_seconds']))
    manifest = {'command': [sys.executable, '-m', 'scripts.prospectus_bes_cash_flow', '--attempt', args.attempt],
        'git_commit': admission['git_commit'], 'environment': {'python': sys.version, 'executable': sys.executable,
        'PYTHONPATH': str(ROOT / 'src'), 'service_module': service.__file__},
        'cpu_gpu': 'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1; no GPU framework used',
        'data_version': frozen['inputs'],
        'methods': {n: file_hash(ROOT / n) for n in METHODS}, 'plan': PLAN,
        'random_seeds': 'N/A; deterministic integer arithmetic', 'preparation_seconds': preparation,
        'previous_failed_seconds': previous_failed,
        'historical_seconds': 948.8160658078269, 'accounting': SELECTOR,
        'result': args.attempt + '/RESULT.md', 'outputs': args.attempt,
        'exclusions': 'Historical startup/final-receipt exclusions retained; agent authoring/reading and unknown older time are not measured; no reset of original history'}
    write(attempt / 'started.json', manifest, exclusive=True)
    status, error, summary = 'PASS', None, {}
    try:
        storage(ROOT, attempt)
        command = [sys.executable, '-m', 'pytest', *TESTS, '-q', '--junitxml=' + str(attempt / 'tests.xml')]
        manifest['test_command'] = command
        with (attempt / 'tests.log').open('x') as log:
            subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHONPATH': str(ROOT / 'src'),
                'PYTHONDONTWRITEBYTECODE': '1'}, stdout=log, stderr=subprocess.STDOUT, timeout=60, check=True)
        print(json.dumps({'stage': 'focused-tests', 'status': 'PASS'}), flush=True)
        summary = run(ROOT, attempt)
        require(manifest['methods'] == {n: file_hash(ROOT / n) for n in METHODS}, 'Methods changed during package')
        print(json.dumps({'stage': 'normal-consumer-and-separate-verifier', 'status': 'PASS',
            'relations': summary['relations'], 'mutations_rejected': summary['mutations_rejected']}), flush=True)
    except Exception as exc:
        status, error = 'FAIL', type(exc).__name__ + ': ' + str(exc)
        (attempt / 'failure-trace.txt').write_text(traceback.format_exc(limit=12)[-8192:])
    signal.alarm(0)
    manifest.update(wall_seconds=time.monotonic() - start)
    try:
        manifest['storage'] = storage(ROOT, attempt)
        require(manifest['historical_seconds'] + preparation + previous_failed + manifest['wall_seconds'] <= SELECTOR['combined003_onward_seconds'],
                'Historical cumulative command clock exhausted')
    except Exception as exc:
        status, error = 'FAIL', type(exc).__name__ + ': ' + str(exc)
        manifest['storage'] = storage(ROOT, attempt, enforce=False)
    manifest.update(status=status,error=error)
    write(attempt / 'run-manifest.json', manifest, exclusive=True)
    write(attempt / 'result.json', {'task': 'source-bes-dep-07', 'status': status,
        'scope': 'CONDITIONAL_BES_INDIVIDUAL_CASH_FLOW', 'summary': summary, 'error': error,
        'whole_program_complete': False, 'task_complete': False}, exclusive=True)
    (attempt / 'RESULT.md').write_text('# BES individual cash-flow integration\n\nStatus: ' + status + '.\n\n'
        + ('The actual frozen normal consumer retains the two editions, checks eight relations and preserves the complete earlier answer. '
           'The English2008 investing residual is40 thousand EUR; the Portuguese residual is0. '
           'The net-change bridges retain unknown dashes.\n\n' if status == 'PASS' else str(error) + '\n\n')
        + '| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Limit |\n'
          '| --- | --- | --- | --- | --- | --- |\n'
        + ('| Accept finite conditional integration | Normal consumer, independent original map/arithmetic, full preservation | Declared mutations refused | Corrected source, priority and accounting cause remain unknown | Continue H1 units and property comparative | Original task/build incomplete; no fresh extraction claim |\n'
           if status == 'PASS' else '| Reject current implementation | Failed | See retained trace/log | Local implementation or input defect | Review the discriminating repair | No fundamental package rejection |\n')
        + '\nPost-run red team: both source editions could contain the same undetected error. Exact arithmetic does not prove source authenticity, '
          'accounting scope, legal priority or extraction completeness. The row mapping and visual observations remain supplied readings. '
          'A controlling public correction could change the source conclusion. No external opinion, corrected amount, financial authorization or general-build completion is established.\n')
    write(attempt / 'outputs.json', {str(p.relative_to(attempt)): file_hash(p) for p in sorted(attempt.rglob('*'))
          if p.is_file() and p.name != 'outputs.json'}, exclusive=True)
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
