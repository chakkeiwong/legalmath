"""Complete German issuer covenant, real definition loss and wrong-option controls."""
from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.prospectus.successor import basf, basf_status_pledge as pledge, jobs, service, source_graph
from legalmath.prospectus.successor.contracts import digest, read
from scripts.prospectus_closure_basf_amount_holder import prepared_request as amount_request
from scripts.prospectus_closure_basf_status_pledge import REL, check_report, prepared_request


@pytest.fixture(scope='module')
def case():
    root = Path(__file__).resolve().parents[2]
    graph = source_graph.build(jobs.basf_request(root)['bundle'], root)
    construction = basf.construct(graph, read(root / jobs.BASF))
    previous = amount_request(root, graph)
    assembly = basf.as_assembly(graph, construction, previous['construction']['scalar_admission'])
    return root, graph, construction, assembly, previous, read(root / REL / 'review.json')


@pytest.fixture(scope='module')
def products(case):
    root, graph, construction, assembly, previous, packet = case
    request = pledge.prepare(graph, construction, assembly, previous, packet)
    p1 = service.seal('P1', request['bundle'], {'request': digest(request)}, {'request': request, 'graph': graph})
    p2 = service.construction_product(p1, root)
    return request, p1, p2, service.interpretation_product(p1, p2)


def report_for(case, products):
    _, _, p2, p3 = products
    return {'source_map': case[1], 'selected_contract': case[2], 'assembly': p2['payload']['assembly'],
            'clause_graph': p3['payload']['clauses'], 'questions': p3['payload']['questions'],
            'dependencies': p3['payload']['dependencies'], 'mode': 'ASSISTED', 'independent_legal_acceptance': False}


@pytest.fixture(scope='module')
def definition_omission(case, products):
    request, p1, p2, _ = products
    return service.interpretation_product(p1, p2, {
        'clauses': pledge.omitted_clauses(p2['payload']['assembly'], request, pledge.DEFINITION)})['payload']


def check_omission(case, products, identity, omitted):
    report = report_for(case, products)
    node = next(n for n in case[-1]['clauses'] if n['id'] == identity)
    matched = pledge.matched_omission(report['assembly'], report['clause_graph'], omitted['clauses'], [node])
    assert matched['unknown_with_reading'] == 0
    assert matched['unknown_without_reading'] == matched['reviewed_nonspace_characters'] > 0
    assert matched['outside_unknown_characters_equal']
    retained = set(pledge.PRIOR_IDS) | (set(pledge.PARAGRAPHS) - {identity})
    assert [n for n in omitted['clauses']['nodes'] if n['id'] in retained] == [n for n in report['clause_graph']['nodes'] if n['id'] in retained]
    assert [omitted['questions'][q]['status'] for q in ('Q1', 'Q2', 'Q3')] == ['UNKNOWN', 'UNKNOWN', 'PARTIAL']


def test_basf_pledge_p3_smoke_and_definition_omission(case, products, definition_omission):
    request, _, p2, _ = products
    report = report_for(case, products)
    outcome = check_report(report, request, case[-1])
    assert outcome['reviewed_references'] == 6
    assert outcome['target_occurrences'] == [34, 30, 4, 15, 15, 42]
    assert outcome['mapped_scalar_operations'] == 6
    assert outcome['retained_markers'] == 15 and outcome['unresolved_intervals'] == 537
    assert outcome['status_pledge']['reviewed_units'] == 32
    assert outcome['status_pledge']['definition_edge'] == pledge.definition_edge(True)
    assert p2['payload']['selected_contract'] == read(case[0] / 'docs/implementation/prospectus-adoption/phases/A1/attempt-008/product.json')
    assert request['reference_admission']['references'] == case[-2]['reference_admission']['references']
    nodes = {n['id']: n for n in report['clause_graph']['nodes']}
    assert nodes[pledge.STATUS]['quote'].endswith('Bestimmungen ein Vorrang eingeräumt wird.')
    assert nodes[pledge.PLEDGE]['quote'].endswith('teilnehmen zu lassen.')
    assert 'jedoch nur bis zu dem Zeitpunkt' in nodes[pledge.PLEDGE]['quote']
    assert 'bestehen zu lassen' not in nodes[pledge.PLEDGE]['quote']
    assert '§ 328' not in nodes[pledge.PLEDGE]['quote']
    assert 'ursprünglichen Laufzeit von mehr als einem Jahr' in nodes[pledge.DEFINITION]['quote']
    assert 'gehandelt werden oder werden können' in nodes[pledge.DEFINITION]['quote']
    comparison = nodes[pledge.STATUS]['source_comparison']
    assert comparison == outcome['status_pledge']['source_comparison']
    assert comparison['records_citation_correction']['corrected_sources'][0]['unit'].endswith(':p66:l71')
    check_omission(case, products, pledge.DEFINITION, definition_omission)
    effect = pledge.matched_missing_definition(report, definition_omission)
    assert effect['other_meanings_equal'] and effect['direct_dependencies_equal']
    assert set(effect['question_evidence']) == {'Q1','Q2','Q2.compulsory_common','Q2.possible_common','Q2.common_only'}


