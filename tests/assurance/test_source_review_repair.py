from copy import deepcopy
from dataclasses import replace
import json
import pytest
from jsonschema import validate, ValidationError
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.phased.product import PhasedProduct
from legalmath.interpretation.assurance.phased import group_review, review_repair, capacity_policy
from legalmath.interpretation.assurance.phased.downstream_input import PROFILE as INPUT, CAPACITY_PROFILE
from legalmath.interpretation.search.providers import Completion
from tests.assurance.test_bounded_product import Scripted, envelope, limits
from tests.assurance.test_requirement_correction import setup_product, AccountDefect


def product(tmp_path, provider=None, **kwargs):
    return PhasedProduct(tmp_path, tmp_path/'p', provider or Scripted(), envelope(), list,
        limits=replace(limits(), input_tokens=12000), maximum_corrections=1,
        phase_admit=lambda name, count: {'name': name, 'count': count}, phase_identity='repair-test',
        downstream_input_profile=INPUT, downstream_capacity_profile=CAPACITY_PROFILE,
        common_capacity_profile=capacity_policy.PROFILE, review_repair_profile=review_repair.PROFILE, **kwargs)


def decision(source, verdict='ACCEPT'):
    return dict(verdict=verdict, reason='This assigned conditional statement follows.',
        support=[dict(record_id=source['id'], quote=source['text'], locator='')],
        issues=[], source_gaps=[], assertion_bindings=[], context_needs=[])


def with_missing_index(p):
    from legalmath.interpretation.assurance.legal_locators import build_index
    from legalmath.interpretation.assurance.integration_contract import evidence_file
    value = deepcopy(p.route.envelope)
    html = '<ol start="99"><li>Additional provision outside the delivered record.</li></ol>'
    path = p.root/'extra-provision.html'
    path.write_text(html)
    value['legal_indexes'] = [build_index(value['source_packet'], html,
        source_ref=evidence_file(path, p.root), unit_ids=[], root=p.root)]
    return BoundedProduct(p.root, p.directory/'indexed', p.provider, value, p.route.encode,
        limits=p.route.limits, maximum_corrections=1)


def test_typed_schema_rejects_false_adverse_label_and_absent_authority_with_source_ids(tmp_path):
    p = product(tmp_path)
    source = next(r for r in p.route.records.values() if r['kind'] == 'source')
    value = {'analyses': [{'analysis_id': 'a', 'decision': decision(source)}],
             'assignments': {'x': {'analysis_id': 'a'}}}
    schema = group_review.schema(['x'], legal_indexes=[], repair_profile=review_repair.PROFILE)
    validate(value, schema)
    value['analyses'][0]['decision']['verdict'] = 'REJECT'
    with pytest.raises(ValidationError): validate(value, schema)
    row = value['analyses'][0]['decision']
    row['verdict'] = 'UNRESOLVED'
    row['context_needs'] = [dict(kind='EXTERNAL_AUTHORITY', reason='Absent', record_ids=[source['id']], locators=[], query='')]
    with pytest.raises(ValidationError): validate(value, schema)
    # Historical schema remains historical; semantic checks were stricter.
    validate(value, group_review.schema(['x'], legal_indexes=[]))


def test_capacity_selected_before_direct_builder_and_context_packing(tmp_path, monkeypatch):
    p = product(tmp_path)
    source = next(r for r in p.route.records.values() if r['kind'] == 'source')
    question = envelope()['original_questions'][0]
    seen = []
    original = p.dispatch.measure
    def measure(request, schema):
        seen.append(request)
        assert request['downstream_capacity_profile'] == CAPACITY_PROFILE
        return original(request, schema)
    monkeypatch.setattr(p.dispatch, 'measure', measure)
    p.request('AUDIT_ANSWER_AND_DETAILED_ACCOUNT', question, [], payload={'answer': decision(source)}, expected=['x'])
    assert seen
    assert p._request('AUDIT_EXPLICIT_DEPENDENCY_CONTEXT', question, [source])['downstream_capacity_profile'] == CAPACITY_PROFILE
    assert 'downstream_capacity_profile' not in p._request('SYNTHESIZE_FINDINGS', question, [source])


