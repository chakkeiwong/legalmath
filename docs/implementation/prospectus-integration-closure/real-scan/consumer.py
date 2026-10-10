"""Consume the reviewed BES cell readings through the actual prospectus service."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'docs/implementation/prospectus-integration-closure'
PACKAGE = Path(__file__).resolve().parent
PLAN = ROOT / 'docs/plans/prospectus-real-scan-2026-10-11.md'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from legalmath.prospectus.successor import annotation_bridge, corrections, service, source_graph  # noqa: E402
from legalmath.prospectus.successor.contracts import digest  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def verify(folder):
    manifest = read(folder / 'manifest.json')['files']
    actual = {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p.name != 'manifest.json'}
    if actual != set(manifest) or any(sha(folder / p) != value for p, value in manifest.items()):
        raise ValueError('Retained evidence changed: ' + str(folder))


def load_review():
    folder = PACKAGE / 'authoring/attempt-001'
    verify(folder)
    review = read(folder / 'review.json')
    if (read(folder / 'result.json')['status'] != 'PASS' or
            review['oracle_sha256'] != sha(PACKAGE / 'oracle.json') or
            review['raw_worker_sha256'] != sha(PACKAGE / 'baseline/attempt-001/raw-worker.json')):
        raise ValueError('Reviewed source/oracle identity changed')
    return review


def raw_request():
    req = read(PACKAGE / 'baseline/attempt-001/request.json')
    document = req['bundle']['documents'][0]
    document.pop('scan_profile')
    raw = PACKAGE / 'baseline/attempt-001/raw-worker.json'
    document['ocr'] = {'path': str(raw.relative_to(ROOT)), 'sha256': sha(raw)}
    return req


def request(review, *, omit_meaning=None, exclude_target=None):
    req = raw_request()
    graph = source_graph.build(req['bundle'], ROOT)
    req['correction_admission'] = {'version': 'reviewed-corrections.v1', 'graph_sha256': digest(graph),
                                  'review': review['review'], 'entries': review['corrections']}
    with_corrections = service.source_product(req, ROOT)['payload']['graph']
    targets = {t['id']: t for t in review['targets']}
    edges = []
    for row in review['relations']:
        sources = [s['source'] for key in (row['from'], row['to']) for s in targets[key]['segments']]
        edges.append({'id': 'bes-' + row['id'], 'kind': 'governs', 'from': sources[0],
                      'to': sources, 'questions': ['Q1', 'Q2'],
                      'reason': 'Conservative supplied source-completeness dependency for the ' + row['kind'] +
                                '; both complete endpoints must survive. No eligibility decision inferred.'})
    req['layout_admission'] = {'version': 'prospectus-layout.v1', 'graph_sha256': digest(with_corrections),
                              'documents': [], 'governing': edges, 'review': review['review']}
    active = {s['source']['unit'] for t in review['targets'] for s in t['segments']}
    excluded = {s['source']['unit'] for s in targets[exclude_target]['segments']} if exclude_target else set()
    req['assembly'] = {'operations': [{'unit': u['id'], 'source_text_sha256': u['text_sha256'],
        'role': 'EXCLUDED' if u['id'] in excluded else 'OPERATIVE',
        'reason': 'Adverse omission control' if u['id'] in excluded else
                  'Raw occurrence supports a designated source reading; unreviewed characters retain unknown meaning',
        'context': u['id'], 'questions': ['Q1', 'Q2']} for u in graph['units'] if u['id'] in active]}
    p1 = service.source_product(req, ROOT)
    assembly = service.construction_product(p1, ROOT)['payload']['assembly']
    texts, groups, maps, meanings = [], [], [], []
    length = 0
    for target in review['targets']:
        if target['id'] in {omit_meaning, exclude_target}:
            continue
        spans = []
        for segment in target['segments']:
            if texts:
                texts.append('\n')
                length += 1
            text = segment['display']
            start, end = length, length + len(text)
            texts.append(text)
            length = end
            spans.append({'start': start, 'end': end, 'quote': text})
            mapping = {'start': start, 'end': end, 'source': segment['source'], 'use': segment['source']['unit']}
            if segment.get('correction'):
                mapping['correction'] = segment['correction']
            maps.append(mapping)
        groups.append({'id': target['id'], 'label': target['role'], 'spans': spans})
        meanings.append({'groups': ['bes:' + target['id']], 'clause': {
            'id': 'bes:' + target['id'], 'effect': target['effect'], 'actor': 'issuer', 'affected': 'holder',
            'modality': 'statement', 'election': 'none', 'assets': [], 'polarity': True,
            'conditions': [], 'exceptions': []}})
    text = ''.join(texts)
    packet = annotation_bridge.export(text, {'document': req['bundle']['documents'][0]['id'],
         'source_sha256': review['source_sha256'], 'text_sha256': digest(text.encode())}, groups, [])
    req['annotation_admission'] = {'version': 'reviewed-annotation-meaning.v1',
         'assembly_sha256': digest(assembly), 'review': review['review'],
         'packets': [{'id': 'bes', 'packet': packet, 'map': maps}], 'meanings': meanings}
    return req


def require_error(req, expected):
    try:
        service.assess(req, ROOT)
    except ValueError as exc:
        if expected not in str(exc):
            raise ValueError('Unexpected rejection: ' + str(exc)) from exc
        return {'type': type(exc).__name__, 'message': str(exc)}
    raise ValueError('Adverse input was accepted: ' + expected)


def main():
    if len(sys.argv) != 1 or sys.flags.optimize:
        raise ValueError('Exact invocation with assertions enabled required')
    if Path(corrections.__file__).resolve() != ROOT / 'src/legalmath/prospectus/successor/corrections.py':
        raise ValueError('Wrong checkout imported')
    candidate = read(PACKAGE / 'candidate/baseline.json')
    if sha(Path(corrections.__file__)) != candidate['candidate_sha256']:
        raise ValueError('Integrate and test the reviewed image guard before this consumer')
    completed = BASE / 'worker-recovery/validation-001'
    verify(completed)
    if read(completed / 'result.json')['status'] != 'PASS':
        raise ValueError('R6 predecessor must have completed before integration')
    verify(PACKAGE / 'baseline/attempt-001')
    verify(PACKAGE / 'analysis/attempt-001')
    review = load_review()
    folder = PACKAGE / 'consumer/attempt-001'
    if folder.exists():
        raise ValueError('Inspect prior consumer before any changed-method retry')
    folder.mkdir(parents=True)
    paths = [*sorted((ROOT / 'src/legalmath').rglob('*.py')), Path(__file__), PLAN,
             PACKAGE / 'authoring/attempt-001/manifest.json', PACKAGE / 'baseline/attempt-001/manifest.json']
    method = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    save(folder / 'started.json', {'command': ['timeout', '300', '.venv/bin/python', str(Path(__file__).relative_to(ROOT))],
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'method': method, 'started_at': datetime.now(timezone.utc).isoformat(),
        'environment': {'python': sys.executable, 'CUDA_VISIBLE_DEVICES': '-1'},
        'cpu_gpu': 'CPU; GPU intentionally hidden; retained current-worker output; no OCR rerun',
        'random_seeds': 'N/A deterministic supplied-source controls', 'data_version': review['source_sha256'],
        'timeout_seconds': 300, 'evidence_limit_bytes': 100_000_000, 'metadata_reserve_bytes': 1_048_576,
        'plan_file': str(PLAN.relative_to(ROOT)), 'result_file': str((folder / 'result.json').relative_to(ROOT))})
    tick = time.monotonic()
    try:
        req = request(review)
        save(folder / 'request.json', req)
        plain = service.assess(raw_request(), ROOT)
        full = service.assess(req, ROOT)
        save(folder / 'unassisted-report.json', plain)
        save(folder / 'assisted-report.json', full)
        if full['source_map']['units'] != plain['source_map']['units']:
            raise ValueError('Assistance changed original OCR text or geometry')
        if full['mode'] != 'ASSISTED' or full['independent_legal_acceptance']:
            raise ValueError('Supplied source reading lost its assistance boundary')
        expected_status = {k: v['status'] for k, v in plain['questions'].items()}
        if {k: v['status'] for k, v in full['questions'].items()} != expected_status:
            raise ValueError('Narrow source reading unexpectedly promoted a legal question')
        all_nodes = {n['id']: n for n in full['clause_graph']['nodes']}
        checks = []
        packet_record = req['annotation_admission']['packets'][0]
        export = {'packet': packet_record['packet'], 'map': [
            {k: v for k, v in row.items() if k != 'use'} for row in packet_record['map']]}
        raw_evidence = annotation_bridge.bound_evidence(full['source_map'], export)
        expected_evidence = [s['source'] for t in review['targets'] for s in t['segments']]
        if raw_evidence != expected_evidence:
            raise ValueError('Annotation bridge lost or changed original cell occurrences')
        for target in review['targets']:
            node = all_nodes['bes:' + target['id']]
            if node['quote'] != ' '.join(s['source']['quote'] for s in target['segments']):
                raise ValueError('Displayed correction replaced raw semantic quotation')
            omitted_req = request(review, omit_meaning=target['id'])
            omitted = service.assess(omitted_req, ROOT)
            omitted_nodes = {n['id']: n for n in omitted['clause_graph']['nodes']}
            expected_nodes = {key: value for key, value in all_nodes.items() if key != 'bes:' + target['id']}
            if omitted_nodes != expected_nodes:
                raise ValueError('One-meaning omission changed another source reading')
            lost_units = {s['source']['unit'] for s in target['segments']}
            if not lost_units.issubset(set(omitted['clause_graph']['uncovered_units'])):
                raise ValueError('Omitted source meaning did not restore unknown coverage')
            save(folder / ('omitted-' + target['id'] + '.json'), omitted)
            checks.append({'kind': 'meaning-omission', 'target': target['id'], 'uncovered_units': sorted(lost_units)})
        expected_deps = {'governing:bes-' + edge['id'] + ':' + q for edge in review['relations'] for q in ('Q1', 'Q2')}
        deps = {d['id']: d for d in full['dependencies'] if d['id'] in expected_deps}
        if set(deps) != expected_deps or any(d['status'] != 'RESOLVED' for d in deps.values()):
            raise ValueError('Complete supplied relationships did not reach the actual service')
        for edge in review['relations']:
            # Qualifiers must themselves survive; ordinary rows lose the value.
            target = edge['from'] if edge['kind'] == 'qualifies' else edge['to']
            changed = service.assess(request(review, exclude_target=target), ROOT)
            ids = {'governing:bes-' + edge['id'] + ':' + q for q in ('Q1', 'Q2')}
            missing = {d['id'] for d in changed['dependencies'] if d['status'] == 'UNRESOLVED'}
            if not ids.issubset(missing) or any(
                    'governing:bes-' + edge['id'] + ':' + q not in changed['questions'][q]['unresolved'] for q in ('Q1', 'Q2')):
                raise ValueError('Required row/qualification omission escaped the service')
            save(folder / ('excluded-' + edge['id'] + '.json'), changed)
            checks.append({'kind': 'required-source-omission', 'edge': edge['id'], 'unresolved': sorted(ids)})
        adverse = {}
        for case in ('wrong-image', 'missing-image', 'wrong-raw-occurrence', 'stale-graph'):
            changed = deepcopy(req)
            row = changed['correction_admission']['entries'][0]
            if case == 'wrong-image':
                row['image_sha256'] = '0' * 64
                error = 'retained source-page image identity'
            elif case == 'missing-image':
                row.pop('image_sha256')
                error = 'retained source-page image identity'
            elif case == 'wrong-raw-occurrence':
                source = row['source']
                alternate = next(u for u in plain['source_map']['units']
                    if u['id'] != source['unit'] and u['document'] == source['document'] and
                    len(u['raw']) >= source['end'] and
                    u['raw'][source['start']:source['end']] != source['quote'])
                source['unit'] = alternate['id']
                error = 'Source quote changed'
            else:
                changed['correction_admission']['graph_sha256'] = '0' * 64
                error = 'Corrected-text source graph changed'
            adverse[case] = require_error(changed, error)
        changed = deepcopy(req)
        changed['correction_admission']['entries'][0]['operations'][0]['kind'] = 'uncertain'
        # Bind each unchanged parent legitimately so the semantic span check is
        # what rejects uncertainty, rather than an earlier stale hash.
        changed.pop('layout_admission')
        graph = service.source_product(changed, ROOT)['payload']['graph']
        changed['layout_admission'] = {**deepcopy(req['layout_admission']), 'graph_sha256': digest(graph)}
        p1 = service.source_product(changed, ROOT)
        changed['annotation_admission']['assembly_sha256'] = digest(service.construction_product(p1, ROOT)['payload']['assembly'])
        adverse['uncertain-meaning'] = require_error(changed, 'uncertain text')
        changed = deepcopy(req)
        packet = changed['annotation_admission']['packets'][0]
        decoded = annotation_bridge.reimport(packet['packet'], packet['packet']['text'], packet['packet']['source'])
        group = next(g for g in decoded['groups'] if g['id'] == 'responsibility')
        group['spans'][0]['start'] += 1
        group['spans'][0]['quote'] = group['spans'][0]['quote'][1:]
        packet['packet'] = annotation_bridge.export(packet['packet']['text'], packet['packet']['source'],
                                                    decoded['groups'], decoded['relations'])
        adverse['partial-replacement'] = require_error(changed, 'Partial replacement has ambiguous raw correspondence')
        changed = deepcopy(req)
        targets = {t['id']: t for t in review['targets']}
        mapping = next(m for m in changed['annotation_admission']['packets'][0]['map']
                       if m['source'] == targets['isin']['segments'][0]['source'])
        mapping['source'] = deepcopy(targets['common-code']['segments'][0]['source'])
        mapping['use'] = mapping['source']['unit']
        adverse['wrong-table-value'] = require_error(changed, 'Correction does not bind this annotation source')
        save(folder / 'comparisons.json', {'omission_controls': checks, 'adverse_controls': adverse,
             'raw_evidence': raw_evidence, 'required_dependencies': deps,
             'question_statuses': expected_status, 'raw_graph_units_equal': True})
        if method != {p: sha(ROOT / p) for p in method}:
            raise ValueError('Consumer method changed')
        payload = sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())
        if payload + 1_048_576 > 100_000_000:
            raise ValueError('Consumer evidence bound exceeded')
        result = {'status': 'PASS', 'reviewed_targets': 23, 'corrections': 8, 'required_relationships': 8,
                  'meaning_omissions': 23, 'relationship_omissions': 8, 'adverse_controls': len(adverse),
                  'question_statuses': expected_status, 'raw_evidence_equal': True,
                  'automatic_relations_promoted': False, 'independent_acceptance': 'NOT_ESTABLISHED',
                  'scope': 'Actual assisted source/correction/annotation consumer; not independent law or package accuracy',
                  'evidence_payload_bytes': payload, 'wall_seconds': time.monotonic() - tick}
    except Exception as exc:
        result = {'status': 'FAIL', 'error': type(exc).__name__ + ': ' + str(exc),
                  'wall_seconds': time.monotonic() - tick}
    save(folder / 'result.json', result)
    save(folder / 'manifest.json', {'files': {p.name: sha(p) for p in folder.iterdir()
                                         if p.is_file() and p.name != 'manifest.json'}})
    print(json.dumps(result), flush=True)
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
