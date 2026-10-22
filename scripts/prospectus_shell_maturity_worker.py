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
        packet=read(path);_,answer=consume(packet['request'],packet['graph'])
        old=PRIOR/'ordinary'/(name+'-answer.json.gz');authenticate(old,PRIOR/'outputs.json')
        assert answer==read(old),'Legacy full coupon answer changed'
        results.append(name)
    return results


def prepare():
    original=legacy();cases=[]
    for form in ('global','definitive'):
        variants=['plain','maturity-holiday','coupon-only','principal-only','excluded']
        if form=='definitive':variants.append('two-recipients')
        for variant in variants:
            name=form+'-'+variant;old=read(OLD/(form+'-plain-packet.json.gz'))
            request=deepcopy(old['request']);graph=deepcopy(old['graph'])
            coupon=request['contract_calculation'];common=coupon['premises']
            text=('HYPOTHETICAL COUPONS AND SCHEDULED PRINCIPAL. No actual payment or legal ownership established.\n'
                  f'Form {form}; case {variant}; unchanged holdings and form through 10 December 2030.\n'
                  'Calendar is a complete hypothetical payment calendar, not observed London bank days.\n'
                  'All coupon term assumptions apply. Principal eligibility is separately declared per account.\n'
                  'For this conditional calculation assume the following statements are true:\n'+
                  '\n'.join(checks.ASSUMPTIONS)+'\n')
            path=PREP/(name+'-hypotheses.txt')
            with path.open('x') as f:f.write(text)
            doc=next(d for d in request['bundle']['documents'] if d['id']=='hypotheses')
            doc.update(path=str(path.relative_to(ROOT)),sha256=digest(path.read_bytes()))
            generated=source_graph.build({**deepcopy(request['bundle']),'documents':[deepcopy(doc)]},ROOT)
            assert len(generated['units'])==1 and not generated['references'] and not generated['unresolved']
            graph['documents']=[d for d in graph['documents'] if d['id']!='hypotheses']+generated['documents']
            graph['units']=[u for u in graph['units'] if u['document']!='hypotheses']+generated['units']
            graph['unit_count']=len(graph['units']);graph['bundle_sha256']=digest(request['bundle'])
            assert [u for u in graph['units'] if u['document']!='hypotheses']==[u for u in old['graph']['units'] if u['document']!='hypotheses']
            evidence={'source':occurrences.anchor(generated['units'][0]),'reason':'Explicit hypothetical assumptions; no real event or ownership inferred'}
            common['evidence']={k:deepcopy(evidence) for k in common['evidence']}
            if variant in {'principal-only','excluded'}:common['holdings'][0]['entitled']=False
            if variant=='two-recipients':
                common['holdings'].append({**common['holdings'][0],'account_id':'second-account','legal_holder_id':'second-holder','principal':'199000'})
            if variant=='maturity-holiday':common['calendar']['holidays']=['2030-12-10']
            for i,period in enumerate(coupon['periods']):
                period['evidence']={k:deepcopy(evidence) for k in period['evidence']}
                day=date(2021+i,12,10)
                while day.weekday() in common['calendar']['weekend'] or day.isoformat() in common['calendar']['holidays']:
                    day+=timedelta(days=1)
                period['payment_date']=day.isoformat()
                next(e for e in period['events'] if e['kind']=='payment')['at']=day.isoformat()+'T00:00:00Z'
            assembly=contract_assembly.assemble(graph,request['assembly'])
            request['term_interpretations']['assembly_sha256']=digest(assembly)
            admitted=contract_terms.admit(graph,assembly,request['term_interpretations'])
            coupon['terms_sha256']=digest(admitted)
            _,baseline=consume(request,graph)
            pay=coupon['periods'][-1]['payment_date']
            redemption={'version':'conditional-scheduled-redemption.v1','premise_kind':'HYPOTHETICAL',
                'source_profile':read(PREP/'source-profile.json'),'payment_date':pay,
                'principal_entitlements':[{'account_id':h['account_id'],'principal_entitled':variant not in {'coupon-only','excluded'}} for h in common['holdings']],
                'assumptions':{k:True for k in checks.ASSUMPTIONS},
                'events':[{'id':'maturity-'+kind,'kind':kind,'at':day+'T00:00:00Z','order':order}
                    for kind,day,order in [('redemption_due','2030-12-10',0),('presentation',pay,1),('payment',pay,2)]],
                'evidence':{k:deepcopy(evidence) for k in ('principal_entitlements','assumptions','payment_date','events')}}
            request['contract_calculation']={'version':'selected-fixed-maturity-calculation.v1','terms_sha256':digest(admitted),
                                             'coupon_term':deepcopy(coupon),'redemption':redemption}
            packet={'request':request,'graph':graph,'assembly':assembly,'admitted':admitted,'baseline_answer':baseline}
            packet['expected']=checks.expected(packet)
            try:contract_terms.scenario(admitted,request['contract_calculation'],graph,assembly)
            except ValueError as exc:packet['prior_refusal']=str(exc)
            else:raise AssertionError('Maturity route unexpectedly supported before repair')
            save(PREP/(name+'-packet.json.gz'),packet);cases.append(name)
    save(PREP/'cases.json',cases)
    return {'status':'PASS','cases':len(cases),'legacy_complete_answers_equal':original,'unsupported_route_reproduced':True}


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
    imports={n:m.__file__ for n,m in sys.modules.items() if (n=='legalmath' or n.startswith('legalmath.')) and getattr(m,'__file__',None)}
    assert all(Path(p).resolve().is_relative_to(PACKAGE.resolve()) for p in imports.values())
    save(OUT/(MODE+'-imports.json'),imports)
    return {'status':'PASS','cases':records,'legacy_complete_answers_equal':original,
            'installed_ordinary_equal':MODE=='installed','import_count':len(imports),'whole_task_complete':False}


result=prepare() if MODE=='prepare' else run()
save(OUT/(MODE+'-summary.json'),result)
print(json.dumps({'status':result['status'],'mode':MODE,'cases':result['cases'] if MODE=='prepare' else len(result['cases'])}))
