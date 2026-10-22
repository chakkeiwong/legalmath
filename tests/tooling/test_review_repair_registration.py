from copy import deepcopy
import pytest
from scripts import legal_review_repair as repair
from scripts.legal_review_repair_service import restore_deferred, reconcile_completed_probe
from legalmath.canonical import digest
from scripts.legal_mission_execution import save, ref, Refused
from tests.tooling.test_legal_mission_execution import setup, task


def test_batch_deferral_preserves_attempts_and_restores_only_service(tmp_path):
    execution = setup(tmp_path, [task('a'), task('b'), task('c')])
    save(tmp_path/'receipt.json', dict(transport='ended'))
    evidence = [ref(tmp_path, 'receipt.json')]
    execution.block_before_dispatch_many(['a','b'], 'Shared outage', evidence, shared_scope=['provider-service'])
    execution.block_before_dispatch('c', 'Source missing', evidence, shared_scope=['source'])
    assert not execution.summary()['ready']
    assert restore_deferred(execution, evidence[0]) == ['a','b']
    assert execution.summary()['ready'] == ['a','b']
    with execution.locked() as state:
        assert all(r['attempts'] == [] for r in state['tasks'].values())
        assert len([e for e in state['events'] if e['action'] == 'PREREQUISITE_BLOCKED']) == 3


def test_review_repair_retains_history_and_rejects_success_reopening(tmp_path):
    before = dict(tasks={'a':dict(status='FAILED', attempts=[{'number':1}]),
        'b':dict(status='SUCCEEDED', attempts=[{'number':1}])}, events=[dict(action='old')],
        continuation_vetoes=[{'reason':'unchanged'}])
    save(tmp_path/'before.json', before)
    program = dict(review_repair=dict(reopened_nodes=['a'], prior_state=ref(tmp_path,'before.json'), review={}))
    current = repair.project_state(before, program, 'now')
    repair.validate_state_history(program, current, tmp_path)
    assert current['tasks']['a']['attempts'] == before['tasks']['a']['attempts']
    current['tasks']['a']['attempts'] = []
    with pytest.raises(Refused): repair.validate_state_history(program, current, tmp_path)
    program['review_repair']['reopened_nodes'] = ['b']
    with pytest.raises(Refused): repair.project_state(before, program, 'now')


def test_plain_terminal_timeout_is_opt_in_and_cannot_hide_output():
    from legalmath.interpretation.search.providers import transient_service_details
    from tests.assurance.test_service_continuation import events
    value = events('request timed out')
    assert transient_service_details(value, output_present=False) is None
    assert transient_service_details(value, output_present=False, allow_terminal_timeout=True)
    for addition in ([{'type':'turn.completed'}],
            [{'type':'item.completed','item':{'type':'agent_message','text':'partial'}}], events('401 unauthorized')):
        assert transient_service_details(value+addition, output_present=False, allow_terminal_timeout=True) is None


def test_successful_probe_restart_restores_without_resampling(tmp_path):
    execution = setup(tmp_path, [task('a')])
    save(tmp_path/'receipt.json', dict(transport='ended'))
    receipt = ref(tmp_path, 'receipt.json')
    execution.block_before_dispatch('a', 'Shared outage', [receipt], shared_scope=['provider-service'])
    folder = tmp_path/'resumption/7'
    stage, scope = {'stage': 'exact'}, {'scope': 'reviewed'}
    value = {'answer': 'saved'}
    save(folder/'scheduled.json', dict(charge=dict(failed_slot=7, request_hash='request', stage=stage),
        original_failure=receipt))
    save(folder/'started.json', dict(stage=stage))
    response = dict(value=value, service_scope=scope, failed_slot=7,
        provenance=dict(request_hash='request', response_hash=digest(value), allowance_slot=9),
        legal_acceptance=False, substituted_into_product=False)
    save(folder/'response.json', response)
    circuit = dict(open=False, failed_slots=[7, 8])
    assert reconcile_completed_probe(execution, folder, circuit, scope)['restored'] == ['a']
    assert reconcile_completed_probe(execution, folder, circuit, scope)['restored'] == []
    with execution.locked() as state:
        assert state['tasks']['a']['attempts'] == []
    with pytest.raises(Refused):
        reconcile_completed_probe(execution, folder, dict(open=False, failed_slots=[10]), scope)
    response['value'] = {'answer': 'changed'}
    save(folder/'response.json', response)
    with pytest.raises(Refused): reconcile_completed_probe(execution, folder, circuit, scope)


def test_budget_registration_rejects_shifted_reserves_and_ledger(tmp_path):
    save(tmp_path/'ledger.json', dict(maximum=8100, calls=[{}]*3539))
    prior = ref(tmp_path, 'ledger.json')
    budget = dict(profile='reviewed-original-question-reserves.v1', ledger_before=prior,
        launch_authorized=True, global_remaining=4561, prior_service_replacements=24,
        service_replacements_remaining=64, shared_pool=1753, full_matrix_completion_guaranteed=False,
        protected_calls=dict(p10=600, p14=600, evidence=600, gatecoin=800, service=64, comparisons=144))
    repair.validate_budget(budget, prior, tmp_path)
    shifted = deepcopy(budget)
    shifted['protected_calls'].update(p10=0, p14=1200)
    with pytest.raises(Refused): repair.validate_budget(shifted, prior, tmp_path)
    shifted = deepcopy(budget)
    shifted['ledger_before'] = {'path': 'other', 'sha256': 'other'}
    with pytest.raises(Refused): repair.validate_budget(shifted, prior, tmp_path)
