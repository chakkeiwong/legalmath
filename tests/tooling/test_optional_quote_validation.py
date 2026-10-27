"""A quotation repair preserves history and does not interrupt active calls."""
from copy import deepcopy
from pathlib import Path
import signal
import pytest
from scripts import legal_optional_quote_validation as repair
from scripts.legal_mission_execution import Refused, read, save

def owner_fixture(tmp_path,monkeypatch):
    monkeypatch.setattr(repair,'ROOT',tmp_path)
    monkeypatch.setattr(repair,'verify_preparation',lambda: {})
    save(tmp_path/repair.HERE/'local-result.json',dict(verdict='PASS',provider_calls=0,evidence=[]))
    owner=dict(pid=987654,start='123')
    for name in ('armed.json','worker.json'):
        save(tmp_path/repair.OLD_WORK/name,dict(process=owner))
    save(tmp_path/repair.STATE,dict(tasks={'baseline-p14':dict(status='RUNNING',
        attempts=[dict(number=i) for i in range(1,6)],master_live=True,live_supervisor=owner)}))
    save(tmp_path/repair.BASE/'current-binding.json',dict(phase_service_scope=dict(path='service/scope.json')))
    save(tmp_path/'service/service-circuit.json',dict(open=False))
    save(tmp_path/repair.BASE/'live-calls.json',dict(calls=[dict(slot=1)]))
    save(tmp_path/repair.SOURCE/'arms/p14/baseline/calls/dispatch.json',dict(calls={'one':dict(status='VALIDATED')}))
    alive=[True];signals=[]
    monkeypatch.setattr(repair,'process_identity',lambda _:owner if alive[0] else None)
    monkeypatch.setattr(repair,'process_alive',lambda _:alive[0])
    monkeypatch.setattr(repair,'owner_children',lambda _: '')
    monkeypatch.setattr(repair,'owner_state',lambda _: 'T')
    def kill(pid,number):
        assert pid==owner['pid'];signals.append(number)
        if number==signal.SIGTERM: alive[0]=False
    monkeypatch.setattr(repair.os,'kill',kill)
    return owner,signals

@pytest.mark.parametrize('problem',['reserved','open','half_open_reserved','half_open_request_hash',
    'half_open_schema_hash','child','identity','different_owner','provider_lock'])
