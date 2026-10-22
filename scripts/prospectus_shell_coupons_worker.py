"""Source preparation and complete-consumer checks for Shell's fixed coupon term."""
from copy import deepcopy
from datetime import date, timedelta
from fractions import Fraction
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT, OUT, MODE = Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3]
AUTH=ROOT/'docs/implementation/prospectus-execution-authority'
PREP=AUTH/'reviews/shell-full-coupons-360'
SOURCE=AUTH/'attempts/finance-conventions/attempt-002'
PRIOR=AUTH/'attempts/finance-conventions/attempt-010'
os.environ['CUDA_VISIBLE_DEVICES']='-1'
PACKAGE=OUT/'installed' if MODE=='installed' else ROOT/'src'
sys.path.insert(0,str(PACKAGE))
from legalmath.prospectus.successor import service, source_graph, contract_assembly, contract_terms, occurrences
from legalmath.prospectus.successor.contracts import digest

DUE=[f'{y}-12-10' for y in range(2021,2031)]
START=['2020-09-10',*DUE[:-1]]

def read(p):
    raw=Path(p).read_bytes();return json.loads(gzip.decompress(raw) if str(p).endswith('.gz') else raw)
def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(value,sort_keys=True,ensure_ascii=False).encode()
    if str(p).endswith('.gz'):raw=gzip.compress(raw,mtime=0)
    with p.open('xb') as f:f.write(raw)

def expected(holiday=False,form='GLOBAL',excluded=False):
    rows=[]
    for i,(start,end) in enumerate(zip(START,DUE)):
        refs=([{'start':'2019-12-10','end':'2020-12-10'},{'start':'2020-12-10','end':'2021-12-10'}]
              if i==0 else [{'start':start,'end':end}])
        count=Fraction()
        for ref in refs:
            left,right=map(date.fromisoformat,(ref['start'],ref['end']))
            a,b=max(left,date.fromisoformat(start)),min(right,date.fromisoformat(end))
            count+=Fraction((b-a).days,(right-left).days)
        pay=date.fromisoformat(end)
        while pay.weekday() in (5,6) or holiday and pay.isoformat()==DUE[0]:pay+=timedelta(days=1)
        principal=500000000 if form=='GLOBAL' else 100000
        unrounded=principal*count/100
        basis=unrounded if form=='GLOBAL' else 1000*count/100
        cents=basis*100;q,r=divmod(cents.numerator,cents.denominator)
        amount=Fraction(q+int(2*r>=cents.denominator),100)*(1 if form=='GLOBAL' else 100)
        rows.append({'start':start,'end':end,'payment':pay.isoformat(),'references':refs,
                     'fraction':str(count),'unrounded':str(unrounded),'amount':str(amount),'excluded':excluded})
    assert rows[0]['fraction']=='457/366'
    assert sum((Fraction(r['amount']) for r in rows),Fraction())==(Fraction('51243169.40') if form=='GLOBAL' else 10249)
    return rows

def consume(request,graph):
    p1=service.seal('P1',request['bundle'],{'request':digest(request)},{'request':request,'graph':graph})
    p2=service.construction_product(p1,ROOT);p3=service.interpretation_product(p1,p2)
    ps={'P1':p1,'P2':p2,'P3':p3,'P4':service.law_product(p1,p3),'P5':service.financial_product(p1,p2,p3)}
    return ps,service.consume(ps,ROOT,mode='frozen')

