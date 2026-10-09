"""Complete selected contractual capacity, prior notices, and adverse readings."""
from copy import deepcopy
from pathlib import Path

import pytest

from legalmath.prospectus.successor import basf, basf_agent_capacity, basf_agents, basf_notices, jobs, service, source_graph
from legalmath.prospectus.successor.contracts import digest, read
from scripts.prospectus_closure_basf_agent_notices import prepared_request as agent_request
from scripts.prospectus_closure_basf_agent_capacity import REL, check_report


@pytest.fixture(scope='module')
def case():
    root = Path(__file__).resolve().parents[2]
    graph = source_graph.build(jobs.basf_request(root)['bundle'], root)
    construction = basf.construct(graph, read(root / jobs.BASF))
    previous = agent_request(root, graph)
    assembly = basf.as_assembly(graph, construction, previous['construction']['scalar_admission'])
    return root, graph, construction, assembly, previous, read(root / REL / 'review.json')


@pytest.fixture(scope='module')
def products(case):
    root, graph, construction, assembly, previous, packet = case
    request = basf_agent_capacity.prepare(graph, construction, assembly, previous, packet)
    p1 = service.seal('P1', request['bundle'], {'request': digest(request)}, {'request': request, 'graph': graph})
    p2 = service.construction_product(p1, root)
    return request, p1, p2, service.interpretation_product(p1, p2)


def test_basf_capacity_actual_p3_and_exact_matched_omission(case, products):
    root, graph, construction, _, previous, packet = case
    request, p1, p2, p3 = products
    output = p3['payload']
    report = {'source_map': graph, 'selected_contract': construction, 'assembly': p2['payload']['assembly'],
              'clause_graph': output['clauses'], 'questions': output['questions'],
              'dependencies': output['dependencies'], 'mode': 'ASSISTED', 'independent_legal_acceptance': False}
    outcome = check_report(report, request, packet)
    assert outcome['reviewed_references'] == 5
    assert outcome['target_occurrences'] == [34, 30, 4, 15, 15]
    assert outcome['mapped_scalar_operations'] == 6
    assert outcome['retained_markers'] == 15
    assert outcome['unresolved_intervals'] == 537
    assert outcome['capacity']['statutory_duties'] == 'NOT_EVALUATED'
    assert outcome['capacity']['notice_duties_preserved']
    assert request['reference_admission']['references'] == previous['reference_admission']['references']
    assert basf_agent_capacity.prior_readings(output['clauses']['nodes']) == basf_agent_capacity.prior_readings(previous['clauses'])
    assert p2['payload']['selected_contract'] == read(root / 'docs/implementation/prospectus-adoption/phases/A1/attempt-008/product.json')
    node = next(node for node in output['clauses']['nodes'] if node['id'] == basf_agent_capacity.IDENTITY)
    assert node['quote'].endswith('Auftrags- oder Treuhandverhältnis zwischen ihnen und den Gläubigern begründet.')
    assert node['capacity_reading'] == basf_agent_capacity.READING
    assert len(node['source_uses']) > len(node['spans'])  # edited raw brackets require split pieces
    # Receiving a holder notice and lacking a holder mandate must coexist.
    holder = next(node for node in output['clauses']['nodes'] if node['id'] == 'basf-notices:holder-notice')
    change = next(node for node in output['clauses']['nodes'] if node['id'] == 'basf-agents:effectiveness-reference')
    assert holder['procedural_reading']['proof_reference'] == 'holder-notice-proof'
    assert change['agent_reading']['notice_reference'] == 'agent-change-notices'
    assert node['capacity_reading']['holder_mandate_created'] is False
    assert node['capacity_reading']['holder_trust_created'] is False
    omitted = service.interpretation_product(p1, p2, {
        'clauses': basf_agent_capacity.omitted_clauses(report['assembly'], request)})['payload']
    matched = basf_agent_capacity.matched_omission(report['assembly'], output['clauses'], omitted['clauses'], packet['clauses'])
    assert matched['unknown_with_reading'] == 0
    assert matched['unknown_without_reading'] == matched['reviewed_nonspace_characters'] > 0
    assert matched['outside_unknown_characters_equal']
    assert basf_agent_capacity.prior_readings(omitted['clauses']['nodes']) == basf_agent_capacity.prior_readings(output['clauses']['nodes'])
    assert [omitted['questions'][q]['status'] for q in ('Q1', 'Q2', 'Q3')] == ['UNKNOWN', 'UNKNOWN', 'PARTIAL']


