"""Source-specific printed extents; scope review does not determine body meaning."""
from functools import lru_cache
import json
from pathlib import Path

from .contracts import digest
from .occurrences import segments

PREFIXES = {'listed': 'basf-listed-notices-margin-',
            'redemption': 'basf-redemption-margin:',
            'remaining': 'basf-remaining-margin:'}
QUESTIONS = ['Q1', 'Q2']


@lru_cache(maxsize=1)
def specification():
    return json.loads(Path(__file__).with_name('basf_printed_scope_spec.json').read_text())


def family(identity):
    return next((name for name, prefix in PREFIXES.items() if identity.startswith(prefix)), None)


def _anchor(raw, source, *, whole=False):
    unit = raw.get(source['unit'])
    if (unit is None or unit['document'] != source['document']
            or unit['source_sha256'] != source['source_sha256']
            or unit['raw'][source['start']:source['end']] != source['quote']
            or whole and (source['start'] != 0 or source['end'] != len(unit['raw']))):
        raise ValueError('BASF printed scope source anchor changed: ' + source['unit'])


def _edge_id(group, governor):
    if group['family'] == 'listed':
        return PREFIXES['listed'] + governor['unit'].rsplit(':l', 1)[1]
    return PREFIXES[group['family']] + group['id'] + ':' + governor['unit'].split(':', 1)[1]


def check(graph, assembly, admission):
    """Check each supplied family in full; a missing family remains unreviewed.

    This specification is tied to the reviewed editions and final-term choices.
    Other instruments do not acquire these choices merely through similar text.
    """
    edges = [] if admission is None else admission['governing']
    named = [e for e in edges if family(e['id']) is not None]
    spec = specification()
    raw = {u['id']: u for u in graph['units']}
    documents = {u['document']: u['source_sha256'] for u in graph['units']}
    if any(documents.get(s['id']) != s['sha256'] for s in spec['sources']):
        if named:
            raise ValueError('BASF printed scope is bound to different source editions')
        return None
    units = {u['unit']: u for u in assembly['units']}
    required = {a['unit'] for g in spec['groups'] for k in ('governors', 'body', 'premises') for a in g[k]}
    required |= {o['source']['unit'] for o in spec['occurrences']}
    if (len([u for u in graph['units'] if u['id'] in required]) != len(required.intersection(raw))
            or len([u for u in assembly['units'] if u['unit'] in required]) != len(required.intersection(units))):
        raise ValueError('Duplicate BASF printed source or selected occurrence identity')
    if not required <= units.keys() or not required <= raw.keys():
        if named:
            raise ValueError('BASF complete printed scope requires all original source occurrences')
        return {'status': 'UNREVIEWED', 'missing_families': list(PREFIXES), 'groups': [],
                'original_inventory_available': False, 'specification_sha256': digest(spec)}
    present = {family(e['id']) for e in named}
    expected, groups = {}, []
    for group in spec['groups']:
        for key in ('governors', 'printed_governors', 'body', 'premises'):
            for source in group[key]:
                _anchor(raw, source, whole=key != 'printed_governors')
        if any(units[a['unit']]['role'] != 'INSTRUCTION' for a in group['governors']):
            raise ValueError('BASF printed governor role changed: ' + group['id'])
        retained = [units[a['unit']] for a in group['body'] if units[a['unit']]['role'] != 'EXCLUDED']
        if any(u['role'] not in ('OPERATIVE', 'UNKNOWN') for u in retained):
            raise ValueError('BASF printed body has an unreviewed role: ' + group['id'])
        if bool(retained) is not group['applies']:
            raise ValueError('BASF printed scope applicability changed: ' + group['id'])
        targets = []
        for unit in retained:
            pieces = segments(graph, unit, _raw=raw)
            if ''.join(p['source']['quote'] for p in pieces) != unit['text']:
                raise ValueError('BASF printed selected body has incomplete source mapping')
            targets.extend({'source': p['source'], 'use': {
                'unit': unit['unit'], 'start': p['start'], 'end': p['end']}} for p in pieces)
        identities = []
        if group['applies']:
            for governor in group['printed_governors']:
                identity = _edge_id(group, governor)
                identities.append(identity)
                expected[identity] = {'from': governor, 'to': targets, 'questions': QUESTIONS, 'kind': 'governs'}
        groups.append({**group, 'selected_targets': targets, 'edge_ids': identities,
                       'review_present': group['family'] in present})
    actual = {e['id']: e for e in named}
    if len(actual) != len(named):
        raise ValueError('Duplicate BASF printed scope edge')
    selected_expected = {k: v for k, v in expected.items() if family(k) in present}
    if actual.keys() != selected_expected.keys():
        raise ValueError('BASF printed scope family is omitted, extended or inapplicable')
    version = None if admission is None else admission['version']
    for identity, expected_edge in selected_expected.items():
        edge = actual[identity]
        targets = expected_edge['to']
        if version == 'prospectus-layout.v1':
            targets = [t['source'] for t in targets]
        elif version != 'prospectus-layout.v2':
            raise ValueError('Unsupported BASF printed scope selected-use version')
        want = {**expected_edge, 'to': targets}
        got = {key: edge.get(key) for key in want}
        if digest(want) != digest(got):
            raise ValueError('BASF printed scope extent or selected occurrence changed: ' + identity)
    for occurrence in spec['occurrences']:
        _anchor(raw, occurrence['source'], whole=True)
        if units[occurrence['source']['unit']]['role'] != occurrence['current_role']:
            raise ValueError('BASF original margin/header occurrence role changed')
    for sources in spec['shared_outside_scope'].values():
        for source in sources:
            _anchor(raw, source, whole=True)
    for anomaly in spec['anomalies']:
        for source in anomaly['sources']:
            _anchor(raw, source)
    missing = [name for name in PREFIXES if name not in present]
    return {'status': 'COMPLETE_REVIEWED_SCOPE' if not missing else 'PARTIAL' if present else 'UNREVIEWED',
            'missing_families': missing, 'groups': groups, 'original_inventory_available': True,
            'specification_sha256': digest(spec)}


