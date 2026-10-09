"""Exact selected BASF agent readings; supplied premises, not adjudication."""
from copy import deepcopy
from . import basf, basf_notices, clause_graph
from .admissions import dispositions, review
from .contracts import digest
from .occurrences import anchor, segments
from .reviewed_references import admit

lines = basf_notices.lines
AGENT_PARAGRAPHS = {
    'basf-agents:initial-agent': lines(124, 8, 14),
    'basf-agents:office-replacement': lines(124, 45, 47),
    'basf-agents:appointment-change': lines(124, 48, 52) + lines(124, 63, 64),
    'basf-agents:effectiveness-reference': lines(124, 64, 68),
}
AUTHORITY_IDS = [f'basf-2032-final:p7:l{i}' for i in range(22, 30)]
PROTECTED_IDS = lines(124, 22, 44) + lines(124, 53, 62)
PLACEHOLDER = '[Name und bezeichnete Geschäftsstelle]'


def paragraph_spans(units, identity):
    """Retain complete sentences across construction edits and PDF line breaks."""
    spans = [{'unit': key, 'start': 0, 'end': len(units[key]['text'])}
             for key in AGENT_PARAGRAPHS[identity]]
    split = units[basf.KEY + ':p124:l64']['text'].index('Eine Änderung')
    if identity.endswith('appointment-change'):
        spans[-1]['end'] = split
    elif identity.endswith('effectiveness-reference'):
        spans[0]['start'] = split
        spans[-1]['end'] = len('wurden.')
    return spans


def source_pieces(graph, units, spans):
    """Clip already validated raw/output copies to the reviewed sentence."""
    result = []
    for span in spans:
        for piece in segments(graph, units[span['unit']]):
            a, b = max(span['start'], piece['start']), min(span['end'], piece['end'])
            if a < b:
                source = deepcopy(piece['source'])
                offset = a - piece['start']
                source.update(start=source['start'] + offset, end=source['start'] + offset + b - a,
                              quote=source['quote'][offset:offset + b - a])
                result.append({'source': source, 'use': span['unit']})
    return result


