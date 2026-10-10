"""Real selected BASF exchange requirements and adverse source/meaning controls."""
from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.prospectus.successor import basf, basf_global_exchange as exchange, jobs, service, source_graph
from legalmath.prospectus.successor.contracts import digest, read
from legalmath.prospectus.successor.occurrences import anchor
from scripts.prospectus_closure_basf_agent_capacity import prepared_request as capacity_request
from scripts.prospectus_closure_basf_global_exchange import REL, check_report


@pytest.fixture(scope='module')
def case():
    root = Path(__file__).resolve().parents[2]
    graph = source_graph.build(jobs.basf_request(root)['bundle'], root)
    construction = basf.construct(graph, read(root / jobs.BASF))
    previous = capacity_request(root, graph)
    assembly = basf.as_assembly(graph, construction, previous['construction']['scalar_admission'])
    return root, graph, construction, assembly, previous, read(root / REL / 'review.json')


@pytest.fixture(scope='module')
def products(case):
    root, graph, construction, assembly, previous, packet = case
    request = exchange.prepare(graph, construction, assembly, previous, packet)
    p1 = service.seal('P1', request['bundle'], {'request': digest(request)}, {'request': request, 'graph': graph})
    p2 = service.construction_product(p1, root)
    return request, p1, p2, service.interpretation_product(p1, p2)


def report_for(case, products):
    request, _, p2, p3 = products
    return {'source_map': case[1], 'selected_contract': case[2], 'assembly': p2['payload']['assembly'],
            'clause_graph': p3['payload']['clauses'], 'questions': p3['payload']['questions'],
            'dependencies': p3['payload']['dependencies'], 'mode': 'ASSISTED', 'independent_legal_acceptance': False}


def test_basf_global_actual_p3_and_each_exact_matched_omission(case, products):
    request, p1, p2, p3 = products
    report = report_for(case, products)
    outcome = check_report(report, request, case[-1])
    assert outcome['reviewed_references'] == 5
    assert outcome['target_occurrences'] == [34, 30, 4, 15, 15]
    assert outcome['mapped_scalar_operations'] == 6
    assert outcome['retained_markers'] == 15 and outcome['unresolved_intervals'] == 537
    assert outcome['global_exchange']['actual_tax_eligibility'] == 'NOT_EVALUATED'
    assert p2['payload']['selected_contract'] == read(case[0] / 'docs/implementation/prospectus-adoption/phases/A1/attempt-008/product.json')
    assert request['reference_admission']['references'] == case[-2]['reference_admission']['references']
    nodes = {n['id']: n for n in report['clause_graph']['nodes']}
    actual = nodes[exchange.EXCHANGE]
    meaning = actual['global_reading']
    assert meaning['earliest_exchange_days_after_issue'] == 40
    assert meaning['earliest_exchange_comparison'] == 'AT_LEAST'
    assert meaning['certificate_receipt_comparison'] == 'ON_OR_AFTER'
    assert len(meaning['express_exceptions']) == 2
    assert meaning['separate_certificate_each_interest_payment'] is True
    assert 'nur außerhalb' in actual['quote'] and actual['quote'].endswith('geliefert werden.')
    assert nodes[exchange.GEOGRAPHY]['quote'].startswith('Für die Zwecke')
    assert nodes[exchange.GEOGRAPHY]['quote'].endswith('Northern Mariana Islands).')
    assert nodes[exchange.GEOGRAPHY]['spans'][0]['start'] == 8
    assert nodes['basf-agents:effectiveness-reference']['quote'].endswith('wurden.')
    assert len(nodes[exchange.GEOGRAPHY]['global_reading']['territory_examples']) == 6
    assert nodes[exchange.GEOGRAPHY]['global_reading']['territory_list_exhaustive'] is False
    assert nodes[exchange.GEOGRAPHY]['global_reading']['defines_us_person'] is False
    for node in case[-1]['clauses']:
        omitted = service.interpretation_product(p1, p2, {'clauses': exchange.omitted_clauses(report['assembly'], request, node['id'])})['payload']
        matched = exchange.matched_omission(report['assembly'], report['clause_graph'], omitted['clauses'], [node])
        assert matched['unknown_with_reading'] == 0
        assert matched['unknown_without_reading'] == matched['reviewed_nonspace_characters'] > 0
        assert matched['outside_unknown_characters_equal']
        retained = set(exchange.PRIOR_IDS) | (set(exchange.PARAGRAPHS) - {node['id']})
        assert [n for n in omitted['clauses']['nodes'] if n['id'] in retained] == [n for n in report['clause_graph']['nodes'] if n['id'] in retained]
        assert [omitted['questions'][q]['status'] for q in ('Q1', 'Q2', 'Q3')] == ['UNKNOWN', 'UNKNOWN', 'PARTIAL']


