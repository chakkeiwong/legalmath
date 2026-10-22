"""Versioned supplied initial-agent reading with its introductory source premise.

This repairs a source dependency in the retained BASF development reading. It
does not establish an actual appointment or fill the Calculation Agent office.
"""
from copy import deepcopy

from . import basf, basf_agents
from .contracts import digest
from .occurrences import anchor

VERSION = 'basf-initial-agent-source.v1'
IDENTITY = 'basf-agents:initial-agent'
UNKNOWN_ID = basf.KEY + ':p123:l51:clause:4037'
INTRO_TEXT = {
    basf.KEY + ':p123:l82': '(1) Bestellung; bezeichnete Geschäftsstelle. Der anfänglich bestellte Fiscal Agent ,',
    basf.KEY + ':p123:l83': ' die anfänglich bestellte Zahlstelle und die anfänglich bestellte',
    basf.KEY + ':p123:l84': 'Berechnungsstelle und deren bezeichnete Geschäftsstellen lauten wie folgt:',
}
APPOINTMENT_WORDING = (
    'The selected introduction describes the Fiscal Agent, Paying Agent and '
    'Calculation Agent as initially appointed and introduces their designated '
    'offices. This is contractual wording, not evidence that an appointment '
    'occurred or remains effective. The Calculation Agent office is unresolved.'
)
REASON = ('Reviewed selected initial-agent introductory wording; the mixed '
          'caption remains unknown in P3 and the calculation-office field stays unresolved.')


def introduction_spans(units):
    for key, text in INTRO_TEXT.items():
        if units[key]['text'] != text:
            raise ValueError('Selected initially-appointed introduction changed')
    return [{'unit': key, 'start': 45 if key.endswith(':l82') else 0,
             'end': len(text)} for key, text in INTRO_TEXT.items()]


def expected_node(graph, units, *, include_introduction=True):
    # Imported here to keep the legacy reporter free of an import cycle.
    from .basf_agent_report import SPEC
    spans = basf_agents.paragraph_spans(units, IDENTITY)
    node = deepcopy(SPEC[IDENTITY])
    if include_introduction:
        intro = introduction_spans(units)
        if any(units[s['unit']]['role'] != 'OPERATIVE' for s in intro):
            raise ValueError('Initial-agent introduction requires reviewed operative sources')
        spans = intro + spans
        node['initial_agent_provenance'] = VERSION
        node['agent_reading']['appointment_wording'] = APPOINTMENT_WORDING
    raw = {u['id']: u for u in graph['units']}
    node.update(units=list(dict.fromkeys(s['unit'] for s in spans)), spans=spans,
                quote=' '.join(units[s['unit']]['text'][s['start']:s['end']] for s in spans),
                source_uses=basf_agents.source_pieces(graph, units, spans),
                selection_authority=[anchor(raw[k]) for k in basf_agents.AUTHORITY_IDS])
    return node


def prepare_request(graph, assembly, request):
    """Amend only the reviewed premise; ordinary phase APIs rebuild the products."""
    units = {u['unit']: u for u in assembly['units']}
    spans = introduction_spans(units)
    if any(units[s['unit']]['role'] != 'UNKNOWN' for s in spans):
        raise ValueError('Expected the retained unknown initial-agent introduction')
    nodes = {n['id']: n for n in request['clauses']}
    if len(nodes) != len(request['clauses']):
        raise ValueError('Duplicate baseline clause identity')
    if nodes[IDENTITY] != expected_node(graph, units, include_introduction=False):
        raise ValueError('Retained initial-agent reading changed')
    unknown = nodes[UNKNOWN_ID]
    if (unknown['effect'] != 'unknown' or unknown['role'] != 'UNKNOWN' or
            unknown['spans'] != spans or unknown['units'] != list(INTRO_TEXT) or
            unknown['quote'] != ' '.join(units[s['unit']]['text'][s['start']:s['end']] for s in spans)):
        raise ValueError('Exact introductory unknown node required')
    result = deepcopy(request)
    admission = result['reviewed_dispositions']
    if set(INTRO_TEXT).intersection(r['unit'] for r in admission['units']):
        raise ValueError('Initial-agent source already has a reviewed disposition')
    selected = deepcopy(units)
    for key in INTRO_TEXT:
        full = [{'unit': key, 'start': 0, 'end': len(units[key]['text'])}]
        admission['units'].append({'unit': key, 'text_sha256': digest(units[key]['text'].encode()),
            'role': 'OPERATIVE', 'reason': REASON,
            'sources': [p['source'] for p in basf_agents.source_pieces(graph, units, full)]})
        selected[key].update(role='OPERATIVE', reason=REASON)
    node = expected_node(graph, selected)
    result['clauses'] = [node if n['id'] == IDENTITY else deepcopy(n)
                         for n in request['clauses'] if n['id'] != UNKNOWN_ID]
    return result


def validate_transition(before, after):
    """Check the exact admitted edit independently of phase/product hashes."""
    from .service import verify
    b1, a1 = verify(before['P1'], 'P1'), verify(after['P1'], 'P1')
    b2, a2 = verify(before['P2'], 'P2'), verify(after['P2'], 'P2')
    if a1['graph'] != b1['graph']:
        raise ValueError('Core repair changed original source graph')
    expected = prepare_request(b1['graph'], b2['assembly'], b1['request'])
    expected['reference_admission']['assembly_sha256'] = digest(a2['assembly'])
    if a1['request'] != expected:
        raise ValueError('Core request changed outside the admitted premise')
    assembly = deepcopy(b2['assembly'])
    for unit in assembly['units']:
        if unit['unit'] in INTRO_TEXT:
            unit.update(role='OPERATIVE', reason=REASON)
    assembly['reviewed_dispositions'] = deepcopy(expected['reviewed_dispositions'])
    assembly['unresolved'] = [u['unit'] for u in assembly['units'] if u['role'] == 'UNKNOWN']
    if a2 != {**b2, 'assembly': assembly}:
        raise ValueError('Core construction changed an outside unit or protected branch')
    b3, a3 = verify(before['P3'], 'P3'), verify(after['P3'], 'P3')
    if a3['clauses']['nodes'] != expected['clauses']:
        raise ValueError('Core clauses changed outside the exact introductory replacement')
    if {k: v for k, v in a3.items() if k not in {'clauses', 'questions'}} != {
            k: v for k, v in b3.items() if k not in {'clauses', 'questions'}}:
        raise ValueError('Core repair changed reference, incorporation or other interpretation inputs')
    if {k: v for k, v in a3['clauses'].items() if k not in {'nodes', 'assembly_sha256'}} != {
            k: v for k, v in b3['clauses'].items() if k not in {'nodes', 'assembly_sha256'}}:
        raise ValueError('Core repair changed outside clause edges or coverage')
    for phase in ('P4', 'P5'):
        if verify(before[phase], phase) != verify(after[phase], phase):
            raise ValueError('Core repair changed law or financial calculation')
    return {'status': 'PASS', 'added_initial_source_units': list(INTRO_TEXT),
            'removed_unknown_node': UNKNOWN_ID, 'all_outside_nodes_equal': True,
            'selected_text_and_protected_branches_equal': True,
            'calculation_agent_office': 'UNRESOLVED', 'independent_legal_acceptance': False}
