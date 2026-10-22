"""Missing intended contract sources remain unresolved, without reading them."""
from copy import deepcopy

import pytest

from scripts.prospectus_closure_fixtures import request, PREFIX, LOSS, TIME
from legalmath.prospectus.successor import basf, service
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor


def mixed_request(tmp_path, disposition='OPERATIVE', cause='knowledge', questions=None):
    req = request(tmp_path, [PREFIX])
    path = tmp_path / 'loss.txt'
    path.write_text(LOSS)
    doc = {'id': 'loss', 'path': path.name, 'sha256': digest(path.read_bytes()),
           'format': 'text', 'language': 'en', 'authority': 'Synthetic unavailable scope',
           'document_date': TIME, 'known_from': TIME}
    if cause == 'knowledge':
        doc['known_from'] = '2099-01-01T00:00:00Z'
    elif cause == 'future':
        doc['valid_from'] = '2099-01-01T00:00:00Z'
    elif cause == 'expired':
        doc['valid_until'] = TIME
    elif cause == 'post-issue':
        req['bundle']['purpose'] = 'issue_formation'
        doc['document_date'] = '2099-01-01T00:00:00Z'
    req['bundle']['documents'].append(doc)
    graph = service.source_product(req, tmp_path)['payload']['graph']
    unit = next(u for u in graph['units'] if u['document'] == 'loss')
    if disposition is not None:
        op = {'unit': unit['id'], 'source_text_sha256': unit['text_sha256'],
              'role': disposition, 'reason': 'Explicit synthetic source scope'}
        if questions is not None:
            op['questions'] = questions
        req['assembly']['operations'].append(op)
    return req


@pytest.mark.parametrize('role', ['OPERATIVE', 'UNKNOWN', None])
@pytest.mark.parametrize('cause', ['knowledge', 'future', 'expired', 'post-issue'])
def test_unavailable_intended_source_cannot_disappear_behind_visible_repayment(tmp_path, role, cause):
    req = mixed_request(tmp_path, role, cause)
    answer = service.assess(req, tmp_path)
    assert answer['questions']['Q1']['status'] == 'UNKNOWN'
    assert answer['questions']['Q2']['status'] == 'UNKNOWN'
    assert answer['questions']['Q3']['status'] == 'PARTIAL'
    assert any(reason.startswith('loss:') for reason in answer['questions']['Q1']['unresolved'])
    rows = answer['assembly']['unavailable_sources']
    assert rows == [{'unit': 'loss:p1:l0', 'document': 'loss',
                     'intended_role': role or 'UNKNOWN', 'questions': ['Q1', 'Q2']}]
    assert not any(n['effect'] == 'principal_loss' for n in answer['clause_graph']['nodes'])
    assert not answer['may_execute_transaction'] and not answer['independent_legal_acceptance']


@pytest.mark.parametrize('role', ['EXCLUDED', 'HEADER', 'INSTRUCTION', 'EXAMPLE'])
def test_explicit_nonoperative_unavailable_source_does_not_change_scope(tmp_path, role):
    req = mixed_request(tmp_path, role)
    baseline = deepcopy(req)
    baseline['bundle']['documents'].pop()
    baseline['assembly']['operations'].pop()
    answer = service.assess(req, tmp_path)
    assert answer['questions'] == service.assess(baseline, tmp_path)['questions']
    assert 'unavailable_sources' not in answer['assembly']


def test_unavailable_source_keeps_its_declared_question_scope(tmp_path):
    req = mixed_request(tmp_path, questions=['Q1'])
    answer = service.assess(req, tmp_path)
    assert answer['questions']['Q1']['status'] == 'UNKNOWN'
    assert answer['questions']['Q2']['status'] == 'NO'
    assert answer['questions']['Q3']['status'] == 'PARTIAL'
    assert all(d['questions'] == ['Q1'] for d in answer['dependencies'])


@pytest.mark.parametrize('excluded', [False, True])
def test_ast_omission_cannot_silently_dispose_of_unavailable_inventory(tmp_path, excluded):
    req = mixed_request(tmp_path, 'EXCLUDED' if excluded else None)
    graph = service.source_product(req, tmp_path)['payload']['graph']
    visible = next(u for u in graph['units'] if u['document'] == 'd')
    req['assembly']['ast'] = {'version': 'contract-ast.v2', 'root': 'visible', 'nodes': [
        {'id': 'visible', 'kind': 'Text', 'source': anchor(visible)}]}
    answer = service.assess(req, tmp_path)
    assert answer['questions']['Q1']['status'] == ('NO' if excluded else 'UNKNOWN')
    assert answer['questions']['Q3']['status'] == ('COMPLETE' if excluded else 'PARTIAL')


def test_ast_hidden_selection_still_rejects_even_with_excluded_raw_role(tmp_path):
    req = mixed_request(tmp_path, 'EXCLUDED')
    graph = service.source_product(req, tmp_path)['payload']['graph']
    hidden = next(u for u in graph['units'] if u['document'] == 'loss')
    req['assembly']['ast'] = {'version': 'contract-ast.v2', 'root': 'hidden', 'nodes': [
        {'id': 'hidden', 'kind': 'Text', 'source': anchor(hidden)}]}
    with pytest.raises(ValueError, match='Source occurrence unavailable'):
        service.assess(req, tmp_path)


@pytest.mark.parametrize('mutation', ['visible', 'document', 'role', 'missing-issue'])
def test_unavailable_scope_record_must_match_actual_graph(tmp_path, mutation):
    req = mixed_request(tmp_path)
    p1 = service.source_product(req, tmp_path)
    p2 = service.construction_product(p1, tmp_path)
    graph, assembly = deepcopy(p1['payload']['graph']), deepcopy(p2['payload']['assembly'])
    hidden = next(u for u in graph['units'] if u['document'] == 'loss')
    if mutation == 'visible':
        hidden['visible'] = True
    elif mutation == 'document':
        assembly['unavailable_sources'][0]['document'] = 'unrelated'
    elif mutation == 'role':
        assembly['unavailable_sources'][0]['intended_role'] = 'EXCLUDED'
    else:
        graph['unresolved'] = []
    with pytest.raises(ValueError, match='Unavailable source'):
        service.dependencies(req, graph, assembly)


def test_basf_assembly_retains_unavailable_body_intent(tmp_path):
    req = mixed_request(tmp_path)
    graph = service.source_product(req, tmp_path)['payload']['graph']
    construction = {'source_map': [], 'unit_accounting': [
        {'unit': u['id'], 'role': 'BODY'} for u in graph['units']],
        'operations': [], 'candidate_text': 'Synthetic assembly-adapter diagnostic'}
    assembly = basf.as_assembly(graph, construction)
    assert assembly['unavailable_sources'] == [
        {'unit': 'loss:p1:l0', 'document': 'loss', 'intended_role': 'UNKNOWN',
         'questions': ['Q1', 'Q2']}]
    assert any(d['id'].startswith('loss:') for d in service.dependencies(req, graph, assembly))


def test_visible_only_construction_payload_has_no_new_ledger(tmp_path):
    req = mixed_request(tmp_path, cause='visible')
    answer = service.assess(req, tmp_path)
    assert answer['questions']['Q1']['status'] == 'YES'
    assert 'unavailable_sources' not in answer['assembly']
