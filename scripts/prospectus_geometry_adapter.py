"""Bounded public geometry-adapter experiment using retained sealed native inputs."""
from copy import deepcopy
from datetime import datetime,timezone
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
os.environ.update(CUDA_VISIBLE_DEVICES='-1',LEGALMATH_OCR_PYTHON='/home/chakwong/miniconda3/envs/tfgpu/bin/python')
from legalmath.prospectus import geometry_transfer as adapter, native_binding_acceptance as checks
from legalmath.prospectus.execution_authority import Authority,read,write,file_hash
from legalmath.prospectus.successor import sealed_source,sealed_runtime,process_ledger
from legalmath.prospectus.successor.contracts import digest

BASE=ROOT/'docs/implementation/prospectus-execution-authority/attempts'
HERE=BASE/'native-candidates/attempt-006'
OLD=BASE/'native-candidates/attempt-005'
PRIOR=BASE/'native-candidates/attempt-002'
SNAPSHOT=BASE/'native-binding/attempt-008/snapshot'
PLAN='docs/plans/prospectus-geometry-adapter-2026-10-15.md'
ARMS=('unpatched-enabled','patched')
STAGES={'prepare','compare',*[a+'-'+b for a in ARMS for b in ('source','construct','interpret','consume')]}
spec=importlib.util.spec_from_file_location('retained_transfer_driver',OLD/'run_transfer.py')
prototype=importlib.util.module_from_spec(spec);spec.loader.exec_module(prototype)
prototype.HERE=HERE
prototype.driver.HERE=HERE


def save(name,data):write(HERE/name,data,exclusive=True)


def methods():
    names={str(p.relative_to(ROOT)) for p in (ROOT/'src/legalmath/prospectus/successor').glob('*.py')}
    names|={str(Path(__file__).relative_to(ROOT)),str(Path(adapter.__file__).relative_to(ROOT)),
      str((OLD/'run_transfer.py').relative_to(ROOT)),str((PRIOR/'consume_reports.py').relative_to(ROOT)),
      str((PRIOR/'compare_pages.py').relative_to(ROOT)),str((PRIOR/'compare_consumers.py').relative_to(ROOT)),
      'scripts/prospectus_geometry_consumer.py','scripts/prospectus_report_scope.py',
      'src/legalmath/prospectus/native_binding_acceptance.py','tests/prospectus/test_geometry_transfer.py',PLAN}
    return {n:file_hash(ROOT/n) for n in sorted(names)}


def prepare():
    checks.verify_files(OLD,read(OLD/'outputs.json'))
    checks.verify_files(PRIOR,read(PRIOR/'outputs.json'))
    manifest=checks.snapshot(SNAPSHOT)
    base=read(PRIOR/'workers/unpatched-enabled.json');patched=read(PRIOR/'workers/patched.json')
    source=prototype.driver.read(prototype.driver.OLD/'request.json')['bundle']['documents'][0]
    required=str(ROOT/source['path'])
    assert any(r['path']==required and r['sha256']==source['sha256'] for r in manifest['files'])
    (HERE/'workers').mkdir()
    shutil.copyfile(PRIOR/'workers/unpatched-enabled.json',HERE/'workers/unpatched-enabled.json')
    result=adapter.transfer_files(PRIOR/'workers/unpatched-enabled.json',PRIOR/'workers/patched.json',HERE/'workers/patched.json',
       original_sha256=file_hash(PRIOR/'workers/unpatched-enabled.json'),candidate_sha256=file_hash(PRIOR/'workers/patched.json'),policy=adapter.POLICY)
    actual=read(HERE/'workers/patched.json');historical=read(OLD/'workers/patched.json')
    assert actual['pages']==historical['pages'] and result['words']==1311 and result['changed_rectangles']==8
    controls=[]
    for name in ('wrong-source','wrong-image','wrong-model','changed-word','missing-word','invalid-box','reordered','duplicate-page'):
        bad=deepcopy(patched)
        if name=='wrong-source':bad['source_sha256']='0'*64
        elif name=='wrong-image':bad['pages'][0]['image_sha256']='0'*64
        elif name=='wrong-model':bad['runtime']['language_models']={'por':'0'*64}
        elif name=='changed-word':bad['pages'][0]['words'][0][4]+='x'
        elif name=='missing-word':bad['pages'][0]['words'].pop()
        elif name=='invalid-box':bad['pages'][0]['words'][0][0]=-100
        elif name=='reordered':bad['pages'][0]['words'].reverse()
        else:bad['pages'].append(deepcopy(bad['pages'][0]))
        try:adapter.transfer(base,bad,original_sha256=digest(base),candidate_sha256=digest(bad),policy=adapter.POLICY)
        except ValueError as error:controls.append({'case':name,'refused':True,'reason':str(error)})
        else:raise AssertionError('Adverse real worker accepted: '+name)
    process_ledger.create(HERE/'native-ledger.json',8,54,'Eight actual source text/image starts; no native build or fresh OCR; internal forks outside counter')
    shutil.copyfile('/tmp/prospectus-geometry-adapter-focused.xml',HERE/'tests.xml')
    frozen=methods();save('frozen-methods.json',frozen)
    for name in frozen:
        target=HERE/'method'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    save('preparation.json',{'status':'PASS','pages':len(base['pages']),'words':result['words'],
      'changed_rectangles':result['changed_rectangles'],'controls':controls,
      'workers':{a:file_hash(HERE/'workers'/(a+'.json')) for a in ARMS},
      'snapshot':str(SNAPSHOT.relative_to(ROOT)),'snapshot_sha256':sealed_runtime.digest(manifest),
      'historical_candidate_pages_equal':True,'policy':adapter.POLICY})
    return {'words':1311,'changed_rectangles':8,'actual_adverse_controls':len(controls),'native_starts':0}


