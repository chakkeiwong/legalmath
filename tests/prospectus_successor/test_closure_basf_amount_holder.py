"""Real selected BASF amount, form and holder, with source/meaning loss controls."""
from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.prospectus.successor import basf, basf_amount_holder as amount, basf_global_records as records, jobs, service, source_graph
from legalmath.prospectus.successor.contracts import digest, read
from legalmath.prospectus.successor.occurrences import anchor
from scripts.prospectus_closure_basf_global_records import prepared_request as records_request
from scripts.prospectus_closure_basf_amount_holder import REL, check_report


@pytest.fixture(scope='module')
def case():
    root = Path(__file__).resolve().parents[2]
    graph = source_graph.build(jobs.basf_request(root)['bundle'], root)
    construction = basf.construct(graph, read(root / jobs.BASF))
    previous = records_request(root, graph)
    assembly = basf.as_assembly(graph, construction, previous['construction']['scalar_admission'])
    return root, graph, construction, assembly, previous, read(root / REL / 'review.json')


@pytest.fixture(scope='module')
def products(case):
    root, graph, construction, assembly, previous, packet = case
    request = amount.prepare(graph, construction, assembly, previous, packet)
    p1 = service.seal('P1', request['bundle'], {'request': digest(request)}, {'request': request, 'graph': graph})
    p2 = service.construction_product(p1, root)
    return request, p1, p2, service.interpretation_product(p1, p2)


def report_for(case, products):
    _, _, p2, p3 = products
    return {'source_map': case[1], 'selected_contract': case[2], 'assembly': p2['payload']['assembly'],
            'clause_graph': p3['payload']['clauses'], 'questions': p3['payload']['questions'],
            'dependencies': p3['payload']['dependencies'], 'mode': 'ASSISTED', 'independent_legal_acceptance': False}


def check_omission(case, products, identity):
    request, p1, p2, _ = products
    report = report_for(case, products)
    node = next(n for n in case[-1]['clauses'] if n['id'] == identity)
    omitted = service.interpretation_product(p1, p2, {
        'clauses': amount.omitted_clauses(report['assembly'], request, identity)})['payload']
    matched = amount.matched_omission(report['assembly'], report['clause_graph'], omitted['clauses'], [node])
    assert matched['unknown_with_reading'] == 0
    assert matched['unknown_without_reading'] == matched['reviewed_nonspace_characters'] > 0
    assert matched['outside_unknown_characters_equal']
    retained = set(amount.PRIOR_IDS) | (set(amount.PARAGRAPHS) - {identity})
    assert [n for n in omitted['clauses']['nodes'] if n['id'] in retained] == [n for n in report['clause_graph']['nodes'] if n['id'] in retained]
    assert [omitted['questions'][q]['status'] for q in ('Q1', 'Q2', 'Q3')] == ['UNKNOWN', 'UNKNOWN', 'PARTIAL']


def test_basf_amount_p3_smoke_and_amount_omission(case, products):
    request, _, p2, _ = products
    report = report_for(case, products)
    outcome = check_report(report, request, case[-1])
    assert outcome['reviewed_references'] == 6
    assert outcome['target_occurrences'][:5] == [34, 30, 4, 15, 15]
    assert outcome['target_occurrences'][-1] == len(case[-1]['references'][0]['targets'])
    assert outcome['mapped_scalar_operations'] == 6
    assert outcome['retained_markers'] == 15 and outcome['unresolved_intervals'] == 537
    assert outcome['amount_holder']['reviewed_units'] == 12
    assert outcome['global_records']['incoming_ngn_reference'] == 'RESOLVED_UNDER_SUPPLIED_REVIEW'
    assert outcome['global_records']['redemption_reduction_wording'] == 'UNRESOLVED_BILINGUAL_DISCREPANCY'
    assert p2['payload']['selected_contract'] == read(case[0] / 'docs/implementation/prospectus-adoption/phases/A1/attempt-008/product.json')
    assert request['reference_admission']['references'][:5] == case[-2]['reference_admission']['references']
    nodes = {n['id']: n for n in report['clause_graph']['nodes']}
    assert 'vorbehaltlich § 1 Absatz (4)' in nodes[amount.AMOUNT]['quote']
    assert 'EUR 500.000.000' in nodes[amount.AMOUNT]['quote']
    assert 'EUR fünfhundert Millionen' in nodes[amount.AMOUNT]['quote']
    assert 'EUR 100.000' in nodes[amount.AMOUNT]['quote']
    assert nodes[amount.BEARER]['quote'].endswith('auf den Inhaber.')
    assert 'CDS' not in nodes[amount.HOLDER]['quote'] and '§ 4(1)' not in nodes[amount.HOLDER]['quote']
    assert nodes[amount.HOLDER]['quote'].endswith('Schuldverschreibungen.')
    assert not any(row['id'].startswith(records.INCOMING_REFERENCE + '@') for row in report['dependencies'])
    check_omission(case, products, amount.AMOUNT)


