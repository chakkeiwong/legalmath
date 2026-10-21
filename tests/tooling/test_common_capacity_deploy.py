from copy import deepcopy
from pathlib import Path
import pytest
from scripts import legal_common_capacity_deploy as deploy


def environment(tmp_path, monkeypatch):
    for key, value in dict(ROOT=tmp_path, WORK=tmp_path/'work', STAGE=tmp_path/'work/staging',
            OLD=tmp_path/'old', BASE=tmp_path/'master', PROGRAM=tmp_path/'program.json',
            MISSION=tmp_path/'mission.json', PLAN=tmp_path/'plan.md').items():
        monkeypatch.setattr(deploy,key,value)
    process = dict(pid=123,start='old')
    deploy.save(deploy.PROGRAM, {'program':'old'})
    deploy.save(deploy.WORK/'implementation-files.json', ['scripts/changed.py'])
    rows = []
    for name in ('scripts/changed.py','plan.md'):
        path = deploy.STAGE/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('reviewed replacement')
        rows.append(dict(target=name,before=None,replacement=deploy.ref(path)))
    manifest = dict(profile='common-capacity-deployment.v1', deadline_utc=deploy.DEADLINE.isoformat(),
        provider_calls_added=0,evidence=[],writes=rows,
        predecessor_program=deploy.ref(deploy.PROGRAM),predecessor_worker=process)
    deploy.save(deploy.WORK/'deployment-manifest.json',manifest)
    deploy.save(deploy.OLD/'execution/worker.json', {'process':process})
    deploy.save(deploy.OLD/'execution/active-command.json', {'process':dict(pid=124,start='child')})
    deploy.save(deploy.OLD/'execution/result.json', {'commands':[]})
    commands=[]
    for i in range(4):
        row={}
        for stream in ('stdout','stderr'):
            path=deploy.OLD/('log-'+str(i)+stream)
            path.write_text('complete')
            row[stream]=deploy.ref(path)
        commands.append(row)
    deploy.save(deploy.OLD/'execution/result.json', {'commands':commands})
    deploy.save(deploy.BASE/'execution-state.json', {'tasks':{'old-owner':{'status':'FAILED'}}})
    monkeypatch.setattr(deploy,'identity',lambda pid:None)
    return manifest


@pytest.mark.parametrize('mutation', ['outside','protected','replacement','duplicate','authority','source'])
def test_manifest_refuses_unreviewed_writes(tmp_path,monkeypatch,mutation):
    manifest=environment(tmp_path,monkeypatch)
    assert deploy.checked_manifest()==manifest
    if mutation=='outside': manifest['writes'][0]['target']='../outside.py'
    elif mutation=='protected': manifest['writes'][0]['target']='.codex/config.toml'
    elif mutation=='replacement': manifest['writes'][0]['replacement']=deploy.ref(deploy.PROGRAM)
    elif mutation=='duplicate': manifest['writes'].append(deepcopy(manifest['writes'][0]))
    elif mutation=='authority': manifest['provider_calls_added']=1
    else: (deploy.STAGE/'scripts/changed.py').write_text('unreviewed')
    deploy.save(deploy.WORK/'deployment-manifest.json',manifest)
    with pytest.raises(ValueError): deploy.checked_manifest()


def test_running_predecessor_only_delays_adoption(tmp_path,monkeypatch):
    manifest=environment(tmp_path,monkeypatch)
    monkeypatch.setattr(deploy,'identity',lambda pid:manifest['predecessor_worker'])
    assert deploy.settled(manifest) is False
    with pytest.raises(ValueError):deploy.adopt()
    assert not (deploy.ROOT/'scripts/changed.py').exists()


@pytest.mark.parametrize('blocker',['child','owner','reserved','missing_result','master','logs'])
def test_settlement_requires_complete_authenticated_quiescence(tmp_path,monkeypatch,blocker):
    manifest=environment(tmp_path,monkeypatch)
    assert deploy.settled(manifest)
    if blocker=='child':
        monkeypatch.setattr(deploy,'identity',lambda pid:dict(pid=124,start='child') if pid==124 else None)
    elif blocker=='owner':
        deploy.save(deploy.BASE/'execution-state.json', {'tasks':{'old-owner':{'status':'RUNNING'}}})
    elif blocker=='reserved':
        deploy.save(deploy.OLD/'live/q/calls/dispatch.json', {'calls':{'pending':{'status':'RESERVED'}}})
    elif blocker=='missing_result': (deploy.OLD/'execution/result.json').unlink()
    elif blocker=='master': deploy.save(deploy.PROGRAM,{'changed':True})
    else: (deploy.OLD/'log-0stdout').write_text('changed')
    with pytest.raises(ValueError):deploy.settled(manifest)


def test_adopted_reentry_checks_files_without_requiring_old_master(tmp_path,monkeypatch):
    manifest=environment(tmp_path,monkeypatch)
    for row in manifest['writes']:
        path=deploy.ROOT/row['target']
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes((deploy.ROOT/row['replacement']['path']).read_bytes())
    deploy.save(deploy.WORK/'adoption.json',dict(status='APPLIED',manifest=deploy.ref(deploy.WORK/'deployment-manifest.json')))
    deploy.save(deploy.PROGRAM,{'program':'new'})
    assert deploy.adopt()['reused']
    (deploy.ROOT/'scripts/changed.py').write_text('changed')
    with pytest.raises(ValueError):deploy.adopt()


def test_command_never_reissues_an_interrupted_child(tmp_path,monkeypatch):
    environment(tmp_path,monkeypatch)
    deploy.save(deploy.WORK/'continuation-state.json',dict(stage='live',process=dict(pid=1,start='s')))
    with pytest.raises(ValueError):deploy.command('live',['never','dispatch'])


def test_worker_runs_independent_local_refresh_after_live_failure(tmp_path,monkeypatch):
    environment(tmp_path,monkeypatch)
    monkeypatch.setattr(deploy,'adopt',lambda:{'adopted':True})
    commands=[]
    def command(label,argv):
        commands.append(label)
        return dict(exit_code=1 if label=='live' else 0)
    monkeypatch.setattr(deploy,'command',command)
    # Deterministic future deadline for this isolated control only.
    from datetime import datetime,timezone,timedelta
    monkeypatch.setattr(deploy,'DEADLINE',datetime.now(timezone.utc)+timedelta(days=1))
    monkeypatch.setattr(deploy,'checked_manifest',lambda:{})
    monkeypatch.setattr(deploy,'settled',lambda _:True)
    result=deploy.worker()
    assert commands==['register','refresh','verify','live','ready','final-refresh','final-verify']
    assert result['status']=='BLOCKED' and not result['integration_complete']
