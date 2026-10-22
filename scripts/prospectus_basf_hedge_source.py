"""Immutable four-page original render and complete source-boundary inventory."""
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from scripts import prospectus_basf_oci_source as base
from legalmath.prospectus.execution_authority import read, file_hash
from legalmath.prospectus.successor import process_ledger

ROOT,BASE=base.ROOT,base.BASE
HERE=BASE/'basf-references/attempt-004'
PRIOR=BASE/'basf-references/attempt-003'
PLAN='docs/plans/prospectus-basf-hedge-note-2026-10-15.md'
base.HERE,base.PRIOR,base.PLAN=HERE,PRIOR,PLAN
save,load,bindings=base.save,base.load,base.bindings


def prepare():
    protected={str((PRIOR/p).relative_to(ROOT)):h for p,h in read(PRIOR/'outputs.json').items()}
    protected[str((PRIOR/'outputs.json').relative_to(ROOT))]=file_hash(PRIOR/'outputs.json')
    assert all(file_hash(ROOT/p)==h for p,h in protected.items())
    save('protected-inputs.json',protected)
    names=[Path(__file__),Path(base.__file__),ROOT/PLAN,HERE/'EXECUTION-AUDIT.md',Path(process_ledger.__file__)]
    save('source-methods.json',{str(p.relative_to(ROOT)):file_hash(p) for p in names})
    for p in names:
        target=HERE/'source-methods'/p.relative_to(ROOT)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p,target)
    shutil.copyfile(PRIOR/'products.json.gz',HERE/'products.json.gz')
    products=load(HERE/'products.json.gz')
    doc=next(d for d in products['P1']['payload']['request']['bundle']['documents'] if d['id']=='basf-annual-2022-exchange')
    assert file_hash(ROOT/doc['path'])==doc['sha256']
    save('original-source.json',doc)
    units=[u for u in products['P1']['payload']['graph']['units'] if u['document']==doc['id'] and 279<=u['page']<=282]
    assert len(units)==452
    excluded=[u for u in units if u['page']==282 and int(u['id'].rsplit(':l',1)[1])>=10]
    assert len(excluded)==76
    save('source-units.json',units)
    save('boundary-inventory.json',{'all_occurrences':452,'note_occurrences':376,'excluded_occurrences':76,
        'excluded_units':[u['id'] for u in excluded],'first_excluded_heading':[u['raw'] for u in excluded[:2]],
        'supplied_boundary':True,'image_review_pending':True})
    renderer=Path(shutil.which('pdftoppm')).resolve(strict=True)
    save('renderer.json',{'path':str(renderer),'sha256':file_hash(renderer)})
    process_ledger.create(HERE/'native-ledger.json',1,78,'One original279-282 render;no extraction/OCR')
    process_ledger.create(HERE/'command-ledger.json',5,0,'Render,build,install,replay;one repair spare')
    return {'page_occurrences':452,'note_occurrences':376,'excluded_occurrences':76}


def render():
    renderer,doc=read(HERE/'renderer.json'),read(HERE/'original-source.json')
    assert file_hash(Path(renderer['path']))==renderer['sha256']
    assert file_hash(ROOT/doc['path'])==doc['sha256']
    assert not list(HERE.glob('note-*.png'))
    argv=[renderer['path'],'-f','279','-l','282','-scale-to','1800','-png',str(ROOT/doc['path']),str(HERE/'note')]
    folder=HERE/'commands/render'
    folder.mkdir(parents=True,exist_ok=False)
    save('commands/render/started.json',{'argv':argv,'timeout':110,'cpu_gpu':'CPU only'})
    tick=time.monotonic()
    with (folder/'stdout').open('xb') as out,(folder/'stderr').open('xb') as err:
        with process_ledger.observe(HERE/'command-ledger.json'),process_ledger.observe(HERE/'native-ledger.json'):
            result=subprocess.run(argv,stdout=out,stderr=err,timeout=110,env={**os.environ,'CUDA_VISIBLE_DEVICES':'-1'})
    save('commands/render/result.json',{'returncode':result.returncode,'wall_seconds':time.monotonic()-tick})
    assert result.returncode==0
    images=[]
    for page in range(279,283):
        p=HERE/('note-'+str(page)+'.png')
        assert p.is_file()
        images.append({'page':page,'path':str(p.relative_to(ROOT)),'sha256':file_hash(p)})
    save('rendered-source.json',{'document':doc['id'],'path':doc['path'],'sha256':doc['sha256'],
        'images':images,'renderer':renderer,'native_render_reservations':1,'native_extractions':0,
        'historical_visible_native_reservation_lower_bound':79,'source_http_lower_bound':9})
    return {'rendered_pages':4,'new_native_render_reservations':1,'http_calls':0}


def main():
    stage=sys.argv[1]
    assert stage in {'prepare','render'}
    ad=bindings()
    if stage=='render':
        assert read(HERE/'invocations/prepare/result.json')['status']=='PASS'
    folder=HERE/'invocations'/stage
    folder.mkdir(parents=True,exist_ok=False)
    save('invocations/'+stage+'/started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_basf_hedge_source',stage],
        'git_commit':ad['git_commit'],'plan':PLAN,'environment':sys.executable,
        'started_at':datetime.now(timezone.utc).isoformat(),'random_seeds':'N/A deterministic',
        'cpu_gpu':'CPU only;child CUDA_VISIBLE_DEVICES=-1'})
    tick=time.monotonic()
    def expire(signum,frame):
        raise TimeoutError('120-second source-stage limit;no automatic retry')
    signal.signal(signal.SIGALRM,expire);signal.alarm(120)
    try:
        details=globals()[stage]()
        bindings()
        size=sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file())
        assert size<500*1024*1024
        result={'status':'PASS','stage':stage,'details':details,'wall_seconds':time.monotonic()-tick,'retained_bytes':size}
    except BaseException as error:
        save('invocations/'+stage+'/result.json',{'status':'FAIL','error':repr(error),'wall_seconds':time.monotonic()-tick})
        raise
    finally:
        signal.alarm(0)
    save('invocations/'+stage+'/result.json',result)
    print(result)


if __name__=='__main__':
    main()
