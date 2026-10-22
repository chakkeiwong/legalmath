"""Exact archive boundary consumers with lossless large-evidence references."""
import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import gzip
import json
import os
from pathlib import Path
import signal
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus.execution_authority import Authority, REL, read, write, file_hash, digest as authority_digest
from legalmath.prospectus.successor import service, corrections
from legalmath.prospectus.successor.contracts import digest

PLAN = 'docs/plans/prospectus-source-archive-consumers-2026-10-18.md'
SCRIPT = 'scripts/prospectus_archive_consumer_stage.py'
REVIEW = REL + '/reviews/source-archive-consumers-265'
ATTEMPT = REL + '/attempts/source-authority/attempt-007'
ACQUISITION = REL + '/attempts/source-authority/attempt-006'
PT08 = REL + '/attempts/portuguese-2008/attempt-003'
PT09 = 'docs/implementation/prospectus-integration-closure/ocr-geometry-repair-2026-10-12/consumer/attempt-002/evidence'
PROPOSAL = REL + '/proposals/source-archive-consumers-265.json'
ROUTES = REL + '/closure-routes-2026-10-18-source-archive-consumers-265.json'
BOUNDS = {'preparation_seconds': 90, 'stage_seconds': 110, 'new_seconds': 360,
          'new_bytes': 64 * 1024**2, 'aggregate006plus_bytes': 100 * 1024**2,
          'reserve_bytes': 2 * 1024**2, 'report_workers': 2, 'new_network_calls': 0}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def load(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def save(path, value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
    if path.suffix == '.gz':
        raw = gzip.compress(raw, compresslevel=1, mtime=0)
    with path.open('xb') as stream:
        stream.write(raw)


def same(a, b, message):
    require(digest(a) == digest(b), message)


def reference_answer(retained):
    if 'source_map' not in retained:
        return retained
    value = {k: v for k, v in retained.items() if k not in
        {'source_map', 'assembly', 'selected_contract', 'clause_graph', 'dependencies', 'report_sha256'}}
    value['report_sha256'] = digest(value)
    return value


def storage():
    files = {ROOT / n for n in (PLAN, SCRIPT, PROPOSAL, ROUTES,
        REL + '/revisions/0265.json')}
    files |= {p for folder in (ROOT / REVIEW, ROOT / ATTEMPT) for p in folder.rglob('*') if p.is_file()}
    added = sum(p.stat().st_size for p in files if p.is_file())
    prior = read(ROOT / ACQUISITION / 'result.json')['budget']['retained_bytes_before_seal']
    # Charge the entire acquisition directory in addition to its pre-seal total:
    # conservative overcount, so metadata/seal files cannot escape accounting.
    prior += sum(p.stat().st_size for p in (ROOT / ACQUISITION).rglob('*') if p.is_file())
    require(added < BOUNDS['new_bytes'] - BOUNDS['reserve_bytes'], 'Consumer storage ceiling')
    require(added + prior < BOUNDS['aggregate006plus_bytes'] - BOUNDS['reserve_bytes'], 'Aggregate archive storage ceiling')
    return {'new_bytes': added, 'conservative006plus_bytes': prior + added}


def inputs():
    names = {ACQUISITION + '/outputs.json', ACQUISITION + '/result.json',
             PT08 + '/outputs.json', PT08 + '/common-products.json.gz',
             PT08 + '/positive-v2-products.json.gz', PT08 + '/positive-v2-answer.json.gz',
             PT09 + '/manifest.json', PT09 + '/source-product.json.gz',
             PT09 + '/scope-admission.json', PT09 + '/answer.json.gz'}
    for year in ('2008', '2009'):
        names.update(ACQUISITION + f'/{kind}-{year}/{filename}'
            for kind, files in [('metadata', ('body.json', 'result.json')),
                                ('content', ('source.pdf', 'headers.txt', 'result.json', 'started.json'))]
            for filename in files)
    return names


def original(year):
    if year == '2008':
        common = load(ROOT / PT08 / 'common-products.json.gz')
        later = load(ROOT / PT08 / 'positive-v2-products.json.gz')
        ps = {**common, **later}
        baseline = load(ROOT / PT08 / 'positive-v2-answer.json.gz')
    else:
        p1 = load(ROOT / PT09 / 'source-product.json.gz')
        p2 = service.construction_product(p1, ROOT)
        p3 = service.interpretation_product(p1, p2, {'source_report_scope': read(ROOT / PT09 / 'scope-admission.json')})
        ps = {'P1': p1, 'P2': p2, 'P3': p3,
              'P4': service.law_product(p1, p3), 'P5': service.financial_product(p1, p2, p3)}
        baseline = load(ROOT / PT09 / 'answer.json.gz')
    for name, p in ps.items():
        service.verify(p, name)
    require(set(ps) == {'P1', 'P2', 'P3', 'P4', 'P5'}, 'Incomplete original products')
    return ps, baseline


def verify_original_files():
    for folder, manifest in ((ACQUISITION, 'outputs.json'), (PT08, 'outputs.json'), (PT09, 'manifest.json')):
        expected = read(ROOT / folder / manifest)
        if 'files' in expected:
            expected = expected['files']
        require(isinstance(expected, dict), 'Missing retained source manifest')
        for n in inputs():
            if n.startswith(folder + '/') and n != folder + '/' + manifest:
                suffix = n[len(folder) + 1:]
                require(expected.get(suffix) == file_hash(ROOT / n), 'Retained original hash differs: ' + n)


def prepare():
    tick = time.monotonic()
    auth = Authority(ROOT)
    old, tasks, _ = auth.spec()
    require(old['revision'] == 264, 'Wrong continuation baseline')
    require(next(e for e in reversed(auth.events()) if e.get('task') == 'source-authority')['kind'] == 'RECORD', 'Retain acquisition first')
    verify_original_files()
    folder = ROOT / REVIEW
    folder.mkdir(parents=True, exist_ok=False)
    names = inputs()
    preflight = []
    for year, path in [('2008', PT08 + '/common-products.json.gz'), ('2009', PT09 + '/source-product.json.gz')]:
        value = load(ROOT / path)
        p1 = value['P1'] if year == '2008' else value
        service.verify(p1, 'P1')
        graph = p1['payload']['graph']
        receipt = read(ROOT / ACQUISITION / ('content-' + year) / 'result.json')
        matches = [d for d in p1['payload']['request']['bundle']['documents'] if d['sha256'] == receipt['source']['source_sha256']]
        require(len(matches) == 1 and matches[0]['language'] == 'pt', 'Wrong source edition')
        for d in p1['payload']['request']['bundle']['documents']:
            require(file_hash(ROOT / d['path']) == d['sha256'], 'Source bytes changed')
            names.add(d['path'])
        require(graph['bundle_sha256'] == digest(p1['payload']['request']['bundle']), 'Original graph binding differs')
        check_tick = time.monotonic()
        ps, retained = original(year)
        same(service.consume(ps, ROOT), reference_answer(retained), 'Fresh original consumer differs before admission: ' + year)
        preflight.append({'year': year, 'seconds': time.monotonic() - check_tick,
                          'whole_original_answer_equal': True})
    controls = ({'complete': False}, {'complete': 0}, {}, {'complete': False, 'extra': None})
    for changed in controls[1:]:
        try:
            same(controls[0], changed, 'Expected typed/coverage mismatch')
        except ValueError:
            pass
        else:
            raise ValueError('Comparator permits changed type, missing or extra field')
    methods = {str(p.relative_to(ROOT)) for p in (ROOT / 'src/legalmath/prospectus/successor').glob('*.py')}
    methods |= {PLAN, SCRIPT}
    frozen = {'inputs': {n: file_hash(ROOT / n) for n in sorted(names)},
              'methods': {n: file_hash(ROOT / n) for n in sorted(methods)}}
    write(folder / 'frozen.json', frozen, exclusive=True)
    new = deepcopy(old)
    new['revision'] = 265
    task = next(t for t in new['tasks'] if t['id'] == 'source-authority')
    task.update(dossier=PLAN, priority=-10,
        reason='Consume both exact Portuguese archive copies at date/knowledge boundaries; preserve full answers with immutable references',
        archive_consumer_followup={'version': 'archive-consumers.v1', 'review': REVIEW, 'bounds': BOUNDS})
    task['inputs'] = sorted(set(task['inputs']) | names | methods | {REVIEW + '/frozen.json', REVIEW + '/preparation.json'})
    attempts = [e['attempt'] for e in auth.events() if e['kind'] == 'ADMIT' and e['budget_key'] == task['budget_key']]
    require(len(attempts) == old['budgets'][task['budget_key']]['maximum_new_attempts'] == 6, 'Source admission lineage differs')
    new['budgets'][task['budget_key']]['maximum_new_attempts'] = 7
    routes = read(ROOT / old['continuation_review']['routes'])
    routes['baseline_revision'] = 265
    for row in routes['tasks']:
        if row['task'] == task['id']:
            row.update(task_sha256=authority_digest(task), dossier=PLAN, mode='local', phase=0,
                remaining=task['reason'], next_action='Run one bounded normal-consumer worker per Portuguese source, then reconcile original source acceptance.',
                stop_condition=json.dumps(BOUNDS, sort_keys=True))
    write(ROOT / ROUTES, routes, exclusive=True)
    new['continuation_review'].update(plan=PLAN, routes=ROUTES)
    for n in (PLAN, SCRIPT, ROUTES):
        new['continuation_review']['bindings'][n] = file_hash(ROOT / n)
    elapsed = time.monotonic() - tick
    require(elapsed < BOUNDS['preparation_seconds'], 'Preparation time ceiling')
    write(folder / 'preparation.json', {'status': 'PASS', 'seconds': elapsed,
        'input_files': len(names), 'correct_portuguese_editions': 2,
        'original_consumer_preflight': preflight, 'comparator_adverse_controls': 3,
        'prior_acquisition': read(ROOT / ACQUISITION / 'result.json')['budget'],
        'historical_unmeasured_time': 'UNKNOWN'}, exclusive=True)
    review = {'baseline': authority_digest(old), 'changes': task['reason'], 'scope_unchanged': True, 'budget_unchanged': False,
        'skeptical_audit': {'verdict': 'PASS', 'plan': PLAN,
            'repairs': ['Use Portuguese2009 instead of English2009 P1', 'Lossless references avoid full-answer duplication',
                        'Retain unknown acquisition overhead; do not certify old240second ceiling']},
        'evidence_contract': {'question': 'Exact archive observations through complete original-source consumers',
            'baseline': [PT08, PT09], 'primary': 'Independent date truth and exact matched products/answers with adverse refusals',
            'veto': 'Source/edition drift, unexplained answer changes, invalid reconstruction, budget exhaustion',
            'not_concluded': ['original publication', 'authenticity', 'legal availability', 'whole task']},
        'budget_revision': {'budget_key': task['budget_key'], 'previous_maximum': 6, 'new_maximum': 7,
            'retained_attempts': attempts, 'reason': 'Finish omitted consumer stage after audited storage/edition/time repair',
            'next_discriminating_check': 'Two actual exact-edition boundary consumers', 'stop_condition': BOUNDS,
            'same_scope_authorization': 'Continue user-authorized conditional source build without external opinions'}}
    auth.validate_program(new)
    write(ROOT / PROPOSAL, new, exclusive=True)
    write(folder / 'review.json', review, exclusive=True)
    print(json.dumps({'revision': 265, 'preparation_seconds': elapsed, 'source_editions': 2}))


def frozen():
    value = read(ROOT / REVIEW / 'frozen.json')
    for group in value.values():
        for n, h in group.items():
            require(file_hash(ROOT / n) == h, 'Frozen evidence changed: ' + n)
    return value


def packet(year, document):
    folder = ROOT / ACQUISITION
    receipt = read(folder / ('content-' + year) / 'result.json')
    selected = receipt['capture']
    capture = datetime.strptime(selected['metadata']['tstamp'], '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
    binding = lambda name: {'path': str((folder / name).relative_to(ROOT)), 'sha256': file_hash(folder / name)}
    return {'version': 'source-archive-observations.v1', 'query_at': capture.isoformat(),
        'review': {'kind': 'DEVELOPMENT', 'reviewer': 'executor',
                   'reason': 'Exact independently retained issuer bytes; archive record only, publication/authenticity unknown'},
        'captures': [{'id': 'arquivo-2015-bes-' + year + '-pt', 'document': document,
            'source_sha256': receipt['source']['source_sha256'], 'original_url': selected['metadata']['originalURL'],
            'capture_at': capture.isoformat(), 'retrieved_at': receipt['retrieved_at'],
            'index': binding('metadata-' + year + '/body.json'), 'record_index': selected['index'],
            'headers': binding('content-' + year + '/headers.txt'), 'content': binding('content-' + year + '/source.pdf')}]}


def rebuild(original_ps, known_at, observation=None):
    request = deepcopy(original_ps['P1']['payload']['request'])
    graph = deepcopy(original_ps['P1']['payload']['graph'])
    request['bundle']['known_at'] = known_at
    graph['context']['known_at'] = known_at
    graph['bundle_sha256'] = digest(request['bundle'])
    if 'correction_admission' in request:
        previous = graph.pop('corrections')
        request['correction_admission']['graph_sha256'] = digest(graph)
        graph['corrections'] = corrections.admit(graph, request['correction_admission'])
        same(graph['corrections']['entries'], previous['entries'], 'Correction text or provenance changed')
    request['source_report_readings']['graph_sha256'] = digest(graph)
    if observation is not None:
        request['archive_observations'] = observation
    p1 = service.seal('P1', request['bundle'], {'request': digest(request)}, {'request': request, 'graph': graph})
    p2 = service.construction_product(p1, ROOT)
    interpretation = deepcopy(original_ps['P3']['payload']['interpretation_input'])
    interpretation['source_report_scope']['readings_sha256'] = digest(p2['payload']['source_report_readings'])
    p3 = service.interpretation_product(p1, p2, interpretation)
    p4old, p5old = original_ps['P4']['payload'], original_ps['P5']['payload']
    return {'P1': p1, 'P2': p2, 'P3': p3,
        'P4': service.law_product(p1, p3, p4old.get('cases'), p4old.get('law_input')),
        'P5': service.financial_product(p1, p2, p3, p5old.get('cases'), p5old.get('scenario_input'))}


def compact_products(ps, original_ps):
    result = deepcopy(ps)
    references = {}
    for label, path in [('units', ('P1', 'payload', 'graph', 'units')),
                        ('documents', ('P1', 'payload', 'graph', 'documents')),
                        ('references', ('P1', 'payload', 'graph', 'references')),
                        ('assembly_units', ('P2', 'payload', 'assembly', 'units'))]:
        old, current = original_ps, result
        for key in path[:-1]:
            old, current = old[key], current[key]
        key = path[-1]
        same(current[key], old[key], 'Source or assembly content changed: ' + label)
        references[label] = {'path': list(path), 'sha256': digest(old[key])}
        current[key] = {'retained_original_reference': label}
    restored = deepcopy(result)
    for label, ref in references.items():
        old, current = original_ps, restored
        for key in ref['path'][:-1]:
            old, current = old[key], current[key]
        current[ref['path'][-1]] = old[ref['path'][-1]]
    same(restored, ps, 'Lossless complete product reconstruction failed')
    for name, product in restored.items():
        service.verify(product, name)
    return {'products': result, 'references': references, 'complete_sha256': digest(ps)}


def assess_case(original_ps, archive, known_at, query_at):
    candidate_packet = deepcopy(archive)
    candidate_packet['query_at'] = query_at
    baseline = rebuild(original_ps, known_at)
    candidate = rebuild(original_ps, known_at, candidate_packet)
    before = service.consume(baseline, ROOT)
    after = service.consume(candidate, ROOT)
    same({k: v for k, v in candidate['P2']['payload'].items() if k != 'archive_observations'},
         baseline['P2']['payload'], 'Unrelated construction changed')
    for name in ('P3', 'P4', 'P5'):
        same(candidate[name]['payload'], baseline[name]['payload'], 'Unrelated interpretation/law/finance changed')
    stripped = deepcopy(after)
    del stripped['source_archive_observations']
    for report in stripped['source_reports']:
        del report['archive_observations']
    for key in ('consumed_products', 'request_sha256', 'report_sha256'):
        stripped[key] = before[key]
    same(stripped, before, 'Complete unrelated answer changed')
    row, = archive['captures']
    dt = datetime.fromisoformat
    expected = ('EVIDENCE_NOT_YET_KNOWN' if dt(known_at) < dt(row['retrieved_at']) else
                'NOT_ESTABLISHED_BY_THIS_CAPTURE' if dt(query_at) < dt(row['capture_at']) else
                'ARCHIVE_RECORDED_BY_QUERY_DATE')
    observation, = after['source_archive_observations']['observations']
    require(observation['as_of_query'] == expected, 'Independent date classification disagrees')
    require(observation['publication_date'] == observation['edition_authenticity'] == 'UNKNOWN', 'Unknown source fact promoted')
    require(observation['legal_availability_established'] is False and observation['earlier_absence_established'] is False, 'Archive overclaim')
    require(len(after['source_reports']) >= 2, 'Complete paired report scope missing')
    require(all(r['archive_observations'] == [observation] for r in after['source_reports']), 'Wrong downstream report')
    require(after['may_execute_transaction'] is False and after['independent_legal_acceptance'] is False, 'Authority promoted')
    return baseline, candidate, before, after, expected


def adverse(original_ps, archive):
    row = archive['captures'][0]
    base = rebuild(original_ps, row['retrieved_at'])
    names = ('document', 'source-hash', 'record-index', 'capture-date', 'retrieval-date', 'content-binding')
    results = []
    for name in names:
        changed = deepcopy(archive)
        r = changed['captures'][0]
        if name == 'document': r['document'] = 'wrong-edition'
        if name == 'source-hash': r['source_sha256'] = '0' * 64
        if name == 'record-index': r['record_index'] = True
        if name == 'capture-date': r['capture_at'] = '2011-01-01T00:00:00+00:00'
        if name == 'retrieval-date': r['retrieved_at'] = '2011-01-01T00:00:00+00:00'
        if name == 'content-binding': r['content']['sha256'] = '0' * 64
        try:
            rebuild(original_ps, row['retrieved_at'], changed)
        except ValueError as error:
            results.append({'case': name, 'rejected': True, 'reason': str(error)})
        else:
            raise ValueError('Incorrect source packet accepted: ' + name)
    valid = rebuild(original_ps, row['retrieved_at'], archive)
    p2payload = deepcopy(valid['P2']['payload'])
    p2payload['archive_observations']['observations'][0]['publication_date'] = '2011-01-01'
    forged = {**valid, 'P2': service.seal('P2', valid['P1']['payload']['request']['bundle'], {'P1': valid['P1']['sha256']}, p2payload)}
    # The final consumer checks the archive observation before downstream parent links.
    for name, ps in [('resealed-publication', forged), ('observation-without-request',
            {**base, 'P2': service.seal('P2', base['P1']['payload']['request']['bundle'],
                {'P1': base['P1']['sha256']}, valid['P2']['payload'])})]:
        try:
            service.consume(ps, ROOT)
        except ValueError as error:
            require('Archive observation' in str(error), 'Adverse case stopped at an unrelated validator')
            results.append({'case': name, 'rejected': True, 'reason': str(error)})
        else:
            raise ValueError('Incorrect archive consumer accepted: ' + name)
    return results


def run(year):
    tick = time.monotonic()
    def expired(_signal, _frame):
        raise TimeoutError('Reviewed archive consumer stage ceiling')
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(BOUNDS['stage_seconds'])
    folder = ROOT / ATTEMPT
    out = folder / ('report-' + year)
    out.mkdir(exist_ok=False)
    result = {'status': 'FAIL', 'year': year}
    try:
        auth = Authority(ROOT)
        program, tasks, _ = auth.spec()
        admission = read(folder / 'admission.json')
        require(admission['program_sha256'] == authority_digest(program) and
            admission['binding'] == auth.binding(tasks['source-authority']), 'Admission changed')
        require(next(e for e in reversed(auth.events()) if e.get('task') == 'source-authority')['kind'] == 'ADMIT', 'No active source admission')
        frozen()
        storage()
        ps, retained = original(year)
        before = service.consume(ps, ROOT)
        same(before, reference_answer(retained), 'Fresh original consumer differs from retained complete answer')
        document, = ps['P1']['payload']['request']['bundle']['documents']
        archive = packet(year, document['id'])
        row = archive['captures'][0]
        capture = datetime.fromisoformat(row['capture_at'])
        known = datetime.fromisoformat(row['retrieved_at'])
        cases = [('prior-query', known, capture - timedelta(seconds=1)),
                 ('at-capture', known, capture),
                 ('before-knowledge', known - timedelta(microseconds=1), capture),
                 ('2011-query', known, datetime(2011, 7, 15, tzinfo=timezone.utc))]
        outcomes = []
        for name, k, q in cases:
            baseline, candidate, prior_answer, answer, expected = assess_case(ps, archive, k.isoformat(), q.isoformat())
            save(out / (name + '.json.gz'), {'baseline': compact_products(baseline, ps),
                'candidate': compact_products(candidate, ps), 'baseline_answer': prior_answer,
                'candidate_answer': answer, 'expected': expected})
            outcomes.append({'case': name, 'expected': expected, 'answer_sha256': answer['report_sha256']})
            storage()
            print(json.dumps({'year': year, 'case': name, 'status': 'PASS'}), flush=True)
        rejected = adverse(ps, archive)
        save(out / 'adverse.json', rejected)
        frozen()
        result['storage'] = storage()
        result.update(status='PASS', cases=outcomes, adverse_cases=len(rejected),
            complete_original_answer_equal=True, source_document=document['id'],
            source_sha256=document['sha256'], current_extraction_claimed=False)
    except Exception as error:
        result.update(error=str(error), traceback=traceback.format_exc())
    finally:
        signal.alarm(0)
        result.update(seconds=time.monotonic() - tick, environment=sys.executable,
            command=['.venv/bin/python', '-m', 'scripts.prospectus_archive_consumer_stage', 'run', '--year', year],
            cpu_gpu='CPU only; GPU intentionally hidden before imports', seeds='N/A deterministic',
            plan=PLAN, recorded_at=datetime.now(timezone.utc).isoformat())
        write(out / 'result.json', result, exclusive=True)
    print(json.dumps({k: result[k] for k in ('status', 'year', 'seconds')} | {'error': result.get('error')}))
    return 0 if result['status'] == 'PASS' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'run'))
    parser.add_argument('--year', choices=('2008', '2009'))
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
        return 0
    return run(args.year)


if __name__ == '__main__':
    raise SystemExit(main())
