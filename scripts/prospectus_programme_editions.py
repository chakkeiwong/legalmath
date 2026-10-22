"""Actual JPX editions through an optional, unaccepted target review."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from scripts import prospectus_jpx_sources as source_tools
from legalmath.prospectus.execution_authority import read, write, file_hash
from legalmath.prospectus import programme_editions
from legalmath.prospectus.successor import process_ledger, sealed_runtime, sealed_source, service
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor
from legalmath.prospectus.successor.relation_discovery import discover, PROFILE, SCOPED_PROFILE

BASE = ROOT / 'docs/implementation/prospectus-execution-authority/attempts'
HERE = BASE / 'relation-discovery/attempt-005'
PRIOR = BASE / 'native-layout-cases/attempt-006'
CATALOGUE = BASE / 'native-layout-cases/attempt-002'
PLAN = 'docs/plans/prospectus-jpx-edition-target-2026-10-15.md'
URL = source_tools.PREFIX + 'um3qrc000001sf1y.pdf'
source_tools.HERE = HERE
source_tools.ACQUISITION = HERE
source_tools.SNAPSHOT = PRIOR / 'snapshot'
source_tools.FILES = {'programme-2025': 'um3qrc000001sf1y.pdf'}
source_tools.NATIVE_HISTORY = 73
source_tools.NATIVE_LIMIT = 4
source_tools.PLAN = PLAN
save = source_tools.save
load = source_tools.load


def bindings():
    assert not (HERE / 'outputs.json').exists()
    ad = read(HERE / 'admission.json')
    assert all(file_hash(ROOT / p) == h for p, h in ad['binding'].items())
    if (HERE / 'methods.json').exists():
        assert all(file_hash(ROOT / p) == h for p, h in read(HERE / 'methods.json').items())
    return ad


def prepare():
    for name, hashed in read(PRIOR / 'outputs.json').items():
        assert file_hash(PRIOR / name) == hashed
    assert URL in read(CATALOGUE / 'jpx-issuer-document-links.json')
    paths = [Path(__file__), ROOT / 'scripts/prospectus_jpx_sources.py', source_tools.WORKER,
             ROOT / 'src/legalmath/prospectus/programme_editions.py', ROOT / 'tests/prospectus/test_programme_editions.py']
    paths += sorted((ROOT / 'src/legalmath/prospectus/successor').glob('*.py'))
    methods = {str(p.relative_to(ROOT)): file_hash(p) for p in paths}
    save('methods.json', methods)
    for name in methods:
        target = HERE / 'methods' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    save('pre-run-audit.json', {'status': 'PASS', 'plan': PLAN,
        'baseline': str(PRIOR.relative_to(ROOT)), 'exact_url': URL,
        'catalogue_sha256': file_hash(CATALOGUE / 'fetches/06/body'),
        'question': 'Distinguish printed2025 target from same-publication-date2026 candidate',
        'field_associations': 'Supplied exposed review;not independent or automatic Japanese construction',
        'date_equality_role': 'Necessary edition screen only;never legal acceptance',
        'http_limit': 2, 'prior_http_starts': 8, 'native_limit': 4, 'prior_native_reservations': 73})
    return {'exact_candidates': 1, 'http_starts': 0, 'native_starts': 0}


def reserve():
    folder = HERE / 'fetches/01'
    folder.mkdir(parents=True, exist_ok=False)
    argv = ['curl', '--silent', '--show-error', '--connect-timeout', '10', '--max-time', '25',
        '--max-filesize', '20971520', '--max-redirs', '0', '--dump-header', str((folder / 'headers').relative_to(ROOT)),
        '--output', str((folder / 'body').relative_to(ROOT)), '--write-out',
        '{"http_code":"%{http_code}","size_download":%{size_download},"time_total":%{time_total}}', URL]
    write(folder / 'started.json', {'command': argv, 'started_at': datetime.now(timezone.utc).isoformat(),
        'state': 'RESERVED_HTTP_COMMAND', 'budget_maximum': 2, 'prior_http_starts': 8}, exclusive=True)
    return {'command': argv}


def record():
    folder = HERE / 'fetches/01'
    metrics = json.loads(sys.argv[2])
    code = int(sys.argv[3])
    result = {**metrics, 'exit_code': code, 'actual_command': read(folder / 'started.json')['command'],
        'execution': 'trusted network command', 'redirect_followed': False,
        'retained_files': {name: {'sha256': file_hash(folder / name), 'bytes': (folder / name).stat().st_size}
                          for name in ('headers', 'body') if (folder / name).exists()}}
    write(folder / 'result.json', result, exclusive=True)
    body = (folder / 'body').read_bytes()
    assert code == 0 and str(metrics['http_code']) == '200' and body.startswith(b'%PDF-')
    assert len(body) == metrics['size_download'] <= 20 * 1024 * 1024
    with (HERE / 'programme-2025.pdf').open('xb') as stream:
        stream.write(body)
    return {'bytes': len(body), 'source_sha256': file_hash(HERE / 'programme-2025.pdf')}


def source():
    assert read(HERE / 'IMAGE-REVIEW.json')['reviewed'] is True
    inspection = read(HERE / 'inspection.json')['sources']
    assert len(inspection) == 1
    request = deepcopy(load(PRIOR / 'products.json.gz')['P1']['payload']['request'])
    doc = inspection[0]
    request['bundle']['documents'].append({'id': doc['id'], 'path': str((HERE / 'programme-2025.pdf').relative_to(ROOT)),
        'sha256': doc['source_sha256'], 'format': 'pdf', 'language': 'ja', 'page_count': doc['page_count'],
        'authority': 'Retained exact official JPX candidate;historical authority and legal amendment scope unaccepted',
        'acquisition': {'path': str((HERE / 'fetches/01/result.json').relative_to(ROOT)),
                        'sha256': file_hash(HERE / 'fetches/01/result.json')}})
    save('request.json', request)
    rt = source_tools.runtime('source')
    with process_ledger.observe(HERE / 'native-ledger.json'):
        product = sealed_source.source_product(request, ROOT, rt)
    save('source-product.json.gz', product)
    assert len(rt.receipts) == 3
    save('source-receipts.json', rt.receipts)
    return {'documents': 3, 'units': product['payload']['graph']['unit_count'], 'native_calls': 3}


def construct():
    p1 = load(HERE / 'source-product.json.gz')
    p2 = service.construction_product(p1, ROOT)
    p3 = service.interpretation_product(p1, p2)
    products = {'P1': p1, 'P2': p2, 'P3': p3, 'P4': service.law_product(p1, p3), 'P5': service.financial_product(p1, p2, p3)}
    answer = service.consume(products, ROOT, include_artifacts=True)
    save('products.json.gz', products)
    save('baseline-answer.json.gz', answer)
    prior = load(PRIOR / 'products.json.gz')['P1']['payload']['graph']['units']
    current = p1['payload']['graph']['units']
    ids = {u['document'] for u in prior}
    assert [u for u in current if u['document'] in ids] == prior
    return {'old_units_unchanged': len(prior), 'new_units': len(current)-len(prior),
        'questions': {q: r['status'] for q, r in answer['questions'].items()}}


def profile():
    products = load(HERE / 'products.json.gz')
    graph = products['P1']['payload']['graph']
    units = graph['units']
    def one(document, literal):
        rows = [u for u in units if u['document'] == document and u['page'] == 1 and u['raw'] == literal]
        assert len(rows) == 1, (document, literal, len(rows))
        return anchor(rows[0], 0, len(rows[0]['raw']))
    def date_anchor(document, expected):
        rows = []
        for u in units:
            if u['document'] != document or u['page'] != 1:
                continue
            try:
                parsed = programme_editions.printed_date(u['raw'])
            except ValueError:
                continue
            if parsed == expected:
                rows.append(u)
        assert len(rows) == 1, (document, expected, len(rows))
        return anchor(rows[0], 0, len(rows[0]['raw']))
    def identity(document, expected):
        return {'document': document, 'issuer_label': one(document, '【発行者の名称】'),
            'issuer': one(document, '独立行政法人国際協力機構'), 'publication_label': one(document, '【公表日】'),
            'publication_date': date_anchor(document, expected)}
    sources = []
    for doc in read(HERE / 'request.json')['bundle']['documents']:
        folder = HERE if doc['id'] == 'jpx-jica-programme-2025' else PRIOR
        image = folder / (doc['id'] + '-page-1.png')
        sources.append({'document': doc['id'], 'source_path': doc['path'], 'source_sha256': doc['sha256'],
                        'cover_path': str(image.relative_to(ROOT)), 'cover_sha256': file_hash(image)})
    programmes = [identity('jpx-jica-programme', '2026-08-06'), identity('jpx-jica-programme-2025', '2025-08-07')]
    correction = identity('jpx-jica-correction', '2026-08-06')
    doc = correction['document']
    indexed = {u['id']: u for u in units}
    def numbered(n):
        u = indexed[doc + ':p1:l' + str(n)]
        return anchor(u, 0, len(u['raw']))
    correction.update(target_context=[numbered(n) for n in (30,31,32)],
        before_label=numbered(35), before_period_label=numbered(36), before_period=numbered(37),
        after_label=numbered(38), after_period_label=numbered(39), after_period=numbered(40))
    value = {'version': programme_editions.VERSION, 'source_graph_sha256': digest(graph),
        'reviewer': {'identity': 'Codex exposed original-image review2026-10-15',
                     'basis': 'AGENT_EXPOSED_DEVELOPMENT_REVIEW', 'independent': False},
        'sources': sources, 'programmes': programmes, 'correction': correction, 'accepted_relations': []}
    save('profile.json', value)
    save('profile-pin.json', {'sha256': digest(value)})
    return {'programmes': 2, 'correction_context_units': 3, 'automatic_field_associations': False}


def tests():
    import pytest
    code = pytest.main(['-q', 'tests/prospectus/test_programme_editions.py', '--junitxml=' + str(HERE / 'tests.xml')])
    assert code == 0
    return {'pytest_exit': int(code)}


def compare():
    products = load(HERE / 'products.json.gz')
    original = read(HERE / 'profile.json')
    output = programme_editions.consume(products, original, ROOT, expected_profile_sha256=digest(original))
    save('edition-consumer.json.gz', output)
    baseline = load(HERE / 'baseline-answer.json.gz')
    assert output['answer'] == baseline
    review = output['edition_review']
    assert review['target_state'] == 'COMPATIBLE_CANDIDATE'
    assert [r['status'] for r in review['candidates']] == ['EDITION_MISMATCH', 'EDITION_COMPATIBLE_REQUIRES_REVIEW']
    assert review['correction_publication_date'] == '2026-08-06' and review['target_programme_date'] == '2025-08-07'
    assert review['printed_before_period']['end'] == '2027-08-07' and review['printed_after_period']['end'] == '2026-08-06'
    cases = []
    for name in ('missing', 'duplicate'):
        value = deepcopy(original)
        if name == 'missing': value['programmes'] = value['programmes'][:1]
        else: value['programmes'].append(deepcopy(value['programmes'][-1]))
        result = programme_editions.consume(products, value, ROOT, expected_profile_sha256=digest(value))
        save(name + '-consumer.json.gz', result)
        expected = 'MISSING_TARGET' if name == 'missing' else 'AMBIGUOUS_TARGET'
        assert result['edition_review']['target_state'] == expected
        assert result['answer'] == baseline and result['edition_review']['accepted_relations'] == []
        cases.append({'case': name, 'state': expected, 'full_answer_unchanged': True})
    old_products = load(PRIOR / 'products.json.gz')
    repeated = service.consume(old_products, ROOT, include_artifacts=True)
    assert repeated == load(PRIOR / 'answer.json.gz')
    save('prior-two-source-reconsumed.json.gz', repeated)
    discovery = {p: discover(products['P1']['payload']['graph'], p) for p in (PROFILE, SCOPED_PROFILE)}
    save('existing-discovery.json.gz', discovery)
    ledger = process_ledger.checked(HERE / 'native-ledger.json')
    assert len(ledger['reservations']) == 4
    for stage, count in (('inspect', 1), ('source', 3)):
        for index in range(count):
            folder = HERE / ('native-' + stage) / str(index)
            receipt = read(folder / 'receipt.json')
            sealed_runtime.verify_receipt(receipt, read(HERE / 'snapshot/manifest.json'), receipt['argv'],
                (folder / 'stdin').read_bytes(), (folder / 'stdout').read_bytes(), (folder / 'stderr').read_bytes())
    report = {'status': 'PASS', 'scope': 'OPTIONAL_JAPANESE_PRINTED_EDITION_SCREEN',
        'compatible_2025_candidate': True, 'incompatible_2026_candidate': True,
        'correction_publication_date_not_used_as_target': True, 'context_preserved': True,
        'actual_cases': cases, 'full_current_answer_unchanged': True, 'prior_full_answer_reproduced': True,
        'default_candidates': {p: len(v['candidates']) for p, v in discovery.items()},
        'accepted_relations': 0, 'independent_legal_acceptance': False,
        'http_starts': 1, 'historical_visible_source_http_lower_bound': 9,
        'native_reservations': 4, 'historical_visible_native_reservation_lower_bound': 77,
        'installed_optional_evaluated': False}
    save('comparison.json', report)
    return report


def controls():
    products = load(HERE / 'products.json.gz')
    original = read(HERE / 'profile.json')
    results = []
    for name in ('changed-image', 'changed-original', 'changed-quote', 'wrong-date-label',
                 'omitted-joint-context', 'reversed-period-roles', 'publication-as-target', 'fabricated-acceptance', 'stale-pin'):
        value = deepcopy(original)
        if name == 'changed-image': value['sources'][0]['cover_sha256'] = '0' * 64
        elif name == 'changed-original': value['sources'][0]['source_sha256'] = '0' * 64
        elif name == 'changed-quote': value['programmes'][0]['publication_date']['quote'] = '2025年8月7日'
        elif name == 'wrong-date-label': value['programmes'][0]['publication_label'] = deepcopy(value['programmes'][0]['issuer_label'])
        elif name == 'omitted-joint-context': value['correction']['target_context'].pop()
        elif name == 'reversed-period-roles':
            a,b = value['correction']['before_period'],value['correction']['after_period']
            value['correction']['before_period'],value['correction']['after_period'] = b,a
        elif name == 'publication-as-target': value['correction']['target_context'] = [deepcopy(value['correction']['publication_date'])]
        elif name == 'fabricated-acceptance': value['accepted_relations'] = [{'from': 'correction', 'to': '2026'}]
        else: value['reviewer']['identity'] += 'changed'
        pin = digest(original) if name == 'stale-pin' else digest(value)
        try:
            programme_editions.consume(products, value, ROOT, expected_profile_sha256=pin)
        except ValueError as error:
            results.append({'case': name, 'refused': True, 'repinned': name != 'stale-pin', 'reason': str(error)})
        else:
            raise AssertionError('Adverse edition packet accepted: ' + name)
    save('actual-controls.json', results)
    return {'adverse_controls_refused': len(results)}


def main(stage):
    assert stage in {'prepare','reserve','record','native-prepare','inspect','source','construct','profile','tests','compare','controls'}
    ad = bindings()
    folder = HERE / 'invocations' / stage
    folder.mkdir(parents=True, exist_ok=False)
    save('invocations/' + stage + '/started.json', {
        'command': ['.venv/bin/python','-m','scripts.prospectus_jpx_sources', *sys.argv[1:]],
        'environment': sys.executable, 'native_environment': source_tools.PYTHON, 'git_commit': ad['git_commit'],
        'plan': PLAN, 'started_at': datetime.now(timezone.utc).isoformat(),
        'cpu_gpu': 'CPU only;CUDA_VISIBLE_DEVICES=-1', 'random_seeds': 'N/A deterministic'})
    tick = time.monotonic()
    def expire(signum, frame):
        raise TimeoutError('120-second stage bound;no automatic retry')
    signal.signal(signal.SIGALRM, expire)
    signal.alarm(120)
    try:
        if stage == 'native-prepare': details = source_tools.native_prepare()
        elif stage == 'inspect': details = source_tools.inspect()
        else: details = globals()[stage]()
        bindings()
        size = sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
        assert size < 350 * 1024 * 1024
        result = {'status':'PASS','stage':stage,'details':details,'evidence_bytes':size}
    except BaseException as error:
        save('invocations/' + stage + '/result.json', {'status':'FAIL','error':repr(error),'wall_seconds':time.monotonic()-tick})
        raise
    finally:
        signal.alarm(0)
    result['wall_seconds'] = time.monotonic()-tick
    save('invocations/' + stage + '/result.json', result)
    print(json.dumps(result,ensure_ascii=False))