def missing_dependencies(review):
    if review is None:
        return []
    return [{'id': 'margin-scope:' + name, 'questions': QUESTIONS, 'status': 'UNRESOLVED',
             'reason': 'The complete printed scope family has not been supplied for review'}
            for name in review['missing_families']]


def _scope_dependency(identity):
    return identity.startswith('margin-scope:') or (
        identity.startswith('governing:') and family(identity.removeprefix('governing:')) is not None)


def verify_consumed(graph, assembly, request, semantic):
    admission = request.get('governing_admission')
    review = check(graph, assembly, admission)
    if review is None:
        return None
    from .admissions import structure, governing_dependencies
    expected = missing_dependencies(review)
    if admission is not None:
        layout = structure(graph, admission)
        layout = {**layout, 'governing': [e for e in layout['governing'] if family(e['id']) is not None]}
        from .occurrences import _DependencyLookup
        expected += governing_dependencies({**graph, 'layout': layout}, assembly,
                                           _lookup=_DependencyLookup(graph, assembly))
    actual = [d for d in semantic['dependencies'] if _scope_dependency(d['id'])]
    if digest(sorted(expected, key=lambda d: d['id'])) != digest(sorted(actual, key=lambda d: d['id'])):
        raise ValueError('Consumed BASF printed scope dependencies differ from source review')
    if semantic.get('governing_admission_sha256') != (digest(admission) if admission else None):
        raise ValueError('Consumed BASF governing admission identity changed')
    for q in QUESTIONS:
        required = {d['id'] for d in expected if q in d['questions'] and d['status'] == 'UNRESOLVED'}
        answers = [semantic['questions'][q], *semantic['questions'][q].get('subquestions', {}).values()]
        for answer in answers:
            got = {identity for identity in answer['unresolved'] if _scope_dependency(identity)}
            if got != required:
                raise ValueError('Consumed BASF question hides or invents unresolved printed scope')
    return review


def explain(review, ordinary, semantic):
    spec = specification()
    pending = {row['unit']: row for row in ordinary.get('meaning_coverage', {}).get('selected_body_pending', [])}
    groups = []
    for group in review['groups']:
        unresolved = [pending[a['unit']] for a in group['body'] if a['unit'] in pending]
        groups.append({**group, 'unresolved_body_meanings': unresolved})
    return {**review, 'groups': groups,
        'occurrences': spec['occurrences'] if review['original_inventory_available'] else [],
        'shared_outside_scope': spec['shared_outside_scope'], 'anomalies': spec['anomalies'],
        'source_documents': spec['sources'], 'source_review_inputs': spec['review_inputs'],
        'unresolved_dependency_ids': [d['id'] for d in semantic['dependencies']
            if _scope_dependency(d['id']) and d['status'] == 'UNRESOLVED'],
        'meaning': 'Reviewed printed extents under the supplied final terms; body meanings and actual facts remain separate.',
        'automatic_discovery': False, 'all_body_meanings_established': False,
        'independent_legal_acceptance': False, 'actual_event_established': False}
