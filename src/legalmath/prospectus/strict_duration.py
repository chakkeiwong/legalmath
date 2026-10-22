"""Conditional strict-duration application of the selected default(b) source."""
from copy import deepcopy
from .successor import calendar_facts
from .successor.anchors import fields
from .successor.contracts import digest
from .successor.predicates import dispatch, names

VERSION = 'basf-strict-duration.v1'
KEY = 'strict_duration_review'
NODE = 'basf-default:b'
COMPUTED = 'default.b.other30'
QUALIFICATIONS = ('holder_notice_received', 'continuous_other_obligation_failure',
                  'counting_convention_supported')
ROLES = {'start': 'fiscal_agent_holder_notice_receipt', 'end': 'assessment'}


def context(products):
    rows = [n for n in products['P3']['payload']['clauses']['nodes'] if n['id'] == NODE]
    if (len(rows) != 1 or rows[0]['effect'] != 'repayment'
            or 'länger als 30 Tage' not in rows[0]['quote']
            or 'Benachrichtigung von einem Gläubiger erhalten hat' not in rows[0]['quote']):
        raise ValueError('Exact selected default(b) duration source required')
    return deepcopy(rows[0])


def analyze(row, node, instrument):
    keys = {'id', 'kind', 'interval', 'other_facts', *QUALIFICATIONS}
    fields(row, keys, keys)
    if not isinstance(row['id'], str) or not row['id'] or row['kind'] != 'HYPOTHETICAL_DEVELOPMENT':
        raise ValueError('Explicit hypothetical duration scenario required')
    for key in QUALIFICATIONS:
        v = row[key]
        if v is not None and v != 'conflict' and type(v) is not bool:
            raise ValueError('Duration qualifications must be Boolean,unknown or conflict')
    interval = row['interval']
    keys = {'instrument_id', 'event_id', 'start', 'end', 'convention'}
    fields(interval, keys, keys)
    if interval['instrument_id'] != instrument or interval['event_id'] != row['id']:
        raise ValueError('Duration instrument or event mismatch')
    convention = interval['convention']
    empty = interval['start'] is None and interval['end'] is None
    if not (convention is None and empty):
        if not isinstance(convention, str) or convention not in calendar_facts.CONVENTIONS:
            raise ValueError('Explicit supported duration convention required')
    values, unresolved = {}, []
    for label in ('start', 'end'):
        operand = interval[label]
        if operand is None:
            unresolved.append('Missing ' + label)
            continue
        fields(operand, {'value', 'role'}, {'value', 'role'})
        if operand['role'] != ROLES[label]:
            raise ValueError('Duration operand has wrong receipt or assessment role')
        values[label] = calendar_facts.operand_value(operand['value'], convention)
    above, exact = None, None
    if len(values) == 2:
        above, exact = calendar_facts.compare(values['start'], values['end'], convention, 30, 'GT')
    qualifications = {'duration_above_thirty_days': above, **{k: row[k] for k in QUALIFICATIONS}}
    derived = dispatch({'all': list(qualifications)}, qualifications)
    allowed = names(node['conditions']) - {COMPUTED}
    facts = row['other_facts']
    fields(facts, allowed)
    if any(v is not None and v != 'conflict' and type(v) is not bool for v in facts.values()):
        raise ValueError('Default premises must be Boolean,unknown or conflict')
    observations = {**facts, COMPUTED: {'YES': True, 'NO': False, 'UNKNOWN': None,
                                      'CONFLICT': 'conflict'}[derived['status']]}
    return {'scenario': deepcopy(row), 'duration_above_thirty_days': above,
            'exact_duration': exact, 'unresolved_interval': unresolved,
            'derived_other30': derived, 'duration_premises': qualifications,
            'complete_default_b': dispatch(node['conditions'], observations),
            'derived_observations': observations, 'actual_default': 'NOT_ESTABLISHED',
            'actual_exercise': 'NOT_ESTABLISHED', 'legal_counting_convention_established': False,
            'meaning': 'Conditional interval and full clause; dates alone establish neither receipt nor continuous breach'}


def evaluate(products, ordinary, profile, root, *, expected_profile_sha256):
    keys = {'version', 'products_sha256', 'ordinary_answer_sha256', 'context',
            'scenarios', 'actual_event_established'}
    fields(profile, keys, keys)
    if (profile['version'] != VERSION or digest(profile) != expected_profile_sha256
            or profile['products_sha256'] != digest(products)
            or profile['ordinary_answer_sha256'] != digest(ordinary)
            or ordinary.get('report_sha256') != digest({k: v for k, v in ordinary.items() if k != 'report_sha256'})
            or KEY in ordinary):
        raise ValueError('Pinned duration profile or complete baseline changed')
    if profile['actual_event_established'] is not False:
        raise ValueError('Conditional duration cannot establish actual events')
    node = context(products)
    if profile['context'] != node:
        raise ValueError('Complete default(b) source context changed')
    rows = profile['scenarios']
    if not isinstance(rows, list) or not rows or len(rows) > 128 or any(not isinstance(r, dict) for r in rows):
        raise ValueError('Bounded hypothetical duration scenarios required')
    ids = [r.get('id') for r in rows]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('Distinct duration scenario identities required')
    first = rows[0]
    if (first['id'] != 'all-open' or first['other_facts']
            or any(first[k] is not None for k in QUALIFICATIONS)
            or any(first['interval'][k] is not None for k in ('start', 'end', 'convention'))):
        raise ValueError('Explicit all-open duration baseline required')
    instrument = products['P1']['payload']['request']['bundle']['instrument_id']
    return {'version': VERSION, 'profile_sha256': digest(profile), 'products_sha256': digest(products),
            'ordinary_answer_sha256': digest(ordinary), 'context': node,
            'scenarios': [analyze(row, node, instrument) for row in rows],
            'actual_event_established': False, 'classification': 'SUPPLIED_SOURCE_BOUND_CONDITIONAL_READING'}


def verify_answer(answer, ordinary, profile, products, root, *, expected_profile_sha256):
    if (answer.get('report_sha256') != digest({k: v for k, v in answer.items() if k != 'report_sha256'})
            or {k: v for k, v in answer.items() if k not in (KEY, 'report_sha256')}
                != {k: v for k, v in ordinary.items() if k != 'report_sha256'}):
        raise ValueError('Complete duration answer changed baseline or digest')
    expected = evaluate(products, ordinary, profile, root, expected_profile_sha256=expected_profile_sha256)
    if answer.get(KEY) != expected:
        raise ValueError('Computed duration answer differs from full reconstruction')
    return {'status': 'PASS', 'baseline_unchanged': True, 'scenarios': len(expected['scenarios'])}
