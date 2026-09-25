from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import sys
import pytest
from legalmath.canonical import canonical,loads,raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.operations import snapshot_registry,execute,bounded_process,snapshot_dispatch_inputs,attention
from legalmath.interpretation.assurance.authorities import AuthorityCatalog
from legalmath.interpretation.assurance.engine import Assurance
from legalmath.java.host_package import prepare,run,verify_package
from legalmath.interpretation.search.formal import bundle
from legalmath.interpretation.assurance.sources import acquire_context,packet_from_context
from tests.search.support import FunctionProvider
from tests.search.test_formal import AT
from .test_integration import source,settings,responder
from .support import reading


def registry(tmp_path):
    doc=source();(tmp_path/'source.txt').write_bytes(doc['data'])
    config={'documents':[{'url':doc['url'],'media_type':'text/plain','path':'source.txt'}],
        'controls':[{'control_id':'gift','source':doc['url'],'dependencies':[],'selected_slice':'Gift control'}],
        'cadence_seconds':10,'max_attempts':2,'fact_schema_hash':'fixture.v1'}
    path=tmp_path/'registry.json';path.write_bytes(canonical(config));return path,config


def test_registry_snapshot_pins_bytes_and_revisions_preserve_history(tmp_path):
    path,config=registry(tmp_path);a=snapshot_registry(path,tmp_path/'snapshots',tmp_path)
    assert snapshot_registry(path,tmp_path/'snapshots',tmp_path)==a
    old={str(p):p.read_bytes() for p in Path(a['directory']).rglob('*') if p.is_file()}
    (tmp_path/'source.txt').write_text('Changed source')
    b=snapshot_registry(path,tmp_path/'snapshots',tmp_path)
    assert a['snapshot_id']!=b['snapshot_id'] and all(Path(p).read_bytes()==v for p,v in old.items())
    Path(a['directory'],'sources/0.bin').write_text('Corrupted snapshot')
    (tmp_path/'source.txt').write_bytes(source()['data'])
    with pytest.raises(LegalMathError):snapshot_registry(path,tmp_path/'snapshots',tmp_path)


@pytest.mark.parametrize('change',['outside','duplicate','source','sha','command'])
def test_registry_rejects_wrong_sources_and_arbitrary_commands(tmp_path,change):
    path,c=registry(tmp_path)
    if change=='outside':c['documents'][0]['path']='/etc/passwd'
    if change=='duplicate':c['controls'].append(deepcopy(c['controls'][0]))
    if change=='source':c['controls'][0]['source']='https://www.sfc.hk/missing'
    if change=='sha':c['documents'][0]['sha256']='0'*64
    if change=='command':c['command']='arbitrary executable'
    path.write_bytes(canonical(c))
    with pytest.raises(LegalMathError):snapshot_registry(path,tmp_path/'snapshots',tmp_path)


def test_scheduler_replays_actual_monitor_process_and_unchanged_second_tick(root,tmp_path):
    path,_=registry(tmp_path);config=settings();responses=[];normal=responder()
    def respond(request):
        value=normal(request);responses.append(value);return value
    jdk=root/'.localresources/java-toolchain/jdk-17.0.20.1+1'
    Assurance(tmp_path/'preparation',FunctionProvider(respond),jdk,AT,config).drive([source()],'Gift control')
    replay=tmp_path/'responses.json';replay.write_bytes(canonical(responses))
    settings_path=tmp_path/'settings.json';settings_path.write_bytes(canonical(config.model_dump()))
    args=SimpleNamespace(config=path,resource_root=tmp_path,out=tmp_path/'scheduler',jdk=jdk,at=AT,
        settings=settings_path,replay_responses=replay,allowance=None,total_calls=100,ticks=2,interval_seconds=0,tick_timeout_seconds=30)
    result=execute(args)
    assert all(r['status']=='RETURNED' for r in result['ticks']),result
    assert result['ticks'][0]['result']['results'][0]['status']=='COMPLETED'
    assert result['ticks'][1]['result']['results'][0]['status']=='UNCHANGED'
    assert len(list((tmp_path/'scheduler/dispatches').glob('*')))==2


def test_timeout_stops_actual_child_and_retains_failed_dispatch(tmp_path):
    script='import subprocess,sys,time; subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"],start_new_session=True); time.sleep(30)'
    result=bounded_process([sys.executable,'-c',script],tmp_path/'dispatch',1)
    assert result['status']=='FAILED' and result['reason']=='TICK_TIMEOUT'
    assert len(result['terminated_dispatch_pids'])==2
    assert (tmp_path/'dispatch/reservation.json').is_file()


