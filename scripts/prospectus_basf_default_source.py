"""Retain original default(f), qualifications and controlling-language sources."""
from pathlib import Path
from datetime import datetime,timezone
import shutil
import signal
import sys
import time
from scripts import prospectus_basf_body_source as old
from legalmath.prospectus.execution_authority import read,file_hash
from legalmath.prospectus.successor import process_ledger

ROOT,BASE=old.ROOT,old.BASE
HERE=BASE/'basf-meanings/attempt-013'
PRIOR=BASE/'basf-meanings/attempt-012'
PLAN='docs/plans/prospectus-basf-default-f-alternatives-2026-10-15.md'
old.HERE,old.PRIOR,old.PLAN=HERE,PRIOR,PLAN
old.base.HERE,old.base.PRIOR,old.base.PLAN=HERE,PRIOR,PLAN
save,load,bindings=old.save,old.load,old.bindings


def prepare():
    protected={str((PRIOR/p).relative_to(ROOT)):h for p,h in read(PRIOR/'outputs.json').items()}
    protected[str((PRIOR/'outputs.json').relative_to(ROOT))]=file_hash(PRIOR/'outputs.json')
    assert all(file_hash(ROOT/p)==h for p,h in protected.items())
    save('protected-inputs.json',protected)
    names=[Path(__file__),Path(old.__file__),Path(old.base.__file__),ROOT/PLAN,HERE/'EXECUTION-AUDIT.md',Path(process_ledger.__file__)]
    save('source-methods.json',{str(p.relative_to(ROOT)):file_hash(p) for p in names})
    for p in names:
        target=HERE/'source-methods'/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    shutil.copyfile(PRIOR/'products.json.gz',HERE/'products.json.gz')
    products=load(HERE/'products.json.gz');graph=products['P1']['payload']['graph']
    sources=[]
    for doc_id,pages in [('basf-base-september-2022-exchange',[82,126,127,133]),('basf-2032-final',[7])]:
        doc=next(d for d in products['P1']['payload']['request']['bundle']['documents'] if d['id']==doc_id)
        assert file_hash(ROOT/doc['path'])==doc['sha256']
        images=[]
        for page in pages:
            if page==82: p=BASE/'basf-meanings/attempt-005/english-82.png'
            else:p=old.IMAGE_ROOT/(('final-' if doc_id=='basf-2032-final' else 'base-')+str(page)+'.png')
            images.append({'page':page,'path':str(p.relative_to(ROOT)),'sha256':file_hash(p)})
        sources.append({'document':doc_id,'path':doc['path'],'sha256':doc['sha256'],'images':images})
    save('original-sources.json',sources)
    save('source-page-units.json',[u for u in graph['units'] if any(u['document']==s['document'] and u['page'] in [i['page'] for i in s['images']] for s in sources)])
    process_ledger.create(HERE/'command-ledger.json',5,0,'Offline build,install,answer replay,control replay;one repair spare')
    return {'source_documents':2,'retained_original_pages':5,'native_calls':0,'http_calls':0}


def main():
    assert sys.argv[1:]==['prepare']
    ad=bindings();folder=HERE/'invocations/prepare';folder.mkdir(parents=True,exist_ok=False)
    save('invocations/prepare/started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_basf_default_source','prepare'],
        'git_commit':ad['git_commit'],'plan':PLAN,'environment':sys.executable,
        'started_at':datetime.now(timezone.utc).isoformat(),'random_seeds':'N/A deterministic','cpu_gpu':'CPU only;no framework imports'})
    tick=time.monotonic()
    def expire(signum,frame):raise TimeoutError('120-second source-stage bound')
    signal.signal(signal.SIGALRM,expire);signal.alarm(120)
    try:
        details=prepare();bindings();result={'status':'PASS','details':details,'wall_seconds':time.monotonic()-tick}
    except BaseException as error:
        save('invocations/prepare/result.json',{'status':'FAIL','error':repr(error),'wall_seconds':time.monotonic()-tick});raise
    finally:signal.alarm(0)
    save('invocations/prepare/result.json',result);print(result)


if __name__=='__main__':main()