def prepare():
    cases=[]
    for form in ('GLOBAL','DEFINITIVE'):
        old=read(SOURCE/('selected-'+form.lower()+'-products.json.gz'))
        for variant in ('plain','holiday','excluded'):
            name=form.lower()+'-'+variant;holiday=variant=='holiday';excluded=variant=='excluded'
            request=deepcopy(old['P1']['payload']['request']);graph=deepcopy(old['P1']['payload']['graph'])
            path=PREP/(name+'-hypotheses.txt')
            text=('HYPOTHETICAL FULL COUPON TERM ONLY. Actual ownership, note form, entitlement and payment are unknown.\n'
                  f'Supplied form {form}; unchanged holdings and this form through all ten coupons.\n'
                  'No early redemption, default, principal reduction, tax or currency change; timely presentation where required.\n'
                  'Hypothetical calendar: Saturday and Sunday weekends; coverage 1 September 2020 to 1 January 2031; '
                  +('10 December 2021 is a holiday.' if holiday else 'no holidays.')+'\n'
                  +('No supplied holder is entitled.' if excluded else 'Supplied holdings are entitled for every period.')+'\n'
                  'Accrual end, determination and payment have explicit chronological order; all other events are outside this slice.\n')
            with path.open('x') as f:f.write(text)
            doc=next(d for d in request['bundle']['documents'] if d['id']=='hypotheses')
            doc.update(path=str(path.relative_to(ROOT)),sha256=digest(path.read_bytes()))
            # Only the new plain-text hypothesis is extracted. Original PDF
            # source units and metadata are preserved exactly from sealed002.
            text_bundle={**deepcopy(request['bundle']),'documents':[deepcopy(doc)]}
            generated=source_graph.build(text_bundle,ROOT)
            assert len(generated['units'])==1 and not generated['references'] and not generated['unresolved']
            graph['documents']=[d for d in graph['documents'] if d['id']!='hypotheses']+generated['documents']
            graph['units']=[u for u in graph['units'] if u['document']!='hypotheses']+generated['units']
            graph['bundle_sha256']=digest(request['bundle']);graph['unit_count']=len(graph['units'])
            assert [u for u in graph['units'] if u['document']!='hypotheses']==[u for u in old['P1']['payload']['graph']['units'] if u['document']!='hypotheses']
            assembly=contract_assembly.assemble(graph,request['assembly'])
            request['term_interpretations']['assembly_sha256']=digest(assembly)
            admitted=contract_terms.admit(graph,assembly,request['term_interpretations'])
            evidence={'source':occurrences.anchor(generated['units'][0]),'reason':'Explicit whole-term numerical hypothesis; no actual facts inferred'}
            original=request['contract_calculation']['premises']
            common={k:deepcopy(original[k]) for k in ('issue_id','source_sha256','premise_kind','holdings','event_scope')}
            common.update(profile='fixed-term.v1',calendar={'edition':'HYPOTHETICAL Sat/Sun '+variant,
                'valid_from':'2020-09-01','valid_until':'2031-01-01','holidays':[DUE[0]] if holiday else [],
                'weekend':[5,6],'coverage':'COMPLETE_DECLARED_INTERVAL'},
                term_assumptions={k:True for k in ('unchanged_holdings','unchanged_note_form','no_early_redemption','no_default','no_principal_reduction','no_tax','no_currency_change','timely_presentation')})
            if excluded:
                for h in common['holdings']:h['entitled']=False
            common['evidence']={k:deepcopy(evidence) for k in ('calendar','holdings','event_scope','term_assumptions')}
            rows=expected(holiday,form,excluded);periods=[]
            for i,row in enumerate(rows):
                events=[{'id':f'period-{i}-{kind}','kind':kind,'at':day+'T00:00:00Z','order':order}
                        for kind,day,order in [('accrual_start',row['start'],0),('accrual_end',row['end'],0),('determination',row['end'],1),('payment',row['payment'],2)]]
                periods.append({'payment_date':row['payment'],'events':events,'evidence':{k:deepcopy(evidence) for k in ('payment_date','events')}})
            legacy_premise={k:deepcopy(v) for k,v in common.items() if k!='term_assumptions'}
            legacy_premise['profile']='fixed-coupon.v3';legacy_premise['evidence'].pop('term_assumptions')
            legacy_premise.update({k:deepcopy(periods[0][k]) for k in ('payment_date','events')})
            legacy_premise['evidence'].update(deepcopy(periods[0]['evidence']))
            legacy=deepcopy(request);legacy['contract_calculation']={'version':'selected-coupon-calculation.v1','terms_sha256':digest(admitted),'premises':legacy_premise}
            _,answer=consume(legacy,graph)
            request['contract_calculation']={'version':'selected-fixed-term-calculation.v1','terms_sha256':digest(admitted),'premises':common,'periods':periods}
            try:contract_terms.scenario(admitted,request['contract_calculation'],graph,assembly)
            except ValueError as exc:refusal=str(exc)
            else:raise AssertionError('New route unexpectedly supported before repair')
            save(PREP/(name+'-packet.json.gz'),{'request':request,'graph':graph,'assembly':assembly,'admitted':admitted,'baseline_answer':answer,'expected':rows,'prior_refusal':refusal})
            cases.append(name)
    package={'cases':[{'id':str(i),'convention':'ACT_ACT_ICMA','start':r['start'],'end':r['end'],'references':r['references'],'frequency':1,'eom':False} for i,r in enumerate(expected())],'calendar_dates':[]}
    save(PREP/'package-input.json',package);save(PREP/'cases.json',cases)
    return {'status':'PASS','prepared_cases':len(cases),'source_mode':'Historical PDF units unchanged; new plain-text hypotheses only','new_version_refused':True}

