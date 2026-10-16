from copy import deepcopy
from datetime import datetime,timedelta,timezone
from pathlib import Path
import pytest

from scripts.legal_integration_service_continuation import (ROOT,BASE,DOC,PROGRAM,STATE,WORK,REVIEW,REOPEN,
    USER,STAGE_CALLS,expected_program,SERVICE_CONTINUATION_POLICY,projection_archives)
from scripts.legal_mission_execution import read,save,ref,validate_program,Refused
from scripts.legal_integration_acceptance_revision import historical_projection
from legalmath.canonical import digest


@pytest.fixture(scope='module')
def candidate():
    baseline=read(ROOT/WORK/'baseline.json')
    archives=projection_archives(baseline['archived'])
    refs={r['previous']['path']:r['archive'] for r in baseline['archived']}
    directory=WORK/'test-registration';local=directory/'local-review-candidate.json'
    save(ROOT/local,{'verdict':'PASS','provider_calls':0,'evidence':[ref(ROOT,REVIEW)],
        'scope':'Offline test only; never registers or dispatches.'})
    revision={'profile':'integration-service-continuation.v1','prior_detours':31,'additional_consolidated_revision':1,
        'live_calls_added':0,'attempts_reset':False,'user_instruction':USER,
        'review':ref(ROOT,REVIEW),'baseline':ref(ROOT,WORK/'baseline.json'),
        'local_review':ref(ROOT,local),'checkpoints':ref(ROOT,WORK/'checkpoints.json'),
        'prior_program':refs[str(PROGRAM)],'prior_state':refs[str(STATE)],
        'prior_binding':refs[str(BASE/'current-binding.json')],'prior_ledger':refs[str(BASE/'live-calls.json')],
        'reopened_nodes':list(REOPEN),'semantic_stage_maximum':STAGE_CALLS,
        'service_recovery_policy':deepcopy(SERVICE_CONTINUATION_POLICY)}
    before=read(ROOT/revision['prior_state']['path'])
    program=expected_program(historical_projection(read(ROOT/revision['prior_program']['path']),archives),
        before,revision,ROOT)
    state=deepcopy(before)
    for tid in REOPEN:
        state['tasks'][tid].update(status='PENDING',reason='Offline candidate')
        state['tasks'][tid].pop('result',None)
    state['program_hash']=digest(program)
    return directory,program,state,before


def test_service_continuation_preserves_sources_and_review_after_failure(candidate):
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


@pytest.mark.parametrize('fault',['deadline','calls','attempts','acquisition','sources','retry','wait','circuit'])
def test_service_continuation_rejects_unreviewed_extensions(candidate,fault):
    _,base,_,_=candidate;program=deepcopy(base);revision=program['service_continuation']
    tasks={t['id']:t for t in program['tasks']}
    if fault=='deadline':program['deadline_utc']='2100-01-01T00:00:00+00:00'
    elif fault=='calls':revision['live_calls_added']=1
    elif fault=='attempts':tasks['semantic-preflight']['maximum_attempts']+=1
    elif fault=='acquisition':tasks['acquire-p10']['maximum_attempts']+=1
    elif fault=='sources':tasks['ownership-handbook']['acceptance']='Ignore source ownership'
    elif fault=='retry':revision['service_recovery_policy']['per_request_replacements']+=1
    elif fault=='wait':revision['service_recovery_policy']['maximum_retry_after_seconds']+=1
    else:revision['service_recovery_policy']['consecutive_failure_ceiling']+=1
    with pytest.raises(Refused):validate_program(program,ROOT)


def test_stage_reserves_maximum_wait_and_jitter(tmp_path,monkeypatch):
    from scripts import legal_integration_current_live as live
    monkeypatch.setattr(live,'ROOT',tmp_path);monkeypatch.setattr(live,'LIVE',Path('live'))
    monkeypatch.setattr(live,'configure_scope',lambda:(Path('review.md'),256,822,1))
    (tmp_path/'review.md').write_text('Offline test')
    save(tmp_path/BASE/'current-binding.json',{'service_recovery_policy':SERVICE_CONTINUATION_POLICY})
    save(tmp_path/BASE/'live-calls.json',{'maximum':8100,'calls':[]});save(tmp_path/PROGRAM,{'execution_refresh':{}})
    grant={'maximum_calls':8100,'deadline_utc':(datetime.now(timezone.utc)+timedelta(hours=7)).isoformat()}
    save(tmp_path/BASE/'live-grant.json',grant)
    assert live.admit_stage('question-canaries',8)['maximum_calls']==56
    grant['deadline_utc']=(datetime.now(timezone.utc)+timedelta(hours=6)).isoformat()
    save(tmp_path/BASE/'live-grant.json',grant)
    with pytest.raises(Refused):live.admit_stage('another',8)


def test_history_points_to_old_program_bytes_without_changing_current_reference():
    from scripts.legal_integration_service_continuation import mission_archives
    rows=read(ROOT/WORK/'baseline.json')['archived']
    row=next(r for r in rows if r['previous']['path']==str(PROGRAM))
    current={'path':str(PROGRAM),'sha256':'different-current-program'}
    value={'history':[row['previous']],'current':current}
    result=historical_projection(value,mission_archives(rows))
    assert result=={'history':[row['archive']],'current':current}
