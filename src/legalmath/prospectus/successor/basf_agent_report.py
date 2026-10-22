"""Report the retained BASF agent readings with exact source and scope checks.

These are supplied development readings for the selected issue, not an extractor
or an independent decision about appointment authority.
"""
from copy import deepcopy
from . import basf, basf_agents, basf_agent_capacity
from .anchors import bind
from .occurrences import anchor, segments

AUTHORITY_TEXT = [
    'Fiscal and Paying Agent', 'Fiscal Agent und Zahlstelle',
    'Calculation Agent', 'Berechnungsstelle',
    'Deutsche Bank Aktiengesellschaft', 'Deutsche Bank Aktiengesellschaft',
    'NatWest Markets N.V.', 'NatWest Markets N.V.',
]


def _sources(graph, units, spans):
    groups = []
    for span in spans:
        unit = units[span['unit']]
        cursor, sources = span['start'], []
        for piece in segments(graph, unit):
            start, end = max(span['start'], piece['start']), min(span['end'], piece['end'])
            if start >= end:
                continue
            if start != cursor:
                raise ValueError('Agent source occurrence has a gap or overlap')
            raw = piece['source']
            raw_start = raw['start'] + start - piece['start']
            sources.append(bind(graph, {**raw, 'start':raw_start,
                'end':raw_start + end - start, 'quote':unit['text'][start:end]}))
            cursor = end
        if cursor != span['end']:
            raise ValueError('Agent source occurrence is incomplete')
        groups.append({'occurrence':dict(span), 'sources':sources})
    return groups


def explain(clauses, graph, assembly, dependencies):
    """Validate and report only supplied agent rows, retaining missing authority."""
    units = {u['unit']:u for u in assembly['units']}
    raw = {u['id']:u for u in graph['units']}
    nodes = [n for n in clauses['nodes'] if n['id'].startswith('basf-agents:')
             or 'agent_reading' in n or 'capacity_reading' in n]
    authority = []
    for key, text in zip(basf_agents.AUTHORITY_IDS, AUTHORITY_TEXT):
        if key not in raw or raw[key]['raw'] != text:
            raise ValueError('Agent final-term role label or identity changed')
        authority.append(bind(graph, anchor(raw[key])))
    office_id = basf.KEY + ':p124:l44'
    office = units[office_id]
    if office['role'] != 'UNKNOWN' or office['text'] != basf_agents.PLACEHOLDER:
        raise ValueError('Unsupported calculation-agent office designation')
    result, seen = [], set()
    for node in nodes:
        identity = node['id']
        if identity in seen or identity not in {*SPEC, basf_agent_capacity.IDENTITY}:
            raise ValueError('Duplicate or unsupported BASF agent reading')
        seen.add(identity)
        capacity = identity == basf_agent_capacity.IDENTITY
        spans = (basf_agent_capacity.spans(units) if capacity else
                 basf_agents.paragraph_spans(units, identity))
        ids = list(dict.fromkeys(s['unit'] for s in spans))
        if any(units[key]['role'] != 'OPERATIVE' for key in ids):
            raise ValueError('Agent reading requires selected operative source')
        expected = ({'id':identity, 'effect':'none', 'effect_scope':['Q1','Q2'],
            'effect_explanation':'This contractual allocation of agency roles does not itself create principal-loss or compulsory-conversion authority; it does not decide statutory duties.',
            'actor':'agent', 'affected':'holder', 'modality':'statement', 'election':'none',
            'assets':[], 'role':'OPERATIVE', 'polarity':True, 'conditions':[],
            'exceptions':[], 'questions':['Q1','Q2'], 'origin':'development-source-review',
            'capacity_reading':basf_agent_capacity.READING} if capacity else SPEC[identity])
        expected = {**deepcopy(expected), 'units':ids, 'spans':spans,
            'quote':' '.join(units[s['unit']]['text'][s['start']:s['end']] for s in spans),
            'source_uses':basf_agents.source_pieces(graph, units, spans)}
        if capacity or identity == 'basf-agents:initial-agent':
            expected['selection_authority'] = [anchor(raw[k]) for k in basf_agents.AUTHORITY_IDS]
        if identity == 'basf-agents:initial-agent' and 'initial_agent_provenance' in node:
            from . import basf_initial_agents
            if node['initial_agent_provenance'] != basf_initial_agents.VERSION:
                raise ValueError('Unsupported initial-agent provenance version')
            expected = basf_initial_agents.expected_node(graph, units)
            spans = expected['spans']
        if node != expected:
            raise ValueError('Agent reading, source extent, condition or authority changed')
        groups = _sources(graph, units, spans)
        row = {'id':identity, 'reading':deepcopy(node['capacity_reading' if capacity else 'agent_reading']),
            'quote':node['quote'], 'source_spans':groups,
            'sources':[s for group in groups for s in group['sources']],
            'selection_authority':deepcopy(authority) if 'selection_authority' in node else [],
            'reading_status':'SUPPLIED_CONTRACTUAL_INTERPRETATION',
            'actual_appointment_or_change':'NOT_ESTABLISHED',
            'historical_law_applicability':'NOT_ESTABLISHED', 'independent_legal_acceptance':False}
        if identity == 'basf-agents:effectiveness-reference':
            found = [d for d in dependencies if d['id'] == 'reviewed-reference:agent-change-notices']
            if len(found) > 1:
                raise ValueError('Duplicate agent-change notice dependency')
            row['notice_dependency'] = deepcopy(found[0]) if found else {
                'id':'reviewed-reference:agent-change-notices', 'status':'UNRESOLVED'}
        result.append(row)
    context_ids = [basf.KEY + f':p123:l{i}' for i in (82,83,84)] + [basf.KEY + ':p124:l43', office_id]
    context = []
    for key in context_ids:
        unit = units[key]
        context.append({'unit':key, 'role':unit['role'], 'text':unit['text'],
            'source_spans':_sources(graph, units, [{'unit':key,'start':0,'end':len(unit['text'])}])})
    return {'readings':result, 'calculation_agent_office':'UNRESOLVED',
        'office_authority_needed':'Applicable original appointment/agency agreement or authoritative issue-specific designated-office source; a lead-manager address alone does not supply it.',
        'unresolved_context':context, 'independent_legal_acceptance':False}