@pytest.mark.parametrize('identity', [pledge.STATUS, pledge.PLEDGE])
def test_basf_pledge_remaining_real_omissions(case, products, identity):
    request, p1, p2, _ = products
    omitted = service.interpretation_product(p1, p2, {
        'clauses': pledge.omitted_clauses(p2['payload']['assembly'], request, identity)})['payload']
    check_omission(case, products, identity, omitted)


def test_basf_pledge_unreviewed_definition_cannot_be_operative(case, products):
    request, p1, p2, _ = products
    payload = deepcopy(p2['payload'])
    next(u for u in payload['assembly']['units'] if u['unit'] == basf.KEY + ':p110:l80')['role'] = 'UNKNOWN'
    references = {**request['reference_admission'], 'assembly_sha256': digest(payload['assembly'])}
    changed = service.seal('P2', request['bundle'], {'P1': p1['sha256']}, payload)
    with pytest.raises(ValueError, match='operative assertion'):
        service.interpretation_product(p1, changed, {'reference_admission': references})


@pytest.mark.parametrize('change', [
    'stale_graph','stale_construction','stale_assembly','stale_prior_meanings','stale_prior_references',
    'missing_authority','wrong_authority','missing_context','wrong_occurrence','wrong_edition',
    'missing_source_piece','truncated_status','truncated_pledge','truncated_definition','changed_quote',
    'duplicate_disposition','extra_guarantor_disposition','lost_prior','changed_prior_reference',
    'no_priority_exception','secured_status','subordinated_status','guaranteed_recovery',
    'holder_receipt_cutoff','all_borrowing','no_guarantees','all_security','no_alternative',
    'issuer_approves_equivalence','proportionality','allow_subsisting_security','actual_compliance',
    'actual_holder_receipt','remaining_maturity','one_year_or_more','listed_only','exchange_only',
    'no_securities_requirement','actual_debt_classified','wrong_effect_scope',
    'missing_definition_edge','wrong_definition_target','wrong_definition_kind','fabricated_statute_edge',
    'same_quote_other_option','missing_comparison_correction','missing_comparison_authority',
])
def test_basf_pledge_admission_rejects_source_or_meaning_mutation(case, change):
    _, graph, construction, assembly, previous, original = case
    packet = deepcopy(original)
    status, covenant, definition = packet['clauses']
    hashes = {'stale_graph':'graph_sha256','stale_construction':'construction_sha256',
        'stale_assembly':'baseline_assembly_sha256','stale_prior_meanings':'prior_clauses_sha256',
        'stale_prior_references':'prior_references_sha256'}
    if change in hashes: packet[hashes[change]] = '0'*64
    elif change == 'missing_authority': packet['authority_sources'].pop()
    elif change == 'wrong_authority': status['selection_authority'][0]['quote'] = 'BASF Finance Europe N.V.'
    elif change == 'missing_context': packet['context_sources'].pop()
    elif change == 'wrong_occurrence': covenant['source_uses'][0]['use'] = basf.KEY + ':p111:l5'
    elif change == 'wrong_edition': definition['source_uses'][0]['source']['source_sha256'] = '0'*64
    elif change == 'missing_source_piece': covenant['source_uses'].pop()
    elif change == 'truncated_status': status['spans'].pop()
    elif change == 'truncated_pledge': covenant['spans'].pop()
    elif change == 'truncated_definition': definition['spans'].pop()
    elif change == 'changed_quote': covenant['quote'] += ' bestehen zu lassen'
    elif change in {'duplicate_disposition','extra_guarantor_disposition'}:
        row = deepcopy(packet['units'][-1])
        if change == 'extra_guarantor_disposition': row['unit'] = basf.KEY + ':p111:l5'
        packet['units'].append(row)
    elif change == 'lost_prior': previous = {**previous,'clauses':[n for n in previous['clauses'] if n['id'] != pledge.PRIOR_IDS[-1]]}
    elif change == 'changed_prior_reference':
        previous = {**previous,'reference_admission':deepcopy(previous['reference_admission'])}
        previous['reference_admission']['references'][-1]['targets'].pop()
    elif change in {'no_priority_exception','secured_status','subordinated_status','guaranteed_recovery'}:
        key, value = {'no_priority_exception':('exception',None),'secured_status':('security','SECURED'),
            'subordinated_status':('subordination','SUBORDINATED'),'guaranteed_recovery':('actual_recovery','FULL')}[change]
        status['pledge_reading'][key] = value
    elif change in {'holder_receipt_cutoff','all_borrowing','no_guarantees','all_security','no_alternative',
                    'issuer_approves_equivalence','proportionality','allow_subsisting_security','actual_compliance','actual_holder_receipt'}:
        key, value = {
            'holder_receipt_cutoff':('duration','UNTIL_EVERY_HOLDER_RECEIVES_PAYMENT'),
            'all_borrowing':('debt_scope',['ALL_BORROWED_MONEY']),
            'no_guarantees':('debt_scope',['PRESENT_OR_FUTURE_CAPITAL_MARKET_INDEBTEDNESS']),
            'all_security':('restricted_security','ALL_SECURITY_FOR_ANY_DEBT'),
            'no_alternative':('security_alternative','SAME_SECURITY_ONLY'),
            'issuer_approves_equivalence':('equivalence_reviewer','ISSUER'),
            'proportionality':('holder_participation','SIMULTANEOUS_EQUAL_PROPORTION'),
            'allow_subsisting_security':('allow_no_security_to_subsist',True),
            'actual_compliance':('actual_covenant_compliance','ESTABLISHED'),
            'actual_holder_receipt':('actual_holder_receipt','ESTABLISHED')}[change]
        covenant['pledge_reading'][key] = value
    elif change in {'remaining_maturity','one_year_or_more','listed_only','exchange_only','no_securities_requirement','actual_debt_classified'}:
        key, value = {'remaining_maturity':('maturity_basis','REMAINING'),
            'one_year_or_more':('maturity_threshold','GREATER_THAN_OR_EQUAL_TO_ONE_YEAR'),
            'listed_only':('market_condition','CURRENTLY_LISTED'),
            'exchange_only':('market','STOCK_EXCHANGE_ONLY'),
            'no_securities_requirement':('representation','ALL_BORROWED_MONEY'),
            'actual_debt_classified':('actual_debt_classification','ESTABLISHED')}[change]
        definition['pledge_reading'][key] = value
    elif change == 'wrong_effect_scope': status['effect_scope'] = ['ALL']
    elif change == 'missing_definition_edge': covenant['references'] = []
    elif change == 'wrong_definition_target': covenant['references'][0]['target'] = pledge.STATUS
    elif change == 'wrong_definition_kind': covenant['references'][0]['kind'] = 'priority'
    elif change == 'fabricated_statute_edge': status['references'] = [{'target':'invented-statute','kind':'reference','reason':'unreviewed'}]
    elif change == 'same_quote_other_option':
        correction = packet['source_comparison']['records_citation_correction']
        assert ' '.join(s['quote'] for s in correction['corrected_sources']) == ' '.join(s['quote'] for s in correction['historical_sources'])
        correction['corrected_sources'] = deepcopy(correction['historical_sources'])
        status['source_comparison'] = deepcopy(packet['source_comparison'])
    elif change == 'missing_comparison_correction': packet['source_comparison'].pop('records_citation_correction')
    elif change == 'missing_comparison_authority': packet['source_comparison']['option_authority'].pop()
    with pytest.raises(ValueError):
        pledge.prepare(graph, construction, assembly, previous, packet)


