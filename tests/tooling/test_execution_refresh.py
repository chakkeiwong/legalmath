from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest

from scripts.legal_mission_execution import Execution, Refused, digest, ref, read, save, validate_program
from scripts.legal_integration_execution_refresh import REOPEN, NEW, PLAN, expected_tasks
from tests.tooling.test_legal_mission_execution import task
from tests.tooling.test_integration_campaign import approved
from legalmath.interpretation.assurance.bounded_provider import CampaignAllowance
from legalmath.errors import LegalMathError


def revision(root):
    names=list(REOPEN)+['sources','runtime','product','legal-p10','legal-p14','legal-evidence','legal-gatecoin',
                         'account-p10','account-p14','account-evidence','account-gatecoin','unrelated']
    old={'profile':'legal-mission-execution.v1','workers':2,
         'deadline_utc':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),
         'protected_evidence':[],'artifact_directory':'artifacts','tasks':[task(n) for n in names]}
    state={'program_hash':digest(old),'tasks':{n:{'status':'PENDING','attempts':[]} for n in names},'events':[]}
    save(root/'prior-program.json',old);save(root/'prior-state.json',state)
    save(root/'baseline.json',{'archived':[]})
    (root/'review.md').write_text('Reviewed finite scoped refresh.')
    (root/PLAN).parent.mkdir(parents=True);(root/PLAN).write_text('Current same master')
    review={'profile':'legal-execution-refresh.v1','prior_detours':24,'additional_consolidated_revision':1,
        'prior_charged_calls':232,'live_calls_added':0,'attempts_reset':False,'user_instruction':'Continue',
        'review':ref(root,'review.md'),'baseline':ref(root,'baseline.json'),
        'prior_program':ref(root,'prior-program.json'),'prior_state':ref(root,'prior-state.json'),
        'reopened_nodes':list(REOPEN),'new_nodes':list(NEW)}
    program=deepcopy(old);program.update(execution_refresh=review,tasks=expected_tasks(old,state,review['review']))
    program['protected_evidence'] += [review['review'],review['baseline'],ref(root,PLAN)]
    validate_program(program,root)
    return program,state


@pytest.mark.parametrize('fault',['deadline','unrelated','attempt','acquisition_dependency','calls'])
def test_refresh_rejects_unreviewed_resource_or_graph_change(tmp_path,fault):
    program,_=revision(tmp_path)
    if fault=='deadline':program['deadline_utc']='2100-01-01T00:00:00+00:00'
    if fault=='unrelated':program['tasks'][-6]['acceptance']='Changed'
    if fault=='attempt':program['tasks'][0]['maximum_attempts']+=1
    if fault=='acquisition_dependency':
        next(t for t in program['tasks'] if t['id']=='live-approval')['requires']=[]
    if fault=='calls':program['global_call_ceiling']=9999
    with pytest.raises(Refused):validate_program(program,tmp_path)


def test_inventory_branch_is_ready_despite_failed_semantic_consumer(tmp_path):
    program,state=revision(tmp_path)
    for tid in NEW:state['tasks'][tid]={'status':'PENDING','attempts':[]}
    state['tasks']['sources']['status']='SUCCEEDED'
    state['tasks']['account-p10']['status']='SUCCEEDED'
    state['tasks']['current-binding']['status']='BLOCKED'
    state['program_hash']=digest(program)
    save(tmp_path/'program.json',program);save(tmp_path/'state.json',state)
    view=Execution(tmp_path,'program.json','state.json').summary()
    assert 'inventory-p10' in view['ready']
    assert view['tasks']['semantic-preflight']['status']=='DEPENDENCY_BLOCKED'
    assert 'live-approval' not in view['ready']


