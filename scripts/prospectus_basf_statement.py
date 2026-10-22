"""Bounded original BASF statement reading and conditional incorporation use."""
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import shutil
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.execution_authority import read, write, file_hash
from legalmath.prospectus import basf_statement as statement
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor

BASE = ROOT / 'docs/implementation/prospectus-execution-authority/attempts'
HERE = BASE / 'basf-incorporation/attempt-002'
PRIOR = BASE / 'basf-meanings/attempt-011'
SOURCE = BASE / 'basf-incorporation/attempt-001'
PLAN = 'docs/plans/prospectus-basf-statement-content-2026-10-15.md'
IMAGE = SOURCE / 'basf-annual-2022-exchange-204.png'
ROW_IDS = [(9, 10, 11), (12, 13, 14), (15, 16, 17), (20, 18, 19), (24, 21, 22),
           (23, 25, 26), (27, 28, 29), (30, 31, 32), (35, 33, 34), (36, 37, 38),
           (39, 40, 41), (42, 43, 44), (45, 46, 47), (58, 48, 49), (59, 50, 51),
           (60, 52, 53), (61, 54, 55), (62, 56, 57)]
# Independently transcribed from the inspected original image, before profile execution.
IMAGE_VALUES = [('–391', '5,982'), ('3,758', '3,476'), ('–1,256', '–811'), ('83', '44'),
    ('2,586', '2,709'), ('510', '284'), ('–455', '–222'), ('565', '1,566'), ('–', '52'),
    ('–15', '–29'), ('604', '313'), ('1,209', '1,964'), ('3,794', '4,673'), ('3,788', '4,583'),
    ('6', '90'), ('3,403', '10,655'), ('3,161', '10,106'), ('242', '549')]


def load(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def save(name, value):
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode()
    with (HERE / name).open('xb') as stream:
        stream.write(gzip.compress(raw, mtime=0) if name.endswith('.gz') else raw)


def methods():
    names = [Path(__file__), ROOT / 'src/legalmath/prospectus/basf_statement.py',
             ROOT / 'tests/prospectus/test_basf_statement.py', ROOT / PLAN]
    names += sorted((ROOT / 'src/legalmath/prospectus/successor').glob('*.py'))
    return {str(p.relative_to(ROOT)): file_hash(p) for p in names}


def bindings():
    assert not (HERE / 'outputs.json').exists()
    ad = read(HERE / 'admission.json')
    assert all(file_hash(ROOT / p) == h for p, h in ad['binding'].items())
    if (HERE / 'methods.json').exists():
        assert methods() == read(HERE / 'methods.json')
    return ad


def prepare():
    for prior in (PRIOR, SOURCE):
        assert all(file_hash(prior / p) == h for p, h in read(prior / 'outputs.json').items())
    save('methods.json', methods())
    for p in methods():
        target = HERE / 'methods' / p
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / p, target)
    common = load(PRIOR / 'common.json.gz')
    request = deepcopy(common['request'])
    request['clauses'] = deepcopy(common['candidate_clauses'])
    request['observations'] = {}
    graph = load(PRIOR / 'original-graph.json.gz')
    p1 = service.seal('P1', request['bundle'], {'request': digest(request)}, {'request': request, 'graph': graph})
    p2 = service.seal('P2', request['bundle'], {'P1': p1['sha256']}, common['P2_payload'])
    retained = load(PRIOR / 'candidate-products.json.gz')
    p3 = load(PRIOR / 'candidate-P3.json.gz')
    products = {'P1': p1, 'P2': p2, 'P3': p3, 'P4': retained['P4'], 'P5': retained['P5']}
    for key in ('P1', 'P2', 'P3'):
        assert {k: v for k, v in products[key].items() if k != 'payload'} == retained[key]
    save('products.json.gz', products)
    save('pre-run-audit.json', {'status': 'PASS', 'plan': PLAN, 'baseline': str(PRIOR.relative_to(ROOT)),
        'retained_product_headers_equal': True, 'native_calls': 0, 'http_calls': 0,
        'historical_native_lower_bound': 77, 'historical_source_http_lower_bound': 9,
        'promotion': 'Full baseline equality,complete source/cell coverage,actual adverse refusal,conditional scopes only',
        'arithmetic_role': 'EXPLANATORY_ONLY', 'independent_reading': False})
    save('IMAGE-REVIEW.json', {'reviewed': True, 'reviewer': 'Codex original image review2026-10-15',
        'independent': False, 'image_path': str(IMAGE.relative_to(ROOT)), 'image_sha256': file_hash(IMAGE),
        'entity': 'BASF Group', 'unit': 'Million €', 'years': ['2022', '2021'],
        'rows': [{'id': k, 'label': statement.ROWS[k], '2022': pair[0], '2021': pair[1]}
                 for k, pair in zip(statement.ROWS, IMAGE_VALUES)],
        'qualifications': ['Two original footnotes retained', 'Standalone dash left unknown',
                           'Page208 not reviewed in this package', 'Printed arithmetic differences do not validate accounts']})
    return {'full_product_headers_equal': True, 'source_units': graph['unit_count'], 'image_cells_reviewed': 36}


