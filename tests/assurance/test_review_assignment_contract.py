"""Exercise real alias/schema transport; no provider or legal acceptance claim."""
from copy import deepcopy
import json
import pytest
from jsonschema import ValidationError
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance import bounded_references
from legalmath.interpretation.assurance.phased import group_review, review_contract, review_repair
from legalmath.interpretation.assurance.phased.source_review import assignments
from tests.assurance.test_bounded_product import envelope
from tests.assurance.test_source_review_repair import product, decision


def case(tmp_path, *, single=False):
    p = product(tmp_path, review_assignment_profile=review_contract.PROFILE)
    items = assignments(p, 'p14', [])
    request, shape = group_review.build(p, 'p14', envelope()['original_questions'][0],
        {'conclusion': 'The duty depends on the request and exception.'}, items)
    if single:
        request['required_considered'] = [items[-1]['id']]
        shape = group_review.schema(request['required_considered'], legal_indexes=[],
            repair_profile=review_repair.PROFILE)
    binding = bounded_references.prepare(request, shape)
    return p, request, binding


def respond(wire_request):
    # Choose output keys using only the information actually delivered to a model.
    targets = wire_request['response_assignment_targets']
    items = {r['id']: r for r in wire_request['payload']['assignments']}
    assert all(t['assignment_id'] in items for t in targets)
    selector = 0 if 'account_integer_citation_instructions' in wire_request else 's0'
    decision = dict(reason='Conditional source reading.', source_gaps=[], assertion_bindings=[],
        context_needs=[], review=dict(verdict='ACCEPT', issues=[], support=[{'span_id': selector}]))
    return dict(analyses=[dict(analysis_id='a', decision=decision)],
        assignments={t['response_key']: {'analysis_id': 'a'} for t in targets})


@pytest.mark.parametrize('single', [False, True])
def test_wire_only_consumer_maps_targets_and_preserves_context(tmp_path, single):
    p, request, binding = case(tmp_path, single=single)
    wire = binding['request']
    legacy_request = deepcopy(request)
    legacy_request.pop(review_contract.FIELD)
    legacy = bounded_references.prepare(legacy_request, binding['original_schema'])
    for field in ('records', 'response_spans', 'account_record_table', 'account_span_recipes',
                  'account_identity_hashes'):
        assert wire.get(field) == legacy['request'].get(field)
    for field in ('answer', 'assignments', 'origin_reading_table'):
        assert wire['payload'][field] == legacy['request']['payload'][field]
    if single:
        assert len(wire['payload']['assignments']) > len(wire['response_assignment_targets']) == 1
        assert 'Individually review every' not in wire['payload']['assignment']
    value = bounded_references.resolve(respond(wire), binding, maximum_bytes=100000)
    checked = group_review.validate(p, 'p14', value, request['required_considered'], request['records'])
    assert set(checked) == set(request['required_considered'])


@pytest.mark.parametrize('damage', ['missing', 'extra', 'alias_key', 'unused', 'unknown_rationale',
    'unsupported_accept', 'unsupported_reject', 'numbered_unbound', 'foreign_path'])
def test_contract_does_not_relax_validation(tmp_path, damage):
    p, request, binding = case(tmp_path)
    value = respond(binding['request'])
    row = value['analyses'][0]['decision']
    key = next(iter(value['assignments']))
    if damage == 'missing':
        value['assignments'].pop(key)
    elif damage == 'extra':
        value['assignments']['foreign'] = {'analysis_id': 'a'}
    elif damage == 'alias_key':
        value['assignments'][binding['request']['required_considered'][0]] = value['assignments'].pop(key)
    elif damage == 'unused':
        value['analyses'].append(dict(analysis_id='unused', decision=deepcopy(row)))
    elif damage == 'unknown_rationale':
        value['assignments'][key]['analysis_id'] = 'missing'
    elif damage == 'unsupported_accept':
        row['review']['support'] = []
    elif damage == 'unsupported_reject':
        row['review']['verdict'] = 'REJECT'
    elif damage == 'numbered_unbound':
        row['reason'] = 'Paragraph 14 requires performance.'
    else:
        row['assertion_bindings'] = [dict(path='/analyses/0/decision/reason',
            index_hash='f'*64, citation=deepcopy(row['review']['support'][0]))]
    with pytest.raises((ValidationError, LegalMathError)):
        expanded = bounded_references.resolve(value, binding, maximum_bytes=100000)
        group_review.validate(p, 'p14', expanded, request['required_considered'], request['records'])


def test_missing_delivered_target_and_profile_downgrade_refused(tmp_path):
    p, request, binding = case(tmp_path)
    request['payload']['assignments'].pop()
    with pytest.raises(LegalMathError):
        bounded_references.prepare(request, binding['original_schema'])
    with pytest.raises(LegalMathError):
        product(tmp_path)  # Previously selected profile cannot silently disappear.


def test_saved_binding_survives_sorted_json_reload(tmp_path):
    p, request, binding = case(tmp_path)
    reloaded = json.loads(json.dumps(binding, sort_keys=True))
    assert bounded_references.prepare(reloaded['original_request'], reloaded['original_schema']) == binding
    value = bounded_references.resolve(respond(reloaded['request']), reloaded, maximum_bytes=100000)
    assert group_review.validate(p, 'p14', value, request['required_considered'], request['records'])


def test_old_group_checkpoint_remains_usable_under_selected_contract(tmp_path):
    from legalmath.canonical import digest
    from legalmath.interpretation.assurance.monitor import save
    from legalmath.interpretation.assurance.integration_contract import evidence_file
    p = product(tmp_path)
    answer = {'conclusion': 'Conditional source reading.'}
    items = assignments(p, 'p14', [])
    p.review_repair_profile = None
    request, shape = group_review.build(p, 'p14', envelope()['original_questions'][0], answer, items)
    value = dict(analyses=[dict(analysis_id='a', decision=decision(request['records'][0]))],
        assignments={r['id']: {'analysis_id': 'a'} for r in items})
    result = dict(status='VALIDATED', value=value)
    p.review_repair_profile = review_repair.PROFILE
    p.review_assignment_profile = review_contract.PROFILE
    references = {}
    for name, content in (('request', request), ('schema', shape), ('result', result)):
        path = tmp_path/(name+'.json')
        save(path, content)
        references[name] = evidence_file(path, tmp_path)
    key = 'audit-group-p14-'+digest([r['id'] for r in items])[:24]
    save(tmp_path/'checkpoint.json', dict(input_hash=p.route.input_hash, review_groups={key: references}))
    p.capacity_checkpoint = evidence_file(tmp_path/'checkpoint.json', tmp_path)
    calls, results = review_repair.retained_groups(p, 'p14', envelope()['original_questions'][0], answer, [])
    assert results[key] == result
    assert calls[0]['request']['payload']['answer'] == answer
    assert calls[0]['request'][review_contract.FIELD] == review_contract.PROFILE
    assert p.review_assignment_profile == review_contract.PROFILE