SPEC = {'basf-agents:initial-agent': {'id': 'basf-agents:initial-agent',
                               'effect': 'none',
                               'effect_scope': ['Q1', 'Q2'],
                               'effect_explanation': 'No direct principal-loss or compulsory-conversion '
                                                     'effect asserted; procedural appointment '
                                                     'conditions remain positive typed meaning.',
                               'actor': 'issuer',
                               'affected': 'holder',
                               'modality': 'statement',
                               'election': 'none',
                               'assets': [],
                               'role': 'OPERATIVE',
                               'polarity': True,
                               'conditions': [],
                               'exceptions': [],
                               'questions': ['Q1', 'Q2'],
                               'origin': 'development-source-review',
                               'agent_reading': {'reading': 'The selected initial Fiscal and Paying '
                                                            'Agent is Deutsche Bank Aktiengesellschaft, '
                                                            'Trust & Agency Services, Taunusanlage 12, '
                                                            '60325 Frankfurt am Main, Germany. The '
                                                            'final terms separately name NatWest '
                                                            'Markets N.V. as Calculation Agent.',
                                                 'fiscal_and_paying_agent': 'Deutsche Bank '
                                                                            'Aktiengesellschaft',
                                                 'final_term_calculation_agent': 'NatWest Markets N.V.',
                                                 'calculation_agent_office': 'UNRESOLVED',
                                                 'qualification': 'Final-term labels and names identify '
                                                                  'the issue agents. No '
                                                                  'calculation-agent office is supplied '
                                                                  'and the B54 template name/office '
                                                                  'placeholder is retained.'}},
 'basf-agents:office-replacement': {'id': 'basf-agents:office-replacement',
                                    'effect': 'none',
                                    'effect_scope': ['Q1', 'Q2'],
                                    'effect_explanation': 'No direct principal-loss or '
                                                          'compulsory-conversion effect asserted; '
                                                          'procedural appointment conditions remain '
                                                          'positive typed meaning.',
                                    'actor': 'agent',
                                    'affected': 'holder',
                                    'modality': 'may',
                                    'election': 'none',
                                    'assets': [],
                                    'role': 'OPERATIVE',
                                    'polarity': True,
                                    'conditions': [],
                                    'exceptions': [],
                                    'questions': ['Q1', 'Q2'],
                                    'origin': 'development-source-review',
                                    'agent_reading': {'reading': 'The Fiscal Agent, Paying Agent and, '
                                                                 'where selected, Calculation Agent may '
                                                                 'replace their designated office with '
                                                                 'another designated office in the same '
                                                                 'country.',
                                                      'same_country': True,
                                                      'qualification': 'The clause supplies a '
                                                                       'same-country office-change '
                                                                       'rule; it does not identify a '
                                                                       'replacement office or establish '
                                                                       'that a change occurred.'}},
 'basf-agents:appointment-change': {'id': 'basf-agents:appointment-change',
                                    'effect': 'none',
                                    'effect_scope': ['Q1', 'Q2'],
                                    'effect_explanation': 'No direct principal-loss or '
                                                          'compulsory-conversion effect asserted; '
                                                          'procedural appointment conditions remain '
                                                          'positive typed meaning.',
                                    'actor': 'issuer',
                                    'affected': 'holder',
                                    'modality': 'statement',
                                    'election': 'none',
                                    'assets': [],
                                    'role': 'OPERATIVE',
                                    'polarity': True,
                                    'conditions': [],
                                    'exceptions': [],
                                    'questions': ['Q1', 'Q2'],
                                    'origin': 'development-source-review',
                                    'agent_reading': {'reading': 'The issuer may change or end the '
                                                                 'appointment of the Fiscal Agent or '
                                                                 'Paying Agent, and where the '
                                                                 'calculation-agent branch is '
                                                                 'operative, may change or end that '
                                                                 'appointment and appoint another or '
                                                                 'additional agent; the issuer must '
                                                                 'maintain a Fiscal Agent.',
                                                      'maintain_fiscal_agent': True,
                                                      'maintain_calculation_agent_if_selected': True,
                                                      'calculation_agent_condition': 'if a Calculation '
                                                                                     'Agent is to be '
                                                                                     'appointed',
                                                      'qualification': 'The frozen construction retains '
                                                                       'the calculation-agent wording. '
                                                                       'Its template condition is if a '
                                                                       'Calculation Agent is to be '
                                                                       'appointed; the issuer then '
                                                                       'maintains one. Final terms name '
                                                                       'NatWest, but B54 name/office '
                                                                       'construction authority remains '
                                                                       'unresolved.'}},
 'basf-agents:effectiveness-reference': {'id': 'basf-agents:effectiveness-reference',
                                         'effect': 'none',
                                         'effect_scope': ['Q1', 'Q2'],
                                         'effect_explanation': 'No direct principal-loss or '
                                                               'compulsory-conversion effect asserted; '
                                                               'procedural appointment conditions '
                                                               'remain positive typed meaning.',
                                         'actor': 'issuer',
                                         'affected': 'holder',
                                         'modality': 'statement',
                                         'election': 'none',
                                         'assets': [],
                                         'role': 'OPERATIVE',
                                         'polarity': True,
                                         'conditions': [],
                                         'exceptions': [],
                                         'questions': ['Q1', 'Q2'],
                                         'origin': 'development-source-review',
                                         'agent_reading': {'reading': 'An appointment, removal, '
                                                                      'appointment of an additional '
                                                                      'agent or other change becomes '
                                                                      'effective only after holders are '
                                                                      'informed under section 13 with '
                                                                      'at least 30 and no more than 45 '
                                                                      'days notice; an insolvency '
                                                                      'change is immediately effective.',
                                                           'notice_window_days': [30, 45],
                                                           'insolvency_immediate_effect': True,
                                                           'notice_reference': 'agent-change-notices',
                                                           'actual_change_validity': 'NOT_EVALUATED',
                                                           'qualification': 'The reading supplies the '
                                                                            'contractual condition and '
                                                                            'onward notice dependency; '
                                                                            'no actual change, '
                                                                            'insolvency event, notice '
                                                                            'or effective date is '
                                                                            'supplied.'}}}