def profile():
    products = load(HERE / 'products.json.gz')
    graph = products['P1']['payload']['graph']
    units = {u['id']: u for u in graph['units']}
    def numbered(n, page=204):
        return anchor(units[statement.DOCUMENT + ':p' + str(page) + ':l' + str(n)])
    source = next(d for d in products['P1']['payload']['request']['bundle']['documents'] if d['id'] == statement.DOCUMENT)
    before = load(PRIOR / 'candidate-answer.json.gz')['incorporation']
    rows = []
    for name, ids, expected in zip(statement.ROWS, ROW_IDS, IMAGE_VALUES):
        label, y22, y21 = [numbered(n) for n in ids]
        assert label['quote'] == statement.ROWS[name] and (y22['quote'], y21['quote']) == expected
        rows.append({'id': name, 'label': label, 'cells': {'2022': y22, '2021': y21}})
    value = {'version': statement.VERSION, 'graph_sha256': digest(graph), 'incorporation_sha256': digest(before),
        'reviewer': {'identity': 'Codex supplied original-image review2026-10-15', 'basis': 'AGENT_EXPOSED_DEVELOPMENT_REVIEW', 'independent': False},
        'source': {'document': statement.DOCUMENT, 'page': 204, 'path': source['path'], 'sha256': source['sha256'],
                   'image_path': str(IMAGE.relative_to(ROOT)), 'image_sha256': file_hash(IMAGE)},
        'metadata': [numbered(n) for n in (0, 1, 2)], 'heading': numbered(3), 'entity': numbered(4),
        'subtitle': numbered(5), 'unit': numbered(6), 'years': {'2022': numbered(7), '2021': numbered(8)},
        'rows': rows, 'footnotes': [numbered(n) for n in (63, 64)],
        'rounding_context': [numbered(n, 6) for n in (8, 9, 10)],
        'selected_reading': None, 'financial_values_validated': False}
    save('profile.json', value)
    save('profile-pin.json', {'sha256': digest(value)})
    return {'rows': 18, 'cells': 36, 'source_occurrences': 65, 'independent': False}


def baseline():
    answer = service.consume(load(HERE / 'products.json.gz'), ROOT)
    save('baseline-answer.json.gz', answer)
    assert answer == load(PRIOR / 'candidate-answer.json.gz')
    return {'full_latest_answer_equal': True, 'questions': {q: r['status'] for q, r in answer['questions'].items()}}


def compare():
    products, packet = load(HERE / 'products.json.gz'), read(HERE / 'profile.json')
    result = statement.consume(products, packet, ROOT, expected_profile_sha256=digest(packet))
    save('statement-consumer.json.gz', result)
    assert result['answer'] == load(HERE / 'baseline-answer.json.gz')
    review = result['statement_review']
    assert review['printed_cells'] == 36 and review['original_occurrences_accounted'] == 65
    assert [(r['cells']['2022']['literal'], r['cells']['2021']['literal']) for r in review['rows']] == IMAGE_VALUES
    arithmetic = review['arithmetic']
    residuals = [(r['group'], r['year'], r['printed_minus_sum']) for r in arithmetic if r['status'] == 'PRINTED_RESIDUAL']
    assert residuals == [('nonrec', '2022', 1), ('oci', '2022', -1)]
    unknown = [(r['group'], r['year']) for r in arithmetic if r['status'] == 'UNKNOWN_COMPONENT']
    assert unknown == [('rec', '2022')]
    assert not review['page208_reviewed'] and not review['financial_values_validated']
    report = {'status': 'PASS', 'full_latest_answer_equal': True, 'ordinary_answer_unchanged': True,
        'rows': 18, 'cells': 36, 'source_occurrences': 65, 'printed_residuals': residuals,
        'unknown_arithmetic': unknown, 'arithmetic_role': 'EXPLANATORY_ONLY',
        'page204_scope_inclusion': [r['page204_in_candidate_scope'] for r in review['incorporation_alternatives']],
        'page208_reviewed': False, 'legal_scope_resolved': False, 'independent_reading': False,
        'financial_values_validated': False, 'native_calls': 0, 'http_calls': 0,
        'installed_optional_evaluated': False}
    save('comparison.json', report)
    return report