@pytest.mark.parametrize('identity', [amount.BEARER, amount.HOLDER])
def test_basf_amount_remaining_p3_omissions(case, products, identity):
    check_omission(case, products, identity)


def test_basf_amount_p3_missing_link_retains_unresolved(case, products):
    request, p1, p2, _ = products
    missing = {**request['reference_admission'], 'references': request['reference_admission']['references'][:5]}
    omitted = service.interpretation_product(p1, p2, {'reference_admission': missing})['payload']
    effect = amount.matched_missing_link(report_for(case, products), omitted)
    assert effect['all_meanings_equal'] and effect['other_direct_dependencies_equal']


def test_basf_amount_p3_missing_operative_target_rejects(case, products):
    request, p1, p2, _ = products
    payload = deepcopy(p2['payload'])
    next(u for u in payload['assembly']['units'] if u['unit'] == basf.KEY + ':p109:l50')['role'] = 'UNKNOWN'
    references = {**request['reference_admission'], 'assembly_sha256': digest(payload['assembly'])}
    changed = service.seal('P2', request['bundle'], {'P1': p1['sha256']}, payload)
    with pytest.raises(ValueError, match='Reference target is not operative'):
        service.interpretation_product(p1, changed, {'clauses': [], 'reference_admission': references})


@pytest.mark.parametrize('change', [
    'stale_graph', 'stale_construction', 'stale_assembly', 'stale_prior_meanings', 'stale_prior_references',
    'missing_authority', 'wrong_authority', 'missing_context', 'cds_raw_line', 'wrong_occurrence',
    'wrong_edition', 'missing_source_piece', 'truncated_amount', 'truncated_holder', 'changed_quote',
    'extra_cds', 'duplicate_disposition', 'wrong_issuer', 'wrong_amount', 'wrong_words', 'wrong_currency',
    'wrong_denomination', 'no_qualification', 'actual_balance', 'registered_form', 'actual_entitlement',
    'cds_qualification', 'actual_ownership', 'universal_standing', 'lost_qualification', 'lost_prior',
    'changed_prior_reference', 'wrong_effect_scope', 'no_reference', 'short_target', 'wrong_target',
    'wrong_reference_source', 'wrong_discovery', 'no_discovery', 'unrelated_reference', 'wrong_scalar',
])
def test_basf_amount_admission_rejects_source_or_meaning_mutation(case, change):
    _, graph, construction, assembly, previous, original = case
    packet = deepcopy(original)
    issue, bearer, holder = packet['clauses']
    reference = packet['references'][0]
    hashes = {'stale_graph': 'graph_sha256', 'stale_construction': 'construction_sha256',
              'stale_assembly': 'baseline_assembly_sha256', 'stale_prior_meanings': 'prior_clauses_sha256',
              'stale_prior_references': 'prior_references_sha256'}
    if change in hashes: packet[hashes[change]] = '0' * 64
    elif change == 'missing_authority': packet['authority_sources'].pop()
    elif change == 'wrong_authority': packet['authority_sources'][0]['quote'] = 'Different issuer'
    elif change == 'missing_context': packet['context_sources'].pop()
    elif change == 'cds_raw_line':
        key = basf.KEY + ':p110:l44'
        next(r for r in packet['units'] if r['unit'] == key)['sources'] = [anchor(next(u for u in graph['units'] if u['id'] == key))]
    elif change == 'wrong_occurrence': issue['source_uses'][0]['use'] = basf.KEY + ':p108:l8'
    elif change == 'wrong_edition': holder['source_uses'][0]['source']['source_sha256'] = '0' * 64
    elif change == 'missing_source_piece': issue['source_uses'].pop()
    elif change == 'truncated_amount': issue['spans'] = issue['spans'][:4]
    elif change == 'truncated_holder': holder['spans'].pop()
    elif change == 'changed_quote': issue['quote'] = issue['quote'].replace('vorbehaltlich', 'unabhängig von')
    elif change in {'extra_cds', 'duplicate_disposition'}:
        row = deepcopy(packet['units'][-1])
        if change == 'extra_cds': row['unit'] = basf.KEY + ':p110:l42'
        packet['units'].append(row)
    elif change in {'wrong_issuer','wrong_amount','wrong_words','wrong_currency','wrong_denomination','no_qualification','actual_balance'}:
        key, value = {'wrong_issuer': ('issuer','BASF Finance Europe N.V.'), 'wrong_amount': ('issue_amount','500000'),
            'wrong_words': ('issue_amount_words','EUR fünf Millionen'), 'wrong_currency': ('currency','USD'),
            'wrong_denomination': ('denomination','1000'), 'no_qualification': ('amount_subject_to',None),
            'actual_balance': ('actual_outstanding_balance','500000000')}[change]
        issue['amount_reading'][key] = value
    elif change == 'registered_form': bearer['amount_reading']['form'] = 'REGISTERED'
    elif change == 'actual_entitlement': bearer['amount_reading']['actual_entitlement'] = 'ESTABLISHED'
    elif change == 'cds_qualification': holder['amount_reading']['cds_qualification_selected'] = True
    elif change == 'actual_ownership': holder['amount_reading']['actual_ownership'] = 'ESTABLISHED'
    elif change == 'universal_standing': holder['amount_reading']['procedural_standing'] = 'ESTABLISHED'
    elif change == 'lost_qualification': del holder['amount_reading']['qualification']
    elif change == 'lost_prior': previous = {**previous, 'clauses': [n for n in previous['clauses'] if n['id'] != records.PARTIAL]}
    elif change == 'changed_prior_reference':
        previous = {**previous, 'reference_admission': deepcopy(previous['reference_admission'])}
        previous['reference_admission']['references'][2]['targets'].pop()
    elif change == 'wrong_effect_scope': issue['effect_scope'] = ['ALL']
    elif change == 'no_reference': packet['references'] = []
    elif change == 'short_target': reference['targets'].pop()
    elif change == 'wrong_target': reference['targets'][-1] = deepcopy(reference['targets'][0])
    elif change == 'wrong_reference_source': reference['source']['end'] = 52
    elif change == 'wrong_discovery': reference['discovery_ids'] = ['unrelated-proposal']
    elif change == 'no_discovery': reference['discovery_ids'] = []
    elif change == 'unrelated_reference': reference['id'] = 'unrelated'
    elif change == 'wrong_scalar':
        next(p for p in issue['source_uses'] if p['source']['unit'] == 'basf-2032-final:p3:l29')['source']['unit'] = 'basf-2032-final:p3:l28'
    with pytest.raises(ValueError):
        amount.prepare(graph, construction, assembly, previous, packet)


