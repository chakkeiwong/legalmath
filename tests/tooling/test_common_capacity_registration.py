from copy import deepcopy
import pytest
from scripts import legal_integration_common_capacity as repair
from scripts.legal_mission_execution import save, ref, Refused


def setup(root):
    old = dict(tasks=[dict(id=name, maximum_attempts=2, inputs=[], deliverable='prior')
        for name in ('acquire-p10','acquire-p14','baseline-p14','tool-p14-bm25','compare-p14-bm25','source-qualification')],
        protected_evidence=[], deadline_utc=repair.DEADLINE, global_call_ceiling=0,
        candidate_capacity_retry={'profile':'prior'}, delayed_service_recovery={'maximum_replacements':24})
    before = dict(tasks={t['id']:dict(status='FAILED', attempts=[{'number':1},{'number':2}]) for t in old['tasks']},
        events=[], continuation_vetoes=[{'reason':'preserved'}])
    before['tasks']['acquire-p14']['status'] = 'SUCCEEDED'
    before['tasks']['tool-p14-bm25']['attempts'] = []
    before['tasks']['tool-p14-bm25']['status'] = 'BLOCKED'
    before['tasks']['compare-p14-bm25']['status'] = 'PENDING'
    save(root/'before.json', before)
    save(root/repair.PLAN, {'plan':'test'})
    revision = dict(attempt_additions=repair.repair_targets(old,before),
        reopened_nodes=sorted(repair.repair_targets(old,before)),
        prior_state=ref(root,'before.json'), implementation={}, review={}, result={}, baseline={}, checkpoints={})
    program = repair.expected_program(old, before, revision, root, plan_reference={})
    return old,before,program


def test_only_missing_original_work_is_reopened(tmp_path):
    old,before,program = setup(tmp_path)
    assert program[repair.KEY]['attempt_additions'] == {'acquire-p10':1, 'baseline-p14':1, 'tool-p14-bm25':0}
    after = repair.project_state(before, program, 'now')
    repair.validate_state_history(program, after, tmp_path)
    assert after['tasks']['acquire-p14'] == before['tasks']['acquire-p14']
    assert after['tasks']['source-qualification'] == before['tasks']['source-qualification']
    for tid in before['tasks']:
        assert after['tasks'][tid]['attempts'] == before['tasks'][tid]['attempts']
    assert program['deadline_utc'] == old['deadline_utc']
    assert program['delayed_service_recovery'] == old['delayed_service_recovery']


@pytest.mark.parametrize('mutation', ['active','attempt','success','veto'])
def test_registration_refuses_running_or_lost_history(tmp_path, mutation):
    old,before,program = setup(tmp_path)
    if mutation == 'active':
        before['tasks']['tool-p14-bm25']['status'] = 'RUNNING'
        with pytest.raises(Refused): repair.project_state(before, program, 'now')
    else:
        after = repair.project_state(before, program, 'now')
        if mutation == 'attempt': after['tasks']['acquire-p10']['attempts'].pop()
        elif mutation == 'success': after['tasks']['acquire-p14']['status'] = 'PENDING'
        else: after['continuation_vetoes'].clear()
        with pytest.raises(Refused): repair.validate_state_history(program, after, tmp_path)


def test_comparison_reads_successful_predecessor_arm(tmp_path, monkeypatch):
    from scripts import legal_integration_campaign as campaign
    from pathlib import Path
    monkeypatch.setattr(campaign,'ROOT',tmp_path)
    monkeypatch.setattr(campaign,'PROGRAM',Path('program.json'))
    monkeypatch.setattr(campaign,'LIVE',Path('new-live'))
    save(tmp_path/'old-product.json',{'exact':'answer'})
    save(tmp_path/'old-evidence.json',{'product':ref(tmp_path,'old-product.json')})
    save(tmp_path/'old-result.json',{'evidence':[ref(tmp_path,'old-evidence.json')]})
    save(tmp_path/'prior-state.json',{'tasks':{
        'tool-p14-bm25':{'status':'SUCCEEDED','result':ref(tmp_path,'old-result.json')},
        'baseline-p14':{'status':'FAILED'}}})
    save(tmp_path/'program.json',{'common_capacity':{'prior_state':ref(tmp_path,'prior-state.json')}})
    assert campaign.arm_result_path('p14','bm25')==tmp_path/'old-product.json'
    assert campaign.arm_result_path('p14','baseline')==tmp_path/'new-live/arms/p14/baseline/result.json'
    save(tmp_path/'old-product.json',{'changed':True})
    with pytest.raises(Refused):campaign.arm_result_path('p14','bm25')
