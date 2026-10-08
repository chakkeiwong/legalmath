#!/usr/bin/env python3
"""Actual finite behavior witnesses, with explicit projection and divergence rules."""
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import time
from legalmath.canonical import canonical, digest, loads, raw_digest
from legalmath.errors import LegalMathError
from legalmath.catala.native.boundary import make_snapshot
from legalmath.catala.native.runtime import build, evaluate, verify_cases, execute_values, interpreter_check
from legalmath.catala.native.semantics import SEMANTICS
from legalmath.interpretation.search.formal import bundle, expression, RULE
from legalmath.java.manifest import build_candidate, verify_candidate
from tests.catala.backend_support import JDK, TOOLCHAIN
from tests.catala.native.reference import task, f, controls
from tests.catala.native.test_extended import extended_control

ROOT=Path(__file__).resolve().parents[1]
TYPES={'boolean':'bool','money':'money_hkd','integer':'integer','date':'date'}


def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(canonical(v))


def candidate(t,source):
    return {'record_type':'NativeCatalaCandidate','task_hash':digest(t),'source':'```catala\nscope Control:\n'+source+'\n```',
            'interpretation':t['question'],'assumptions':[],'unresolved':[],
            'anchors':[{'unit_id':'clause.one','quote':t['packet']['selected_slice'],'code_excerpt':'scope Control:'}]}


def irbundle(t,expr):
    typ=TYPES[t['outputs'][0]['type']]
    reading={'statement':t['question'],'citations':[{'unit_id':'clause.one','quote':t['packet']['selected_slice']}],
        'formalization':{'facts':[{'name':x['name'],'type':TYPES[x['type']],'meaning':x['meaning'],'unit':x['unit'],
            'source_unit_ids':['clause.one'],'requires_judgment':False} for x in t['inputs']],
            'scope':'true','result':expr or '(integer 0)','result_type':typ}}
    return bundle(reading,t['packet'],t['valid_from'])


def ircase(t,b,s,ident,expected):
    facts={}
    for field in t['inputs']:
        n=field['name'];v=s['facts'][n];typ=TYPES[field['type']]
        if v['status']=='unknown':facts[n]={'type':typ,'status':'unknown','reason':'MISSING'}
        elif v['status']=='conflict':facts[n]={'type':typ,'status':'conflict','evidence_ids':['synthetic.a','synthetic.b']}
        else:facts[n]={'type':typ,'status':'known','value':v['value'],'evidence_ids':['synthetic.'+n],
                      **{k:v[k] for k in ('valid_from','valid_until','recorded_at')}}
    return {'id':ident,'bundle':b,'rule_id':RULE,'snapshot':{'subject_id':'synthetic','facts':facts},
            'valid_at':s['valid_at'],'known_at':s['known_at'],'expected':expected}


