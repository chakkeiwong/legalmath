"""Selected BASF exchange/certification terms; no actual tax eligibility decision."""
from copy import deepcopy

from . import basf, basf_agent_capacity, basf_agents, basf_notices, clause_graph
from .admissions import dispositions, review
from .contracts import digest
from .occurrences import anchor
from .reviewed_references import admit

EXCHANGE = 'basf-global:exchange-certification'
GEOGRAPHY = 'basf-global:united-states-definition'
PARAGRAPHS = {EXCHANGE: basf_notices.lines(108, 59, 81),
              GEOGRAPHY: basf_notices.lines(124, 68, 71)}
PRIOR_IDS = [*basf_agent_capacity.PRIOR_IDS, basf_agent_capacity.IDENTITY]
AUTHORITY_IDS = ([f'basf-2032-final:p3:l{i}' for i in [*range(5, 16), *range(20, 24), *range(36, 56)]]
                 + [f'basf-2032-final:p7:l{i}' for i in range(48, 54)])
CONTEXT_IDS = basf_notices.lines(108, 49, 58)
READINGS = {
    EXCHANGE: {
        'reading': 'The temporary global note is exchangeable for the permanent global note no earlier than 40 days after the issue day. Exchange requires presentation of certificates under U.S. tax law that the beneficial owners are not U.S. persons, except certain financial institutions or certain persons holding through such institutions. Interest on notes represented by the temporary global note is paid only after such certificates are presented, with a separate certificate for each payment. A certificate received on or after the 40th day after the issue day is treated as a request to exchange under section 1(3)(b). Securities delivered in exchange may be delivered only outside the United States as defined in section 6(2).',
        'earliest_exchange_days_after_issue': 40,
        'earliest_exchange_comparison': 'AT_LEAST',
        'exchange_requires_certificate': True,
        'certificate_basis': 'U.S. tax law as referenced by this contract; substantive rules not evaluated',
        'certified_subject': 'beneficial owners',
        'certified_non_us_person_status': True,
        'express_exceptions': ['certain financial institutions', 'certain persons holding through such financial institutions'],
        'interest_requires_prior_certificate': True,
        'separate_certificate_each_interest_payment': True,
        'certificate_receipt_exchange_request_day': 40,
        'certificate_receipt_comparison': 'ON_OR_AFTER',
        'certificate_is_request_not_completed_exchange': True,
        'delivery_only_outside_contractual_united_states': True,
        'geography_reference': 'us-definition',
        'actual_tax_eligibility': 'NOT_EVALUATED',
        'actual_exchange_or_delivery': 'NOT_EVALUATED',
        'qualification': 'These are contractual prerequisites, not proof that a beneficial owner is eligible or a certificate is legally sufficient. The territory definition does not define U.S.-person status or the unspecified classes of excepted institutions/persons. No actual certificate, owner status, exchange request or delivery is supplied. Reaching day 40 does not waive certification, complete an exchange or establish interest entitlement.',
    },
    GEOGRAPHY: {
        'reading': 'For these terms and conditions, United States means the United States of America, including its states and the District of Columbia, and its territories, including Puerto Rico, the U.S. Virgin Islands, Guam, American Samoa, Wake Island and the Northern Mariana Islands.',
        'scope': 'THESE_TERMS_AND_CONDITIONS',
        'includes_states_and_district_of_columbia': True,
        'includes_territories': True,
        'territory_examples': ['Puerto Rico', 'U.S. Virgin Islands', 'Guam', 'American Samoa', 'Wake Island', 'Northern Mariana Islands'],
        'territory_list_exhaustive': False,
        'defines_us_person': False,
        'actual_tax_eligibility': 'NOT_EVALUATED',
        'qualification': 'This contractual geography governs the imported delivery restriction. It survives independently of the excluded U.S.-dollar/New York and CDS payment-agent branches. It does not define U.S.-person status, tax residence, citizenship or actual U.S. tax eligibility.',
    },
}


def spans(units, identity):
    result = [{'unit': key, 'start': 0, 'end': len(units[key]['text'])} for key in PARAGRAPHS[identity]]
    if identity == GEOGRAPHY:
        result[0]['start'] = len('wurden. ')
        if not units[result[0]['unit']]['text'].startswith('wurden. Für die Zwecke'):
            raise ValueError('United States definition boundary changed')
    return result


def prior_readings(clauses):
    rows = [node for node in clauses if node['id'] in PRIOR_IDS]
    if [node['id'] for node in rows] != PRIOR_IDS:
        raise ValueError('All nine prior BASF readings must survive in order')
    return rows


