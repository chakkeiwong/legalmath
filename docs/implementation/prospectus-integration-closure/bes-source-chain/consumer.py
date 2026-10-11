"""Run the reviewed eight-document BES source-chain consumer.

The final-terms OCR and correction/annotation path stays the protected
development comparator. The base prospectus and six supplements are added as
native PDF sources, with exact reviewed anchors and explicit unresolved
onward-source dependencies. This is a bounded source-consumption trial, not a
legal conclusion.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import gzip

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'docs/implementation/prospectus-integration-closure'
PACKAGE = Path(__file__).resolve().parent
PLAN = ROOT / 'docs/plans/prospectus-bes-source-chain-2026-10-11.md'
REAL_SCAN = BASE / 'real-scan'
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.successor import annotation_bridge, corrections, service, source_graph  # noqa: E402
from legalmath.prospectus.successor.contracts import digest  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def save_gzip(path, value):
    with gzip.open(path, 'wt', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, separators=(',', ':'))
        stream.write('\n')


def anchor(unit, start=0, end=None):
    end = len(unit['raw']) if end is None else end
    return {'unit': unit['id'], 'document': unit['document'],
            'source_sha256': unit['source_sha256'], 'start': start, 'end': end,
            'quote': unit['raw'][start:end]}


def one(units, document, predicate, label, pages=None):
    matches = [u for u in units if u['document'] == document and
               (pages is None or u['page'] in pages) and predicate(u['raw'])]
    if len(matches) != 1:
        raise ValueError(f'{label}: expected one occurrence, got {len(matches)}')
    return matches[0]


def base_documents():
    inventory = read(PACKAGE / 'source-review-001/inventory.json')
    request = read(REAL_SCAN / 'baseline/attempt-001/request.json')
    final = request['bundle']['documents'][0]
    final.pop('scan_profile', None)
    raw = REAL_SCAN / 'baseline/attempt-001/raw-worker.json'
    final['ocr'] = {'path': str(raw.relative_to(ROOT)), 'sha256': sha(raw)}
    documents = [final]
    names = ['bes-base-2010', 'bes-supplement-1', 'bes-supplement-2',
             'bes-supplement-3', 'bes-supplement-4', 'bes-supplement-5',
             'bes-supplement-6']
    for name, row in zip(names, inventory[1:], strict=True):
        documents.append({'id': name, 'path': row['path'], 'sha256': row['sha256'],
                          'page_count': row['pages'], 'language': 'en',
                          'authority': 'Retained programme source; authenticity not independently established',
                          'document_date': row['document_date'] + 'T00:00:00Z',
                          'known_from': row['known_from']})
    return request, documents


def unresolved_dependencies():
    historical = read(ROOT / 'docs/implementation/prospectus-closure-2026-10-05/dossier-review.json')
    deps = []
    included = {f'BES-DEP-{i:02d}' for i in range(1, 12)}
    for row in historical['dependencies']:
        if row['id'] in included:
            deps.append({'id': row['id'], 'questions': ['Q1', 'Q2'], 'status': 'UNRESOLVED',
                         'reason': 'Historical incorporated source is named and anchored, but its separate bytes are absent from this eight-document request; do not treat repository absence as fresh exhaustive search.',
                         'introduced_by': row['introduced_by'], 'title': row['title'],
                         'incorporated_scope': row['incorporated_scope']})
    for ident, title in (
            ('BES-DEP-AGENCY-01', 'Principal Agency Agreement dated 18 January 2008'),
            ('BES-DEP-AGENCY-02', 'Interbolsa Notes Agency Agreement dated 18 February 2009'),
            ('BES-DEP-AGENCY-03', 'Common Representative Appointment Agreement dated 3 November 2010')):
        deps.append({'id': ident, 'questions': ['Q1', 'Q2'], 'status': 'UNRESOLVED',
                     'reason': 'Base conditions identify this onward agreement, but the agreement bytes are absent from this request.',
                     'title': title})
    return deps


def review_and_graph():
    review = read(REAL_SCAN / 'authoring/attempt-001/review.json')
    template, documents = base_documents()
    template['bundle'] = deepcopy(template['bundle'])
    template['bundle']['documents'] = documents
    template['bundle']['dependencies'] = unresolved_dependencies()
    graph = source_graph.build(template['bundle'], ROOT)
    units = graph['units']
    final_intro = one(units, 'bes-final-terms-2011',
                      lambda text: 'Terms used herein shall be deemed to be defined' in text,
                      'final-terms introduction')
    base_rows = [
        ('issuer-and-class', lambda text: 'Notes will only be issued by the Bank acting through its head office' in text, {76}),
        ('final-terms-precedence', lambda text: text.startswith('The Final Terms for this Note'), {77}),
        ('agreement-precedence', lambda text: 'the Principal Agency Agreement will prevail' in text, {78}),
        ('senior-status', lambda text: 'The Senior Notes and any relative Receipts and Coupons are direct' in text, {80}),
        ('governing-law', lambda text: 'Governing law and submission to jurisdiction' in text, {111}),
        ('portuguese-courts', lambda text: 'The Bank agrees for the exclusive benefit of the Noteholders' in text, {112}),
        ('other-competent-courts', lambda text: 'Nothing contained in this Condition shall limit any right' in text, {112}),
        ('incorporation-scope', lambda text: 'The following documents which have been filed with the CSSF' in text, {37}),
    ]
    selected = {'final-introduction': anchor(final_intro)}
    selected['base'] = [anchor(one(units, 'bes-base-2010', predicate, label, pages))
                        for label, predicate, pages in base_rows]
    supp_rows = [
        ('bes-supplement-1', 'supplement-1-scope', lambda text: text.startswith('This Supplement (the "Supplement")')),
        ('bes-supplement-1', 'supplement-1-rating', lambda text: 'Fitch Ratings ("Fitch") downgraded BES' in text),
        ('bes-supplement-2', 'supplement-2-scope', lambda text: text.startswith('This Supplement (the "Supplement")')),
        ('bes-supplement-2', 'supplement-2-accounts', lambda text: 'incorporate by reference the Bank\'s unaudited Consolidated' in text),
        ('bes-supplement-3', 'supplement-3-scope', lambda text: text.startswith('This Supplement (the "Supplement")')),
        ('bes-supplement-3', 'supplement-3-ratings', lambda text: 'Portuguese Republic from A- to BBB, Standard & Poor\'s downgraded the ratings of Portuguese' in text),
        ('bes-supplement-4', 'supplement-4-scope', lambda text: text.startswith('This Supplement (the "Supplement")')),
        ('bes-supplement-4', 'supplement-4-amendment', lambda text: 'The purpose of this Supplement is: (a) to amend' in text),
        ('bes-supplement-5', 'supplement-5-scope', lambda text: text.startswith('This Supplement (the "Supplement")')),
        ('bes-supplement-5', 'supplement-5-separate-financing', lambda text: 'purpose of this resolution is to fulfil legal provisions' in text),
        ('bes-supplement-6', 'supplement-6-scope', lambda text: text.startswith('This Supplement (the "Supplement")')),
        ('bes-supplement-6', 'supplement-6-sovereign-rating', lambda text: 'BES announces that Moody\'s Investors Service' in text),
    ]
    for doc, label, predicate in supp_rows:
        selected[label] = anchor(one(units, doc, predicate, label))
    return review, template, graph, selected


def request_for(review, template, graph, selected, *, omit_unit=None, wrong_date=False):
    req = deepcopy(template)
    req['bundle'] = deepcopy(template['bundle'])
    if wrong_date:
        for document in req['bundle']['documents']:
            if document['id'] == 'bes-base-2010':
                document['valid_until'] = '2011-07-15T00:00:00Z'
    graph = source_graph.build(req['bundle'], ROOT)
    entries = review['corrections']
    req['correction_admission'] = {'version': 'reviewed-corrections.v1',
        'graph_sha256': digest(graph), 'review': review['review'], 'entries': entries}
    corrected = service.source_product(req, ROOT)['payload']['graph']
    edges = []
    targets = {t['id']: t for t in review['targets']}
    for row in review['relations']:
        sources = [s['source'] for key in (row['from'], row['to']) for s in targets[key]['segments']]
        edges.append({'id': 'bes-' + row['id'], 'kind': 'governs', 'from': sources[0],
                      'to': sources, 'questions': ['Q1', 'Q2'],
                      'reason': 'Supplied source-row dependency; complete endpoints must survive. No eligibility decision inferred.'})
    chain_targets = {'base': selected['base']}
    for i in range(1, 7):
        chain_targets['supplement-' + str(i)] = [selected[k] for k in selected
            if k.startswith('supplement-' + str(i) + '-')]
    for name, targets_for_doc in chain_targets.items():
        edges.append({'id': 'source-chain-' + name, 'kind': 'governs',
                      'from': selected['final-introduction'], 'to': targets_for_doc,
                      'questions': ['Q1', 'Q2'],
                      'reason': 'Final Terms expressly require this dated source; selected passages are reviewed source-chain evidence, not automatic legal interpretation.'})
    req['layout_admission'] = {'version': 'prospectus-layout.v1', 'graph_sha256': digest(corrected),
        'documents': [], 'governing': edges, 'review': review['review']}
    active = set()
    for target in review['targets']:
        active.update(s['source']['unit'] for s in target['segments'])
    active.add(selected['final-introduction']['unit'])
    for values in chain_targets.values():
        active.update(row['unit'] for row in values)
    operations = []
    for unit in graph['units']:
        if unit['id'] not in active:
            continue
        excluded = unit['id'] == omit_unit
        operations.append({'unit': unit['id'], 'source_text_sha256': unit['text_sha256'],
            'role': 'EXCLUDED' if excluded else 'OPERATIVE',
            'reason': 'Omission control' if excluded else
                      'Image-reviewed final reading or source-chain occurrence; all other source text remains unknown',
            'context': unit['parent'], 'questions': ['Q1', 'Q2']})
    req['assembly'] = {'operations': operations}
    p1 = service.source_product(req, ROOT)
    assembly = service.construction_product(p1, ROOT)['payload']['assembly']
    texts, groups, maps, meanings = [], [], [], []
    length = 0
    for target in review['targets']:
        if target['id'] == omit_unit:
            continue
        spans = []
        for segment in target['segments']:
            if texts:
                texts.append('\n')
                length += 1
            text_value = segment['display']
            start, end = length, length + len(text_value)
            texts.append(text_value)
            length = end
            spans.append({'start': start, 'end': end, 'quote': text_value})
            mapping = {'start': start, 'end': end, 'source': segment['source'], 'use': segment['source']['unit']}
            if segment.get('correction'):
                mapping['correction'] = segment['correction']
            maps.append(mapping)
        groups.append({'id': target['id'], 'label': target['role'], 'spans': spans})
        meanings.append({'groups': ['bes:' + target['id']], 'clause': {
            'id': 'bes:' + target['id'], 'effect': target['effect'], 'actor': 'issuer',
            'affected': 'holder', 'modality': 'statement', 'election': 'none',
            'assets': [], 'polarity': True, 'conditions': [], 'exceptions': []}})
    rendered = ''.join(texts)
    packet = annotation_bridge.export(rendered,
        {'document': req['bundle']['documents'][0]['id'], 'source_sha256': review['source_sha256'],
         'text_sha256': digest(rendered.encode())}, groups, [])
    req['annotation_admission'] = {'version': 'reviewed-annotation-meaning.v1',
        'assembly_sha256': digest(assembly), 'review': review['review'],
        'packets': [{'id': 'bes', 'packet': packet, 'map': maps}],
        'meanings': meanings}
    return req


def expect_rejection(req, marker):
    try:
        service.assess(req, ROOT)
    except (ValueError, KeyError) as exc:
        if marker not in str(exc):
            raise ValueError('Unexpected adverse rejection: ' + str(exc)) from exc
        return {'status': 'PASS', 'message': str(exc)}
    raise ValueError('Adverse source-chain input was accepted: ' + marker)


def main():
    if len(sys.argv) != 1 or sys.flags.optimize:
        raise ValueError('Exact invocation with assertions enabled required')
    if Path(corrections.__file__).resolve() != ROOT / 'src/legalmath/prospectus/successor/corrections.py':
        raise ValueError('Wrong checkout imported')
    if read(REAL_SCAN / 'validation-001/result.json')['status'] != 'PASS':
        raise ValueError('Current real-scan validation must pass before source-chain consumer')
    consumer_root = PACKAGE / 'consumer'
    consumer_root.mkdir(parents=True, exist_ok=True)
    existing = sorted(consumer_root.glob('attempt-*'))
    number = 1 + max((int(p.name.split('-')[1]) for p in existing
                      if p.name.split('-')[1].isdigit()), default=0)
    folder = consumer_root / ('attempt-%03d' % number)
    folder.mkdir(parents=True)
    review, template, graph, selected = review_and_graph()
    if len(template['bundle']['documents']) != 8 or len({d['id'] for d in template['bundle']['documents']}) != 8:
        raise ValueError('Eight distinct source documents required')
    started = {'version': 'bes-source-chain-consumer.v1',
        'command': ['timeout', '900', '.venv/bin/python', str(Path(__file__).relative_to(ROOT))],
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'started_at': datetime.now(timezone.utc).isoformat(), 'plan': str(PLAN.relative_to(ROOT)),
        'environment': {'python': sys.executable, 'CUDA_VISIBLE_DEVICES': '-1'},
        'cpu_gpu': 'CPU; GPU intentionally hidden; no OCR rerun', 'seeds': 'N/A deterministic source controls',
        'documents': [d['id'] for d in template['bundle']['documents']],
        'repair_of': 'consumer/attempt-001: annotation map must retain required use field' if number > 1 else None,
        'evidence_limit_bytes': 100_000_000, 'metadata_reserve_bytes': 1_048_576}
    save(folder / 'started.json', started)
    tick = time.monotonic()
    try:
        req = request_for(review, template, graph, selected)
        save(folder / 'request.json', req)
        plain = service.assess(deepcopy(template), ROOT)
        full = service.assess(req, ROOT)
        save_gzip(folder / 'unassisted-report.json.gz', plain)
        save_gzip(folder / 'assisted-report.json.gz', full)
        if len(full['source_map']['documents']) != 8 or {d['id'] for d in full['source_map']['documents']} != set(started['documents']):
            raise ValueError('Actual service report did not consume all eight sources')
        if full['source_map']['units'] != plain['source_map']['units']:
            raise ValueError('Assistance changed original OCR/native source text or geometry')
        if full['mode'] != 'ASSISTED' or full['independent_legal_acceptance']:
            raise ValueError('Supplied source reading lost its assistance boundary')
        if {k: v['status'] for k, v in full['questions'].items()} != {k: v['status'] for k, v in plain['questions'].items()}:
            raise ValueError('Adding source evidence silently promoted a legal question')
        expected_evidence = [s['source'] for target in review['targets'] for s in target['segments']]
        packet_record = req['annotation_admission']['packets'][0]
        export_map = [{k: v for k, v in row.items() if k != 'use'} for row in packet_record['map']]
        if annotation_bridge.bound_evidence(full['source_map'], {'packet': packet_record['packet'], 'map': export_map}) != expected_evidence:
            raise ValueError('Annotation bridge changed original final-terms evidence')
        source_deps = [d for d in full['dependencies'] if d['id'].startswith('governing:source-chain-')]
        if len(source_deps) != 14 or any(d['status'] != 'RESOLVED' for d in source_deps):
            raise ValueError('All reviewed source-chain endpoints did not reach the service')
        unresolved = [d for d in full['dependencies'] if d['id'].startswith('BES-DEP-')]
        if len(unresolved) != 14 or any(d['status'] != 'UNRESOLVED' for d in unresolved):
            raise ValueError('Unresolved onward source dependencies were promoted')
        checks = []
        omission_controls = [selected['base'][0]] + [selected[k] for k in selected
                            if k.startswith('supplement-') and k.endswith('-scope')]
        if len(omission_controls) != 7:
            raise ValueError('One representative source-chain omission per edge required')
        for row in omission_controls:
            changed = service.assess(request_for(review, template, graph, selected, omit_unit=row['unit']), ROOT)
            missing = [d['id'] for d in changed['dependencies']
                       if d['id'].startswith('governing:source-chain-') and d['status'] == 'UNRESOLVED']
            if not missing:
                raise ValueError('Omitted source-chain occurrence remained resolved: ' + row['unit'])
            checks.append({'kind': 'source-chain-omission', 'unit': row['unit'], 'unresolved': missing})
        adverse = {}
        wrong = deepcopy(req)
        wrong['layout_admission']['governing'][0]['to'][0]['source_sha256'] = '0' * 64
        adverse['wrong-edition'] = expect_rejection(wrong, 'Source edition mismatch')
        stale = deepcopy(req)
        stale['bundle']['documents'] = [dict(d) for d in stale['bundle']['documents']]
        for document in stale['bundle']['documents']:
            if document['id'] == 'bes-base-2010':
                document['valid_until'] = '2011-07-15T00:00:00Z'
        adverse['wrong-date'] = expect_rejection(stale, 'Corrected-text source graph changed')
        save(folder / 'checks.json', {'source_chain_omissions': checks, 'adverse_controls': adverse})
        result = {'status': 'PASS', 'documents_consumed': 8, 'source_chain_edges': 7,
            'source_chain_dependencies': 14, 'unresolved_onward_dependencies': 14,
            'source_chain_omissions': len(checks), 'omission_scope': 'one representative occurrence per source-chain edge; full report checks all 14 Q1/Q2 dependencies',
            'adverse_controls': len(adverse),
            'question_statuses': {k: v['status'] for k, v in full['questions'].items()},
            'raw_evidence_equal': True, 'automatic_relations_promoted': False,
            'independent_acceptance': 'NOT_ESTABLISHED', 'legal_completion': 'NOT_ESTABLISHED',
            'scope': 'Eight-document source-chain consumption; selected passages and final-terms readings are supplied development evidence',
            'wall_seconds': time.monotonic() - tick}
    except Exception as exc:
        result = {'status': 'FAIL', 'error': type(exc).__name__ + ': ' + str(exc),
                  'wall_seconds': time.monotonic() - tick}
        save(folder / 'result.json', result)
        raise
    save(folder / 'result.json', result)
    files = {str(p.relative_to(folder)): sha(p) for p in folder.rglob('*') if p.is_file() and p.name != 'manifest.json'}
    payload = sum((folder / p).stat().st_size for p in files)
    if payload + 1_048_576 > 100_000_000:
        raise ValueError('Source-chain evidence cap exceeded')
    save(folder / 'manifest.json', {'files': files, 'payload_bytes': payload})
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
