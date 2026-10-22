"""Source-bound maturity, coupon, day-count and tax-call amount references."""
from functools import lru_cache
import json
from pathlib import Path

from .anchors import bind
from .contracts import digest
from .occurrences import segments


@lru_cache(maxsize=1)
def specification():
    return json.loads(Path(__file__).with_name('basf_financial_references_spec.json').read_text())


def check(graph, assembly, packet):
    from .structural_roles import legacy_view, reference_report
    original=legacy_view(graph,assembly)
    return reference_report(_check(graph,original,packet),assembly)


def _check(graph, assembly, packet):
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
            raise ValueError('BASF financial reference source edition differs')
        return None
    raw = {u['id']: u for u in graph['units']}
    units = {u['unit']: u for u in assembly['units']}
    if len(raw) != len(graph['units']) or len(units) != len(assembly['units']):
        raise ValueError('Duplicate BASF financial occurrence')

    def bound(source):
        bind({'units': [raw[source['unit']]] if source['unit'] in raw else []}, source)

    for source in spec['contexts']:
        bound(source)
    expected = []
    for row in spec['references']:
        bound(row['source'])
        selected = units.get(row['from_use'])
        if selected is None or selected['role'] not in ('OPERATIVE', 'UNKNOWN', 'EXCLUDED'):
            raise ValueError('BASF financial source selection unavailable or unreviewed')
        if selected['role'] != 'EXCLUDED':
            expected.append(row)
    actual = {r['id']: r for r in relevant}
    if len(actual) != len(relevant) or not set(actual) <= {r['id'] for r in expected}:
        raise ValueError('Duplicate, renamed or inapplicable BASF financial reference')
    pair = set(spec['paired_citation'])
    if set(actual) & pair and not pair <= set(actual):
        raise ValueError('BASF financial maturity citation requires both adjacent parts')
    for row in expected:
        if row['id'] not in actual:
            continue
        got = actual[row['id']]
        if digest({k: v for k, v in got.items() if k != 'reason'}) != digest(
                {k: v for k, v in row.items() if k != 'reason'}):
            raise ValueError('BASF financial reference requires its exact complete selected target')
        if not isinstance(got.get('reason'), str) or not got['reason'].strip():
            raise ValueError('BASF financial reference requires a source-review reason')
        if units[row['from_use']]['role'] != 'OPERATIVE':
            raise ValueError('BASF financial reference source is not operative')
    for group in {spec['groups'][key] for key in actual}:
        for expected_selection in spec['selection'][group]:
            bound(expected_selection['raw_source'])
            selected = units.get(expected_selection['use'])
            if (selected is None or any(selected.get(k) != expected_selection[k]
                    for k in ('role', 'questions', 'text', 'character_map'))
                    or segments(graph, selected, _raw=raw) != expected_selection['segments']):
                raise ValueError('BASF financial target selection or scalar provenance changed')
            for segment in expected_selection['segments']:
                bound(segment['source'])
    unknown = {t['use'] for r in expected for t in r['targets']
               for s in spec['selection'][spec['groups'][r['id']]]
               if s['use'] == t['use'] and s['role'] == 'UNKNOWN'}
    return {'status': 'REVIEWED' if len(actual) == len(expected) else 'UNREVIEWED',
            'references': expected, 'missing': [r['id'] for r in expected if r['id'] not in actual],
            'source_documents': spec['sources'], 'source_images': spec['images'],
            'specification_sha256': digest(spec), 'automatic_discovery': False,
            'actual_payment_and_tax_call_compliance': 'UNKNOWN', 'complete_reference_graph': False,
            'unknown_target_uses': sorted(unknown)}


def missing_dependencies(report):
    if report is None:
        return []
    return [{'id': 'financial-reference:' + identity, 'questions': ['Q1', 'Q2'],
             'status': 'UNRESOLVED', 'reason': 'The complete selected financial definition has no reviewed source link'}
            for identity in report['missing']]


def _owned(identity):
    return identity in {prefix + row['id'] for row in specification()['references']
                       for prefix in ('reviewed-reference:', 'financial-reference:')}


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
        raise ValueError('Consumed BASF financial dependencies differ from source review')
    required = {d['id'] for d in expected if d['status'] == 'UNRESOLVED'}
    for q in ('Q1', 'Q2'):
        for answer in [semantic['questions'][q], *semantic['questions'][q].get('subquestions', {}).values()]:
            if {v for v in answer['unresolved'] if _owned(v)} != required:
                raise ValueError('Consumed BASF question hides or invents a missing financial link')
    return report
