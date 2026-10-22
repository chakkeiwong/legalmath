"""Exact local (b) notice references in the reviewed BASF2032 construction."""
from functools import lru_cache
import json
from pathlib import Path

from .anchors import bind
from .contracts import digest
from .occurrences import segments


@lru_cache(maxsize=1)
def specification():
    return json.loads(Path(__file__).with_name('basf_call_references_spec.json').read_text())


def check(graph, assembly, packet):
    spec = specification()
    rows = [] if packet is None else packet['references']
    ids = {r['id'] for r in spec['references']}
    sources = {r['source']['unit'] for r in spec['references']}
    relevant = [r for r in rows if r['id'] in ids or r['source']['unit'] in sources]
    editions = {(u['document'], u['source_sha256']) for u in graph['units']}
    if not all((s['id'], s['sha256']) in editions for s in spec['sources']):
        if relevant:
            raise ValueError('BASF relative notice reference source edition differs')
        return None
    raw = {u['id']: u for u in graph['units']}
    units = {u['unit']: u for u in assembly['units']}
    if len(raw) != len(graph['units']) or len(units) != len(assembly['units']):
        raise ValueError('Duplicate BASF relative notice occurrence')
    for source in spec['contexts']:
        bind({'units': [raw[source['unit']]] if source['unit'] in raw else []}, source)
    expected = []
    for row in spec['references']:
        source = row['source']
        bind({'units': [raw[source['unit']]] if source['unit'] in raw else []}, source)
        selected = units.get(row['from_use'])
        if selected is None:
            raise ValueError('BASF relative notice source selection unavailable')
        if selected['role'] == 'EXCLUDED':
            continue
        if selected['role'] not in ('OPERATIVE', 'UNKNOWN'):
            raise ValueError('BASF relative notice source has an unreviewed role')
        expected.append(row)
    actual = {r['id']: r for r in relevant}
    if len(actual) != len(relevant) or not set(actual) <= {r['id'] for r in expected}:
        raise ValueError('Duplicate, renamed or inapplicable BASF relative notice reference')
    for row in expected:
        if row['id'] not in actual:
            continue
        got = actual[row['id']]
        if digest({k: v for k, v in got.items() if k != 'reason'}) != digest(
                {k: v for k, v in row.items() if k != 'reason'}):
            raise ValueError('BASF relative notice requires its exact complete local paragraph')
        if not isinstance(got.get('reason'), str) or not got['reason'].strip():
            raise ValueError('BASF relative notice requires a source-review reason')
        if units[row['from_use']]['role'] != 'OPERATIVE':
            raise ValueError('BASF relative notice source is not operative')
        for target in row['targets']:
            source = target['source']
            bind({'units': [raw[source['unit']]] if source['unit'] in raw else []}, source)
            selected = units.get(target['use'])
            if (selected is None or selected['role'] != 'OPERATIVE'
                    or selected['questions'] != row['questions']
                    or selected['text'] != source['quote']
                    or segments(graph, selected, _raw=raw) != [
                        {'source': source, 'start': 0, 'end': len(source['quote'])}]):
                raise ValueError('BASF relative notice target selection changed')
    return {'status': 'REVIEWED' if len(actual) == len(expected) else 'UNREVIEWED',
            'references': expected, 'missing': [r['id'] for r in expected if r['id'] not in actual],
            'source_documents': spec['sources'], 'source_images': spec['images'],
            'specification_sha256': digest(spec), 'automatic_discovery': False,
            'actual_notice_compliance': 'UNKNOWN', 'complete_reference_graph': False}


def missing_dependencies(report):
    if report is None:
        return []
    return [{'id': 'relative-notice:' + identity, 'questions': ['Q1', 'Q2'],
             'status': 'UNRESOLVED', 'reason': 'The complete local notice paragraph has no reviewed source link'}
            for identity in report['missing']]


def _owned(identity):
    return identity in {prefix + row['id'] for row in specification()['references']
                       for prefix in ('reviewed-reference:', 'relative-notice:')}


def verify_consumed(graph, assembly, request, semantic):
    return _verify_consumed(graph, assembly, request, semantic)


def _verify_consumed(graph, assembly, request, semantic, *, _resolved=None):
    """Internal full-consumer reuse; public calls always admit fresh inputs."""
    packet = request.get('reference_admission')
    report = check(graph, assembly, packet)
    if report is None:
        return None
    expected = missing_dependencies(report)
    ids = {r['id'] for r in report['references']}
    present = [] if packet is None else [r for r in packet['references'] if r['id'] in ids]
    if present:
        if _resolved is None:
            from .reviewed_references import admit
            from .occurrences import _DependencyLookup
            resolved, _ = admit(graph, assembly, {**packet, 'references': present},
                                _lookup=_DependencyLookup(graph, assembly))
        else:
            owned = {'reviewed-reference:' + row['id'] for row in present}
            resolved = [row for row in _resolved if row['id'] in owned]
        expected += resolved
    actual = [d for d in semantic['dependencies'] if _owned(d['id'])]
    if digest(sorted(expected, key=lambda d: d['id'])) != digest(sorted(actual, key=lambda d: d['id'])):
        raise ValueError('Consumed BASF relative notice dependencies differ from source review')
    required = {d['id'] for d in expected if d['status'] == 'UNRESOLVED'}
    for q in ('Q1', 'Q2'):
        for answer in [semantic['questions'][q], *semantic['questions'][q].get('subquestions', {}).values()]:
            if {v for v in answer['unresolved'] if _owned(v)} != required:
                raise ValueError('Consumed BASF question hides or invents a missing relative notice link')
    return report
