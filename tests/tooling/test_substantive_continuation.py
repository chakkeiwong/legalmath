"""The substantive follow-up is additive and never renews live work."""
from copy import deepcopy

import pytest

from scripts.legal_mission_execution import Execution, Refused, digest, ref, save, validate_program
from tests.tooling.test_legal_mission_execution import task
from tests.tooling.test_remaining_work_revision import revised


def followup(root):
    old, state = revised(root)
    save(root/'before.json', old)
    state['program_hash'] = digest(old)
    save(root/'before-state.json', state)
    for name in ('followup-plan.md','followup-review.md','followup-baseline.json'):
        (root/name).write_text('Reviewed local continuation '+name)
    program = deepcopy(old)
    new_task = task('ownership-2023', executor='command',
        command=['.venv/bin/python','scripts/legal_integration_master.py','worker','ownership-2023'],
        timeout_seconds=60, maximum_attempts=1)
    program['tasks'].append(new_task)
    program['substantive_continuation_revision'] = {
        'profile':'legal-substantive-continuation.v1','prior_detours':22,
        'additional_consolidated_revision':1,'prior_charged_calls':232,
        'live_calls_added':0,'attempts_reset':False,'user_instruction':'Execute reviewed local work',
        'plan':ref(root,'followup-plan.md'),'review':ref(root,'followup-review.md'),
        'prior_program':ref(root,'before.json'),'prior_state':ref(root,'before-state.json'),
        'baseline':ref(root,'followup-baseline.json'),'reopened_nodes':['ownership-2023'],
        'attempt_ceilings':{'ownership-2023':1}}
    validate_program(program,root)
    return program,state


@pytest.mark.parametrize('fault',['deadline','old_task','live','new_attempt','calls'])
def test_followup_rejects_history_or_authority_changes(tmp_path,fault):
    program,_ = followup(tmp_path)
    if fault=='deadline':program['deadline_utc']='2101-01-01T00:00:00+00:00'
    if fault=='old_task':program['tasks'][0]['acceptance']='changed'
    if fault=='live':
        program['tasks'][-1]['id']='acquire-new'
        program['substantive_continuation_revision']['reopened_nodes']=['acquire-new']
        program['substantive_continuation_revision']['attempt_ceilings']={'acquire-new':1}
    if fault=='new_attempt':
        program['tasks'][-1]['maximum_attempts']=2
        program['substantive_continuation_revision']['attempt_ceilings']['ownership-2023']=2
    if fault=='calls':program['global_call_ceiling']=8100
    with pytest.raises(Refused):validate_program(program,tmp_path)


def test_followup_preserves_attempts_and_independent_ready_work(tmp_path):
    program,state=followup(tmp_path)
    save(tmp_path/'program.json',program)
    state['program_hash']=digest(program)
    state['tasks']['ownership-2023']={'status':'PENDING','attempts':[]}
    save(tmp_path/'state.json',state)
    execution=Execution(tmp_path,'program.json','state.json')
    assert set(execution.summary()['ready']) >= {'ownership-2023','product','acquire-p10'}
    state['tasks']['runtime']['attempts']=[]
    save(tmp_path/'state.json',state)
    with pytest.raises(Refused,match='Historical attempts'):execution.summary()


def corrected(root):
    program,state=followup(root)
    program['artifact_directory']='artifacts'
    state['tasks']['ownership-2023']={'status':'SUCCEEDED','attempts':[{'number':1}]}
    state['program_hash']=digest(program)
    save(root/'first-program.json',program);save(root/'first-state.json',state)
    for name in ('correction-review.md','correction-baseline.json'):
        (root/name).write_text('Reviewed correction '+name)
    correction={'profile':'legal-substantive-correction.v1','prior_detours':23,
        'additional_consolidated_revision':1,'live_calls_added':0,
        'review':ref(root,'correction-review.md'),'baseline':ref(root,'correction-baseline.json'),
        'prior_program':ref(root,'first-program.json'),'prior_state':ref(root,'first-state.json'),
        'attempt_ceilings':{'ownership-2023':2}}
    program['substantive_continuation_revision']['post_review']=correction
    program['tasks'][-1].update(maximum_attempts=2,deliverable='artifacts/ownership-2023/attempt-2/result.json')
    validate_program(program,root)
    return program,state


@pytest.mark.parametrize('fault',['third_attempt','dependency','first_result','live_calls'])
def test_correction_cannot_renew_or_change_scope(tmp_path,fault):
    program,state=corrected(tmp_path)
    correction=program['substantive_continuation_revision']['post_review']
    if fault=='third_attempt':
        correction['attempt_ceilings']['ownership-2023']=3
        program['tasks'][-1]['maximum_attempts']=3
    elif fault=='dependency':program['tasks'][-1]['requires']=['product']
    elif fault=='live_calls':correction['live_calls_added']=1
    else:
        state['tasks']['ownership-2023']['attempts']=[]
        save(tmp_path/'first-state.json',state)
    with pytest.raises(Refused):validate_program(program,tmp_path)


def test_correction_preserves_first_attempt_in_execution(tmp_path):
    program,state=corrected(tmp_path)
    state['program_hash']=digest(program)
    state['tasks']['ownership-2023']['status']='PENDING'
    save(tmp_path/'program.json',program);save(tmp_path/'state.json',state)
    execution=Execution(tmp_path,'program.json','state.json')
    assert 'ownership-2023' in execution.summary()['ready']
    state['tasks']['ownership-2023']['attempts'][0]['number']=99
    save(tmp_path/'state.json',state)
    with pytest.raises(Refused,match='Historical attempts'):execution.summary()