@pytest.mark.parametrize('change', [
    'stale_graph', 'changed_construction', 'stale_assembly', 'stale_prior_meanings',
    'stale_prior_references', 'wrong_authority', 'missing_authority_label',
    'wrong_occurrence', 'wrong_edition', 'raw_line_instead_of_selected',
    'missing_source_piece', 'truncated_ending', 'changed_quote',
    'extra_disposition', 'duplicate_disposition', 'placeholder_admission',
    'issuer_actor', 'wrong_beneficiary', 'holder_principal', 'holder_mandate',
    'holder_trust', 'holder_obligation', 'statutory_immunity', 'contradictory_prose',
    'erased_notice_duties', 'unqualified_scope', 'missing_qualification',
    'filled_office', 'wrong_effect_scope', 'lost_prior_reading', 'changed_prior_reference',
])
def test_basf_capacity_rejects_incomplete_or_overbroad_reading(case, change):
    _, graph, construction, assembly, previous, original = case
    packet = deepcopy(original)
    node = packet['clauses'][0]
    meaning = node['capacity_reading']
    if change in {'stale_graph', 'changed_construction', 'stale_assembly', 'stale_prior_meanings', 'stale_prior_references'}:
        key = {'stale_graph': 'graph_sha256', 'changed_construction': 'construction_sha256',
               'stale_assembly': 'baseline_assembly_sha256', 'stale_prior_meanings': 'prior_clauses_sha256',
               'stale_prior_references': 'prior_references_sha256'}[change]
        packet[key] = '0' * 64
    elif change == 'wrong_authority': packet['authority_sources'][0]['quote'] = 'Another role'
    elif change == 'missing_authority_label': packet['authority_sources'].pop(0)
    elif change == 'wrong_occurrence': node['source_uses'][0]['use'] = basf.KEY + ':p124:l73'
    elif change == 'wrong_edition': node['source_uses'][0]['source']['source_sha256'] = '0' * 64
    elif change == 'raw_line_instead_of_selected':
        from legalmath.prospectus.successor.occurrences import anchor
        packet['units'][0]['sources'] = [anchor(next(unit for unit in graph['units'] if unit['id'] == basf.KEY + ':p124:l72'))]
    elif change == 'missing_source_piece': node['source_uses'].pop(1)
    elif change == 'truncated_ending': node['spans'][-1]['end'] -= len('begründet.')
    elif change == 'changed_quote': node['quote'] = node['quote'].replace('kein', 'ein')
    elif change in {'extra_disposition', 'duplicate_disposition', 'placeholder_admission'}:
        row = deepcopy(packet['units'][0])
        if change == 'extra_disposition': row['unit'] = basf.KEY + ':p124:l71'
        elif change == 'placeholder_admission': row['unit'] = basf.KEY + ':p124:l44'
        packet['units'].append(row)
    elif change == 'issuer_actor': node['actor'] = 'issuer'
    elif change == 'wrong_beneficiary': node['affected'] = 'issuer'
    elif change == 'holder_principal': meaning['contractual_principal'] = 'holder'
    elif change == 'holder_mandate': meaning['holder_mandate_created'] = True
    elif change == 'holder_trust': meaning['holder_trust_created'] = True
    elif change == 'holder_obligation': meaning['holder_contractual_obligations_assumed'] = True
    elif change == 'statutory_immunity': meaning['statutory_duties'] = 'NONE'
    elif change == 'contradictory_prose': meaning['reading'] += ' All agents are immune from every statutory duty.'
    elif change == 'erased_notice_duties': meaning['notice_duties_preserved'] = False
    elif change == 'unqualified_scope': meaning['scope'] = 'ALL_APPLICABLE_LAW'
    elif change == 'missing_qualification': del meaning['qualification']
    elif change == 'filled_office': meaning['calculation_agent_office'] = 'Frankfurt'
    elif change == 'wrong_effect_scope': node['effect_scope'] = ['ALL']
    elif change == 'lost_prior_reading':
        previous = {**previous, 'clauses': [node for node in previous['clauses'] if node['id'] != 'basf-notices:holder-notice']}
    elif change == 'changed_prior_reference':
        previous = {**previous, 'reference_admission': deepcopy(previous['reference_admission'])}
        previous['reference_admission']['references'][-1]['targets'].pop()
    with pytest.raises(ValueError):
        basf_agent_capacity.prepare(graph, construction, assembly, previous, packet)


@pytest.mark.parametrize('change', ['lost_capacity', 'lost_notice', 'lost_agent', 'promoted_immunity',
                                   'filled_placeholder', 'acceptance', 'changed_reference'])
def test_basf_capacity_rejects_downstream_loss_or_promotion(case, products, change):
    request, _, p2, p3 = products
    report = {'clause_graph': deepcopy(p3['payload']['clauses']), 'assembly': p2['payload']['assembly'],
              'independent_legal_acceptance': False}
    remove = {'lost_capacity': basf_agent_capacity.IDENTITY, 'lost_notice': 'basf-notices:holder-notice',
              'lost_agent': 'basf-agents:effectiveness-reference'}
    if change in remove:
        report['clause_graph']['nodes'] = [node for node in report['clause_graph']['nodes'] if node['id'] != remove[change]]
    elif change == 'promoted_immunity':
        next(node for node in report['clause_graph']['nodes'] if node['id'] == basf_agent_capacity.IDENTITY)['capacity_reading']['statutory_duties'] = 'NONE'
    elif change == 'filled_placeholder':
        report['assembly'] = deepcopy(report['assembly'])
        next(unit for unit in report['assembly']['units'] if unit['unit'] == basf.KEY + ':p124:l44')['text'] = 'NatWest, Frankfurt'
    elif change == 'acceptance': report['independent_legal_acceptance'] = True
    elif change == 'changed_reference':
        request = {**request, 'reference_admission': deepcopy(request['reference_admission'])}
        request['reference_admission']['references'][-1]['targets'].pop()
    with pytest.raises(ValueError):
        basf_agent_capacity.check_meanings(report, request, case[-1])
