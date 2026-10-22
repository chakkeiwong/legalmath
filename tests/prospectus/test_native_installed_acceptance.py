"""Installed acceptance refuses incomplete or misleading evidence without native calls."""
from copy import deepcopy
import hashlib
from pathlib import Path
import zipfile
import pytest

from legalmath.prospectus import native_installed_acceptance as installed
from legalmath.prospectus.execution_authority import write, file_hash
from legalmath.prospectus.successor import process_ledger


def proof(environment):
    methods={'prospectus/native_profile.py':'a'*64}
    package=environment/'lib/python3.11/site-packages/legalmath'
    value={'module_path':str(package/'prospectus/native_profile.py'),
           'python':str(environment/'bin/python'),'methods':methods,
           'sys_path':[str(package.parent)]}
    return value,methods


@pytest.mark.parametrize('change',['module','python','method','editable','missing-site'])
def test_installed_proof_rejects_wrong_location_or_method(tmp_path,change):
    value,methods=proof(tmp_path)
    installed.installed_proof(value,tmp_path,methods)
    value=deepcopy(value)
    if change=='module': value['module_path']='/checkout/src/legalmath/prospectus/native_profile.py'
    elif change=='python': value['python']='/checkout/.venv/bin/python'
    elif change=='method': value['methods']['prospectus/native_profile.py']='b'*64
    elif change=='editable': value['sys_path'].append('/checkout/src')
    else: value['sys_path']=[]
    with pytest.raises(ValueError): installed.installed_proof(value,tmp_path,methods)


@pytest.mark.parametrize('change',['missing','duplicate','launched','false','wrong-reason'])
def test_installed_controls_reject_incomplete_or_false_evidence(tmp_path,change):
    value,methods=proof(tmp_path)
    value.update(status='PASS',native_starts=0,cases=[{'case':k,'refused':True,'error':v} for k,v in installed.ERRORS.items()])
    assert installed.control_evidence(value,tmp_path,methods)==11
    if change=='missing': value['cases'].pop()
    elif change=='duplicate': value['cases'][-1]=value['cases'][0]
    elif change=='launched': value['native_starts']=1
    elif change=='false': value['cases'][0]['refused']=False
    else: value['cases'][0]['error']='Unrelated failure'
    with pytest.raises(ValueError): installed.control_evidence(value,tmp_path,methods)


def test_installed_wheel_requires_actual_method_bytes(tmp_path):
    path=tmp_path/'local.whl'
    data=b'current optional module'
    name='prospectus/native_profile.py'
    with zipfile.ZipFile(path,'w') as archive: archive.writestr('legalmath/'+name,data)
    write(tmp_path/'built-wheel.json',{'file':path.name,'sha256':file_hash(path)})
    methods={name:hashlib.sha256(data).hexdigest()}
    installed.wheel_evidence(tmp_path,methods)
    with pytest.raises(ValueError,match='method differs'):
        installed.wheel_evidence(tmp_path,{name:'0'*64})
    path.write_bytes(b'wrong wheel')
    with pytest.raises(ValueError,match='identity changed'): installed.wheel_evidence(tmp_path,methods)


def campaign(tmp_path):
    old=tmp_path/'attempt-001'; current=tmp_path/'attempt-002'
    old.mkdir(); current.mkdir()
    (old/'invocations/capture').mkdir(parents=True)
    (old/'commands/capture').mkdir(parents=True)
    write(old/'result.json',{'status':'FAIL'})
    write(old/'invocations/capture/result.json',{'status':'FAIL'})
    (old/'commands/capture/stderr').write_text('Invalid or reserved snapshot destination')
    for folder,name,limit,history,n in [(old,'command',18,0,5),(old,'native',6,50,0),
                                       (current,'command',13,5,13),(current,'native',6,50,4)]:
        path=folder/(name+'-ledger.json')
        process_ledger.create(path,limit,history,'Synthetic deterministic accounting fixture')
        for i in range(n):
            index=process_ledger.reserve(path,['synthetic',str(i)])
            process_ledger.transition(path,index,pid=100+i)
    for i,name in enumerate(installed.COMMANDS):
        folder=current/'commands'/name; folder.mkdir(parents=True)
        write(folder/'command.json',{'argv':['synthetic',str(i)],'timeout':120,
              'environment':{'CUDA_VISIBLE_DEVICES':'-1','PYTHONPATH':'','PYTHONNOUSERSITE':'1'}})
        write(folder/'result.json',{'returncode':0})
    write(old/'outputs.json',{str(p.relative_to(old)):file_hash(p) for p in old.rglob('*') if p.is_file()})
    return current


@pytest.mark.parametrize('change',['limit','history','extra','unresolved','command','old-failure'])
def test_installed_campaign_refuses_changed_limits_or_launches(tmp_path,change):
    folder=campaign(tmp_path)
    installed.campaign(folder)
    path=folder/'native-ledger.json'
    data=process_ledger.checked(path)
    if change=='limit': data['limit']=7
    elif change=='history': data['historical_lower_bound']=0
    elif change=='extra':
        index=process_ledger.reserve(path,['extra']); process_ledger.transition(path,index,pid=110)
        data=process_ledger.checked(path)
    elif change=='unresolved': data['reservations'][0]['state']='RESERVED'
    elif change=='command':
        write(folder/'commands/build/result.json',{'returncode':1})
    else: (folder.parent/'attempt-001/commands/capture/stderr').write_text('different failure')
    process_ledger.save(path,data)
    with pytest.raises(ValueError): installed.campaign(folder)


def test_installed_forged_pass_without_matrix_refuses(tmp_path):
    write(tmp_path/'result.json',{'status':'PASS','full_semantics_equal':True})
    write(tmp_path/'outputs.json',{'result.json':file_hash(tmp_path/'result.json')})
    with pytest.raises((ValueError,FileNotFoundError)): installed.evidence(tmp_path,tmp_path)


@pytest.mark.parametrize('change',['changed-worker','missing-worker','other-source','collision'])
def test_installed_requirement_mapping_preserves_bytes_and_unrelated_sources(tmp_path,change):
    directory=tmp_path/'lib/python3.11/site-packages/legalmath/prospectus/successor'
    sources={str(Path(installed.product.extraction.__file__).with_name(name).resolve()):name
             for name in ('ocr_worker.py','native_inputs.py')}
    required={**{k:'a'*64 for k in sources},'/actual.pdf':'b'*64}
    manifest={'files':[{'path':str(directory/name),'sha256':'a'*64} for name in sources.values()]}
    original=deepcopy(required)
    result=installed.installed_requirements(required,manifest,tmp_path)
    assert required==original and result['/actual.pdf']=='b'*64
    assert all(source not in result for source in sources)
    if change=='changed-worker': manifest['files'][0]['sha256']='c'*64
    elif change=='missing-worker': manifest['files'].pop()
    elif change=='collision': required[manifest['files'][0]['path']]='a'*64
    else:
        required['/actual.pdf']='c'*64
        assert installed.installed_requirements(required,manifest,tmp_path)['/actual.pdf']=='c'*64
        return
    with pytest.raises(ValueError): installed.installed_requirements(required,manifest,tmp_path)
