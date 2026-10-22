"""Source-bound conditional agent notice; no actual appointment finding."""
from copy import deepcopy
from .causal_rating import boolean
from .successor import basf_agents, basf_notices, calendar_facts
from .successor.anchors import bind, fields
from .successor.contracts import digest
from .successor.predicates import dispatch

VERSION = 'basf-agent-notice-application.v1'
KEY = 'agent_notice_review'
EXPRESSION = {'any': ['insolvency', {'all': ['section13_notice', 'lower', 'upper']}]}
VALUES = {'YES': True, 'NO': False, 'UNKNOWN': None, 'CONFLICT': 'conflict'}
IDENTITY = {'instrument_id', 'agent_id', 'change_event_id'}


def context(products, ordinary):
    graph = products['P1']['payload']['graph']
    assembly = products['P2']['payload']['assembly']
    semantic = products['P3']['payload']
    nodes = semantic['clauses']['nodes']
    chosen = [n for n in nodes if n['id'] == 'basf-agents:effectiveness-reference']
    if len(chosen) != 1:
        raise ValueError('Exactly one complete agent-effectiveness source required')
    node = chosen[0]
    units = {u['unit']: u for u in assembly['units']}
    spans = basf_agents.paragraph_spans(units, node['id'])
    if (node['spans'] != spans or node['role'] != 'OPERATIVE'
            or node['quote'] != ' '.join(units[s['unit']]['text'][s['start']:s['end']] for s in spans)
            or node['source_uses'] != basf_agents.source_pieces(graph, units, spans)):
        raise ValueError('Complete original agent source extent changed')
    if not all(s in node['quote'] for s in ('nur wirksam', 'außer im Insolvenzfall',
            'mindestens 30 Tage', 'nicht mehr als 45 Tagen', 'gemäß § 13')):
        raise ValueError('Inclusive limits, exception or notice reference changed')
    reading = node['agent_reading']
    if (reading['notice_window_days'] != [30, 45] or reading['insolvency_immediate_effect'] is not True
            or reading['notice_reference'] != 'agent-change-notices'
            or reading['actual_change_validity'] != 'NOT_EVALUATED'):
        raise ValueError('Limited source reading changed')
    refs = semantic['interpretation_input']['reference_admission']['references']
    selected = [r for r in refs if r['id'] == 'agent-change-notices']
    if len(selected) != 1:
        raise ValueError('Complete onward notice reference required')
    ref = selected[0]
    if (ref['source']['quote'] != '§ 13' or ref['source']['unit'] != basf_notices.lines(124, 66, 66)[0]
            or ref['source']['start'] != 67 or ref['source']['end'] != 71
            or ref['authority'] != ref['source']
            or [r['use'] for r in ref['targets']] != basf_notices.lines(132, 20, 29) + basf_notices.lines(132, 35, 39)):
        raise ValueError('Complete section 13 target context changed')
    bind(graph, ref['source'])
    for row in node['source_uses'] + ref['targets']:
        bind(graph, row['source'])
    notices = []
    for identity in ('basf-notices:publication', 'basf-notices:clearing-substitution', 'basf-notices:holder-notice'):
        matches = [n for n in nodes if n['id'] == identity]
        if len(matches) != 1:
            raise ValueError('Onward procedural source reading missing')
        notices.append(deepcopy(matches[0]))
    if ordinary.get('basf_agents', {}).get('calculation_agent_office') != 'UNRESOLVED':
        raise ValueError('Agent office uncertainty changed; review required')
    return {'agent_clause': deepcopy(node), 'notice_reference': deepcopy(ref), 'notice_clauses': notices,
            'calculation_agent_office': 'UNRESOLVED', 'holders_informed_date_derived': False,
            'date_dependency': 'Section 13 publication/clearing timing and route requirements remain separate; supplied dates identify holders informed, not publication or delivery'}


def notice_condition(premises):
    fields(premises, {'insolvency', 'section13_notice', 'lower', 'upper'},
           {'insolvency', 'section13_notice', 'lower', 'upper'})
    for value in premises.values():
        boolean(value)
    return dispatch(EXPRESSION, premises)