def test_basf_pledge_changed_reviewed_image_rejects_before_assessment(case):
    packet = deepcopy(case[-1])
    packet['images'][next(iter(packet['images']))] = '0'*64
    with pytest.raises(ValueError, match='image changed'):
        prepared_request(case[0], case[1], packet)


@pytest.mark.parametrize('change', ['lost_status','lost_pledge','lost_definition','lost_prior','recovery','acceptance',
    'missing_edge','unresolved_edge','wrong_edge_target','wrong_edge_kind','changed_reference',
    'lost_comparison','wrong_option','revived_guarantee'])
def test_basf_pledge_downstream_mutation_rejects(case, products, change):
    request = deepcopy(products[0])
    report = deepcopy(report_for(case, products))
    lost = {'lost_status':pledge.STATUS,'lost_pledge':pledge.PLEDGE,'lost_definition':pledge.DEFINITION,'lost_prior':pledge.PRIOR_IDS[-1]}
    if change in lost: report['clause_graph']['nodes'] = [n for n in report['clause_graph']['nodes'] if n['id'] != lost[change]]
    elif change == 'recovery': next(n for n in report['clause_graph']['nodes'] if n['id']==pledge.STATUS)['pledge_reading']['actual_recovery'] = 'FULL'
    elif change == 'acceptance': report['independent_legal_acceptance'] = True
    elif change == 'missing_edge': report['clause_graph']['edges'] = [e for e in report['clause_graph']['edges'] if e['from']!=pledge.PLEDGE]
    elif change in {'unresolved_edge','wrong_edge_target','wrong_edge_kind'}:
        edge = next(e for e in report['clause_graph']['edges'] if e['from']==pledge.PLEDGE)
        key, value = {'unresolved_edge':('resolved',False),'wrong_edge_target':('to',pledge.STATUS),'wrong_edge_kind':('kind','priority')}[change]
        edge[key] = value
    elif change == 'changed_reference': request['reference_admission']['references'][-1]['targets'].pop()
    elif change == 'lost_comparison': next(n for n in report['clause_graph']['nodes'] if n['id']==pledge.STATUS).pop('source_comparison')
    elif change == 'wrong_option': next(n for n in report['clause_graph']['nodes'] if n['id']==pledge.STATUS)['source_comparison']['selected_option'] = 'II'
    elif change == 'revived_guarantee':
        unit = next(u for u in report['assembly']['units'] if u['unit']==basf.KEY+':p111:l5')
        unit.update(role='OPERATIVE',text='Guarantee revived')
    with pytest.raises(ValueError):
        check_report(report, request, case[-1])


