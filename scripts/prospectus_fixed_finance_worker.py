"""Original-source preparation and ordinary/isolated installed maturity consumers."""
from copy import deepcopy
from datetime import date, timedelta
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT,OUT,MODE=Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3]
AUTH=ROOT/'docs/implementation/prospectus-execution-authority'
PREP=AUTH/'reviews/shell-maturity-361'
OLD=AUTH/'reviews/shell-full-coupons-360'
PRIOR=AUTH/'attempts/finance-conventions/attempt-011'
os.environ['CUDA_VISIBLE_DEVICES']='-1'
PACKAGE=OUT/'installed' if MODE=='installed' else ROOT/'src'
sys.path.insert(0,str(PACKAGE))
from legalmath.prospectus.successor import service,source_graph,contract_assembly,contract_terms,occurrences
from legalmath.prospectus.successor.contracts import digest
spec=importlib.util.spec_from_file_location('maturity_checks',ROOT/'scripts/prospectus_shell_maturity_checks.py')
checks=importlib.util.module_from_spec(spec);spec.loader.exec_module(checks)


def read(path):
    raw=path.read_bytes();return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);raw=json.dumps(value,sort_keys=True,ensure_ascii=False).encode()
    if str(path).endswith('.gz'):raw=gzip.compress(raw,mtime=0)
    with path.open('xb') as f:f.write(raw)


def consume(request,graph):
    p1=service.seal('P1',request['bundle'],{'request':digest(request)},{'request':request,'graph':graph})
    p2=service.construction_product(p1,ROOT);p3=service.interpretation_product(p1,p2)
    products={'P1':p1,'P2':p2,'P3':p3,'P4':service.law_product(p1,p3),'P5':service.financial_product(p1,p2,p3)}
    return products,service.consume(products,ROOT,mode='frozen')


def authenticate(path,manifest):
    assert hashlib.sha256(path.read_bytes()).hexdigest()==read(manifest)[str(path.relative_to(manifest.parent))]


def legacy():
    results=[]
    for name in read(OLD/'cases.json'):
        path=OLD/(name+'-packet.json.gz')
        bindings=read(OLD/'freeze.json')['bindings'];assert hashlib.sha256(path.read_bytes()).hexdigest()==bindings[str(path.relative_to(ROOT))]
        packet=read(path);products,answer=consume(packet['request'],packet['graph'])
        old=PRIOR/'ordinary'/(name+'-answer.json.gz');authenticate(old,PRIOR/'outputs.json')
        assert json.dumps(answer,sort_keys=True)==json.dumps(read(old),sort_keys=True),'Legacy full coupon answer changed'
        save(OUT/'legacy'/MODE/(name+'-answer.json.gz'),answer)
        save(OUT/'legacy'/MODE/(name+'-P5.json.gz'),products['P5'])
        results.append(name)
    return results


def danske():
    preparation=AUTH/'reviews/coupon-premises-359'
    prior=AUTH/'attempts/finance-conventions/attempt-010/ordinary'
    selected=[row for row in read(preparation/'cases.json') if row['id'].startswith('danske-')]
    assert [row['id'] for row in selected]==['danske-selected','danske-holiday','danske-excluded']
    for row in selected:
        data=row['products']
        ps=read(ROOT/data) if isinstance(data,str) else {k:read(ROOT/v) for k,v in data.items()}
        ps['P5']=service.financial_product(ps['P1'],ps['P2'],ps['P3'])
        answer=service.consume(ps,ROOT,mode='frozen')
        for kind,value in (('answer',answer),('P5',ps['P5'])):
            assert json.dumps(value,sort_keys=True)==json.dumps(read(prior/(row['id']+'-'+kind+'.json.gz')),sort_keys=True)
            save(OUT/'danske'/MODE/(row['id'].removeprefix('danske-')+'-'+kind+'.json.gz'),value)


def run():
    records=[]
    for name in read(PREP/'cases.json'):
        packet=read(PREP/(name+'-packet.json.gz'))
        ps,answer=consume(packet['request'],packet['graph']);checks.validate(answer,packet)
        if MODE=='installed':assert answer==read(OUT/'ordinary'/(name+'-answer.json.gz'))
        save(OUT/MODE/(name+'-answer.json.gz'),answer);save(OUT/MODE/(name+'-P5.json.gz'),ps['P5'])
        refused=[]
        for defect,bad in checks.bad_calculations(packet['request']['contract_calculation']):
            try:contract_terms.scenario(packet['admitted'],bad,packet['graph'],packet['assembly'])
            except ValueError:refused.append(defect)
            else:raise AssertionError('Accepted adverse input '+name+'/'+defect)
        bad_outputs=[]
        for defect,bad in checks.corrupt_answers(answer):
            try:checks.validate(bad,packet)
            except (AssertionError,KeyError):bad_outputs.append(defect)
            else:raise AssertionError('Accepted corrupt answer '+defect)
        records.append({'id':name,'cash_flows':len(packet['expected']['cash_flows']),
                        'input_refusals':refused,'corrupt_answer_refusals':bad_outputs})
    original=legacy()
    danske()
    imports={n:m.__file__ for n,m in sys.modules.items() if (n=='legalmath' or n.startswith('legalmath.')) and getattr(m,'__file__',None)}
    assert all(Path(p).resolve().is_relative_to(PACKAGE.resolve()) for p in imports.values())
    save(OUT/(MODE+'-imports.json'),imports)
    return {'status':'PASS','cases':records,'legacy_complete_answers_equal':original,
            'installed_ordinary_equal':MODE=='installed','import_count':len(imports),'whole_task_complete':False}


assert MODE in ('ordinary','installed'), 'Use original sealed preparation'
result=run()
save(OUT/(MODE+'-summary.json'),result)
print(json.dumps({'status':result['status'],'mode':MODE,'cases':result['cases'] if MODE=='prepare' else len(result['cases'])}))