def analyze(row, instrument):
    keys = {'id', 'kind', 'identity', 'interval', 'insolvency', 'section13_notice', 'reading_applies'}
    fields(row, keys, keys)
    if not isinstance(row['id'], str) or not row['id'] or row['kind'] != 'HYPOTHETICAL_DEVELOPMENT':
        raise ValueError('Explicit hypothetical notice scenario required')
    identity = row['identity']
    fields(identity, IDENTITY, IDENTITY)
    if identity['instrument_id'] != instrument or any(not isinstance(identity[k], str) or not identity[k].strip() for k in IDENTITY):
        raise ValueError('Identified instrument, agent and change event required')
    for key in ('insolvency', 'section13_notice', 'reading_applies'):
        boolean(row[key])
    interval = row['interval']
    fields(interval, {'convention', 'start', 'end'}, {'convention', 'start', 'end'})
    convention = interval['convention']
    empty = interval['start'] is None and interval['end'] is None
    if not (empty and convention is None):
        if not isinstance(convention, str) or convention not in calendar_facts.CONVENTIONS:
            raise ValueError('Explicit supported counting convention required')
    values, missing = {}, []
    for key, role in (('start', 'HOLDERS_INFORMED'), ('end', 'PROPOSED_CHANGE')):
        item = interval[key]
        if item is None:
            missing.append(key)
            continue
        fields(item, IDENTITY | {'role', 'value'}, IDENTITY | {'role', 'value'})
        if any(item[k] != identity[k] for k in IDENTITY) or item['role'] != role:
            raise ValueError('Notice operand subject, agent, event or date role mismatch')
        values[key] = calendar_facts.operand_value(item['value'], convention)
    lower = upper = None
    exact = {}
    if len(values) == 2:
        lower, exact['lower'] = calendar_facts.compare(values['start'], values['end'], convention, 30, 'GE')
        upper, exact['upper'] = calendar_facts.compare(values['start'], values['end'], convention, 45, 'LE')
    premises = {'insolvency': row['insolvency'], 'section13_notice': row['section13_notice'], 'lower': lower, 'upper': upper}
    necessary = notice_condition(premises)
    applied = dispatch({'all': ['necessary', 'reading_applies']},
                       {'necessary': VALUES[necessary['status']], 'reading_applies': row['reading_applies']})
    return {'scenario': deepcopy(row), 'premises': premises, 'exact_interval': exact, 'missing_dates': missing,
            'notice_precondition': necessary, 'conditional_notice_precondition': applied,
            'actual_change_effective': 'NOT_ESTABLISHED', 'calculation_agent_office': 'UNRESOLVED',
            'legal_counting_convention_established': False, 'holders_informed_date_derived': False,
            'meaning': 'Necessary notice condition under supplied hypothetical facts and reading; not sufficient proof of legally effective change'}


def evaluate(products, ordinary, profile, root, *, expected_profile_sha256):
    keys = {'version', 'products_sha256', 'ordinary_answer_sha256', 'context', 'scenarios',
            'actual_event_established', 'historical_application_proved', 'complete_legal_test'}
    fields(profile, keys, keys)
    if (profile['version'] != VERSION or digest(profile) != expected_profile_sha256
            or profile['products_sha256'] != digest(products) or profile['ordinary_answer_sha256'] != digest(ordinary)
            or ordinary.get('report_sha256') != digest({k:v for k,v in ordinary.items() if k != 'report_sha256'})
            or KEY in ordinary):
        raise ValueError('Pinned notice profile or complete baseline changed')
    if any(profile[k] is not False for k in ('actual_event_established', 'historical_application_proved', 'complete_legal_test')):
        raise ValueError('Conditional notice cannot establish actual or complete legal status')
    source = context(products, ordinary)
    if profile['context'] != source:
        raise ValueError('Full agent and onward notice source context changed')
    rows = profile['scenarios']
    if not isinstance(rows, list) or not 1 <= len(rows) <= 128 or any(not isinstance(r, dict) for r in rows):
        raise ValueError('Bounded nonempty notice scenarios required')
    ids = [r.get('id') for r in rows]
    if any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids)):
        raise ValueError('Distinct notice scenario identities required')
    first = rows[0]
    if (first['id'] != 'all-open' or any(first[k] is not None for k in ('insolvency', 'section13_notice', 'reading_applies'))
            or first['interval'] != {'convention': None, 'start': None, 'end': None}):
        raise ValueError('All-open notice baseline required')
    instrument = products['P1']['payload']['request']['bundle']['instrument_id']
    return {'version': VERSION, 'profile_sha256': digest(profile), 'products_sha256': digest(products),
            'ordinary_answer_sha256': digest(ordinary), 'context': source,
            'scenarios': [analyze(r, instrument) for r in rows], 'actual_event_established': False,
            'historical_application_proved': False, 'complete_legal_test': False,
            'classification': 'SUPPLIED_SOURCE_BOUND_NOTICE_PRECONDITION'}


def verify_answer(answer, ordinary, profile, products, root, *, expected_profile_sha256):
    if (answer.get('report_sha256') != digest({k:v for k,v in answer.items() if k != 'report_sha256'})
            or {k:v for k,v in answer.items() if k not in (KEY, 'report_sha256')}
            != {k:v for k,v in ordinary.items() if k != 'report_sha256'}):
        raise ValueError('Notice integration changed the complete prior answer')
    expected = evaluate(products, ordinary, profile, root, expected_profile_sha256=expected_profile_sha256)
    if answer.get(KEY) != expected:
        raise ValueError('Notice answer differs from source reconstruction')
    return {'status': 'PASS', 'baseline_unchanged': True, 'scenarios': len(expected['scenarios'])}
