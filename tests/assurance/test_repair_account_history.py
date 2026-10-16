from copy import deepcopy
import json
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import BoundedProduct
from legalmath.interpretation.assurance.phased import account_contract, account_recovery, account_output
from tests.assurance.test_bounded_product import Scripted, envelope
from tests.assurance.test_corrected_account_reconstruction import corrected
from tests.assurance.test_account_recovery_lineage import lineage, put


def test_saved_record_order_restored_without_changing_success(corrected):
    root, prior, fresh, provider, _, good, recovery, request = corrected
    base, typed = account_recovery.baseline_request(request, account_contract.provider_schema(), root=root)
    assert len(base['records']) > 1
    base['records'].reverse()
    saved = account_recovery.retained_contract(root, recovery, 'detail-0', base, fresh.route.input_hash)
    assert saved == (request, account_contract.provider_schema(), typed)
    assert account_recovery.use_typed(root, recovery, 'detail-0', base, fresh.route.input_hash)
    outcome = fresh.note('detail-0', base['task'], base['question'], base['records'],
        base['payload'], base['required_considered'])
    assert outcome == good and not provider.requests
    for name in ('request', 'schema', 'result'):
        assert (prior.directory / 'calls/detail-0' / (name + '.json')).read_bytes() == (
            fresh.directory / 'calls/detail-0' / (name + '.json')).read_bytes()


@pytest.mark.parametrize('mutation', ['duplicate', 'missing', 'extra', 'text', 'payload', 'question', 'required'])
def test_record_order_repair_rejects_content_changes(corrected, mutation):
    root, _, fresh, provider, _, _, recovery, request = corrected
    base, _ = account_recovery.baseline_request(request, account_contract.provider_schema(), root=root)
    base['records'].reverse()
    if mutation == 'duplicate': base['records'].append(deepcopy(base['records'][0]))
    elif mutation == 'missing': base['records'].pop()
    elif mutation == 'extra': base['records'].append({**base['records'][0], 'id': 'extra'})
    elif mutation == 'text': base['records'][0]['text'] += ' altered'
    elif mutation == 'payload': base['payload']['assignment'] = 'Other assignment'
    elif mutation == 'question': base['question'] = 'Other question'
    elif mutation == 'required': base['required_considered'] = ['other']
    with pytest.raises(LegalMathError) as error:
        account_recovery.retained_contract(root, recovery, 'detail-0', base, fresh.route.input_hash)
    assert error.value.code == 'E_INTEGRITY'
    assert error.value.details == 'Successful account request changed; resampling is forbidden'
    assert not provider.requests


def test_fully_completed_account_checkpoint_reuses_all_successes(tmp_path):
    manifest, options, records, question, good = lineage(tmp_path)
    pointer = put(tmp_path, 'composite.json', manifest)
    completed = BoundedProduct(tmp_path, tmp_path/'completed', Scripted(), envelope(), list,
        requirement_account_recovery=pointer, requirement_account_output_profile=account_output.PROFILE, **options)
    outcomes = [completed.note('detail-' + str(i), 'ASSESS_ORIGINAL_REQUIREMENT',
        question, records, {'assignment': assignment}, ['o' + str(i + 1)])
        for i, assignment in enumerate(('First', 'Second'))]
    details = [{'id': 'o' + str(i + 1), 'result': result} for i, result in enumerate(outcomes)]
    (completed.directory/'requirement-details.json').write_text(json.dumps(details))
    final = account_recovery.build(tmp_path, completed.directory/'calls', details, predecessor=pointer)
    final_ref = put(tmp_path, 'complete.json', final)
    assert final['account_recovery']['roots'] == []
    assert account_recovery.load(tmp_path, final_ref, final['input_hash']) == final
    provider = Scripted()
    fresh = BoundedProduct(tmp_path, tmp_path/'fresh', provider, envelope(), list,
        requirement_account_recovery=final_ref, **options)
    for i, assignment in enumerate(('First', 'Second')):
        assert fresh.note('detail-' + str(i), 'ASSESS_ORIGINAL_REQUIREMENT',
            question, list(reversed(records)), {'assignment': assignment}, ['o' + str(i + 1)]) == outcomes[i]
    assert not provider.requests


def test_interrupted_prefix_retains_untouched_requirements_and_successes(tmp_path):
    manifest, options, records, question, good = lineage(tmp_path)
    pointer = put(tmp_path, 'composite.json', manifest)
    latest = BoundedProduct(tmp_path, tmp_path/'interrupted', Scripted(), envelope(), list,
        requirement_account_recovery=pointer, **options)
    result = latest.note('detail-0', 'ASSESS_ORIGINAL_REQUIREMENT', question, records,
        {'assignment': 'First'}, ['o1'])
    prefix = [{'id': 'o1', 'result': result}]
    (latest.directory/'requirement-details.json').write_text(json.dumps(prefix))
    combined = account_recovery.build(tmp_path, latest.directory/'calls', prefix, predecessor=pointer,
        complete_details_path=tmp_path/'complete-details.json')
    assert combined['account_recovery']['roots'] == ['detail-1']
    assert json.loads((tmp_path/'complete-details.json').read_text())[0]['result'] == good
    retained = put(tmp_path, 'interrupted-recovery.json', combined)
    assert account_recovery.load(tmp_path, retained, combined['input_hash']) == combined
    assert json.loads((latest.directory/'requirement-details.json').read_text()) == prefix


@pytest.mark.parametrize('change', ['order', 'foreign', 'success', 'hash', 'duplicate'])
def test_interrupted_census_rejects_changed_population_or_success(change):
    prior = [{'id': 'a', 'result': {'status': 'VALIDATED', 'value': 1}, 'requirement_hash': 'a'},
        {'id': 'b', 'result': {'status': 'FAILED'}, 'requirement_hash': 'b'}]
    latest = deepcopy(prior[:1])
    if change == 'order': latest = deepcopy(prior[1:])
    elif change == 'foreign': latest[0]['id'] = 'other'
    elif change == 'success': latest[0]['result']['value'] = 2
    elif change == 'hash': latest[0]['requirement_hash'] = 'changed'
    else: latest.append(deepcopy(latest[0]))
    with pytest.raises(LegalMathError): account_recovery.merge_details(prior, latest)