@pytest.mark.parametrize('change',['claimed_resolved','missing_q1_reason','missing_q2_possible_reason','lost_subquestion','changed_pledge','baseline_already_missing'])
def test_basf_pledge_definition_effect_requires_actual_question_evidence(case, products, definition_omission, change):
    omitted = deepcopy(definition_omission)
    report = deepcopy(report_for(case, products))
    reason = 'Missing reference target: '+pledge.DEFINITION
    if change == 'claimed_resolved': next(e for e in omitted['clauses']['edges'] if e['from']==pledge.PLEDGE)['resolved'] = True
    elif change == 'missing_q1_reason': omitted['questions']['Q1']['unresolved'].remove(reason)
    elif change == 'missing_q2_possible_reason': omitted['questions']['Q2']['subquestions']['possible_common']['unresolved'].remove(reason)
    elif change == 'lost_subquestion': omitted['questions']['Q2']['subquestions'].pop('common_only')
    elif change == 'changed_pledge': next(n for n in omitted['clauses']['nodes'] if n['id']==pledge.PLEDGE)['quote'] += ' changed'
    elif change == 'baseline_already_missing': report['questions']['Q1']['unresolved'].append(reason)
    with pytest.raises(ValueError):
        pledge.matched_missing_definition(report, omitted)
