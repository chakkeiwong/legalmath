"""Authentication controls use synthetic identities; no human review is inferred."""
from copy import deepcopy
import hashlib
import hmac
import pytest
from scripts.prospectus_closure_fixtures import annotation_fixture
from legalmath.prospectus.successor import review_records, annotation_bridge, source_graph
from legalmath.prospectus.successor.contracts import digest

KEY = b'development-only-administrator-key-32-bytes'


def signed(payload):
    return {'payload': payload, 'signature': hmac.new(KEY, review_records.payload_bytes(payload), hashlib.sha256).hexdigest()}


def review_fixture(tmp_path):
    request = annotation_fixture(tmp_path)
    graph = source_graph.build(request['bundle'], tmp_path)
    cohort = [{'id': 'case', 'questions': ['Q1'], 'request_sha256': digest(request)}]
    identities = {'readers': ['reader-a', 'reader-b'], 'adjudicator': 'reader-c', 'implementer': 'developer'}
    item = request['annotation_admission']['packets'][0]
    export = {'packet': item['packet'], 'map': [{k:v for k,v in row.items() if k != 'use'} for row in item['map']]}
    evidence = annotation_bridge.bound_evidence(graph, export)
    registry = {'version': 'independent-review-registry.v1', 'cohort_sha256': digest(cohort),
        'identities': identities, 'qualification_attested': True, 'development_families': ['exposed'],
        'case_families': {'case': ['heldout']}, 'predictions_released_at': '2026-01-03T00:00:00Z'}
    readings = [{'case': 'case', 'question': 'Q1', 'reader': reader, 'value': 'YES',
        'authenticated_account': reader, 'cohort_sha256': digest(cohort), 'blinded': True,
        'submitted_at': '2026-01-01T00:00:00Z', 'export': export, 'export_sha256': digest(export),
        'evidence': evidence} for reader in identities['readers']]
    decision = {'case': 'case', 'question': 'Q1', 'adjudicator': 'reader-c', 'authenticated_account': 'reader-c',
        'cohort_sha256': digest(cohort), 'adjudicated_at': '2026-01-02T00:00:00Z',
        'reading_sha256s': [digest(row) for row in readings], 'value': 'YES', 'evidence': evidence,
        'reason': 'Synthetic workflow control only'}
    labels = [{'id': 'case', 'question': 'Q1', 'value': 'YES', 'evidence': evidence}]
    packet = {'registry': signed(registry), 'first_readings': [signed(r) for r in readings],
        'adjudications': [signed(decision)]}
    return packet, cohort, identities, labels, {'case': graph}


def test_valid_synthetic_records_bind_actual_export_evidence(tmp_path):
    packet, cohort, identities, labels, graphs = review_fixture(tmp_path)
    result = review_records.admit(packet, KEY, cohort, identities, labels, graphs)
    assert result['status'] == 'AUTHENTICATED_ASSIGNMENTS_AND_READINGS'
    assert 'attested' in result['trust_boundary']


@pytest.mark.parametrize('mutation,match', [
    ('signature', 'signature invalid'), ('export', 'export changed'),
    ('evidence', 'differs from authored export'), ('timing', 'prediction exposure'),
    ('family', 'exposed development family'), ('account', 'Unassigned'),
    ('adjudication', 'bind each first reading'), ('assignment', 'denominator'),
])
def test_review_record_mutations_fail(tmp_path, mutation, match):
    packet, cohort, identities, labels, graphs = review_fixture(tmp_path)
    row = deepcopy(packet['first_readings'][0]['payload'])
    if mutation == 'signature':
        packet['first_readings'][0]['payload']['value'] = 'NO'
    elif mutation == 'family':
        registry = deepcopy(packet['registry']['payload'])
        registry['case_families']['case'] = ['exposed']
        packet['registry'] = signed(registry)
    elif mutation == 'adjudication':
        decision = deepcopy(packet['adjudications'][0]['payload'])
        decision['reading_sha256s'][0] = '0' * 64
        packet['adjudications'][0] = signed(decision)
    elif mutation == 'assignment':
        packet['adjudications'] = []
    else:
        if mutation == 'export':
            row['export']['packet']['text'] += 'changed'
        elif mutation == 'evidence':
            row['evidence'] = row['evidence'][:1]
        elif mutation == 'timing':
            row['submitted_at'] = '2026-01-04T00:00:00Z'
        elif mutation == 'account':
            row['authenticated_account'] = 'reader-b'
        packet['first_readings'][0] = signed(row)
    with pytest.raises(ValueError, match=match):
        review_records.admit(packet, KEY, cohort, identities, labels, graphs)


def test_resigned_fabricated_export_cannot_bind_source(tmp_path):
    packet, cohort, identities, labels, graphs = review_fixture(tmp_path)
    row = deepcopy(packet['first_readings'][0]['payload'])
    row['export']['map'][0]['source']['quote'] = 'fabricated quotation'
    row['export_sha256'] = digest(row['export'])
    packet['first_readings'][0] = signed(row)
    with pytest.raises(ValueError, match='quote changed'):
        review_records.admit(packet, KEY, cohort, identities, labels, graphs)


def test_evaluation_recomputes_and_rejects_self_hashed_fake_report(tmp_path):
    from scripts.prospectus_closure_fixtures import request, PREFIX
    from legalmath.prospectus.successor import prediction_execution, evaluation
    from legalmath.prospectus.successor.occurrences import anchor
    req = request(tmp_path, [PREFIX])
    cohort = [{'id': 'case', 'questions': ['Q1'], 'request_sha256': digest(req)}]
    inputs = {'case': {'request': req, 'root': tmp_path}}
    records, graphs = prediction_execution.execute(cohort, inputs)
    identities = {'readers': ['a', 'b'], 'adjudicator': 'c', 'implementer': 'dev'}
    labels = [{'id': 'case', 'question': 'Q1', 'value': 'NO', 'blinded': True, 'readers': ['a', 'b'],
        'adjudicator': 'c', 'cohort_sha256': digest(cohort), 'evidence': [anchor(graphs['case']['units'][0])]}]
    predictions = [{'id': 'case', 'question': 'Q1', 'value': 'NO'}]
    method = records['case']['method_sha256']
    result = evaluation.score(predictions, labels, cohort, identities, method,
        graphs=graphs, prediction_records=records, execution_inputs=inputs)
    assert result['prediction_binding'] == 'RECOMPUTED_CURRENT_SERVICE'
    assert result['review_binding'] == 'NOT_AUTHENTICATED'
    records['case']['report']['questions']['Q1']['status'] = 'YES'
    report = records['case']['report']
    report['report_sha256'] = digest({k:v for k,v in report.items() if k != 'report_sha256'})
    with pytest.raises(ValueError, match='differ from current execution'):
        evaluation.score(predictions, labels, cohort, identities, method,
            prediction_records=records, execution_inputs=inputs)