@pytest.mark.parametrize('change', ['lost_amount', 'lost_holder', 'lost_records', 'balance', 'acceptance',
                                  'missing_dependency','fabricated_status','short_dependency','unrelated_dependency',
                                  'missing_proposal','short_target','changed_prior_reference','lost_reference'])
def test_basf_amount_downstream_mutation_rejects(case, products, change):
    request = deepcopy(products[0])
    report = deepcopy(report_for(case, products))
    lost = {'lost_amount': amount.AMOUNT, 'lost_holder': amount.HOLDER, 'lost_records': records.RECORDS}
    if change in lost: report['clause_graph']['nodes'] = [n for n in report['clause_graph']['nodes'] if n['id'] != lost[change]]
    elif change == 'balance': next(n for n in report['clause_graph']['nodes'] if n['id'] == amount.AMOUNT)['amount_reading']['actual_outstanding_balance'] = 0
    elif change == 'acceptance': report['independent_legal_acceptance'] = True
    elif change == 'missing_dependency': report['dependencies'] = [r for r in report['dependencies'] if r['id'] != 'reviewed-reference:' + amount.REFERENCE_ID]
    elif change in {'fabricated_status', 'short_dependency', 'unrelated_dependency'}:
        row = next(r for r in report['dependencies'] if r['id'] == 'reviewed-reference:' + amount.REFERENCE_ID)
        if change == 'fabricated_status': row['status'] = 'UNRESOLVED'
        elif change == 'short_dependency': row['targets'].pop()
        else: row['discovery_ids'] = ['unrelated-proposal']
    elif change == 'missing_proposal': report['source_map']['references'] = [r for r in report['source_map']['references'] if r['id'] != records.INCOMING_REFERENCE]
    elif change == 'short_target': request['reference_admission']['references'][-1]['targets'].pop()
    elif change == 'changed_prior_reference': request['reference_admission']['references'][0]['targets'].pop()
    elif change == 'lost_reference': request['reference_admission']['references'].pop()
    with pytest.raises(ValueError):
        check_report(report, request, case[-1])


def test_basf_amount_historical_records_mode_rejects_resolved_report(case, products):
    request = products[0]
    prior = {**request, 'reference_admission': {**request['reference_admission'], 'references': request['reference_admission']['references'][:5]}}
    packet = read(case[0] / 'docs/implementation/prospectus-integration-closure/basf-global-records/review.json')
    with pytest.raises(ValueError, match='must remain unresolved'):
        records.check_meanings(report_for(case, products), prior, packet)
