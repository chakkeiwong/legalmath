"""Bounded source-authority004 document timestamp validation evidence."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import gzip
import json
import os
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
sys.dont_write_bytecode=True;os.environ['CUDA_VISIBLE_DEVICES']='-1'
from legalmath.prospectus.execution_authority import Authority,REL,read,write,file_hash
from legalmath.prospectus.successor import source_graph,service

PLAN='docs/plans/prospectus-document-time-validation-2026-10-17.md'
REVIEW=ROOT/REL/'reviews/document-time-validation'
HERE=ROOT/REL/'attempts/source-authority/attempt-004'
OLD=ROOT/REL/'attempts/law-applicability/attempt-006'
PRODUCTION='src/legalmath/prospectus/successor/source_graph.py'
TESTS=['tests/prospectus_successor/test_document_time_validation.py',
       'tests/prospectus_successor/test_interval_validation.py',
       'tests/prospectus_successor/test_successor.py',
       'tests/prospectus_successor/test_repairs.py']
BAD=[False,0,0.0,'',[],{},True,1,['2026-01-01'],'not-a-date',
     '2026-01-01','2026-01-01T00:00:00','2026-02-30T00:00:00Z']
FIELDS=('document_date','known_from','valid_from','valid_until')
PURPOSES=('review','issue_formation','amendment','event')

def require(value,reason):
    if not value:raise ValueError(reason)

def load(path):
    raw=path.read_bytes();return json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(gzip.compress(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode(),mtime=0))

def methods():
    paths={p for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths|={ROOT/p for p in TESTS}|{Path(__file__)}
    return {str(p.relative_to(ROOT)):file_hash(p) for p in sorted(paths)}

def seconds():
    return read(REVIEW/'reproduction.json')['seconds']+sum(read(p)['seconds'] for p in (HERE/'stages').glob('*/result.json'))

def storage():
    paths=[REVIEW,HERE,ROOT/PLAN,Path(__file__),ROOT/TESTS[0],ROOT/REL/'proposals/document-time-227.json',
        ROOT/REL/'proposals/document-time-227-review.json',ROOT/REL/'revisions/0227.json',
        ROOT/REL/'closure-routes-2026-10-17-document-time-227.json']
    files=set()
    for p in paths:
        files.update(q for q in p.rglob('*') if q.is_file()) if p.is_dir() else files.add(p)
    return sum(p.stat().st_size for p in files if p.exists())

def authenticate():
    auth=Authority(ROOT);program,tasks,_=auth.spec();admission=read(HERE/'admission.json')
    require(program['revision']==227 and admission['binding']==auth.binding(tasks['source-authority']),'Admission drift')
    for n,h in read(OLD/'outputs.json').items():require(file_hash(OLD/n)==h,'Original retained evidence changed')
    for n,h in read(REVIEW/'source-bindings.json').items():require(file_hash(ROOT/n)==h,'Source bytes changed')
    current=methods();before=read(REVIEW/'before-methods.json')
    require({n for n in current if n.startswith('src/')}==set(before),'Production file set changed')
    require([n for n,h in before.items() if current[n]!=h]==[PRODUCTION],'Production change outside review')
    pin=HERE/'repaired-methods.json'
    if pin.exists():require(read(pin)==current,'Methods changed between stages')
    else:
        write(pin,current,exclusive=True)
        for n in [PRODUCTION,*TESTS,str(Path(__file__).relative_to(ROOT))]:
            target=HERE/'methods'/n;target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as f:f.write((ROOT/n).read_bytes())
    require(storage()+1024**2<32*1024**2 and seconds()<300,'Cumulative resource ceiling')
    return admission

def tests():
    argv=[sys.executable,'-c',
        'import sys; sys.path[:0]=[sys.argv[1],sys.argv[2]]; import pytest; raise SystemExit(pytest.main(sys.argv[3:]))',
        str(ROOT/'src'),str(ROOT),'-q',*TESTS,'--junitxml='+str(HERE/'tests.xml')]
    write(HERE/'test-command.json',{'argv':argv},exclusive=True)
    with (HERE/'tests.stdout').open('xb') as out,(HERE/'tests.stderr').open('xb') as err:
        result=subprocess.run(argv,cwd=ROOT,stdout=out,stderr=err,timeout=50,
            env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    require(result.returncode==0,'Focused regression failed; inspect retained logs')
    xml=ET.parse(HERE/'tests.xml').getroot()
    counts={k:sum(int(s.get(k,'0')) for s in xml.iter('testsuite')) for k in ('tests','failures','errors','skipped')}
    require(counts['tests']>0 and not any(counts[k] for k in ('failures','errors','skipped')),'Invalid test report')
    return counts

def consumers():
    base=read(REVIEW/'request.json');baseline=service.assess(base,ROOT)
    require(baseline==load(REVIEW/'baseline-answer.json.gz'),'Complete original baseline changed')
    save(HERE/'baseline-answer.json.gz',baseline)
    ns={'__name__':'legalmath.prospectus.successor._before_document_time',
        '__package__':'legalmath.prospectus.successor'}
    exec(compile((REVIEW/'before-source-graph.py').read_text(),str(REVIEW/'before-source-graph.py'),'exec'),ns)
    current_build=source_graph.build
    def prior(r):
        try:
            source_graph.build=ns['build'];return service.assess(r,ROOT)
        finally:source_graph.build=current_build
    valid=[];adverse=[];boundaries=[]
    for field in FIELDS:
        for missing in (True,False):
            r=deepcopy(base);doc=r['bundle']['documents'][0]
            if missing:doc.pop(field,None)
            else:doc[field]=None
            result=service.assess(r,ROOT);old=prior(r)
            require(result==old,'Missing/null complete output changed')
            valid.append({'field':field,'missing':missing,'input':r,'answer':result,'complete_old_equal':True})
    for purpose in PURPOSES:
        for field in FIELDS:
            for bad in BAD:
                r=deepcopy(base);r['bundle']['purpose']=purpose;r['bundle']['documents'][0][field]=bad
                try:service.assess(r,ROOT)
                except ValueError as exc:
                    adverse.append({'purpose':purpose,'field':field,'bad':bad,'status':'REFUSED','reason':str(exc)})
                else:raise ValueError('Malformed source date reached answer: '+str((purpose,field,bad)))
    at=base['bundle']['effective_at'];future='2026-10-14T00:00:00Z';past='2026-10-12T00:00:00Z'
    cases=[('document_date',at,'issue_formation'),('document_date',future,'issue_formation'),
        ('document_date',future,'review'),('known_from',at,'review'),('known_from',future,'review'),
        ('valid_from',at,'review'),('valid_from',future,'review'),('valid_until',at,'review'),
        ('valid_until',future,'review'),('valid_until',past,'review'),
        ('known_from','2026-10-13T08:00:00+08:00','review'),('valid_until','2026-10-13T08:00:00+08:00','review')]
    def parse(v):return datetime.fromisoformat(v.replace('Z','+00:00'))
    for field,value,purpose in cases:
        r=deepcopy(base);r['bundle']['purpose']=purpose;r['bundle']['documents'][0][field]=value
        if field=='document_date':expected=purpose!='issue_formation' or parse(value)<=parse(r['bundle']['issue_date'])
        elif field=='known_from':expected=parse(value)<=parse(r['bundle']['known_at'])
        elif field=='valid_from':expected=parse(value)<=parse(at)
        else:expected=parse(at)<parse(value)
        graph=source_graph.build(r['bundle'],ROOT)
        require(graph['documents'][0]['visible']==expected,'Independent temporal boundary mismatch')
        row={'field':field,'value':value,'purpose':purpose,'input':r,'graph':graph,'expected_visible':expected}
        if expected:
            answer=service.assess(r,ROOT);old=prior(r)
            require(answer==old and answer['questions']['Q4']['status']=='YES','Valid complete boundary changed')
            row.update(answer=answer,complete_old_equal=True)
        else:
            try:service.assess(r,ROOT)
            except ValueError as exc:
                require('Source occurrence unavailable' in str(exc),'Unexpected exclusion error')
                row.update(refusal=str(exc))
            else:raise ValueError('Excluded source supported bound conditional premises')
        boundaries.append(row)
    bad=deepcopy(base);bad['bundle']['documents'][0]['valid_until']=False
    old=prior(bad);require(old['questions']['Q4']['status']=='YES','Old visibility control failed to reproduce')
    save(HERE/'known-bad-old-answer.json.gz',old)
    save(HERE/'valid-controls.json.gz',valid);save(HERE/'adverse-controls.json.gz',adverse)
    save(HERE/'boundary-controls.json.gz',boundaries)
    require(baseline['may_execute_transaction'] is False and baseline['independent_legal_acceptance'] is False,'Claim boundary changed')
    return {'original_complete_equal':True,'missing_null_complete_equal':len(valid),
        'malformed_refusals':len(adverse),'boundary_consumers':len(boundaries),
        'excluded_source_refusals':sum('refusal' in r for r in boundaries),
        'known_bad_old_implementation_detected':True,'scope':'FRESH_SELECTED_TEXT_INTAKE; no fresh original PDF extraction'}

def seal():
    require(all(read(HERE/'stages'/s/'result.json')['status']=='PASS' for s in ('tests','consumers')),'Missing required stage')
    return read(HERE/'stages/consumers/result.json')['detail']

def main():
    stage=sys.argv[1];require(stage in {'tests','consumers','seal'},'Unknown stage')
    folder=HERE/'stages'/stage
    write(folder/'started.json',{'command':['.venv/bin/python','scripts/prospectus_document_time_validation.py',stage],
        'at':datetime.now(timezone.utc).isoformat(),'cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1'},exclusive=True)
    signal.alarm(60);start=time.monotonic()
    try:
        admission=authenticate();detail=globals()[stage]()
        require(methods()==read(HERE/'repaired-methods.json'),'Methods changed during stage')
        require(seconds()+time.monotonic()-start<300 and storage()+1024**2<32*1024**2,'Resource ceiling')
        result={'status':'PASS','seconds':time.monotonic()-start,'detail':detail}
    except Exception as exc:
        write(folder/'result.json',{'status':'FAIL','seconds':time.monotonic()-start,'error':type(exc).__name__+': '+str(exc)},exclusive=True)
        raise
    write(folder/'result.json',result,exclusive=True)
    if stage=='seal':
        require((HERE/'RESULT.md').is_file(),'Detailed result required')
        write(HERE/'run-manifest.json',{'git_commit':admission['git_commit'],'plan':PLAN,
            'result':str((HERE/'RESULT.md').relative_to(ROOT)),'python':sys.version,'interpreter':sys.executable,
            'environment':'Existing .venv; current worktree src pinned','cpu_gpu':'CPU_ONLY; CUDA_VISIBLE_DEVICES=-1',
            'random_seeds':'N/A deterministic','sources':read(REVIEW/'source-bindings.json'),
            'methods':'repaired-methods.json','commands':[read(p) for p in sorted((HERE/'stages').glob('*/started.json'))],
            'stages':{p.parent.name:read(p) for p in (HERE/'stages').glob('*/result.json')},
            'known_seconds_including_preparation':seconds(),'historical_unmeasured_seconds':'UNKNOWN',
            'new_bytes_before_manifest':storage()},exclusive=True)
        write(HERE/'result.json',{'task':'source-authority','status':'PASS','whole_task_complete':False,
            'whole_program_complete':False,'scope':'DOCUMENT_TIMESTAMP_VALIDATION','summary':detail},exclusive=True)
        write(HERE/'outputs.json',{str(p.relative_to(HERE)):file_hash(p) for p in sorted(HERE.rglob('*'))
            if p.is_file() and p.name not in {'admission.json','outputs.json'} and '__pycache__' not in p.parts},exclusive=True)
    signal.alarm(0);print(json.dumps({'stage':stage,**result}))

if __name__=='__main__':main()
