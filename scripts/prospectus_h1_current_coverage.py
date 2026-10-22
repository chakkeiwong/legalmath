"""Finite delivered-reference inventory; reference presence is not interpretation."""
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/implementation/prospectus-execution-authority/attempts/source-bes-dep-05'
PLAN = 'docs/plans/prospectus-h1-current-source-audit-2026-10-22.md'
DOCUMENT = 'bes-interim-h1-2010'
CONTEXT = {'source_groups', 'source_context', 'source_scope', 'retained_context',
    'retained_010_reading', 'retained_016_reading', 'source_units', 'target_sources'}


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def ref(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def pointer(path):
    return '/' + '/'.join(str(key).replace('~', '~0').replace('/', '~1') for key in path)


def references(value, units, path=(), context=False, groups=None):
    if isinstance(value, dict):
        local_groups = value.get('source_groups', groups)
        uid = None
        schema = None
        if isinstance(value.get('quote'), str):
            if isinstance(value.get('source_unit'), str):
                uid, schema = value['source_unit'], 'statement-cell'
            elif isinstance(value.get('id'), str):
                uid, schema = value['id'], 'id-quote'
            elif {'unit', 'document', 'source_sha256', 'start', 'end'} <= set(value):
                uid, schema = value['unit'], 'span-anchor'
        if uid is not None:
            require(uid in units, 'Unknown source occurrence at ' + pointer(path))
            source = units[uid]
            start, end = (value['start'], value['end']) if schema == 'span-anchor' else (0, len(source['raw']))
            require(type(start) is int and type(end) is int and 0 <= start < end <= len(source['raw']),
                    'Invalid source interval at ' + pointer(path))
            require(source['raw'][start:end] == value['quote'], 'Changed original quote at ' + pointer(path))
            if schema == 'span-anchor':
                require(value['document'] == source['document'] and value['source_sha256'] == source['source_sha256'],
                        'Changed source edition at ' + pointer(path))
                if 'bbox' in value:
                    require(value['bbox'] == source.get('bbox'), 'Changed source geometry at ' + pointer(path))
            yield {'id': uid, 'start': start, 'end': end, 'path': pointer(path),
                   'schema': schema, 'context': context}
        for key, child in value.items():
            if key in ('anchor', 'anchors') and (isinstance(child, str)
                    or isinstance(child, list) and all(isinstance(item, str) for item in child)):
                names = [child] if isinstance(child, str) else child
                for name in names:
                    require(isinstance(local_groups, dict) and name in local_groups,
                            'Unresolved named source group at ' + pointer((*path, key, name)))
                    for row in references(local_groups[name], units, (*path, key, name), context, local_groups):
                        yield {**row, 'schema': 'named-review-anchor', 'group': name}
            elif key not in ('id', 'quote', 'source_unit'):
                yield from references(child, units, (*path, key), context or key in CONTEXT, local_groups)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from references(child, units, (*path, index), context, groups)


def schema_probes():
    unit = {'id': 'source', 'raw': 'abc def', 'document': 'd', 'source_sha256': 'a' * 64, 'bbox': [1, 2, 3, 4]}
    anchor = {'unit': 'source', 'document': 'd', 'source_sha256': 'a' * 64, 'start': 4, 'end': 7, 'quote': 'def'}
    value = {'source_groups': {'review': [{'id': 'source', 'quote': 'abc def'}]},
        'terms': {'assurance': {'anchor': 'review'}},
        'table': {'source_unit': 'source', 'quote': 'abc def'},
        'cash': anchor, 'target_sources': [anchor]}
    rows = list(references(value, {'source': unit}))
    require(Counter((row['schema'], row['context']) for row in rows) == Counter({
        ('id-quote', True): 1, ('named-review-anchor', False): 1,
        ('statement-cell', False): 1, ('span-anchor', False): 1, ('span-anchor', True): 1}),
        'Context/source schema discrimination failed')
    refused = []
    for name, bad in [('quote', {**anchor, 'quote': 'abc'}),
                      ('edition', {**anchor, 'source_sha256': 'b' * 64}),
                      ('interval', {**anchor, 'start': True}),
                      ('geometry', {**anchor, 'bbox': [0, 0, 0, 0]}),
                      ('named-group', {'anchor': 'unknown'})]:
        try:
            list(references(bad, {'source': unit}))
        except ValueError:
            refused.append(name)
        else:
            raise ValueError('Scanner accepted corrupt ' + name)
    return {'status': 'PASS', 'refused': refused, 'context_does_not_become_substantive': True}


def inspect(attempt):
    require(attempt in (62, 63), 'Only reviewed provisional 062 or final 063 snapshots')
    tick = time.monotonic()
    folder = BASE / f'attempt-{attempt:03d}'
    target = ROOT / f'.localresources/prospectus-preparation/h1-current-source-audit/snapshot-{attempt:03d}.json'
    require(not target.exists(), 'Preserve previous diagnostic; no unchanged retry')
    outcome = {'status': 'FAIL', 'snapshot_attempt': attempt, 'plan': PLAN}
    try:
        probes = schema_probes()
        graph = read(BASE / 'attempt-007/products.json.gz')['P1']['payload']['graph']
        units = {unit['id']: unit for unit in graph['units']}
        require(len(units) == len(graph['units']), 'Duplicate original identity')
        require(read(folder / 'stages/ordinary/result.json')['status'] == 'PASS', 'Actual ordinary delivery required')
        answer = read(folder / 'ordinary-answer.json.gz')
        receipt = read(folder / 'ordinary.json')
        require(ref(folder / 'ordinary-answer.json.gz')['sha256'] == receipt['answer_file']['sha256'],
                'Ordinary answer changed')
        inner = answer['answer'] if attempt == 63 else answer
        reading = inner['source_statement_cells']
        sections = {'source_statement_cells': reading}
        if attempt == 63:
            require(read(folder / 'result.json')['status'] == 'PASS', 'Recorded 063 required for final audit')
            sections.update({name: answer[name] for name in ('cash_flow_review', 'risk_table_review',
                'h1_scope_review', 'h1_individual_unit_review')})
        refs = [row for row in references(sections, units) if units[row['id']]['document'] == DOCUMENT]
        direct, context = defaultdict(list), defaultdict(list)
        for row in refs:
            (context if row['context'] else direct)[row['id']].append(row)
        target_units = sorted([u for u in units.values() if u['document'] == DOCUMENT and 51 <= u['page'] <= 173],
                              key=lambda u: (u['page'], u['order'], u['id']))
        pages = []
        for page in range(51, 174):
            local = [u for u in target_units if u['page'] == page]
            pages.append({'page': page, 'original_occurrences': len(local),
                'direct_reference_occurrences': sum(u['id'] in direct for u in local),
                'context_reference_occurrences': sum(u['id'] in context for u in local),
                'no_direct_reference': [{'id': u['id'], 'quote': u['raw']} for u in local if u['id'] not in direct]})
        residual = read(ROOT / '.localresources/prospectus-preparation/h1-coverage-reconciliation/delivery-check-060.json')['residual_note_references']
        residual_rows = [{**row, 'current_direct': direct[row['id']], 'current_context': context[row['id']]} for row in residual]
        outcome.update(status='REFERENCE_INVENTORY_COMPLETE_WITH_MEANING_UNCHECKED',
            provisional=attempt == 62, original_graph=ref(BASE / 'attempt-007/products.json.gz'),
            actual_answer=ref(folder / 'ordinary-answer.json.gz'), schema_probes=probes,
            schema_counts=dict(Counter(row['schema'] for row in refs)), pages=pages,
            direct_references=dict(direct), residual_context_items=residual_rows,
            interpretation_limits=['Reference presence does not prove meaning, completeness or source authority.',
                'Retained context, historical inputs and whole target pool do not establish substantive reading.',
                'A source occurrence can contain multiple characters or clauses; occurrence counts are explanatory.',
                'No original-task acceptance, source authentication or legal incorporation selection.'])
    except Exception as exc:
        outcome['error'] = {'type': type(exc).__name__, 'reason': str(exc)}
    outcome['seconds'] = time.monotonic() - tick
    outcome['method'] = ref(Path(__file__))
    raw = (json.dumps(outcome, ensure_ascii=False, indent=2) + '\n').encode()
    require(len(raw) < 16 * 1024**2, 'Audit output exceeds 16 MiB')
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'status': outcome['status'], 'seconds': outcome['seconds'],
        'bytes': len(raw), 'error': outcome.get('error'), 'output': str(target.relative_to(ROOT))}))


if __name__ == '__main__':
    inspect(int(sys.argv[1]))