def validate_answer(answer,packet):
    value=answer['questions']['Q5']['value'];rows=packet['expected']
    assert value['version']=='conditional-fixed-term.v1' and len(value['calculations'])==len(value['coupon_schedule'])==10
    assert not value['redemption_calculated'] and not value['full_settlement_supported'] and value['actual_event']=='NOT_ESTABLISHED'
    assert value['term_assumptions']==packet['request']['contract_calculation']['premises']['term_assumptions']
    for i,(c,p,r) in enumerate(zip(value['calculations'],value['coupon_schedule'],rows)):
        assert p=={'accrual_start':r['start'],'accrual_end':r['end'],'due_date':r['end'],'stub':'LONG_FIRST' if i==0 else 'REGULAR'}
        assert c['day_fraction']==r['fraction'] and c['payment_date']==r['payment']
        s=c['calculation_inputs']
        for key,target in [('accrual_start',r['start']),('accrual_end',r['end']),('references',r['references']),('due_date',r['end'])]:assert s[key]==target
        assert s['calendar']==packet['request']['contract_calculation']['premises']['calendar']
        assert s['events']==packet['request']['contract_calculation']['periods'][i]['events']
        assert s['holdings']==packet['request']['contract_calculation']['premises']['holdings']
        if r['excluded']:assert c['transfers']==[]
        else:
            assert len(c['transfers'])==1 and c['transfers'][0]['amount']==r['amount'] and c['transfers'][0]['unrounded']==r['unrounded']
        assert c['actual_event']=='NOT_ESTABLISHED' and not c['entitlement_basis']['legal_entitlement_established']
    assert value['calculations'][0]==packet['baseline_answer']['questions']['Q5']['value']['calculation']
    assert {k:v for k,v in answer['questions'].items() if k!='Q5'}=={k:v for k,v in packet['baseline_answer']['questions'].items() if k!='Q5'}
    assert not answer['may_execute_transaction'] and not answer['independent_legal_acceptance']
    assert answer['report_sha256']==digest({k:v for k,v in answer.items() if k!='report_sha256'})

def run():
    records=[]
    for name in read(PREP/'cases.json'):
        packet=read(PREP/(name+'-packet.json.gz'))
        ps,answer=consume(packet['request'],packet['graph']);validate_answer(answer,packet)
        if MODE=='installed':assert answer==read(OUT/'ordinary'/(name+'-answer.json.gz'))
        save(OUT/MODE/(name+'-answer.json.gz'),answer);save(OUT/MODE/(name+'-P5.json.gz'),ps['P5'])
        refused=[]
        for defect in ('missing-period','duplicate-period','wrong-date','unknown-event','false-assumption','over-issue','stale-terms','premise-override'):
            bad=deepcopy(packet['request']['contract_calculation'])
            if defect=='missing-period':bad['periods'].pop()
            elif defect=='duplicate-period':bad['periods'][1]=deepcopy(bad['periods'][0])
            elif defect=='wrong-date':bad['periods'][1]['payment_date']='2022-12-10'
            elif defect=='unknown-event':bad['periods'][1]['events'][0]['kind']='unknown'
            elif defect=='false-assumption':bad['premises']['term_assumptions']['no_default']=False
            elif defect=='over-issue':bad['premises']['holdings'][0]['principal']='500000001'
            elif defect=='stale-terms':bad['terms_sha256']='0'*64
            else:bad['premises']['annual_rate']='0.5'
            try:contract_terms.scenario(packet['admitted'],bad,packet['graph'],packet['assembly'])
            except ValueError:refused.append(defect)
            else:raise AssertionError('Accepted adverse case '+defect)
        for defect in ('omitted-last','wrong-regular-amount','false-redemption'):
            bad=deepcopy(answer);v=bad['questions']['Q5']['value']
            if defect=='omitted-last':v['calculations'].pop()
            elif defect=='false-redemption':v['redemption_calculated']=True
            else:v['calculations'][1]['day_fraction']='457/366'
            bad['report_sha256']=digest({k:v for k,v in bad.items() if k!='report_sha256'})
            try:validate_answer(bad,packet)
            except (AssertionError,KeyError):pass
            else:raise AssertionError('Permissive answer checker '+defect)
        records.append({'id':name,'coupons':10,'input_refusals':refused,'corrupt_answer_refusals':3})
    for form in ('global','definitive'):
        ps=read(SOURCE/('selected-'+form+'-products.json.gz'))
        ps['P5']=service.financial_product(ps['P1'],ps['P2'],ps['P3'])
        assert service.consume(ps,ROOT)==read(PRIOR/'ordinary'/('shell-selected-'+form+'-answer.json.gz'))
    imports={n:m.__file__ for n,m in sys.modules.items() if (n=='legalmath' or n.startswith('legalmath.')) and getattr(m,'__file__',None)}
    assert all(Path(p).resolve().is_relative_to(PACKAGE.resolve()) for p in imports.values())
    save(OUT/(MODE+'-imports.json'),imports)
    return {'status':'PASS','cases':records,'legacy_complete_answers_equal':True,'installed_ordinary_equal':MODE=='installed','import_count':len(imports),'whole_task_complete':False}

value=prepare() if MODE=='prepare' else run()
save(OUT/(MODE+'-summary.json'),value)
print(json.dumps({'status':'PASS','mode':MODE,'cases':value.get('prepared_cases',len(value.get('cases',[])))}))
