from copy import deepcopy
import pytest
from scripts import legal_integration_candidate_retry as repair
from scripts.legal_mission_execution import save, ref, Refused


def setup(root):
    old = {'tasks': [{'id':'acquire-'+q,'maximum_attempts':n,'inputs':[],'deliverable':'old'}
        for q,n in repair.ATTEMPTS.items()] + [{'id':'answer-p10','maximum_attempts':2,'inputs':[]}],
        'protected_evidence':[], 'deadline_utc':repair.DEADLINE, 'global_call_ceiling':0,
        'synthesis_resolution':{'recoveries':{'p10':'old'}},
        'delayed_service_recovery':{'maximum_replacements':24}}
    before = {'tasks':{t['id']:{'status':'FAILED','attempts':[{'number':i} for i in range(t['maximum_attempts'])]}
        for t in old['tasks']},'events':[],'continuation_vetoes':[{'reason':'unrelated'}]}
    save(root/'before.json',before)
    save(root/repair.PLAN,{'plan':'current'})
    revision = {'prior_state':ref(root,'before.json'),'implementation':{},'review':{},'result':{},
        'baseline':{},'checkpoints':{}}
    return old,before,repair.expected_program(old,revision,root)


def test_retry_changes_only_exhausted_owners_and_preserves_shared_authority(tmp_path):
    old,before,program = setup(tmp_path)
    for prior,current in zip(old['tasks'],program['tasks']):
        if prior['id'] in repair.REOPEN:
            assert current['maximum_attempts']==prior['maximum_attempts']+1
        else:
            assert current==prior
    for k in ('deadline_utc','global_call_ceiling','synthesis_resolution','delayed_service_recovery'):
        assert program[k]==old[k]
    state=repair.project_state(before,program,'now')
    repair.validate_state_history(program,state,tmp_path)
    for tid in repair.REOPEN:
        assert state['tasks'][tid]['status']=='PENDING'
        assert state['tasks'][tid]['attempts']==before['tasks'][tid]['attempts']


@pytest.mark.parametrize('change',['running','resample_success','lost_attempt','lost_veto','unrelated'])
def test_retry_refuses_history_loss_or_resampling(tmp_path,change):
    old,before,program=setup(tmp_path)
    if change in ('running','resample_success'):
        before['tasks']['acquire-p10']['status']='RUNNING' if change=='running' else 'SUCCEEDED'
        with pytest.raises(Refused):repair.project_state(before,program,'now')
        return
    state=repair.project_state(before,program,'now')
    if change=='lost_attempt':state['tasks']['acquire-p10']['attempts'].pop()
    elif change=='lost_veto':state['continuation_vetoes'].clear()
    else:state['tasks']['answer-p10']['status']='PENDING'
    with pytest.raises(Refused):repair.validate_state_history(program,state,tmp_path)


def test_existing_exact_historical_alias_is_preserved_and_verified(tmp_path):
    source='src/legalmath/interpretation/assurance/phased/preparation_diagnosis.py'
    save(tmp_path/'old-copy.json',{'original':'exact bytes'})
    save(tmp_path/'new-copy.json',{'original':'exact bytes'})
    older=ref(tmp_path,'old-copy.json');newer=ref(tmp_path,'new-copy.json')
    row=dict(previous={'path':source,'sha256':older['sha256']},archive=older)
    save(tmp_path/'prior-binding.json',{'historical_archives':[row]})
    binding=ref(tmp_path,'prior-binding.json')
    baseline={'archived':[dict(previous={'path':str(repair.BASE/'current-binding.json'),'sha256':binding['sha256']},archive=binding),
        {**row,'archive':newer}]}
    frozen=deepcopy(baseline)
    assert repair.projection(baseline,root=tmp_path)[(source,older['sha256'])]==older
    assert baseline==frozen
    save(tmp_path/'old-copy.json',{'original':'tampered'})
    with pytest.raises(Refused):repair.projection(baseline,root=tmp_path)