def controls():
    products, original = load(HERE / 'products.json.gz'), read(HERE / 'profile.json')
    incorporation = load(HERE / 'baseline-answer.json.gz')['incorporation']
    graph = products['P1']['payload']['graph']
    result = []
    (HERE / 'adverse-inputs').mkdir()
    cases = ('swapped-years', 'swapped-cells', 'cross-row', 'sign-loss', 'omitted-cell', 'duplicate-cell',
             'changed-unit', 'changed-source', 'changed-image', 'omitted-footnote', 'omitted-rounding',
             'claimed-legal-selection', 'claimed-financial-validation', 'stale-pin')
    for name in cases:
        value = deepcopy(original)
        if name == 'swapped-years':
            value['years']['2022'], value['years']['2021'] = value['years']['2021'], value['years']['2022']
        elif name == 'swapped-cells':
            cells = value['rows'][0]['cells']; cells['2022'], cells['2021'] = cells['2021'], cells['2022']
        elif name == 'cross-row':
            a, b = value['rows'][0]['cells'], value['rows'][1]['cells']
            value['rows'][0]['cells'], value['rows'][1]['cells'] = b, a
        elif name == 'sign-loss': value['rows'][0]['cells']['2022']['quote'] = '391'
        elif name == 'omitted-cell': del value['rows'][0]['cells']['2021']
        elif name == 'duplicate-cell': value['rows'][0]['cells']['2022'] = deepcopy(value['rows'][1]['cells']['2022'])
        elif name == 'changed-unit': value['unit'] = deepcopy(value['entity'])
        elif name == 'changed-source': value['source']['sha256'] = '0' * 64
        elif name == 'changed-image': value['source']['image_sha256'] = '0' * 64
        elif name == 'omitted-footnote': value['footnotes'].pop()
        elif name == 'omitted-rounding': value['rounding_context'].pop()
        elif name == 'claimed-legal-selection': value['selected_reading'] = 'full-financial-statements'
        elif name == 'claimed-financial-validation': value['financial_values_validated'] = True
        else: value['reviewer']['identity'] += 'changed'
        pin = digest(original) if name == 'stale-pin' else digest(value)
        save('adverse-inputs/' + name + '.json', {'profile': value, 'expected_profile_sha256': pin})
        try:
            statement.evaluate(graph, incorporation, value, ROOT, expected_profile_sha256=pin)
        except ValueError as error:
            result.append({'case': name, 'refused': True, 'repinned': name != 'stale-pin', 'reason': str(error)})
        else:
            raise AssertionError('Altered table reading accepted: ' + name)
    save('actual-controls.json', result)
    return {'actual_controls_refused': len(result), 'repinned_controls': len(result) - 1}


def tests():
    import pytest
    code = pytest.main(['-q', 'tests/prospectus/test_basf_statement.py', '--junitxml=' + str(HERE / 'tests.xml')])
    assert code == 0
    return {'pytest_exit': int(code)}


def main():
    stage = sys.argv[1]
    assert stage in {'prepare', 'profile', 'baseline', 'compare', 'controls', 'tests'}
    ad = bindings()
    folder = HERE / 'invocations' / stage
    folder.mkdir(parents=True, exist_ok=False)
    save('invocations/' + stage + '/started.json', {
        'command': ['.venv/bin/python', '-m', 'scripts.prospectus_basf_statement', stage],
        'git_commit': ad['git_commit'], 'plan': PLAN, 'environment': sys.executable,
        'started_at': datetime.now(timezone.utc).isoformat(),
        'cpu_gpu': 'CPU only;no GPU/framework imports', 'random_seeds': 'N/A deterministic'})
    tick = time.monotonic()
    def expire(signum, frame):
        raise TimeoutError('120-second statement stage bound;no automatic retry')
    signal.signal(signal.SIGALRM, expire)
    signal.alarm(120)
    try:
        details = globals()[stage]()
        bindings()
        size = sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
        assert size < 350 * 1024 * 1024
        result = {'status': 'PASS', 'stage': stage, 'details': details,
                  'wall_seconds': time.monotonic() - tick, 'retained_bytes': size}
    except BaseException as error:
        save('invocations/' + stage + '/result.json', {'status': 'FAIL', 'error': repr(error),
                                                     'wall_seconds': time.monotonic() - tick})
        raise
    finally:
        signal.alarm(0)
    save('invocations/' + stage + '/result.json', result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