def run(out,name,types,output,source,expr,rows,explanation,mutate=None):
    directory=out/name;directory.mkdir()
    t=task('semantics.'+name,'Control',explanation,[f(n,typ) for n,typ in types],[f('result',output)])
    t['native_profile']='legalmath.catala.native.v2';c=candidate(t,source)
    b=irbundle(t,expr)
    if mutate:mutate(b)
    native_dir=directory/'native';build(t,c,native_dir,JDK,**TOOLCHAIN)
    nc=[];ic=[];errors=[]
    for i,(values,ne,ie,statuses) in enumerate(rows):
        snapshot=make_snapshot(t,values)
        for field,status in statuses.items():snapshot['facts'][field]={'status':status,'reason':'Deliberate boundary witness'}
        ident=name+'.'+str(i)
        ic.append(ircase(t,b,snapshot,ident,ie))
        if ne=='CONFLICT_ERROR':
            failures=[]
            for mode in ('plain','instrumented','interpreter'):
                try:
                    if mode=='interpreter':interpreter_check(t,c,values,{'result':'0'},compiler=TOOLCHAIN['compiler'],directory=native_dir)
                    else:execute_values(native_dir,values,JDK,instrumented=mode=='instrumented')
                except LegalMathError as e:
                    if e.code!='E_DEPENDENCY' or 'conflict' not in str(e.details).lower():raise
                    failures.append({'mode':mode,'code':e.code,'diagnostic':e.details})
                else:raise AssertionError('Distinct native exceptions did not conflict')
            errors.append({'id':ident,'snapshot':snapshot,'expected':'CONFLICT_ERROR','actual':failures})
        else:nc.append({'id':ident,'snapshot':snapshot,'expected':ne})
    nr=verify_cases(native_dir,nc,JDK,compiler=TOOLCHAIN['compiler']) if nc else None
    ib=build_candidate(b,directory/'ruleir',JDK);iv=verify_candidate(ib,ic,JDK)
    write(directory/'native-cases.json',nc);write(directory/'native-errors.json',errors);write(directory/'native-verification.json',nr)
    write(directory/'ruleir-cases.json',ic);write(directory/'ruleir-verification.json',iv)
    return {'id':name,'cases':len(rows),'passed':True,'explanation':explanation,
            'native_report_hash':digest(nr),'native_errors_hash':digest(errors),'ruleir_report_hash':digest(iv),
            'native_results':[{'id':r['case_id'],'status':r['result']['status'],'value':r['result'].get('value')} for r in (nr or {}).get('records',[])],
            'ruleir_results':[{'id':r['id'],'status':r['java']['status'],'value':r['java'].get('value')} for r in loads((directory/'ruleir/verification-results.json').read_bytes())]}