@pytest.mark.parametrize('change', [
    'stale_graph', 'changed_construction', 'stale_assembly', 'stale_prior_meanings', 'stale_prior_references',
    'wrong_authority', 'missing_form', 'missing_context', 'raw_bracket', 'wrong_occurrence', 'wrong_edition',
    'missing_source_piece', 'truncated_delivery', 'truncated_territory', 'overlap_agent_sentence', 'overlap_capacity',
    'changed_quote', 'extra_us_agent_branch', 'duplicate_disposition', 'before_day_40', 'strict_day_40',
    'no_certificate', 'lost_exception', 'lost_interest_certificate', 'lost_per_payment', 'request_before_day_40',
    'automatic_exchange', 'inside_delivery', 'tax_clearance', 'territory_is_person', 'exhaustive_territories',
    'contradictory_prose', 'lost_qualification', 'lost_prior', 'changed_prior_reference', 'wrong_effect_scope',
])
def test_basf_global_rejects_incomplete_or_overbroad_reading(case, change):
    _, graph, construction, assembly, previous, original = case
    packet = deepcopy(original)
    node, geo = packet['clauses']
    meaning = node['global_reading']
    hashes = {'stale_graph': 'graph_sha256', 'changed_construction': 'construction_sha256',
              'stale_assembly': 'baseline_assembly_sha256', 'stale_prior_meanings': 'prior_clauses_sha256',
              'stale_prior_references': 'prior_references_sha256'}
    if change in hashes: packet[hashes[change]] = '0' * 64
    elif change == 'wrong_authority': packet['authority_sources'][0]['quote'] = 'Another form'
    elif change == 'missing_form': packet['authority_sources'].pop()
    elif change == 'missing_context': packet['context_sources'].pop()
    elif change == 'raw_bracket':
        packet['units'][22]['sources'] = [anchor(next(u for u in graph['units'] if u['id'] == basf.KEY + ':p108:l81'))]
    elif change == 'wrong_occurrence': node['source_uses'][0]['use'] = basf.KEY + ':p108:l60'
    elif change == 'wrong_edition': node['source_uses'][0]['source']['source_sha256'] = '0' * 64
    elif change == 'missing_source_piece': node['source_uses'].pop()
    elif change == 'truncated_delivery': node['spans'] = node['spans'][:-2]
    elif change == 'truncated_territory': geo['spans'][-1]['end'] -= 25
    elif change == 'overlap_agent_sentence': geo['spans'][0]['start'] = 0
    elif change == 'overlap_capacity': geo['units'].append(basf.KEY + ':p124:l72')
    elif change == 'changed_quote': node['quote'] = node['quote'].replace('frühestens', 'spätestens')
    elif change in {'extra_us_agent_branch', 'duplicate_disposition'}:
        row = deepcopy(packet['units'][0])
        if change == 'extra_us_agent_branch': row['unit'] = basf.KEY + ':p124:l53'
        packet['units'].append(row)
    elif change == 'before_day_40': meaning['earliest_exchange_comparison'] = 'BEFORE'
    elif change == 'strict_day_40': meaning['earliest_exchange_comparison'] = 'AFTER'
    elif change == 'no_certificate': meaning['exchange_requires_certificate'] = False
    elif change == 'lost_exception': meaning['express_exceptions'].pop()
    elif change == 'lost_interest_certificate': meaning['interest_requires_prior_certificate'] = False
    elif change == 'lost_per_payment': meaning['separate_certificate_each_interest_payment'] = False
    elif change == 'request_before_day_40': meaning['certificate_receipt_comparison'] = 'BEFORE'
    elif change == 'automatic_exchange': meaning['certificate_is_request_not_completed_exchange'] = False
    elif change == 'inside_delivery': meaning['delivery_only_outside_contractual_united_states'] = False
    elif change == 'tax_clearance': meaning['actual_tax_eligibility'] = 'ELIGIBLE'
    elif change == 'territory_is_person': geo['global_reading']['defines_us_person'] = True
    elif change == 'exhaustive_territories': geo['global_reading']['territory_list_exhaustive'] = True
    elif change == 'contradictory_prose': meaning['reading'] += ' No certificates are required.'
    elif change == 'lost_qualification': del meaning['qualification']
    elif change == 'lost_prior': previous = {**previous, 'clauses': [n for n in previous['clauses'] if n['id'] != 'basf-agents:contractual-capacity']}
    elif change == 'changed_prior_reference':
        previous = {**previous, 'reference_admission': deepcopy(previous['reference_admission'])}
        previous['reference_admission']['references'][2]['targets'].pop()
    elif change == 'wrong_effect_scope': node['effect_scope'] = ['ALL']
    with pytest.raises(ValueError):
        exchange.prepare(graph, construction, assembly, previous, packet)