def current_binding(root):
    route=approved(root);grant=read(root/'live-grant.json')
    allowance=CampaignAllowance(root,route,root=root)
    allowance.expected='earlier';allowance.reserve('earlier')
    old=ref(root,'bound.py');(root/'old.py').write_bytes((root/'bound.py').read_bytes())
    (root/'bound.py').write_text('# reviewed current code\n')
    (root/'review.md').write_text('Reviewed current code under unchanged resources.')
    save(root/'before.json',read(root/'live-calls.json'))
    binding={'profile':'integration-current-binding.v1','user_instruction':'Continue',
        'review':ref(root,'review.md'),'grant_hash':digest(grant),'maximum_calls':grant['maximum_calls'],
        'deadline_utc':grant['deadline_utc'],'routing_hash':digest(route),
        'ledger_before':ref(root,'before.json'),'bindings':[ref(root,'bound.py')],
        'historical_archives':[{'previous':old,'archive':ref(root,'old.py')}]}
    save(root/'current-binding.json',binding)
    stage={'grant_hash':digest(grant),'binding_hash':digest(binding),'ledger_before':ref(root,'before.json'),
           'maximum_calls':1}
    save(root/'stage.json',stage);save(root/'current-stage.json',ref(root,'stage.json'))
    return allowance,binding


def test_current_binding_preserves_history_and_bounds_stage_before_dispatch(tmp_path):
    allowance,_=current_binding(tmp_path)
    assert len(allowance.check()['calls'])==1
    allowance.expected='current';assert allowance.reserve('current')==2
    allowance.expected='excess'
    with pytest.raises(LegalMathError) as caught:allowance.reserve('excess')
    assert caught.value.code=='E_RESOURCE_LIMIT'
    assert len(allowance.check()['calls'])==2


@pytest.mark.parametrize('fault',['current_code','old_code','prior_charge','route','grant'])
def test_current_binding_refuses_changed_identity(tmp_path,fault):
    allowance,binding=current_binding(tmp_path)
    if fault=='current_code':(tmp_path/'bound.py').write_text('Changed')
    if fault=='old_code':(tmp_path/'old.py').write_text('Changed')
    if fault=='prior_charge':
        state=read(tmp_path/'live-calls.json');state['calls'][0]['request_hash']='changed';save(tmp_path/'live-calls.json',state)
    if fault=='route':allowance.routing['model']='changed'
    if fault=='grant':
        binding['maximum_calls']+=1;save(tmp_path/'current-binding.json',binding)
    with pytest.raises(LegalMathError):allowance.check()


def test_rendered_footnote_id_is_not_assumed_equal_to_display():
    from scripts.legal_integration_source_ownership import rendered_text,visible_label
    text=rendered_text('A\nA  7     A rendered footnote with a source passage.       B\nB\n')
    assert visible_label(text,'A rendered footnote with a source passage.','7')
    assert not visible_label(text,'A rendered footnote with a source passage.','17')


def test_retained_account_keeps_verified_historical_dependency_snapshot(tmp_path):
    from tests.tooling.test_legal_mission_execution import finish
    program,_=revision(tmp_path)
    old=read(tmp_path/'prior-program.json')
    next(t for t in old['tasks'] if t['id']=='account-p10')['after']=['ownership-2023']
    save(tmp_path/'old-program.json',old)
    old_execution=Execution(tmp_path,'old-program.json','old-state.json')
    old_execution.start('ownership-2023');finish(old_execution,'ownership-2023','BLOCKED')
    old_execution.start('account-p10');finish(old_execution,'account-p10')
    before=read(tmp_path/'old-state.json')
    save(tmp_path/'prior-program.json',old);save(tmp_path/'prior-state.json',before)
    rev=program['execution_refresh']
    rev.update(prior_program=ref(tmp_path,'prior-program.json'),prior_state=ref(tmp_path,'prior-state.json'))
    program['tasks']=expected_tasks(old,before,rev['review'])
    state=deepcopy(before)
    for tid in NEW:state['tasks'][tid]={'status':'PENDING','attempts':[]}
    state['tasks']['ownership-2023'].update(status='PENDING',reason='Reviewed source extension')
    state['tasks']['ownership-2023'].pop('result')
    state['program_hash']=digest(program)
    save(tmp_path/'program.json',program);save(tmp_path/'state.json',state)
    execution=Execution(tmp_path,'program.json','state.json')
    assert execution.summary()['tasks']['account-p10']['status']=='SUCCEEDED'
    (tmp_path/'ownership-2023-result.json').write_text('Changed historical dependency')
    assert execution.summary()['tasks']['account-p10']['status']=='INVALID'