def main():
    started=time.monotonic();base=ROOT/'artifacts/catala/gap-closure/semantics'
    out=base/('executed-'+raw_digest(Path(__file__).read_bytes())[:12]);out.mkdir(parents=True,exist_ok=False)
    value=lambda x:{'status':'VALUE','value':{'result':x}}
    ir=lambda x:{'status':('TRUE' if x else 'FALSE') if type(x)is bool else 'VALUE','value':x}
    shared=[]
    for name,typ,expr,source,inputs in [
        ('boolean','boolean','(and a b)','a and b',[(False,False),(False,True),(True,False),(True,True)]),
        ('integer','integer','(+ a b)','a + b',[('-9','3'),('1000000000000000000000000','-1')]),
        ('money','money','(- a b)','a - b',[('101','100'),('-1','101'),('1000000000000000000000000','1')]),
        ('date','date','(> a b)','a > b',[('2024-02-29','2024-02-28'),('2024-02-29','2024-02-29')])]:
        rows=[]
        for a,b in inputs:
            result=a and b if typ=='boolean' else a>b if typ=='date' else str(int(a)+int(b) if typ=='integer' else int(a)-int(b))
            rows.append(({'a':a,'b':b},value(result),ir(result),{}))
        shared.append(run(out,name,[('a',typ),('b',typ)],'boolean' if typ=='date' else typ,
                          '  definition result equals '+source,expr,rows,
                          'Shared complete-input '+name+' operation; compare the single output value. Native VALUE wraps a scope record, RuleIR wraps a scalar and uses TRUE/FALSE for Boolean outputs.'))
    divergences=[]
    rows=[({'a':False,'b':True},{'status':'ABSTAIN','reason':'INCOMPLETE_INPUTS','value':None},ir(False),{'b':'unknown'}),
          ({'a':True,'b':True},{'status':'ABSTAIN','reason':'INCOMPLETE_INPUTS','value':None},{'status':'UNKNOWN'},{'b':'unknown'}),
          ({'a':False,'b':True},{'status':'ABSTAIN','reason':'CONFLICTING_INPUTS','value':None},{'status':'CONFLICT'},{'b':'conflict'})]
    divergences.append(run(out,'partial',[('a','boolean'),('b','boolean')],'boolean','  definition result equals a and b','(and a b)',rows,
        'Native requires both observations even when a is false. RuleIR false AND unknown is FALSE; true AND unknown is UNKNOWN. A referenced input conflict is CONFLICT in RuleIR and pre-execution ABSTAIN in native.'))
    for second in ('1','2'):
        def exception_body(b):
            span=b['source_spans'][0]['id'];meaning=b['interpretations'][0]['id']
            b['rules'][0]['body']={'node_id':'exceptions','op':'default','base':expression('(integer 0)','base'),
              'exceptions':[{'exception_id':n,'guard':expression(n,n+'.condition'),'value':expression('(integer '+v+')',n+'.result'),
                            'interpretation_id':meaning,'source_span_ids':[span]} for n,v in [('first','1'),('second',second)]]}
        src='  label baseRule definition result equals 0\n  exception baseRule definition result under condition first consequence equals 1\n  exception baseRule definition result under condition second consequence equals '+second
        rows=[]
        for a,b in ((False,False),(True,False),(False,True),(True,True)):
            ne='CONFLICT_ERROR' if a and b and second=='2' else value('1' if a else second if b else '0')
            ie={'status':'CONFLICT'} if a and b else ir('1' if a else second if b else '0')
            rows.append(({'first':a,'second':b},ne,ie,{}))
        divergences.append(run(out,'exception-'+second,[('first','boolean'),('second','boolean')],'integer',src,'(integer 0)',rows,
            'Pinned Catala coalesces identical literal consequences; different overlapping consequences raise conflict. RuleIR returns CONFLICT for two applicable exceptions even when their values are identical.',exception_body))
    def scale_body(b):b['rules'][0]['body']={'node_id':'half','op':'scale','arg':expression('amount','amount'),'numerator':'1','denominator':'2'}
    rows=[({'amount':v},value(result),{'status':'ERROR','reason_codes_include':['E_INEXACT_SCALE']},{}) for v,result in [('101','51'),('-101','-51')]]
    rows.append(({'amount':'100'},value('50'),ir('50'),{}))
    divergences.append(run(out,'rounding',[('amount','money')],'money','  definition result equals amount * 0.5','amount',rows,
        'Native money multiplication rounds half minor units away from zero; RuleIR exact scaling rejects a nonintegral minor-unit result. The exact 100/2 control agrees.',scale_body))
    features=[]
    for name,control in [('calendar-months',controls()[2]),('optional-payload-import',extended_control())]:
        t,c,cs=deepcopy(control);t['native_profile']='legalmath.catala.native.v2';c['task_hash']=digest(t)
        d=out/name;build(t,c,d,JDK,**TOOLCHAIN);r=verify_cases(d,cs,JDK,compiler=TOOLCHAIN['compiler'])
        write(d/'cases.json',cs);write(d/'verification.json',r)
        features.append({'id':name,'native_passed':r['passed'],'ruleir':'UNSUPPORTED_IN_CURRENT_PROFILE; not counted as a RuleIR failure','report_hash':digest(r)})
    report={'record_type':'CatalaSemanticConformance','semantics':SEMANTICS,'semantics_hash':digest(SEMANTICS),
            'shared_controls':shared,'intentional_divergences':divergences,'native_features':features,'passed':True,
            'claims':'Finite executable references only; no general equivalence, legal correctness or superiority.',
            'run_directory':out.name}
    write(base/'conformance.json',report)
    write(out/'run-manifest.json',{'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'script_sha256':raw_digest(Path(__file__).read_bytes()),'command':sys.argv,'python':sys.executable,'jdk':str(JDK),
        'CPU_GPU':'CPU; no GPU libraries','seeds':'N/A deterministic','wall_ms':int((time.monotonic()-started)*1000),
        'plan':'docs/plans/catala-gap-closure.md','data_version':digest({'shared':shared,'divergences':divergences}),
        'result':'../conformance.json','result_hash':digest(report)})
    print('PASS',len(shared),'shared controls',len(divergences),'divergence controls',len(features),'native feature controls')

if __name__=='__main__':main()
