"""Real selected BASF form and records, with source/meaning loss controls."""
from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.prospectus.successor import basf, basf_global_records as records, jobs, service, source_graph
from legalmath.prospectus.successor.contracts import digest, read
from legalmath.prospectus.successor.occurrences import anchor
from scripts.prospectus_closure_basf_global_exchange import prepared_request as exchange_request
from scripts.prospectus_closure_basf_global_records import REL, check_report


@pytest.fixture(scope='module')
def case():
    root = Path(__file__).resolve().parents[2]
    graph = source_graph.build(jobs.basf_request(root)['bundle'], root)
    construction = basf.construct(graph, read(root / jobs.BASF))
    previous = exchange_request(root, graph)
    assembly = basf.as_assembly(graph, construction, previous['construction']['scalar_admission'])
    return root, graph, construction, assembly, previous, read(root / REL / 'review.json')


@pytest.fixture(scope='module')
def products(case):
    root, graph, construction, assembly, previous, packet = case
    request = records.prepare(graph, construction, assembly, previous, packet)
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
        'clauses': records.omitted_clauses(report['assembly'], request, identity)})['payload']
    matched = records.matched_omission(report['assembly'], report['clause_graph'], omitted['clauses'], [node])
    assert matched['unknown_with_reading'] == 0
    assert matched['unknown_without_reading'] == matched['reviewed_nonspace_characters'] > 0
    assert matched['outside_unknown_characters_equal']
    retained = set(records.PRIOR_IDS) | (set(records.PARAGRAPHS) - {identity})
    assert [n for n in omitted['clauses']['nodes'] if n['id'] in retained] == [n for n in report['clause_graph']['nodes'] if n['id'] in retained]
    assert [omitted['questions'][q]['status'] for q in ('Q1', 'Q2', 'Q3')] == ['UNKNOWN', 'UNKNOWN', 'PARTIAL']


def test_basf_records_p3_smoke_and_adjustment_omission(case, products):
    request, _, p2, _ = products
    report = report_for(case, products)
    outcome = check_report(report, request, case[-1])
    assert outcome['reviewed_references'] == 5
    assert outcome['target_occurrences'] == [34, 30, 4, 15, 15]
    assert outcome['mapped_scalar_operations'] == 6
    assert outcome['retained_markers'] == 15 and outcome['unresolved_intervals'] == 537
    assert outcome['global_records']['reviewed_units'] == 48
    assert outcome['global_records']['incoming_ngn_reference'] == 'UNRESOLVED'
    assert outcome['global_records']['redemption_reduction_wording'] == 'UNRESOLVED_BILINGUAL_DISCREPANCY'
    assert p2['payload']['selected_contract'] == read(case[0] / 'docs/implementation/prospectus-adoption/phases/A1/attempt-008/product.json')
    assert request['reference_admission']['references'] == case[-2]['reference_admission']['references']
    nodes = {n['id']: n for n in report['clause_graph']['nodes']}
    assert 'Kontrollunterschrift' in nodes[records.FORM]['quote']
    assert 'Funktionsnachfolger.' in nodes[records.CLEARING]['quote']
    assert 'CBF' not in nodes[records.CLEARING]['quote'] and 'CDS & Co.' not in nodes[records.CLEARING]['quote']
    assert 'common safekeeper' in nodes[records.CUSTODY]['quote']
    assert 'zurückgekauften' in nodes[records.ADJUSTMENTS]['quote']
    assert nodes[records.PARTIAL]['quote'].strip().startswith('Bei Austausch')
    assert nodes[records.PARTIAL]['quote'].endswith('aufgenommen werden.')
    check_omission(case, products, records.ADJUSTMENTS)


@pytest.mark.parametrize('identity', [k for k in records.PARAGRAPHS if k != records.ADJUSTMENTS])
def test_basf_records_remaining_p3_omissions(case, products, identity):
    check_omission(case, products, identity)


