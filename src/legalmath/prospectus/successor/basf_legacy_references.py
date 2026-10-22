"""Enforce the twenty retained original BASF source-reference mappings."""
from functools import lru_cache
import json
from pathlib import Path

from .anchors import bind
from .contracts import digest
from .occurrences import segments


@lru_cache(maxsize=1)
def specification():
    return json.loads(Path(__file__).with_name('basf_legacy_references_spec.json').read_text())


def check(graph, assembly, packet):
    spec = specification()
    rows = [] if packet is None else packet['references']
    ids = {r['id'] for r in spec['references']}
    sources = [r['source'] for r in spec['references']]
    relevant = [r for r in rows if r['id'] in ids or any(
        r['source']['unit'] == s['unit'] and r['source']['start'] < s['end']
        and s['start'] < r['source']['end'] for s in sources)]
    editions = {(u['document'], u['source_sha256']) for u in graph['units']}
    if not all((s['id'], s['sha256']) in editions for s in spec['sources']):
        if relevant:
            raise ValueError('BASF legacy reference source edition differs')
        return None
    raw = {u['id']: u for u in graph['units']}
    units = {u['unit']: u for u in assembly['units']}
    if len(raw) != len(graph['units']) or len(units) != len(assembly['units']):
        raise ValueError('Duplicate BASF legacy reference occurrence')
    for context in spec['split_contexts']:
        bind({'units': [raw[context['unit']]] if context['unit'] in raw else []}, context)
    expected = []
    for row in spec['references']:
        source = row['source']
        bind({'units': [raw[source['unit']]] if source['unit'] in raw else []}, source)
        selected = units.get(row['from_use'])
        if selected is None:
            raise ValueError('BASF legacy reference source selection unavailable')
        if selected['role'] == 'EXCLUDED':
            continue
        if selected['role'] not in ('OPERATIVE', 'UNKNOWN'):
            raise ValueError('BASF legacy reference source has an unreviewed role')
        expected.append(row)
    actual = {r['id']: r for r in relevant}
    if len(actual) != len(relevant) or not set(actual) <= {r['id'] for r in expected}:
        raise ValueError('Duplicate, renamed or inapplicable BASF legacy reference')
    checks = {r['reference']['id']: r for r in spec['source_checks']}
    for row in expected:
        if row['id'] not in actual:
            continue
        got = actual[row['id']]
        if digest({k: v for k, v in got.items() if k != 'reason'}) != digest(
                {k: v for k, v in row.items() if k != 'reason'}):
            raise ValueError('BASF legacy reference requires its original complete reviewed target')
        if not isinstance(got.get('reason'), str) or not got['reason'].strip():
            raise ValueError('BASF legacy reference requires a review reason')
        if units[row['from_use']]['role'] != 'OPERATIVE':
            raise ValueError('BASF legacy reference source is not operative')
        for wanted in checks[row['id']]['target_selections']:
            selected = units.get(wanted['use'])
            if (selected is None or selected['role'] != wanted['role']
                    or selected['questions'] != wanted['questions']
                    or selected['text'] != wanted['text']
                    or digest(segments(graph, selected, _raw=raw)) != digest(wanted['segments'])):
                raise ValueError('BASF legacy reference target selection changed')
    return {'status': 'REVIEWED' if len(actual) == len(expected) else 'UNREVIEWED',
        'references': expected, 'missing': [r['id'] for r in expected if r['id'] not in actual],
        'source_documents': spec['sources'], 'original_inventory_sha256': spec['original_inventory_sha256'],
        'specification_sha256': digest(spec), 'automatic_discovery': False,
        'complete_reference_graph': False, 'actual_compliance': 'UNKNOWN'}


def missing_dependencies(report):
    if report is None:
        return []
    return [{'id': 'legacy-reference:' + identity, 'questions': ['Q1', 'Q2'],
        'status': 'UNRESOLVED', 'reason': 'An original reviewed reference lacks its complete source-bound target'}
        for identity in report['missing']]


def verify_consumed(graph, assembly, request, semantic):
    report = check(graph, assembly, request.get('reference_admission'))
    if report is None:
        return None
    expected = missing_dependencies(report)
    actual = [d for d in semantic['dependencies'] if d['id'].startswith('legacy-reference:')]
    if digest(sorted(expected, key=lambda d: d['id'])) != digest(sorted(actual, key=lambda d: d['id'])):
        raise ValueError('Consumed BASF legacy missing-reference dependencies differ')
    required = {d['id'] for d in expected}
    for q in ('Q1', 'Q2'):
        for answer in [semantic['questions'][q], *semantic['questions'][q].get('subquestions', {}).values()]:
            if {v for v in answer['unresolved'] if v.startswith('legacy-reference:')} != required:
                raise ValueError('Consumed BASF question hides or invents a missing legacy reference')
    return report