def test_basf_global_governing_target_loss_rejects_p3(case, products):
    request, p1, p2, _ = products
    payload = deepcopy(p2['payload'])
    target = basf.KEY + ':p124:l71'
    next(u for u in payload['assembly']['units'] if u['unit'] == target)['role'] = 'UNKNOWN'
    changed = service.seal('P2', request['bundle'], {'P1': p1['sha256']}, payload)
    reference = deepcopy(request['reference_admission'])
    reference['assembly_sha256'] = digest(payload['assembly'])
    with pytest.raises(ValueError, match='cannot become an operative assertion'):
        service.interpretation_product(p1, changed, {'reference_admission': reference})
    # Omit only the unsupported geography meaning to reach reference admission.
    # The exchange import and all nine previous readings must remain present.
    clauses = exchange.omitted_clauses(payload['assembly'], request, exchange.GEOGRAPHY)
    assert exchange.prior_readings(clauses) == exchange.prior_readings(request['clauses'])
    with pytest.raises(ValueError, match='not operative'):
        service.interpretation_product(p1, changed, {'reference_admission': reference, 'clauses': clauses})


@pytest.mark.parametrize('change', ['lost_exchange', 'lost_geography', 'lost_capacity', 'promoted_tax', 'changed_reference', 'acceptance'])
def test_basf_global_downstream_loss_or_promotion_rejects(case, products, change):
    request = products[0]
    report = {**report_for(case, products), 'clause_graph': deepcopy(products[3]['payload']['clauses'])}
    lost = {'lost_exchange': exchange.EXCHANGE, 'lost_geography': exchange.GEOGRAPHY, 'lost_capacity': 'basf-agents:contractual-capacity'}
    if change in lost: report['clause_graph']['nodes'] = [n for n in report['clause_graph']['nodes'] if n['id'] != lost[change]]
    elif change == 'promoted_tax': next(n for n in report['clause_graph']['nodes'] if n['id'] == exchange.EXCHANGE)['global_reading']['actual_tax_eligibility'] = 'ELIGIBLE'
    elif change == 'changed_reference':
        request = {**request, 'reference_admission': deepcopy(request['reference_admission'])}
        request['reference_admission']['references'][2]['targets'].pop()
    elif change == 'acceptance': report['independent_legal_acceptance'] = True
    with pytest.raises(ValueError):
        exchange.check_meanings(report, request, case[-1])
