"""Real German paragraphs, exact-use failures and matched P3 meaning omission."""
from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.prospectus.successor import basf, basf_notices, jobs, service, source_graph
from legalmath.prospectus.successor.contracts import digest, read
from scripts.prospectus_closure_basf import prepared_request as scalar_request
from scripts.prospectus_closure_basf_notices import REL, check_report


@pytest.fixture(scope='module')
def case():
    root = Path(__file__).resolve().parents[2]
    graph = source_graph.build(jobs.basf_request(root)['bundle'], root)
    construction = basf.construct(graph, read(root/jobs.BASF))
    request = scalar_request(root, graph)
    assembly = basf.as_assembly(graph, construction, request['construction']['scalar_admission'])
    packet = read(root/REL/'review.json')
    return root, graph, construction, assembly, request, packet


@pytest.fixture(scope='module')
def products(case):
    root, graph, construction, assembly, request, packet = case
    request = basf_notices.prepare(graph, construction, assembly, request, packet)
    p1 = service.seal('P1', request['bundle'], {'request': digest(request)}, {'request': request, 'graph': graph})
    p2 = service.construction_product(p1, root)
    p3 = service.interpretation_product(p1, p2)
    return request, p1, p2, p3


def test_basf_notices_actual_p3_and_exact_omission(case, products):
    root, graph, construction, _, _, packet = case
    request, p1, p2, p3 = products
    output = p3['payload']
    report = {'source_map': graph, 'selected_contract': construction, 'assembly': p2['payload']['assembly'],
              'clause_graph': output['clauses'], 'questions': output['questions'],
              'dependencies': output['dependencies'], 'mode': 'ASSISTED', 'independent_legal_acceptance': False}
    result = check_report(report, request, packet)
    assert result['reviewed_references'] == 4
    assert result['target_occurrences'] == [34, 30, 4, 15]
    assert result['mapped_scalar_operations'] == 6
    assert result['notices']['reviewed_units'] == 45
    omitted = service.interpretation_product(p1, p2, {'clauses': None})['payload']
    matched = basf_notices.matched_omission(report['assembly'], output['clauses'], omitted['clauses'], packet['clauses'])
    assert matched['unknown_with_reading'] == 0
    assert matched['unknown_without_reading'] > 0
    assert matched['outside_unknown_characters_equal']
    assert [omitted['questions'][q]['status'] for q in ('Q1', 'Q2', 'Q3')] == ['UNKNOWN', 'UNKNOWN', 'PARTIAL']
    proof = next(n for n in output['clauses']['nodes'] if n['id'] == 'basf-notices:holding-proof')
    assert proof['procedural_reading']['exclusive_route'] is False
    assert 'prozessual zulässig ist.' in proof['quote']
    assert proof['units'][-1] == basf.KEY + ':p133:l10'
    assert p2['payload']['selected_contract'] == read(root/'docs/implementation/prospectus-adoption/phases/A1/attempt-008/product.json')


@pytest.mark.parametrize('change', ['stale_graph', 'changed_construction', 'stale_assembly', 'wrong_edition',
    'wrong_occurrence', 'excluded_unlisted', 'omitted_target', 'partial_target', 'omitted_ending',
    'omitted_alternative', 'exclusive_proof', 'missing_exchange_permission', 'duplicate_paragraph',
    'changed_quote', 'wrong_scope', 'duplicate_disposition'])
def test_basf_notices_reject_invalid_packet(case, change):
    _, graph, construction, assembly, request, packet = case
    packet = deepcopy(packet)
    if change == 'stale_graph': packet['graph_sha256'] = '0'*64
    elif change == 'changed_construction': packet['construction_sha256'] = '0'*64
    elif change == 'stale_assembly': packet['baseline_assembly_sha256'] = '0'*64
    elif change == 'wrong_edition': packet['clauses'][0]['source_uses'][0]['source']['source_sha256'] = '0'*64
    elif change == 'wrong_occurrence': packet['clauses'][0]['source_uses'][0]['use'] = basf.KEY + ':p132:l21'
    elif change == 'excluded_unlisted':
        packet['units'].append({**packet['units'][0], 'unit': basf.KEY + ':p132:l30'})
    elif change == 'omitted_target': packet['references'][0]['targets'].pop()
    elif change == 'partial_target':
        source = packet['references'][0]['targets'][-1]['source']
        source['end'] -= 1
        source['quote'] = source['quote'][:-1]
    elif change == 'omitted_ending':
        packet['clauses'][-1]['spans'].pop()
        packet['clauses'][-1]['units'].pop()
    elif change == 'omitted_alternative': del packet['clauses'][-1]['procedural_reading']['alternative_route']
    elif change == 'exclusive_proof': packet['clauses'][-1]['procedural_reading']['exclusive_route'] = True
    elif change == 'missing_exchange_permission': packet['clauses'][1]['procedural_reading']['substitution_requires_exchange_rules_permission'] = False
    elif change == 'duplicate_paragraph': packet['clauses'].append(deepcopy(packet['clauses'][0]))
    elif change == 'changed_quote': packet['clauses'][0]['quote'] += ' not present'
    elif change == 'wrong_scope': packet['clauses'][0]['effect_scope'] = ['ALL_LEGAL_EFFECTS']
    elif change == 'duplicate_disposition': packet['units'].append(deepcopy(packet['units'][0]))
    with pytest.raises(ValueError):
        basf_notices.prepare(graph, construction, assembly, request, packet)


@pytest.mark.parametrize('change', ['missing_qualification', 'exclusive_route', 'missing_paragraph', 'acceptance'])
def test_basf_notices_downstream_loss_is_detected(case, products, change):
    request, _, _, p3 = products
    graph = deepcopy(p3['payload']['clauses'])
    proof = next(n for n in graph['nodes'] if n['id'] == 'basf-notices:holding-proof')
    report = {'clause_graph': graph, 'independent_legal_acceptance': False}
    if change == 'missing_qualification': del proof['procedural_reading']['alternative_route']
    elif change == 'exclusive_route': proof['procedural_reading']['exclusive_route'] = True
    elif change == 'missing_paragraph': graph['nodes'].remove(proof)
    elif change == 'acceptance': report['independent_legal_acceptance'] = True
    with pytest.raises(ValueError):
        basf_notices.check_meanings(report, request, case[-1]['clauses'])