@pytest.mark.parametrize('change', [
    'stale_graph', 'stale_construction', 'stale_assembly', 'stale_prior_meanings', 'stale_prior_references',
    'missing_authority', 'wrong_authority', 'missing_context', 'missing_comparison',
    'cbf_raw_line', 'cds_raw_line', 'instruction_raw_line', 'wrong_occurrence', 'wrong_edition',
    'missing_source_piece', 'truncated_authentication', 'truncated_successor', 'truncated_recording',
    'changed_quote', 'extra_cbf', 'extra_cgn', 'extra_cds', 'duplicate_disposition',
    'no_signature', 'no_authentication', 'individual_notes', 'automatic_exchange',
    'no_successor', 'cgn_custody', 'one_icsd', 'actual_balance', 'court_conclusiveness',
    'no_interest_recording', 'no_issuer_duty', 'interest_reduces_principal', 'holder_write_down',
    'silently_use_english', 'actual_compliance', 'no_partial_recording', 'conversion',
    'lost_qualification', 'lost_prior', 'changed_prior_reference', 'wrong_effect_scope',
])
def test_basf_records_admission_rejects_source_or_meaning_mutation(case, change):
    _, graph, construction, assembly, previous, original = case
    packet = deepcopy(original)
    form, clearing, custody, evid, adjust, partial = packet['clauses']
    hashes = {'stale_graph': 'graph_sha256', 'stale_construction': 'construction_sha256',
              'stale_assembly': 'baseline_assembly_sha256', 'stale_prior_meanings': 'prior_clauses_sha256',
              'stale_prior_references': 'prior_references_sha256'}
    if change in hashes: packet[hashes[change]] = '0' * 64
    elif change == 'missing_authority': packet['authority_sources'].pop()
    elif change == 'wrong_authority': packet['authority_sources'][0]['quote'] = 'Different issue'
    elif change == 'missing_context': packet['context_sources'].pop()
    elif change == 'missing_comparison': packet['comparison_sources'].pop()
    elif change in {'cbf_raw_line', 'cds_raw_line', 'instruction_raw_line'}:
        line = {'cbf_raw_line': 5, 'cds_raw_line': 9, 'instruction_raw_line': 47}[change]
        key = basf.KEY + ':p109:l' + str(line)
        row = next(r for r in packet['units'] if r['unit'] == key)
        row['sources'] = [anchor(next(u for u in graph['units'] if u['id'] == key))]
    elif change == 'wrong_occurrence': form['source_uses'][0]['use'] = basf.KEY + ':p108:l50'
    elif change == 'wrong_edition': form['source_uses'][0]['source']['source_sha256'] = '0' * 64
    elif change == 'missing_source_piece': clearing['source_uses'].pop()
    elif change == 'truncated_authentication': form['spans'] = form['spans'][:-3]
    elif change == 'truncated_successor': clearing['spans'].pop()
    elif change == 'truncated_recording': partial['spans'].pop()
    elif change == 'changed_quote': adjust['quote'] = adjust['quote'].replace('zurückgekauften', 'getilgten')
    elif change in {'extra_cbf', 'extra_cgn', 'extra_cds', 'duplicate_disposition'}:
        row = deepcopy(packet['units'][0])
        if change != 'duplicate_disposition':
            row['unit'] = basf.KEY + ':p109:l' + str({'extra_cbf': 4, 'extra_cgn': 61, 'extra_cds': 10}[change])
        packet['units'].append(row)
    elif change == 'no_signature': form['records_reading']['issuer_authorized_signatures_both_forms'] = False
    elif change == 'no_authentication': form['records_reading']['fiscal_agent_authentication_both_forms'] = 'NONE'
    elif change == 'individual_notes': form['records_reading']['individual_notes_or_coupons_issued'] = True
    elif change == 'automatic_exchange': form['records_reading']['exchange_conditions_preserved'] = None
    elif change == 'no_successor': clearing['records_reading']['includes_functional_successors'] = False
    elif change == 'cgn_custody': custody['records_reading']['custodian_role'] = 'COMMON_DEPOSITARY'
    elif change == 'one_icsd': custody['records_reading']['on_behalf_of_both_icsds'] = False
    elif change == 'actual_balance': evid['records_reading']['actual_account_balance'] = 'EUR 500,000,000'
    elif change == 'court_conclusiveness': evid['records_reading']['procedural_law_evidentiary_effect'] = 'CONCLUSIVE_IN_ALL_COURTS'
    elif change == 'no_interest_recording': adjust['records_reading']['recording_triggers'].remove('INTEREST_PAYMENT')
    elif change == 'no_issuer_duty': adjust['records_reading']['issuer_ensures_recording'] = False
    elif change == 'interest_reduces_principal': adjust['records_reading']['interest_payment_alone_reduces_principal'] = True
    elif change == 'holder_write_down': adjust['effect'] = 'principal_loss'
    elif change == 'silently_use_english': adjust['records_reading']['redemption_reduction_wording'] = 'RESOLVED'
    elif change == 'actual_compliance': adjust['records_reading']['actual_event_or_balance'] = 'COMPLIANT'
    elif change == 'no_partial_recording': partial['records_reading']['issuer_ensures_recording'] = False
    elif change == 'conversion': partial['effect'] = 'conversion'
    elif change == 'lost_qualification': del partial['records_reading']['qualification']
    elif change == 'lost_prior': previous = {**previous, 'clauses': [n for n in previous['clauses'] if n['id'] != 'basf-global:exchange-certification']}
    elif change == 'changed_prior_reference':
        previous = {**previous, 'reference_admission': deepcopy(previous['reference_admission'])}
        previous['reference_admission']['references'][2]['targets'].pop()
    elif change == 'wrong_effect_scope': adjust['effect_scope'] = ['ALL']
    with pytest.raises(ValueError):
        records.prepare(graph, construction, assembly, previous, packet)


def test_basf_records_p3_rejects_missing_operative_source(case, products):
    request, p1, p2, _ = products
    payload = deepcopy(p2['payload'])
    next(u for u in payload['assembly']['units'] if u['unit'] == basf.KEY + ':p109:l37')['role'] = 'UNKNOWN'
    changed = service.seal('P2', request['bundle'], {'P1': p1['sha256']}, payload)
    with pytest.raises(ValueError, match='cannot become an operative assertion'):
        service.interpretation_product(p1, changed)


@pytest.mark.parametrize('change', ['lost_form', 'lost_partial', 'lost_exchange', 'balance', 'incoming_reference', 'acceptance'])
def test_basf_records_downstream_mutation_rejects(case, products, change):
    request = products[0]
    report = deepcopy(report_for(case, products))
    lost = {'lost_form': records.FORM, 'lost_partial': records.PARTIAL, 'lost_exchange': 'basf-global:exchange-certification'}
    if change in lost: report['clause_graph']['nodes'] = [n for n in report['clause_graph']['nodes'] if n['id'] != lost[change]]
    elif change == 'balance': next(n for n in report['clause_graph']['nodes'] if n['id'] == records.RECORDS)['records_reading']['actual_account_balance'] = 0
    elif change == 'incoming_reference': report['dependencies'] = [r for r in report['dependencies'] if not r['id'].startswith(records.INCOMING_REFERENCE + '@')]
    elif change == 'acceptance': report['independent_legal_acceptance'] = True
    with pytest.raises(ValueError):
        records.check_meanings(report, request, case[-1])