def prepare(graph, construction, assembly, request, packet):
    if (packet.get('version') != 'basf-agents-review.v1' or
            packet.get('graph_sha256') != digest(graph) or
            packet.get('construction_sha256') != digest(construction) or
            packet.get('baseline_assembly_sha256') != digest(assembly) or
            packet.get('notice_clauses_sha256') != digest(
                [n for n in request.get('clauses', []) if n['id'] in basf_notices.PARAGRAPHS])):
        raise ValueError('BASF agent packet baseline changed')
    review(packet['review'])
    raw = {u['id']: u for u in graph['units']}
    if packet['authority_sources'] != [anchor(raw[key]) for key in AUTHORITY_IDS]:
        raise ValueError('Exact final-term agent labels and names required')
    before = {u['unit']: u for u in assembly['units']}
    expected_ids = list(dict.fromkeys(key for keys in AGENT_PARAGRAPHS.values() for key in keys))
    if ([u['unit'] for u in packet['units']] != expected_ids or
            any(u['role'] != 'OPERATIVE' for u in packet['units'])):
        raise ValueError('Agent dispositions must cover only reviewed selected units')
    result = deepcopy(request)
    rows = {row['unit']: row for row in result['reviewed_dispositions']['units']}
    rows.update({row['unit']: row for row in packet['units']})
    result['reviewed_dispositions'].update(units=list(rows.values()), review=packet['review'])
    selected = dispositions(graph, assembly, result['reviewed_dispositions'])
    units = {u['unit']: u for u in selected['units']}
    if (units[basf.KEY + ':p124:l44']['text'] != PLACEHOLDER or
            any(units[key] != before[key] for key in PROTECTED_IDS)):
        raise ValueError('Agent reading changed protected branch or unresolved placeholder')
    clauses = packet['clauses']
    if [c['id'] for c in clauses] != list(AGENT_PARAGRAPHS):
        raise ValueError('Four complete unique BASF agent readings required')
    for node in clauses:
        expected = paragraph_spans(units, node['id'])
        if (node['units'] != AGENT_PARAGRAPHS[node['id']] or node['spans'] != expected or
                node.get('effect_scope') != ['Q1', 'Q2'] or node['effect'] != 'none' or
                node['role'] != 'OPERATIVE' or not node.get('effect_explanation')):
            raise ValueError('Incomplete agent sentence or changed effect scope')
        if node['source_uses'] != source_pieces(graph, units, expected):
            raise ValueError('Agent sources omit or change exact selected characters')
        meaning = node.get('agent_reading', {})
        if not meaning.get('reading') or not meaning.get('qualification'):
            raise ValueError('Positive agent reading and qualification required')
    initial, office, appointment, effective = [c['agent_reading'] for c in clauses]
    if (initial.get('fiscal_and_paying_agent') != 'Deutsche Bank Aktiengesellschaft' or
            initial.get('final_term_calculation_agent') != 'NatWest Markets N.V.' or
            initial.get('calculation_agent_office') != 'UNRESOLVED' or
            clauses[0].get('selection_authority') != packet['authority_sources'] or
            office.get('same_country') is not True or
            appointment.get('maintain_fiscal_agent') is not True or
            appointment.get('maintain_calculation_agent_if_selected') is not True or
            appointment.get('calculation_agent_condition') != 'if a Calculation Agent is to be appointed' or
            effective.get('notice_window_days') != [30, 45] or
            effective.get('insolvency_immediate_effect') is not True or
            effective.get('notice_reference') != 'agent-change-notices' or
            effective.get('actual_change_validity') != 'NOT_EVALUATED'):
        raise ValueError('Agent identity, condition or effectiveness qualification missing')
    references = packet['references']
    expected_source = anchor(raw[basf.KEY + ':p124:l66'], 67, 71)
    if (len(references) != 1 or references[0]['id'] != 'agent-change-notices' or
            references[0]['form'] != 'relative' or references[0]['source'] != expected_source or
            references[0]['authority'] != expected_source or
            references[0]['from_use'] != basf.KEY + ':p124:l66' or
            references[0]['discovery_ids'] != [basf.KEY + ':p124:l66:ref:67'] or
            references[0]['targets'] != request['reference_admission']['references'][-1]['targets']):
        raise ValueError('Exact §13 agent-change reference and complete notice target required')
    result['reference_admission'].update(assembly_sha256=digest(selected))
    result['reference_admission']['references'].extend(deepcopy(references))
    admit(graph, selected, result['reference_admission'])
    notice_clauses = [n for n in request['clauses'] if n['id'] in basf_notices.PARAGRAPHS]
    result['clauses'] = basf_notices.overlay(selected, notice_clauses + clauses)
    clause_graph.build(selected, result['clauses'])
    return result


def check_meanings(report, request, expected_clauses):
    actual = [n for n in report['clause_graph']['nodes'] if n['id'] in AGENT_PARAGRAPHS]
    requested = [n for n in request['clauses'] if n['id'] in AGENT_PARAGRAPHS]
    if actual != expected_clauses or requested != expected_clauses:
        raise ValueError('BASF agent reading changed between review, request and P3')
    units = {u['unit']: u for u in report['assembly']['units']}
    if (report.get('independent_legal_acceptance') is not False or
            units[basf.KEY + ':p124:l44']['text'] != PLACEHOLDER or
            units[basf.KEY + ':p124:l44']['role'] != 'UNKNOWN'):
        raise ValueError('Unresolved agent authority or independent acceptance was promoted')
    return {'paragraphs': [n['id'] for n in actual], 'meanings_sha256': digest(actual),
            'reviewed_units': len({u for n in actual for u in n['units']}),
            'agent_change_decision': 'NOT_EVALUATED', 'calculation_agent_office': 'UNRESOLVED'}


def omitted_clauses(assembly, request):
    return basf_notices.overlay(assembly, [n for n in request['clauses'] if n['id'] in basf_notices.PARAGRAPHS])


matched_omission = basf_notices.matched_omission