def test_java_package_runs_separate_host_and_rejects_corruption(root,tmp_path):
    doc=source();p=packet_from_context(acquire_context([doc]),'Gift');r=reading();uid=p['units'][0]['unit_id']
    r['citations']=[{'unit_id':uid,'quote':p['units'][0]['text']}]
    for fact in r['formalization']['facts']:fact['source_unit_ids']=[uid]
    b=bundle(r,p,AT);snap={'subject_id':'gift','facts':{name:{'type':'bool','status':'known','value':True,
        'evidence_ids':['fixture'],'valid_from':AT,'valid_until':None,'recorded_at':AT} for name in ('gift','discount')}}
    cases=[{'id':'discount','bundle':b,'snapshot':snap,'rule_id':'selected.control','valid_at':AT,'known_at':AT,'expected':{'status':'FALSE'}}]
    jdk=root/'.localresources/java-toolchain/jdk-17.0.20.1+1';out=tmp_path/'package'
    metadata=prepare(b,cases,{doc['url']:doc['data']},out,jdk)
    assert run(out,snap,'selected.control',AT,jdk)['status']=='FALSE'
    assert not metadata['release_eligible']
    (out/metadata['jar']).write_bytes(b'corrupted')
    with pytest.raises(LegalMathError):run(out,snap,'selected.control',AT,jdk)


def test_authority_identity_and_date_evidence_changes_invalidate_dependencies():
    from .test_authorities import catalog_data
    value,docs=catalog_data();old=AuthorityCatalog(value,docs).version_dependencies(['code.3.11'],AT)
    changed=deepcopy(value);changed['authorities'][0]['issuer']='Another issuer'
    assert AuthorityCatalog(changed,docs).version_dependencies(['code.3.11'],AT)!=old
    changed=deepcopy(value);changed['aliases'][0]['basis']='Changed identity interpretation'
    assert AuthorityCatalog(changed,docs).version_dependencies(['code.3.11'],AT)!=old


def test_exact_dispatch_settings_and_replay_bytes_are_snapshotted(tmp_path):
    settings_path=tmp_path/'settings.json';settings_path.write_text('{"setting":1}')
    replay=tmp_path/'replay.json';replay.write_text('[]')
    args=SimpleNamespace(settings=settings_path,replay_responses=replay,at=AT,jdk=tmp_path,total_calls=100)
    copied,record=snapshot_dispatch_inputs(args,tmp_path/'snapshots')
    assert Path(copied.settings).read_bytes()==settings_path.read_bytes()
    settings_path.write_text('{"setting":2}')
    assert Path(copied.settings).read_text()=='{"setting":1}'
    _,new=snapshot_dispatch_inputs(args,tmp_path/'snapshots')
    assert new['snapshot_id']!=record['snapshot_id']
    Path(copied.replay_responses).write_text('["corrupted"]')
    settings_path.write_text('{"setting":1}')
    with pytest.raises(LegalMathError):snapshot_dispatch_inputs(args,tmp_path/'snapshots')


def test_monitor_nested_failures_and_unresolved_meaning_remain_visible(tmp_path):
    from legalmath.interpretation.assurance.monitor import Monitor
    control=[{'control_id':'gift','source':'s','dependencies':[]}];monitor=Monitor(tmp_path)
    def unresolved(c,s):return {'status':'UNRESOLVED','execution_complete':True,'release_eligible':False,'findings':[{'kind':'UNKNOWN_MEANING'}]}
    first=monitor.tick(control,{'s':'v'},'m','f',0,unresolved)
    second=monitor.tick(control,{'s':'v'},'m','f',1,unresolved)
    assert first['results'][0]['status']=='COMPLETED' and second['results'][0]['status']=='UNCHANGED'
    assert attention(first)==attention(second)==[{'kind':'INTERPRETATION_UNRESOLVED','control_id':'gift'}]
    assert attention({'overdue':True,'results':[{'control_id':'gift','status':'REVISION_RETRY_LIMIT'}]})==[
        {'kind':'MISSED_CADENCE'},{'kind':'REVISION_RETRY_LIMIT','control_id':'gift'}]
    evidence=tmp_path/'results'/(first['results'][0]['result_hash']+'.json');evidence.write_text('{}')
    with pytest.raises(LegalMathError):monitor.tick(control,{'s':'v'},'m','f',2,unresolved)
