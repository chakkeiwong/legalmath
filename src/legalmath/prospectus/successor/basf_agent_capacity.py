"""One source-reviewed BASF contractual capacity; no statutory-law adjudication."""
from copy import deepcopy

from . import basf, basf_agents, basf_notices, clause_graph
from .admissions import dispositions, review
from .contracts import digest
from .occurrences import anchor
from .reviewed_references import admit

IDENTITY = 'basf-agents:contractual-capacity'
UNITS = basf_notices.lines(124, 72, 75)
PRIOR_IDS = [*basf_notices.PARAGRAPHS, *basf_agents.AGENT_PARAGRAPHS]
READING = {
    'reading': 'The Fiscal Agent, Paying Agent and the Calculation Agent retained in the selected wording act exclusively as agents assisting the issuer in performance. Under this contractual paragraph they assume no obligations toward holders, and no mandate or trust relationship between these agents and holders is created.',
    'agents': ['Fiscal Agent', 'Paying Agent', 'Calculation Agent'],
    'contractual_principal': 'issuer',
    'relationship_counterparty': 'holder',
    'exclusive_issuer_capacity': True,
    'holder_contractual_obligations_assumed': False,
    'holder_mandate_created': False,
    'holder_trust_created': False,
    'scope': 'THIS_CONTRACTUAL_PARAGRAPH',
    'statutory_duties': 'NOT_EVALUATED',
    'actual_agency_breach': 'NOT_EVALUATED',
    'notice_duties_preserved': True,
    'calculation_agent_office': 'UNRESOLVED',
    'qualification': 'The frozen construction retains calculation-agent wording. B54 name/office authority remains unresolved. This paragraph supplies a contractual allocation of roles; duties imposed by applicable law and actual disputes are not evaluated. The separate holder-notice and agent-change notice requirements remain operative; receiving a holder notice does not itself create a holder mandate.',
}


def spans(units):
    return [{'unit': key, 'start': 0, 'end': len(units[key]['text'])} for key in UNITS]


def prior_readings(clauses):
    rows = [node for node in clauses if node['id'] in PRIOR_IDS]
    if [node['id'] for node in rows] != PRIOR_IDS:
        raise ValueError('All eight prior notice and agent readings must survive in order')
    return rows


def prepare(graph, construction, assembly, request, packet):
    prior = prior_readings(request['clauses'])
    references = request['reference_admission']['references']
    if (packet.get('version') != 'basf-agent-capacity-review.v1' or
            packet.get('graph_sha256') != digest(graph) or
            packet.get('construction_sha256') != digest(construction) or
            packet.get('baseline_assembly_sha256') != digest(assembly) or
            packet.get('prior_clauses_sha256') != digest(prior) or
            packet.get('prior_references_sha256') != digest(references) or
            len(references) != 5):
        raise ValueError('BASF capacity baseline or prior meanings/references changed')
    review(packet['review'])
    raw = {unit['id']: unit for unit in graph['units']}
    authority = [anchor(raw[key]) for key in basf_agents.AUTHORITY_IDS]
    if packet.get('authority_sources') != authority:
        raise ValueError('Exact final-term agent role labels and names required')
    units = {unit['unit']: unit for unit in assembly['units']}
    expected = spans(units)
    rows = packet['units']
    if ([row['unit'] for row in rows] != UNITS or
            any(row['role'] != 'OPERATIVE' for row in rows)):
        raise ValueError('Capacity dispositions must cover exactly the four selected units')
    for row, span in zip(rows, expected):
        sources = [piece['source'] for piece in basf_agents.source_pieces(graph, units, [span])]
        if row['sources'] != sources:
            raise ValueError('Capacity disposition must bind exact surviving source pieces')
    clauses = packet['clauses']
    if len(clauses) != 1 or clauses[0]['id'] != IDENTITY:
        raise ValueError('One complete contractual-capacity reading required')
    node = clauses[0]
    if (node['units'] != UNITS or node['spans'] != expected or
            node['quote'] != ' '.join(units[key]['text'] for key in UNITS) or
            node['source_uses'] != basf_agents.source_pieces(graph, units, expected) or
            node.get('selection_authority') != authority):
        raise ValueError('Capacity sentence or exact source/authority changed')
    if (node.get('capacity_reading') != READING or node['actor'] != 'agent' or
            node['affected'] != 'holder' or node['role'] != 'OPERATIVE' or
            node['effect'] != 'none' or node.get('effect_scope') != ['Q1', 'Q2'] or
            node['questions'] != ['Q1', 'Q2'] or node['modality'] != 'statement' or
            node['election'] != 'none' or node['assets'] != [] or
            node['polarity'] is not True or node['conditions'] != [] or
            node['exceptions'] != [] or not node.get('effect_explanation')):
        raise ValueError('Reviewed contractual capacity, actor or legal qualification changed')
    result = deepcopy(request)
    selected_rows = {row['unit']: row for row in result['reviewed_dispositions']['units']}
    selected_rows.update({row['unit']: row for row in rows})
    result['reviewed_dispositions'].update(units=list(selected_rows.values()), review=packet['review'])
    selected = dispositions(graph, assembly, result['reviewed_dispositions'])
    protected = next(unit for unit in selected['units'] if unit['unit'] == basf.KEY + ':p124:l44')
    if protected['text'] != basf_agents.PLACEHOLDER or protected['role'] != 'UNKNOWN':
        raise ValueError('Capacity admission changed unresolved B54 authority')
    result['reference_admission'].update(assembly_sha256=digest(selected))
    admit(graph, selected, result['reference_admission'])
    result['clauses'] = basf_notices.overlay(selected, prior + clauses)
    clause_graph.build(selected, result['clauses'])
    if prior_readings(result['clauses']) != prior or result['reference_admission']['references'] != references:
        raise ValueError('Capacity composition changed earlier meanings or notice dependencies')
    return result


def check_meanings(report, request, packet):
    actual = [node for node in report['clause_graph']['nodes'] if node['id'] == IDENTITY]
    requested = [node for node in request['clauses'] if node['id'] == IDENTITY]
    if actual != packet['clauses'] or requested != packet['clauses'] or actual[0]['capacity_reading'] != READING:
        raise ValueError('Contractual capacity changed or was lost between review, request and P3')
    if (digest(prior_readings(report['clause_graph']['nodes'])) != packet['prior_clauses_sha256'] or
            digest(prior_readings(request['clauses'])) != packet['prior_clauses_sha256'] or
            digest(request['reference_admission']['references']) != packet['prior_references_sha256']):
        raise ValueError('Prior notice/agent meanings or reference identities changed downstream')
    protected = next(unit for unit in report['assembly']['units'] if unit['unit'] == basf.KEY + ':p124:l44')
    if (protected['text'] != basf_agents.PLACEHOLDER or protected['role'] != 'UNKNOWN' or
            report.get('independent_legal_acceptance') is not False):
        raise ValueError('Capacity reading promoted unresolved authority or independent acceptance')
    return {'paragraphs': [IDENTITY], 'meanings_sha256': digest(actual),
            'reviewed_units': len(UNITS), 'prior_meanings_sha256': packet['prior_clauses_sha256'],
            'statutory_duties': 'NOT_EVALUATED', 'actual_agency_breach': 'NOT_EVALUATED',
            'holder_mandate_created': False, 'holder_trust_created': False,
            'notice_duties_preserved': True, 'calculation_agent_office': 'UNRESOLVED'}


def omitted_clauses(assembly, request):
    return basf_notices.overlay(assembly, prior_readings(request['clauses']))


matched_omission = basf_notices.matched_omission