class MixedReviews(Scripted):
    def complete(self, request, schema, settings):
        if request['task'] != 'AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS':
            return super().complete(request, schema, settings)
        self.requests.append(deepcopy(request))
        if 'invalid_review_repair' in request['payload']:
            raise RuntimeError('One invalid-review repair failed')
        source = request['records'][0]
        good, bad = decision(source), decision(source, 'REJECT')
        bad['support'] = []
        ids = request['required_considered']
        return Completion({'analyses': [{'analysis_id': 'good', 'decision': good},
            {'analysis_id': 'bad', 'decision': bad}], 'assignments': {
                identity: {'analysis_id': 'bad' if i == 0 else 'good'} for i, identity in enumerate(ids)}}, {})


def test_valid_sibling_survives_and_invalid_assignment_has_one_repair(tmp_path):
    p = product(tmp_path, MixedReviews())
    answer = {'conclusion': 'Conditional answer', 'source_gaps': [], 'support': []}
    rows = p.audit_answer('p14', envelope()['original_questions'][0], answer, [])
    assert sum(r['status'] == 'VALIDATED' for r in rows) == 1
    assert sum(r.get('invalid_review_repair_exhausted', False) for r in rows) == 1
    assert len(p.provider.requests) == 2
    repeated = p.audit_answer('p14', envelope()['original_questions'][0], answer, [])
    assert repeated == rows and len(p.provider.requests) == 2


def test_warrant_dependency_is_per_issue_and_unrelated_gap_does_not_block(tmp_path):
    provider, p, answer, details, adverse = setup_product(tmp_path)
    p = with_missing_index(p)
    original = provider.complete
    def complete(request, schema, settings):
        response = original(request, schema, settings)
        if request['task'] == 'ASSESS_REVIEW_WARRANT':
            for row in response.value['decisions']: row['blocking_source_gaps'] = []
            # Valid source-gap records are checked by the ordinary citation checker.
            response.value['source_gaps'] = [dict(index_hash=p.route.envelope['legal_indexes'][0]['index_hash'], locator='P99',
                status='NOT_VERIFIED_IN_DELIVERED_RECORDS')]
        return response
    provider.complete = complete
    p.review_repair_profile = review_repair.PROFILE
    p.review_warrants = lambda *args: review_repair.review_warrants(p, *args)
    bad = deepcopy(adverse)
    bad['value'].update(support=[], issues=[])
    _, fresh, retained = p.correct_answer('p14', 'When does duty apply?', answer, [bad, adverse], details, [])
    assert retained['status'] == 'REVIEWED'
    assert retained['requirement_corrections'][0]['result']['status'] == 'VALIDATED'
    assert any(r['task'] == 'CORRECT_REVIEWED_REQUIREMENT' for r in provider.requests)
    assert retained['review_warrants'][0]['original_review_index'] == 1


def test_failed_account_correction_does_not_cancel_independent_account(tmp_path):
    provider, p, answer, details, adverse = setup_product(tmp_path)
    second = deepcopy(details[0])
    second['id'] = 'reading:r2'
    p.route.records['reading:r2'] = {**p.route.records['obligation:o1'], 'id': 'reading:r2', 'kind': 'reading'}
    second['result']['value']['considered'] = ['reading:r2']
    another = deepcopy(adverse)
    another['value']['considered'] = ['reading:r2']
    p.review_repair_profile = review_repair.PROFILE
    p.review_warrants = lambda *args: ([], [adverse['value'], another['value']], True)
    calls = []
    original = p.note
    def note(key, *args, **kwargs):
        if key.startswith('correction-p14-requirement'):
            calls.append(key)
            return {'status': 'FAILED', 'reason': 'Independent failure'} if key.endswith('-0') else deepcopy(second['result'])
        return deepcopy(answer)
    p.note = note
    p.audit_answer = lambda *args, **kwargs: []
    p.audit_dependencies = lambda *args, **kwargs: []
    _, fresh, retained = p.correct_answer('p14', 'Duty?', answer, [adverse, another], [*details, second], [])
    assert calls == ['correction-p14-requirement-0', 'correction-p14-requirement-1']
    assert retained['corrected_requirement_details'][1]['result']['status'] == 'VALIDATED'
    assert any('requirement repairs failed' in r.get('reason', '') for r in fresh)


