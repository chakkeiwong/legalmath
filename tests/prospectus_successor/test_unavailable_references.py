"""Unavailable inventory sources cannot poison or supply selected references."""
from copy import deepcopy

import pytest

from scripts.prospectus_closure_fixtures import request, PREFIX, TIME
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor


def with_unavailable(tmp_path):
    req = request(tmp_path, [PREFIX])
    hidden = tmp_path / 'unavailable.txt'
    hidden.write_text('Condition 2 applies.')
    req['bundle']['documents'].append({
        'id': 'later', 'path': hidden.name, 'sha256': digest(hidden.read_bytes()),
        'format': 'text', 'language': 'en', 'authority': 'Synthetic later evidence',
        'document_date': TIME, 'known_from': '2099-01-01T00:00:00Z'})
    p1 = service.source_product(req, tmp_path)
    hidden_unit = next(u for u in p1['payload']['graph']['units'] if u['document'] == 'later')
    req['assembly']['operations'].append({
        'unit': hidden_unit['id'], 'role': 'EXCLUDED',
        'source_text_sha256': hidden_unit['text_sha256'],
        'reason': 'Explicitly unrelated inventory document'})
    p1 = service.source_product(req, tmp_path)
    p2 = service.construction_product(p1, tmp_path)
    return req, p1, p2


def test_unrelated_unavailable_reference_preserves_all_final_questions(tmp_path):
    req, p1, p2 = with_unavailable(tmp_path)
    baseline = deepcopy(req)
    baseline['bundle']['documents'].pop()
    baseline['assembly']['operations'].pop()
    expected = service.assess(baseline, tmp_path)
    p3 = service.interpretation_product(p1, p2)
    products = dict(P1=p1, P2=p2, P3=p3, P4=service.law_product(p1, p3),
                    P5=service.financial_product(p1, p2, p3))
    actual = service.consume(products, tmp_path, mode='current')
    assert actual['questions'] == expected['questions']
    assert p3['payload']['dependencies'] == []
    assert not actual['independent_legal_acceptance'] and not actual['may_execute_transaction']


def test_all_unavailable_without_use_remains_incomplete(tmp_path):
    req, _, _ = with_unavailable(tmp_path)
    for doc in req['bundle']['documents']:
        doc['known_from'] = '2099-01-01T00:00:00Z'
    req['scope'] = {q: {'complete': False} for q in ('Q1', 'Q2', 'Q4')}
    answer = service.assess(req, tmp_path)
    assert answer['questions']['Q1']['status'] == 'UNKNOWN'
    assert answer['questions']['Q3']['status'] == 'PARTIAL'


def test_unavailable_legal_basis_still_rejects_at_law_boundary(tmp_path):
    req, p1, p2 = with_unavailable(tmp_path)
    p3 = service.interpretation_product(p1, p2)
    unit = next(u for u in p1['payload']['graph']['units'] if u['document'] == 'later')
    basis = {'id': 'hidden', 'authority': 'Synthetic', 'jurisdiction': 'Test', 'edition': 'later',
             'source': anchor(unit), 'valid_from': TIME, 'known_from': TIME,
             'instrument_id': req['bundle']['instrument_id'], 'premises': ['event']}
    with pytest.raises(ValueError, match='Source occurrence unavailable'):
        service.law_product(p1, p3, law_input={'law_bases': [basis], 'facts': []})


@pytest.mark.parametrize('representation', ['mapped', 'legacy', 'copy'])
def test_hidden_selected_occurrence_cannot_be_skipped(tmp_path, representation):
    req, p1, p2 = with_unavailable(tmp_path)
    graph, assembly = p1['payload']['graph'], deepcopy(p2['payload']['assembly'])
    unit = next(u for u in assembly['units'] if u['source']['document'] == 'later')
    unit['role'] = 'OPERATIVE'
    if representation == 'legacy':
        unit.pop('character_map')
    elif representation == 'copy':
        unit['unit'] = 'ast:copy-of-hidden-source'
    with pytest.raises(ValueError, match='Source occurrence unavailable'):
        service.dependencies(req, graph, assembly)


def test_explicit_hidden_reference_decision_still_rejects(tmp_path):
    req, p1, p2 = with_unavailable(tmp_path)
    graph = p1['payload']['graph']
    ref = next(r for r in graph['references'] if r['unit'].startswith('later:'))
    req['reference_dispositions'] = {ref['id']: {'reason': 'Explicit attempted use'}}
    with pytest.raises(ValueError, match='Source occurrence unavailable'):
        service.dependencies(req, graph, p2['payload']['assembly'])


def test_visible_reference_still_creates_unresolved_dependency(tmp_path):
    req = request(tmp_path, ['Condition 2 applies.', PREFIX])
    answer = service.assess(req, tmp_path)
    assert any(row['status'] == 'UNRESOLVED' for row in answer['dependencies'])
    assert answer['questions']['Q1']['status'] == 'UNKNOWN'


def test_reference_in_copy_of_excluded_raw_unit_is_still_active(tmp_path):
    req = request(tmp_path, ['Condition 2 applies.', PREFIX])
    p1 = service.source_product(req, tmp_path)
    source = anchor(p1['payload']['graph']['units'][0])
    req['assembly']['operations'][0]['role'] = 'EXCLUDED'
    req['assembly']['ast'] = {'version': 'contract-ast.v2', 'root': 'copy', 'nodes': [
        {'id': 'copy', 'kind': 'Text', 'source': source}]}
    answer = service.assess(req, tmp_path)
    assert any(row['status'] == 'UNRESOLVED' and row.get('source_use')
               for row in answer['dependencies'])


def test_explicit_hidden_target_from_visible_reference_still_rejects(tmp_path):
    req, _, _ = with_unavailable(tmp_path)
    path = tmp_path / 'visible-reference.txt'
    path.write_text('Condition 2 applies.')
    req['bundle']['documents'].append({
        'id': 'visible-reference', 'path': path.name, 'sha256': digest(path.read_bytes()),
        'format': 'text', 'language': 'en', 'authority': 'Synthetic',
        'document_date': TIME, 'known_from': TIME})
    p1 = service.source_product(req, tmp_path)
    graph = p1['payload']['graph']
    visible = next(u for u in graph['units'] if u['document'] == 'visible-reference')
    hidden = next(u for u in graph['units'] if u['document'] == 'later')
    req['assembly']['operations'].append({
        'unit': visible['id'], 'role': 'OPERATIVE', 'reason': 'Explicit reference test',
        'source_text_sha256': visible['text_sha256']})
    ref = next(r for r in graph['references'] if r['unit'] == visible['id'])
    req['reference_dispositions'] = {ref['id']: {
        'source_sha256': ref['source_sha256'], 'targets': [hidden['id']],
        'reason': 'Attempted unavailable target'}}
    with pytest.raises(ValueError, match='Source occurrence unavailable'):
        service.assess(req, tmp_path)
