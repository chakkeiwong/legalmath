"""Declared necessary office conditions; actual designation remains unresolved."""
from copy import deepcopy
import re
from .. import notice_delivery
from ..causal_rating import boolean
from . import basf_agent_report
from .anchors import fields
from .contracts import digest
from .predicates import dispatch

VERSION = 'basf-office-change.v1'
KEY = 'office_change_review'
VALUE = {'YES': True, 'NO': False, 'UNKNOWN': None, 'CONFLICT': 'conflict'}
FLAGS = ('original_office_designated', 'replacement_office_designated', 'reading_applies')
IDENTITY = notice_delivery.IDENTITY
NAMESPACE = 'SCENARIO_LOCAL_COUNTRY_IDENTITY'


def same_country(original, replacement):
    for value in (original, replacement):
        if value is not None and (not isinstance(value, str) or
                re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{0,63}', value) is None):
            raise ValueError('Country must be an opaque explicit identity, unknown or conflict')
    if original == 'conflict' or replacement == 'conflict': return 'conflict'
    if original is None or replacement is None: return None
    return original == replacement


def conjunction(premises):
    required = {'notice', 'same_country', *FLAGS}
    fields(premises, required, required)
    for value in premises.values(): boolean(value)
    return dispatch({'all': sorted(required)}, premises)


def context(products, ordinary):
    graph = products['P1']['payload']['graph']; selected = products['P2']['payload']
    semantic = products['P3']['payload']
    report = basf_agent_report.explain(semantic['clauses'], graph, selected['assembly'], semantic['dependencies'])
    if ordinary.get('basf_agents') != report:
        raise ValueError('Complete original agent source report changed')
    readings = {r['id']: r for r in report['readings']}
    office = readings.get('basf-agents:office-replacement')
    if not office or office['reading'].get('same_country') is not True or 'in demselben Land' not in office['quote']:
        raise ValueError('Complete same-country office replacement source required')
    prior = ordinary.get(notice_delivery.KEY)
    if not isinstance(prior, dict) or prior.get('version') != notice_delivery.VERSION:
        raise ValueError('Existing integrated notice delivery review required')
    source = notice_delivery.context(products, ordinary)
    if prior.get('context') != source:
        raise ValueError('Office composition requires the unchanged notice source context')
    return {'office_reading': deepcopy(office), 'notice_context': source,
        'calculation_agent_office': 'UNRESOLVED',
        'country_namespace': NAMESPACE, 'supported_change': 'OFFICE_REPLACEMENT',
        'reading_status': 'SUPPLIED_CONDITIONAL_NECESSARY_CONDITIONS',
        'qualification': 'Designated-office premises and same-country identity are hypothetical; the notice exception does not waive the separate country condition'}


def analyze(row, notice, instrument):
    keys = {'id', 'kind', 'change_kind', 'identity', 'notice_case', 'country_namespace',
            'original_country', 'replacement_country', *FLAGS}
    fields(row, keys, keys)
    if (not isinstance(row['id'], str) or not row['id'] or row['kind'] != 'HYPOTHETICAL_DEVELOPMENT'
            or row['change_kind'] != 'OFFICE_REPLACEMENT' or row['country_namespace'] != NAMESPACE):
        raise ValueError('Explicit hypothetical office replacement in one country namespace required')
    identity = row['identity']; fields(identity, IDENTITY, IDENTITY)
    if (identity['instrument_id'] != instrument or
            any(not isinstance(identity[k], str) or not identity[k].strip() for k in IDENTITY) or
            identity != notice['scenario']['identity'] or row['notice_case'] != notice['scenario']['id']):
        raise ValueError('Office and notice instrument, agent, change and notice identities differ')
    for key in FLAGS: boolean(row[key])
    status = notice['notice']['conditional_notice_precondition']['status']
    if status not in VALUE: raise ValueError('Supported conditional notice status required')
    # Reconstruct the small selected notice scenario; do not trust an edited status.
    if notice_delivery.analyze(notice['scenario'], instrument) != notice:
        raise ValueError('Notice result differs from its supplied scenario')
    country = same_country(row['original_country'], row['replacement_country'])
    premises = {k: row[k] for k in FLAGS}
    premises.update(notice=VALUE[status], same_country=country)
    return {'scenario': deepcopy(row), 'notice_precondition': status, 'same_country': country,
        'premises': premises, 'conditional_office_preconditions': conjunction(premises),
        'actual_office_designation': 'NOT_ESTABLISHED', 'actual_change_effective': 'NOT_ESTABLISHED',
        'calculation_agent_office': 'UNRESOLVED', 'complete_legal_test': False,
        'meaning': 'Necessary conjunction under declared hypothetical office and notice premises; not sufficient proof of an effective office change'}


def evaluate(products, ordinary, profile, root, *, expected_profile_sha256):
    keys = {'version', 'products_sha256', 'ordinary_answer_sha256', 'context', 'scenarios'}
    fields(profile, keys, keys)
    if (profile['version'] != VERSION or digest(profile) != expected_profile_sha256
            or profile['products_sha256'] != digest(products) or profile['ordinary_answer_sha256'] != digest(ordinary)
            or ordinary.get('report_sha256') != digest({k:v for k,v in ordinary.items() if k != 'report_sha256'})
            or KEY in ordinary):
        raise ValueError('Pinned complete prior answer and office profile required')
    source = context(products, ordinary)
    if profile['context'] != source: raise ValueError('Office and notice source context changed')
    rows = profile['scenarios']
    if not isinstance(rows, list) or not 1 <= len(rows) <= 64 or any(not isinstance(r, dict) for r in rows):
        raise ValueError('One to64 office scenarios required')
    ids = [r.get('id') for r in rows]
    if any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids)):
        raise ValueError('Distinct office scenario identities required')
    first = rows[0]
    if (first['id'] != 'all-open' or first['notice_case'] != 'all-open' or
            any(first[k] is not None for k in (*FLAGS, 'original_country', 'replacement_country'))):
        raise ValueError('All-open office baseline required')
    notices = {r['scenario']['id']: r for r in ordinary[notice_delivery.KEY]['scenarios']}
    instrument = products['P1']['payload']['request']['bundle']['instrument_id']
    result = []
    for row in rows:
        if row.get('notice_case') not in notices: raise ValueError('Existing bound notice case required')
        result.append(analyze(row, notices[row['notice_case']], instrument))
    return {KEY: {'version': VERSION, 'profile_sha256': digest(profile),
        'products_sha256': digest(products), 'ordinary_answer_sha256': digest(ordinary),
        'context': source, 'scenarios': result, 'actual_office_designation': 'NOT_ESTABLISHED',
        'actual_change_effective': 'NOT_ESTABLISHED', 'historical_application_proved': False,
        'complete_legal_test': False, 'selected_interpretation': None}}