def prepare(graph, construction, assembly, request, packet):
    prior = prior_readings(request['clauses'])
    references = request['reference_admission']['references']
    if (packet.get('version') != 'basf-global-exchange-review.v1' or
            packet.get('graph_sha256') != digest(graph) or
            packet.get('construction_sha256') != digest(construction) or
            packet.get('baseline_assembly_sha256') != digest(assembly) or
            packet.get('prior_clauses_sha256') != digest(prior) or
            packet.get('prior_references_sha256') != digest(references) or len(references) != 5):
        raise ValueError('BASF exchange baseline or prior meanings/references changed')
    review(packet['review'])
    raw = {unit['id']: unit for unit in graph['units']}
    authority = [anchor(raw[key]) for key in AUTHORITY_IDS]
    if packet.get('authority_sources') != authority or packet.get('context_sources') != [anchor(raw[key]) for key in CONTEXT_IDS]:
        raise ValueError('Exact form, currency, language and section 1(3)(a) context required')
    units = {unit['unit']: unit for unit in assembly['units']}
    expected_ids = [key for keys in PARAGRAPHS.values() for key in keys]
    if ([row['unit'] for row in packet['units']] != expected_ids or
            any(row['role'] != 'OPERATIVE' for row in packet['units'])):
        raise ValueError('Exchange dispositions must cover exactly the selected paragraph and definition')
    for row in packet['units']:
        whole = [{'unit': row['unit'], 'start': 0, 'end': len(units[row['unit']]['text'])}]
        if row['sources'] != [piece['source'] for piece in basf_agents.source_pieces(graph, units, whole)]:
            raise ValueError('Exchange disposition must bind exact surviving source pieces')
    clauses = packet['clauses']
    if [node['id'] for node in clauses] != list(PARAGRAPHS):
        raise ValueError('Complete exchange and geography readings required')
    for node in clauses:
        expected = spans(units, node['id'])
        if (node['units'] != PARAGRAPHS[node['id']] or node['spans'] != expected or
                node['quote'] != ' '.join(units[s['unit']]['text'][s['start']:s['end']] for s in expected) or
                node['source_uses'] != basf_agents.source_pieces(graph, units, expected) or
                node.get('selection_authority') != authority):
            raise ValueError('Exchange sentence or exact source/authority changed')
        if (node.get('global_reading') != READINGS[node['id']] or node['actor'] != 'issuer' or
                node['affected'] != 'holder' or node['role'] != 'OPERATIVE' or node['effect'] != 'none' or
                node.get('effect_scope') != ['Q1', 'Q2'] or node['questions'] != ['Q1', 'Q2'] or
                node['modality'] != 'statement' or node['election'] != 'none' or node['assets'] != [] or
                node['polarity'] is not True or node['conditions'] != [] or node['exceptions'] != [] or
                not node.get('effect_explanation')):
            raise ValueError('Reviewed exchange/certification or geography qualification changed')
    result = deepcopy(request)
    rows = {row['unit']: row for row in result['reviewed_dispositions']['units']}
    rows.update({row['unit']: row for row in packet['units']})
    result['reviewed_dispositions'].update(units=list(rows.values()), review=packet['review'])
    selected = dispositions(graph, assembly, result['reviewed_dispositions'])
    before = {unit['unit']: unit for unit in assembly['units']}
    after = {unit['unit']: unit for unit in selected['units']}
    if any(after[key] != before[key] for key in basf_agents.PROTECTED_IDS):
        raise ValueError('Exchange admission changed excluded branches or unresolved agent authority')
    result['reference_admission']['assembly_sha256'] = digest(selected)
    admit(graph, selected, result['reference_admission'])
    result['clauses'] = basf_notices.overlay(selected, prior + clauses)
    clause_graph.build(selected, result['clauses'])
    return result


def check_meanings(report, request, packet):
    actual = [node for node in report['clause_graph']['nodes'] if node['id'] in PARAGRAPHS]
    requested = [node for node in request['clauses'] if node['id'] in PARAGRAPHS]
    if (actual != packet['clauses'] or requested != packet['clauses'] or
            {node['id']: node['global_reading'] for node in actual} != READINGS):
        raise ValueError('Exchange/certification or geography changed between review, request and P3')
    if (digest(prior_readings(report['clause_graph']['nodes'])) != packet['prior_clauses_sha256'] or
            digest(prior_readings(request['clauses'])) != packet['prior_clauses_sha256'] or
            digest(request['reference_admission']['references']) != packet['prior_references_sha256']):
        raise ValueError('Prior BASF readings or references changed downstream')
    if report.get('independent_legal_acceptance') is not False:
        raise ValueError('Exchange development review cannot establish independent acceptance')
    return {'paragraphs': list(PARAGRAPHS), 'meanings_sha256': digest(actual),
            'reviewed_units': sum(map(len, PARAGRAPHS.values())),
            'prior_meanings_sha256': packet['prior_clauses_sha256'],
            'actual_tax_eligibility': 'NOT_EVALUATED', 'actual_exchange_or_delivery': 'NOT_EVALUATED',
            'defines_us_person': False, 'geography_reference': 'us-definition'}


def omitted_clauses(assembly, request, identity):
    if identity not in PARAGRAPHS:
        raise ValueError('Unknown exchange meaning omission')
    retained = prior_readings(request['clauses']) + [node for node in request['clauses']
                if node['id'] in PARAGRAPHS and node['id'] != identity]
    return basf_notices.overlay(assembly, retained)


matched_omission = basf_notices.matched_omission
