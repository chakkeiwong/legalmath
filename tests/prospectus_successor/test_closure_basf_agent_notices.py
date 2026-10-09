"""Real selected sentences and failures at the BASF agent/notice boundary."""
from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.prospectus.successor import basf, basf_agents, basf_notices, jobs, service, source_graph
from legalmath.prospectus.successor.contracts import digest, read
from scripts.prospectus_closure_basf_notices import prepared_request as notice_request
from scripts.prospectus_closure_basf_agent_notices import REL, check_report


@pytest.fixture(scope='module')
def case():
    root = Path(__file__).resolve().parents[2]
    graph = source_graph.build(jobs.basf_request(root)['bundle'], root)
    construction = basf.construct(graph, read(root/jobs.BASF))
    request = notice_request(root, graph)
    assembly = basf.as_assembly(graph, construction, request['construction']['scalar_admission'])
    return root, graph, construction, assembly, request, read(root/REL/'review.json')


@pytest.fixture(scope='module')
def products(case):
    root, graph, construction, assembly, request, packet = case
    request = basf_agents.prepare(graph, construction, assembly, request, packet)
    p1 = service.seal('P1', request['bundle'], {'request': digest(request)}, {'request': request, 'graph': graph})
    p2 = service.construction_product(p1, root)
    p3 = service.interpretation_product(p1, p2)
    return request, p1, p2, p3


def test_basf_agents_actual_p3_preserves_notices_and_matched_effect(case, products):
    root, graph, construction, _, previous, packet = case
    request, p1, p2, p3 = products
    output = p3['payload']
    report = {'source_map': graph, 'selected_contract': construction, 'assembly': p2['payload']['assembly'],
              'clause_graph': output['clauses'], 'questions': output['questions'],
              'dependencies': output['dependencies'], 'mode': 'ASSISTED', 'independent_legal_acceptance': False}
    outcome = check_report(report, request, packet)
    assert outcome['reviewed_references'] == 5
    assert outcome['target_occurrences'] == [34, 30, 4, 15, 15]
    assert outcome['agents']['reviewed_units'] == 21
    assert outcome['notices']['reviewed_units'] == 45
    assert request['reference_admission']['references'][:-1] == previous['reference_admission']['references']
    notices = [n for n in output['clauses']['nodes'] if n['id'] in basf_notices.PARAGRAPHS]
    assert notices == [n for n in previous['clauses'] if n['id'] in basf_notices.PARAGRAPHS]
    assert packet['clauses'][-1]['quote'].endswith('wurden.')
    assert 'Für die Zwecke' not in packet['clauses'][-1]['quote']
    assert 'Berechnungsstelle unterhalten.' in packet['clauses'][2]['quote']
    assert p2['payload']['selected_contract'] == read(root/'docs/implementation/prospectus-adoption/phases/A1/attempt-008/product.json')
    units = {u['unit']: u for u in report['assembly']['units']}
    assert units[basf.KEY + ':p124:l44']['text'] == basf_agents.PLACEHOLDER
    assert units[basf.KEY + ':p124:l44']['role'] == 'UNKNOWN'
    assert all(units[key]['role'] == 'EXCLUDED' for key in basf_agents.lines(124, 22, 25) + basf_agents.lines(124, 53, 62))
    omitted = service.interpretation_product(p1, p2, {
        'clauses': basf_agents.omitted_clauses(report['assembly'], request)})['payload']
    matched = basf_agents.matched_omission(report['assembly'], output['clauses'], omitted['clauses'], packet['clauses'])
    assert matched['unknown_with_reading'] == 0
    assert matched['unknown_without_reading'] > 0
    assert matched['outside_unknown_characters_equal']
    assert [omitted['questions'][q]['status'] for q in ('Q1', 'Q2', 'Q3')] == ['UNKNOWN', 'UNKNOWN', 'PARTIAL']


