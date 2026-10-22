"""Bounded actual Q1 consumer counterexample with one financial target omitted."""
from copy import deepcopy
import gzip
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
from legalmath.prospectus.execution_authority import Authority, file_hash
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest

AUTH = ROOT/'docs/implementation/prospectus-execution-authority'
OLD = AUTH/'attempts/source-bes-dep-11/attempt-004'
OUT = ROOT/'.localresources/prospectus-preparation/q1-scope/probe'
PLAN = 'docs/plans/prospectus-q1-scope-reconciliation-2026-10-22.md'


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def save(name, value):
    raw = (json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n').encode()
    if name.endswith('.gz'): raw = gzip.compress(raw,compresslevel=1,mtime=0)
    size = sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
    if size+len(raw)>48*1024**2: raise ValueError('Probe48MiB ceiling')
    with (OUT/name).open('xb') as stream: stream.write(raw)


def products():
    ref = read(OLD/'after-P1-reference.json.gz')
    original = ROOT/ref['original_p1']
    if file_hash(original)!=ref['original_p1_file_sha256']: raise ValueError('Original Q1P1 changed')
    graph = read(original)['payload']['graph']
    request = ref['request']
    p1 = service.seal('P1',request['bundle'],{'request':digest(request)},{'request':request,'graph':graph})
    if p1['sha256']!=ref['expected_P1_sha256']: raise ValueError('Q1P1 reconstruction differs')
    return {'P1':p1,**read(OLD/'after-P2-P5.json.gz')}


def rebuild(p1,supplied):
    p2=service.construction_product(p1,ROOT)
    p3=service.interpretation_product(p1,p2,supplied)
    return {'P1':p1,'P2':p2,'P3':p3,'P4':service.law_product(p1,p3),'P5':service.financial_product(p1,p2,p3)}


def main():
    start=time.monotonic()
    OUT.mkdir(parents=True,exist_ok=False)
    a=Authority(ROOT)
    program,_,_=a.spec()
    if program['revision']!=436: raise ValueError('Expected reviewed436baseline')
    original=next(e for e in reversed(a.events()) if e.get('attempt')==str(OLD.relative_to(ROOT)) and e['kind'] in {'RECORD','ACCEPT'})
    latest=next(e for e in reversed(a.events()) if e.get('task')=='source-bes-dep-08')
    if latest['kind']!='RECORD' or not a.retained_evidence_valid(latest) or not a.retained_evidence_valid(original):
        raise ValueError('Recorded source evidence required')
    save('manifest.json',{'command':[sys.executable,'-B','-m','scripts.prospectus_q1_scope_probe'],'plan':PLAN,
         'revision':436,'source04_event':original['sha256'],'source08_event':latest['sha256'],
         'git_commit':read(AUTH/'attempts/source-bes-dep-08/attempt-009/admission.json')['git_commit'],
         'environment':{'executable':sys.executable,'python':sys.version},'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1',
         'random_seeds':'N/A deterministic','methods':{str(p.relative_to(ROOT)):file_hash(p) for p in (ROOT/'src/legalmath/prospectus').rglob('*.py')},
         'data_version':{'source11_004_outputs':file_hash(OLD/'outputs.json')},'seconds_ceiling':90})
    ps=products()
    ordinary=service.consume(ps,ROOT,mode='frozen')
    save('ordinary-answer.json.gz',ordinary)
    if ordinary!=read(OLD/'after-answer.json.gz'): raise ValueError('Complete004ordinary answer changed')
    baseline=service.consume(ps,ROOT,mode='frozen',include_artifacts=True)
    save('baseline-answer.json.gz',baseline)
    supplied=deepcopy(ps['P3']['payload']['interpretation_input'])
    row=supplied['reference_admission']['references'][0]
    cell=ps['P1']['payload']['request']['source_statement_cells']['reading']['rows'][0]['cells'][0]
    key=cell['source']['source_unit']
    omitted,=[x for x in row['targets'] if x['use']==key]
    row['targets']=[x for x in row['targets'] if x['use']!=key]
    save('omission-input.json.gz',supplied)
    changed=rebuild(ps['P1'],supplied)
    answer=service.consume(changed,ROOT,mode='frozen',include_artifacts=True)
    save('omission-answer.json.gz',answer)
    dep=next(d for d in answer['dependencies'] if d['id']=='reviewed-reference:'+row['id'])
    result={'status':'REPRODUCED' if dep['status']=='RESOLVED' and len(dep['targets'])==298 else 'NOT_REPRODUCED',
            'baseline_targets':299,'altered_targets':len(dep['targets']),'altered_status':dep['status'],
            'omitted':omitted,'printed_financial_cell':cell,'scope_check_present':'statement_scope_check' in dep,
            'complete_ordinary_baseline_equal':True,'cells_unchanged':answer['source_statement_cells']==baseline['source_statement_cells'],
            'q3':answer['questions']['Q3']['status'],'may_execute_transaction':answer['may_execute_transaction'],
            'seconds':time.monotonic()-start,'code_sha256':file_hash(Path(__file__))}
    save('result.json',result)
    print(json.dumps({k:result[k] for k in ('status','baseline_targets','altered_targets','altered_status','seconds')}),flush=True)


if __name__=='__main__':
    def expire(*_): raise TimeoutError('Q1scope probe90seconds')
    signal.signal(signal.SIGALRM,expire)
    signal.alarm(90)
    start=time.monotonic()
    try: main()
    except Exception as exc:
        if OUT.is_dir(): save('failure.json',{'type':type(exc).__name__,'message':str(exc),'seconds':time.monotonic()-start})
        raise
    finally: signal.alarm(0)
