from copy import deepcopy
import pytest

from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_provider import SERVICE_RECOVERY_POLICY
from scripts.legal_integration_acceptance_revision import historical_projection
from scripts.legal_integration_prerequisites import (
    ROOT,BASE,DOC,PROGRAM,STATE,RECOVERY_WORK,RECOVERY_REVIEW,RECOVERY_REOPEN,
    RECOVERY_USER,RECOVERY_STAGE_CALLS,expected_recovery_program)
from scripts.legal_mission_execution import read,save,ref,validate_program,Refused


@pytest.fixture(scope='module')
def candidate():
    baseline=read(ROOT/RECOVERY_WORK/'baseline.json')
    archives={(r['previous']['path'],r['previous']['sha256']):r['archive'] for r in baseline['archived']}
    refs={r['previous']['path']:r['archive'] for r in baseline['archived']}
    directory=RECOVERY_WORK/'test-registration';local=directory/'local-review-candidate.json'
    save(ROOT/local,{'verdict':'PASS','provider_calls':0,'evidence':[ref(ROOT,RECOVERY_REVIEW)],
        'scope':'Offline candidate test; never registers or dispatches.'})
    revision={'profile':'integration-execution-recovery.v1','prior_detours':30,'additional_consolidated_revision':1,
        'live_calls_added':0,'attempts_reset':False,'user_instruction':RECOVERY_USER,
        'review':ref(ROOT,RECOVERY_REVIEW),'baseline':ref(ROOT,RECOVERY_WORK/'baseline.json'),
        'local_review':ref(ROOT,local),'checkpoints':ref(ROOT,RECOVERY_WORK/'checkpoints.json'),
        'prior_program':refs[str(PROGRAM)],'prior_state':refs[str(STATE)],
        'prior_binding':refs[str(BASE/'current-binding.json')],'prior_ledger':refs[str(BASE/'live-calls.json')],
        'reopened_nodes':list(RECOVERY_REOPEN),'semantic_stage_maximum':RECOVERY_STAGE_CALLS,
        'service_recovery_policy':SERVICE_RECOVERY_POLICY}
    before=read(ROOT/revision['prior_state']['path'])
    program=expected_recovery_program(historical_projection(read(ROOT/revision['prior_program']['path']),archives),
        before,revision,ROOT)
    state=deepcopy(before)
    for tid in RECOVERY_REOPEN:
        state['tasks'][tid].update(status='PENDING',reason='Offline candidate')
        state['tasks'][tid].pop('result',None)
    state['program_hash']=digest(program)
    return directory,program,state,before


def test_recovery_preserves_passed_sources_and_runs_review_after_failure(candidate):
    from scripts.legal_integration_master import MasterExecution
    directory,program,state,before=candidate
    validate_program(program,ROOT)
    save(ROOT/directory/'program.json',program);save(ROOT/directory/'state.json',state)
    execution=MasterExecution(ROOT,directory/'program.json',directory/'state.json')
    with execution.locked() as saved:
        for tid,row in before['tasks'].items():assert saved['tasks'][tid]['attempts']==row['attempts']
    view=execution.classify(state)
    assert not any(row['status']=='INVALID' for row in view.values())
    assert view['current-binding']['status']=='READY'
    assert all(view[t]['status']=='SUCCEEDED' for t in ('ownership-2023','ownership-2025','ownership-handbook'))
    failed=deepcopy(state);failed['tasks']['current-binding']['status']='BLOCKED'
    assert execution.classify(failed)['continuation-review']['status']=='READY'


@pytest.mark.parametrize('fault',['deadline','calls','attempts','acquisition','sources','retry','timeout'])
def test_recovery_rejects_unreviewed_extensions(candidate,fault):
    _,base,_,_=candidate;program=deepcopy(base);revision=program['execution_recovery']
    tasks={t['id']:t for t in program['tasks']}
    if fault=='deadline':program['deadline_utc']='2100-01-01T00:00:00+00:00'
    elif fault=='calls':revision['live_calls_added']=1
    elif fault=='attempts':tasks['semantic-preflight']['maximum_attempts']+=1
    elif fault=='acquisition':tasks['acquire-p10']['maximum_attempts']+=1
    elif fault=='sources':tasks['ownership-handbook']['acceptance']='Ignore missing pages'
    elif fault=='retry':revision['service_recovery_policy']['per_request_replacements']+=1
    else:revision['service_recovery_policy']['timeout_seconds']=301
    with pytest.raises(Refused):validate_program(program,ROOT)


def test_recovery_stage_charges_reserved_replacements_and_actual_timeout(tmp_path,monkeypatch):
    from datetime import datetime,timedelta,timezone
    from scripts import legal_integration_current_live as live
    monkeypatch.setattr(live,'ROOT',tmp_path);monkeypatch.setattr(live,'LIVE',__import__('pathlib').Path('live'))
    monkeypatch.setattr(live,'configure_scope',lambda:(__import__('pathlib').Path('review.md'),256,822,1))
    (tmp_path/'review.md').write_text('Offline test')
    save(tmp_path/BASE/'current-binding.json',{'service_recovery_policy':SERVICE_RECOVERY_POLICY})
    save(tmp_path/BASE/'live-calls.json',{'maximum':8100,'calls':[]})
    save(tmp_path/PROGRAM,{'execution_refresh':{}})
    grant={'maximum_calls':8100,'deadline_utc':(datetime.now(timezone.utc)+timedelta(hours=6)).isoformat()}
    save(tmp_path/BASE/'live-grant.json',grant)
    stage=live.admit_stage('question-canaries',8)
    assert stage['maximum_calls']==56 and stage['service_recovery_maximum']==48
    # 300 seconds plus reserve/backoff must be used; the former 120-second
    # arithmetic would admit a stage that cannot fit the actual reviewed bound.
    grant['deadline_utc']=(datetime.now(timezone.utc)+timedelta(hours=2)).isoformat()
    save(tmp_path/BASE/'live-grant.json',grant)
    with pytest.raises(Refused):live.admit_stage('another-stage',8)