def product(arm,stage):
    assert methods()==read(HERE/'frozen-methods.json')
    if stage=='source':
        folder=HERE/'consumers'/arm
        folder.mkdir(parents=True,exist_ok=True)
        runtime=sealed_source.SourceRuntime(SNAPSHOT,read(HERE/'preparation.json')['snapshot_sha256'],
            evidence_directory=folder/'native',native_text_max_stream=64*1024*1024)
        with process_ledger.observe(HERE/'native-ledger.json'),sealed_source.selected(runtime):
            result=prototype.product(arm,stage)
        assert len(runtime.receipts)==4
        save('consumers/'+arm+'/native-receipts.json',runtime.receipts)
        return result
    return prototype.product(arm,stage)


def compare():
    result=prototype.compare()
    manifest=checks.snapshot(SNAPSHOT)
    ledger=process_ledger.checked(HERE/'native-ledger.json')
    assert ledger['limit']==8 and ledger['historical_lower_bound']==54 and len(ledger['reservations'])==8
    receipts=[]
    for arm in ARMS:
        folder=HERE/'consumers'/arm
        products,answer=checks.products(folder)
        checks.consumer(ROOT,products,answer)
        current=read(folder/'native-receipts.json')
        assert len(current)==4
        for index in range(4):
            receipt,streams=checks.receipt(folder/'native'/str(index),manifest)
            assert receipt==current[index]
            if index%2:
                assert json.loads(streams[0])['verify_images_only'] is True
                assert json.loads(streams[1])['verification_only'] is True
            receipts.append(receipt)
        doc=answer['source_map']['documents'][0]
        assert doc['native_extraction']['sealed_execution']==current[2]
        assert doc['image_verification']['verification_runtime']['sealed_execution']==current[3]
    for reservation,receipt in zip(ledger['reservations'],receipts):
        argv=reservation['argv'];assert reservation['state']=='STARTED' and argv[argv.index('--')+1:]==receipt['argv']
    extra={'status':'PASS','actual_consumers_recomputed':True,'native_starts':8,'native_limit':8,
           'historical_visible_lower_bound':62,'delivered_final_receipts':True,
           'raw_initial_receipts_preserved':True,'fresh_ocr_or_build_starts':0,
           'assisted_optional_adapter':True,'installed_adapter_evaluated':False}
    save('actual-consumer-checks.json',extra)
    return {**result,**extra}


def main():
    stage=sys.argv[1];assert stage in STAGES
    authority=Authority(ROOT);ad=read(HERE/'admission.json');_,tasks,_=authority.spec()
    assert ad['binding']==authority.binding(tasks['native-candidates']) and not (HERE/'outputs.json').exists()
    folder=HERE/'invocations'/stage;folder.mkdir(parents=True,exist_ok=False);tick=time.monotonic()
    save('invocations/'+stage+'/started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_geometry_adapter',stage],
      'git_commit':ad['git_commit'],'plan':PLAN,'environment':sys.executable,'started_at':datetime.now(timezone.utc).isoformat(),
      'cpu_gpu':'CPU only; GPUs intentionally hidden','random_seeds':'N/A deterministic','methods':methods()})
    def expire(s,f):raise TimeoutError('120-second geometry stage bound; no automatic retry')
    signal.signal(signal.SIGALRM,expire);signal.alarm(120)
    try:
        if stage=='prepare':result=prepare()
        elif stage=='compare':result=compare()
        else:
            arm,action=stage.rsplit('-',1);result=product(arm,action)
        assert methods()==read(HERE/'frozen-methods.json')
        assert ad['binding']==authority.binding(tasks['native-candidates'])
        outcome={'status':'PASS','details':result,'wall_seconds':time.monotonic()-tick}
    except BaseException as error:
        save('invocations/'+stage+'/result.json',{'status':'FAIL','error':type(error).__name__+': '+str(error),
             'wall_seconds':time.monotonic()-tick});raise
    finally:signal.alarm(0)
    save('invocations/'+stage+'/result.json',outcome)
    print(json.dumps(outcome))


if __name__=='__main__':
    with (HERE/'execution.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);main()