def test_uncertain_boundary_sends_no_signal(tmp_path,monkeypatch,problem):
    owner,signals=owner_fixture(tmp_path,monkeypatch)
    if problem=='reserved':
        save(tmp_path/repair.SOURCE/'arms/p14/baseline/calls/dispatch.json',dict(calls={'one':dict(status='RESERVED')}))
    elif problem in ('open','half_open_reserved','half_open_request_hash','half_open_schema_hash'):
        circuit=dict(open=False);circuit[problem]=True;save(tmp_path/'service/service-circuit.json',circuit)
    elif problem=='child': monkeypatch.setattr(repair,'owner_children',lambda _: '999')
    elif problem=='identity': monkeypatch.setattr(repair,'process_identity',lambda _:None)
    elif problem=='different_owner':
        state=read(tmp_path/repair.STATE);state['tasks']['baseline-p14']['live_supervisor']=dict(pid=111,start='222')
        save(tmp_path/repair.STATE,state)
    if problem in ('identity','different_owner'):
        with pytest.raises(Refused): repair.settle_once()
    elif problem=='provider_lock':
        import fcntl
        with (tmp_path/'service/service-worker.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            assert not repair.settle_once()['settled']
    else: assert not repair.settle_once()['settled']
    assert signals==[] and not (tmp_path/repair.HERE/'handover.json').exists()

def test_idle_boundary_preserves_attempt_and_ledger(tmp_path,monkeypatch):
    owner,signals=owner_fixture(tmp_path,monkeypatch)
    before=(tmp_path/repair.STATE).read_bytes();ledger=(tmp_path/repair.BASE/'live-calls.json').read_bytes()
    result=repair.settle_once()
    assert result['supervisor_ended'] and result['process']==owner and result['calls']==1
    assert signals==[signal.SIGSTOP,signal.SIGTERM,signal.SIGCONT]
    assert (tmp_path/repair.STATE).read_bytes()==before
    assert (tmp_path/repair.BASE/'live-calls.json').read_bytes()==ledger
    assert repair.settle_once()==result and len(signals)==3

@pytest.mark.parametrize('change',['journal','binding'])
def test_change_after_stop_resumes_original_owner(tmp_path,monkeypatch,change):
    _,signals=owner_fixture(tmp_path,monkeypatch)
    kill=repair.os.kill
    def changed(pid,number):
        kill(pid,number)
        if number==signal.SIGSTOP:
            if change=='journal':
                save(tmp_path/repair.SOURCE/'arms/gatecoin/baseline/calls/dispatch.json',dict(calls={}))
            else:
                monkeypatch.setattr(repair,'verify_preparation',lambda: (_ for _ in ()).throw(Refused('Changed binding')))
    monkeypatch.setattr(repair.os,'kill',changed)
    with pytest.raises(Refused):repair.settle_once()
    assert signals==[signal.SIGSTOP,signal.SIGCONT]
    assert not (tmp_path/repair.HERE/'handover.json').exists()

def test_state_history_preserves_successes_attempts_and_vetoes(tmp_path):
    before=dict(tasks={'p':dict(status='RUNNING',attempts=[dict(number=1)]),
        'done':dict(status='SUCCEEDED',attempts=[dict(number=1)])},events=[dict(action='old')],
        continuation_vetoes=[dict(scope=['p'])])
    save(tmp_path/'before.json',before)
    program=dict(review_repair={repair.KEY:dict(prior_state=dict(path='before.json'))})
    current=deepcopy(before);current['events'].append(dict(action='new'))
    repair.validate_history(program,current,tmp_path)
    for damaged in ('attempt','success','veto'):
        value=deepcopy(current)
        if damaged=='attempt':value['tasks']['p']['attempts'][0]['number']=2
        elif damaged=='success':value['tasks']['done']['status']='PENDING'
        else:value['continuation_vetoes']=[]
        with pytest.raises(Refused):repair.validate_history(program,value,tmp_path)

def checkpoint_pair(tmp_path,monkeypatch):
    entries=[]
    for label,status in (('old','FAILED'),('new','VALIDATED')):
        entry={}
        for name in ('request','schema','result','dispatch'):
            path=Path(label)/(name+'.json')
            save(tmp_path/path,dict(status=status) if name=='result' else dict(contract=label))
            entry[name]=repair.ref(tmp_path,path)
        entry['mode']='RETAINED_FAILURE' if label=='old' else 'VALIDATED'
        entries.append(entry)
    monkeypatch.setattr(repair,'CORRECTED_HASHES',{name:tuple(e[name]['sha256'] for e in entries)
        for name in ('request','schema','result')})
    return entries

def test_known_changed_request_preserves_both_contracts(tmp_path,monkeypatch):
    old,new=checkpoint_pair(tmp_path,monkeypatch)
    before=deepcopy((old,new))
    record=repair.checkpoint_predecessor(tmp_path,'p14','baseline',repair.CORRECTED_KEY,old,new)
    assert record['previous']==old and record['current']==new
    assert (old,new)==before
    assert repair.checkpoint_predecessor(tmp_path,'p14','baseline',repair.CORRECTED_KEY,old,old) is None

@pytest.mark.parametrize('damage',['key','question','arm','request','schema','result','veto','old_status'])
def test_unreviewed_checkpoint_replacement_is_refused(tmp_path,monkeypatch,damage):
    old,new=checkpoint_pair(tmp_path,monkeypatch)
    qid,arm,key='p14','baseline',repair.CORRECTED_KEY
    if damage=='key':key+='other'
    elif damage=='question':qid='gatecoin'
    elif damage=='arm':arm='bm25'
    elif damage in ('request','schema','result'):
        path=Path(new[damage]['path']);value=read(tmp_path/path);value['changed']=True
        save(tmp_path/path,value);new[damage]=repair.ref(tmp_path,path)
    elif damage=='veto':
        path=Path(new['result']['path']);save(tmp_path/path,dict(status='VALIDATED',continuation_veto=True))
        new['result']=repair.ref(tmp_path,path)
    else:
        path=Path(old['result']['path']);save(tmp_path/path,dict(status='VALIDATED',value='old success'))
        old['result']=repair.ref(tmp_path,path)
    with pytest.raises(Refused):repair.checkpoint_predecessor(tmp_path,qid,arm,key,old,new)

def test_exact_saved_corrected_contract_collision():
    program=read(repair.ROOT/repair.PROGRAM)
    checkpoint=read(repair.ROOT/program['review_repair']['deployment']['arm_checkpoints']['p14']['baseline']['path'])
    old=checkpoint['calls'][repair.CORRECTED_KEY]
    folder=repair.SOURCE/'arms/p14/baseline/calls'/repair.CORRECTED_KEY
    current={name:repair.ref(repair.ROOT,folder/(name+'.json')) for name in ('request','schema','result')}
    current['dispatch']=repair.ref(repair.ROOT,folder.parent/'dispatch.json')
    result=repair.checkpoint_predecessor(repair.ROOT,'p14','baseline',repair.CORRECTED_KEY,old,current)
    assert result['previous']['mode']=='RETAINED_FAILURE'
    assert read(repair.ROOT/result['current']['result']['path'])['value']['verdict']=='UNRESOLVED'