@pytest.mark.parametrize('change', [
    'stale_graph', 'changed_construction', 'stale_assembly', 'prior_notice_loss',
    'wrong_edition', 'wrong_occurrence', 'wrong_authority', 'authority_label_missing',
    'canadian_admission', 'us_admission', 'placeholder_admission', 'duplicate_disposition',
    'missing_source_piece', 'raw_line_instead_of_selected', 'omitted_target', 'partial_target',
    'wrong_reference', 'missing_discovery', 'truncated_ending', 'missing_qualification',
    'missing_same_country', 'missing_maintenance', 'missing_calculation_condition',
    'missing_insolvency', 'changed_window', 'filled_office', 'changed_quote', 'wrong_scope',
])
def test_basf_agents_reject_incomplete_or_wrong_packet(case, change):
    _, graph, construction, assembly, request, packet = case
    packet = deepcopy(packet)
    if change == 'stale_graph': packet['graph_sha256'] = '0'*64
    elif change == 'changed_construction': packet['construction_sha256'] = '0'*64
    elif change == 'stale_assembly': packet['baseline_assembly_sha256'] = '0'*64
    elif change == 'prior_notice_loss': packet['notice_clauses_sha256'] = '0'*64
    elif change == 'wrong_edition': packet['clauses'][1]['source_uses'][0]['source']['source_sha256'] = '0'*64
    elif change == 'wrong_occurrence': packet['clauses'][1]['source_uses'][0]['use'] = basf.KEY + ':p124:l46'
    elif change == 'wrong_authority': packet['authority_sources'][-1]['quote'] = 'Another agent'
    elif change == 'authority_label_missing': packet['authority_sources'].pop(0)
    elif change in {'canadian_admission', 'us_admission', 'placeholder_admission'}:
        row = deepcopy(packet['units'][0])
        row['unit'] = basf.KEY + ':p124:l' + {'canadian_admission':'24','us_admission':'53','placeholder_admission':'44'}[change]
        packet['units'].append(row)
    elif change == 'duplicate_disposition': packet['units'].append(deepcopy(packet['units'][0]))
    elif change == 'missing_source_piece': packet['clauses'][1]['source_uses'].pop(1)
    elif change == 'raw_line_instead_of_selected':
        from legalmath.prospectus.successor.occurrences import anchor
        packet['units'][7]['sources'] = [anchor(next(u for u in graph['units'] if u['id'] == basf.KEY + ':p124:l45'))]
    elif change == 'omitted_target': packet['references'][0]['targets'].pop()
    elif change == 'partial_target':
        target = packet['references'][0]['targets'][-1]['source']
        target.update(end=target['end']-1, quote=target['quote'][:-1])
    elif change == 'wrong_reference': packet['references'][0]['from_use'] = basf.KEY + ':p121:l9'
    elif change == 'missing_discovery': packet['references'][0]['discovery_ids'] = []
    elif change == 'truncated_ending': packet['clauses'][-1]['spans'].pop()
    elif change == 'missing_qualification': del packet['clauses'][-1]['agent_reading']['qualification']
    elif change == 'missing_same_country': packet['clauses'][1]['agent_reading']['same_country'] = False
    elif change == 'missing_maintenance': packet['clauses'][2]['agent_reading']['maintain_fiscal_agent'] = False
    elif change == 'missing_calculation_condition': del packet['clauses'][2]['agent_reading']['calculation_agent_condition']
    elif change == 'missing_insolvency': packet['clauses'][-1]['agent_reading']['insolvency_immediate_effect'] = False
    elif change == 'changed_window': packet['clauses'][-1]['agent_reading']['notice_window_days'] = [30, 60]
    elif change == 'filled_office': packet['clauses'][0]['agent_reading']['calculation_agent_office'] = 'Frankfurt'
    elif change == 'changed_quote': packet['clauses'][-1]['quote'] += ' added'
    elif change == 'wrong_scope': packet['clauses'][-1]['effect_scope'] = ['ALL']
    with pytest.raises(ValueError):
        basf_agents.prepare(graph, construction, assembly, request, packet)


@pytest.mark.parametrize('change', ['lost_meaning', 'lost_notice', 'filled_placeholder', 'acceptance'])
def test_basf_agents_detect_downstream_loss(case, products, change):
    request, _, p2, p3 = products
    # Copy only the branches being mutated; the source graph is unchanged.
    report = {'clause_graph': deepcopy(p3['payload']['clauses']),
              'assembly': p2['payload']['assembly'], 'independent_legal_acceptance': False}
    if change == 'lost_meaning':
        report['clause_graph']['nodes'] = [n for n in report['clause_graph']['nodes'] if n['id'] != 'basf-agents:office-replacement']
    elif change == 'lost_notice':
        report['clause_graph']['nodes'] = [n for n in report['clause_graph']['nodes'] if n['id'] != 'basf-notices:holding-proof']
    elif change == 'filled_placeholder':
        report['assembly'] = deepcopy(report['assembly'])
        next(u for u in report['assembly']['units'] if u['unit'] == basf.KEY + ':p124:l44')['text'] = 'NatWest, Frankfurt'
    elif change == 'acceptance': report['independent_legal_acceptance'] = True
    with pytest.raises(ValueError):
        if change == 'lost_notice':
            basf_notices.check_meanings(report, request, read(case[0]/'docs/implementation/prospectus-integration-closure/basf-notices/review.json')['clauses'])
        else:
            basf_agents.check_meanings(report, request, case[-1]['clauses'])