def test_failed_first_batch_withholds_other_batches(tmp_path, monkeypatch):
    p = product(tmp_path, MixedReviews())
    original = group_review.plan
    def plan(*args, **kwargs):
        calls, membership, blocked, items = original(*args, **kwargs)
        duplicate = deepcopy(calls[0])
        duplicate['key'] += '-must-not-dispatch'
        # This artificial second group must never be inspected or dispatched.
        calls.append(duplicate)
        membership[duplicate['key']] = []
        return calls, membership, blocked, items
    monkeypatch.setattr(group_review, 'plan', plan)
    rows = p.audit_answer('p14', envelope()['original_questions'][0], {'conclusion': 'Conditional'}, [])
    assert len(p.provider.requests) == 2  # first group, one invalid-member repair
    saved = json.loads((p.directory/'source-dependency-p14-qualification.json').read_text())
    assert not saved['qualified'] and len(saved['withheld_groups']) == 1
    assert any(r['status'] == 'VALIDATED' for r in rows)


def test_typed_review_survives_actual_reference_transport(tmp_path):
    from legalmath.interpretation.assurance import bounded_references
    p = product(tmp_path)
    source = next(r for r in p.route.records.values() if r['kind'] == 'source')
    request = p._request('AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS', envelope()['original_questions'][0],
        [source], expected=['x'])
    # Real reference protocol, without optional downstream layout changes.
    request.pop('downstream_input_profile', None)
    schema = group_review.schema(['x'], legal_indexes=[], repair_profile=review_repair.PROFILE)
    prepared = bounded_references.prepare(request, schema)
    wire_decision = dict(reason='Conditional source reading.', source_gaps=[], assertion_bindings=[],
        context_needs=[], review=dict(verdict='ACCEPT', issues=[], support=[{'span_id': 's0'}]))
    wire = dict(analyses=[dict(analysis_id='a', decision=wire_decision)], assignments={'x': {'analysis_id': 'a'}})
    expanded = bounded_references.resolve(wire, prepared, maximum_bytes=100000)
    validate(expanded, schema)
    assert expanded['analyses'][0]['decision']['support'][0]['record_id'] == source['id']
    wire_decision['review']['verdict'] = 'REJECT'
    with pytest.raises((ValidationError, LegalMathError)):
        bounded_references.resolve(wire, prepared, maximum_bytes=100000)


@pytest.mark.parametrize('unknown', [False, True])
def test_necessary_issue_gap_cannot_authorize_a_correction(tmp_path, unknown):
    provider, p, answer, details, adverse = setup_product(tmp_path)
    p = with_missing_index(p)
    original = provider.complete
    def complete(request, schema, settings):
        response = original(request, schema, settings)
        for row in response.value['decisions']:
            row['blocking_source_gaps'] = [dict(index_hash='b'*64 if unknown else p.route.envelope['legal_indexes'][0]['index_hash'], locator='P99',
                status='NOT_VERIFIED_IN_DELIVERED_RECORDS')]
        return response
    provider.complete = complete
    assessed, warranted, settled = review_repair.review_warrants(p, 'p14', 'Duty?', answer, [adverse], details)
    assert assessed[0]['result']['status'] == 'FAILED' and not warranted and not settled


def test_mixed_context_bridge_runs_but_retains_client_fact(tmp_path, monkeypatch):
    p = product(tmp_path)
    from legalmath.interpretation.assurance.phased.source_review import assignments
    item = assignments(p, 'p14', [])[0]
    sources = [r for r in p.route.records.values() if r['kind'] == 'source']
    value = decision(sources[0], 'UNRESOLVED')
    value.update(considered=[item['id']], context_needs=[
        dict(kind='SOURCE_TEXT', record_ids=[sources[-1]['id']], locators=[], query='', reason='Exception'),
        dict(kind='CLIENT_FACT', record_ids=[], locators=[], query='', reason='Consent unknown')])
    monkeypatch.setattr(group_review, 'run', lambda *a, **k: [dict(status='VALIDATED', value=deepcopy(value))])
    rows = p.audit_answer('p14', envelope()['original_questions'][0], {'conclusion': 'Conditional'}, [])
    bridge = rows[0]['context_continuation']
    assert bridge['remaining_context_needs'][0]['kind'] == 'CLIENT_FACT'
    assert any(r['task'] == 'AUDIT_EXPLICIT_DEPENDENCY_CONTEXT' for r in p.provider.requests)
    assert rows[0]['value']['verdict'] == 'UNRESOLVED'
