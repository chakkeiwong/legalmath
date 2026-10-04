"""Actual compiled, typed STR controls plus e-IP categories and duty replay."""
from pathlib import Path
from copy import deepcopy
import json
import os
import subprocess
from legalmath.canonical import digest,raw_digest
from legalmath.interpretation.assurance.diversity import save
from legalmath.interpretation.assurance.composition import combine
from legalmath.interpretation.assurance.legal_profile import replay_authority_bound_duty
from legalmath.interpretation.assurance.monitor import Monitor
from legalmath.interpretation.search.formal import bundle,project,RULE
from legalmath.java.manifest import build_candidate,verify_candidate
from legalmath.ir.evaluate import evaluate
from decision_live import load_case,AT
ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'docs/implementation/interpretation-round13'
JDK=ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'

def make_reading(packet,ident,meaning,statement,names,scope,result,citations,questions=()):
    return {'local_id':ident,'family':'scope','subject':ident,'statement':'['+meaning+'] '+statement,
      'distinction':'Explicit authored control used for conditional engineering demonstration',
      'citations':citations,'assumptions':['Selected scope and supplied classifications are factual preconditions; this is not whole-document compliance.'],
      'questions':list(questions),'formalization':{'facts':[{'name':n,'type':t,'meaning':m,'unit':u,
         'source_unit_ids':[q['unit_id'] for q in citations],'requires_judgment':j} for n,t,m,u,j in names],
         'scope':scope,'result':result,'result_type':'bool'}}

def quotes(packet,phrase):
    u=next(u for u in packet['units'] if phrase in u['text']);return [{'unit_id':u['unit_id'],'quote':u['text']}]

def snapshot(compiled,values,ident):
    if set(values)!={f['name'] for f in compiled['facts']}:raise ValueError('Explicit fact set required')
    facts={}
    for fact in compiled['facts']:
        name= fact['name'];v=values[name]
        facts[name]={'type':fact['type'],'status':'unknown','reason':'MISSING'} if v is None else {
          'type':fact['type'],'status':'known','value':v,'evidence_ids':['reference.'+ident],
          'valid_from':AT,'valid_until':None,'recorded_at':AT}
    return {'subject_id':'reference.'+ident,'facts':facts}

def build_str():
    data=load_case('26ec2');p=data['packet']
    quotes_all=quotes(p,'following means')+quotes(p,'(XML)')+quotes(p,'prescribed PDF')+quotes(p,'web-based STR')+quotes(p,'Hongkong Post e-Cert')
    names=[('licensed_firm','bool','Actor belongs to the three stated licensed-firm categories','firm',True),
           ('after_launch','bool','Original submission occurs at or after 9am Hong Kong time on 2 February 2026','submission',True),
           ('method_xml','bool','Selected method is XML submission','submission',False),
           ('method_pdf','bool','Selected method is upload of completed prescribed PDF form','submission',True),
           ('method_web','bool','Selected method is completion of STREAMS 2 web form','submission',True),
           ('via_streams_2','bool','Original event used STREAMS 2','submission',False),
           ('certificate_satisfied','bool','Required electronic certificate is supplied in the accepted technical manner','submission',True)]
    scope='(and licensed_firm after_launch)'
    ec=make_reading(p,'ecert','TRUE_IS_SATISFIED','The e-Cert requirement applies to the selected method.',
          names,scope,'(or method_xml method_pdf)',quotes_all,questions=['The fact adapter must establish exactly one method; unknown or invalid method stays unknown.'])
    compliance=make_reading(p,'submission','TRUE_IS_COMPLIANT','The selected submission meets channel, listed-method and e-Cert conditions.',
          names,scope,'(and via_streams_2 (or method_web (and method_xml certificate_satisfied) (and method_pdf certificate_satisfied)))',
          quotes_all,questions=['XML schema conformance and technical test are separate controls and remain required for a whole-document decision.'])
    trigger=make_reading(p,'resubmission','TRUE_IS_SATISFIED','The original submission event triggers the resubmission duty.',
          names,scope,'(not via_streams_2)',quotes(p,'required to re-submit'),
          questions=['The original event must be an STR actually submitted to JFIU; the resubmission deadline is unspecified.','Midnight versus operational launch remains a retained timing alternative.'])
    candidates={'ecert':ec,'submission':compliance,'resubmission':trigger}
    components=[{'component_id':k,'question':r['statement'],'output_meaning':r['statement'].split(']')[0][1:]} for k,r in candidates.items()]
    compiled,bindings=combine(components,list(candidates),candidates,p,AT)
    return compiled,bindings,candidates

def str_cases(compiled,bindings,refs):
    cases=[];expectations=[]
    for ref in refs:
        if ref['method'] not in (None,'xml','pdf','web'):
            raise ValueError('Unknown method cannot become a negative classification')
        # These complete maps are explicit authored facts, not inferred truth.
        local={'licensed_firm':ref['licensed'],'after_launch':ref['after_launch'],
               'via_streams_2':ref['streams'],'certificate_satisfied':ref['cert']}
        for m in ('xml','pdf','web'):local['method_'+m]=None if ref['method'] is None else ref['method']==m
        all_values={}
        for b in bindings:all_values.update({new:local[old] for old,new in b['fact_mapping'].items()})
        snap=snapshot(compiled,all_values,ref['id'])
        for b in bindings:
            expected=ref['expected'][b['component_id']]
            cases.append({'id':ref['id']+'.'+b['component_id'],'bundle':compiled,'snapshot':snap,
                          'rule_id':b['rule_id'],'valid_at':AT,'known_at':AT,'expected':{'status':expected}})
            expectations.append(expected)
    return cases

def eip_cases():
    p=load_case('24ec50')['packet']
    categories=['investment_linked_assurance','mandatory_provident','open_ended_fund','paper_gold',
                'pooled_retirement','real_estate_trust','unit_trust_mutual_fund','unlisted_structured']
    names=[(c,'bool','Product is classified in the corresponding explicit footnote-1 category','product',True) for c in categories]
    names += [('application_or_submission','bool','Assessed component is an investment-product application or submission','component',True),
              ('submission_date','date','Local date of the submission','Hong Kong calendar date',False),
              ('via_eip','bool','Submission made through e-IP','component',False)]
    scope='(and (or '+' '.join(categories)+') application_or_submission (>= submission_date (date 2024-11-30)))'
    reading=make_reading(p,'eip','TRUE_IS_COMPLIANT','Within listed-category application/submission scope, the channel is e-IP.',
        names,scope,'via_eip',quotes(p,'Investment-linked assurance schemes')+quotes(p,'Starting 30 November'),
        questions=['Footnote categories are explicit; deciding whether an unfamiliar product belongs to one is not automated.',
                   'Optional annual fee settlement does not alone make that component an application/submission.'])
    compiled=bundle(reading,p,AT);cases=[]
    for i,c in enumerate(categories):
        vals={k:k==c for k in categories};vals.update(application_or_submission=True,submission_date='2024-11-30',via_eip=True)
        cases.append({'id':'category.'+c,'bundle':compiled,'snapshot':snapshot(compiled,vals,'eip.'+c),
                      'rule_id':RULE,'valid_at':AT,'known_at':AT,'expected':{'status':'TRUE'}})
    for ident,updates,expected in [('unknown_classification',{k:None for k in categories},'UNKNOWN'),
        ('old_date',{'submission_date':'2024-11-29'},'OUT_OF_SCOPE'),('wrong_channel',{'via_eip':False},'FALSE'),
        ('annual_fee',{'application_or_submission':False},'OUT_OF_SCOPE')]:
        vals={k:k==categories[0] for k in categories};vals.update(application_or_submission=True,submission_date='2024-11-30',via_eip=True);vals.update(updates)
        cases.append({'id':ident,'bundle':compiled,'snapshot':snapshot(compiled,vals,'eip.'+ident),
                      'rule_id':RULE,'valid_at':AT,'known_at':AT,'expected':{'status':expected}})
    return compiled,cases,reading

def events(compiled):
    opening='2026-02-03T00:00:00.000000Z';later='2026-02-04T00:00:00.000000Z'
    header={'stream_id':'str.report.one','profile':'achievement','inception':opening,'subject':'report.one',
      'category':'str','actor':'firm.one','action':'resubmit','obligation_id':'str.resubmit.one',
      'profile_version':'0.1','ordering_authority':'attributed.sequence','initial_snapshot':None}
    event={k:header[k] for k in ('stream_id','subject','category','actor','action','obligation_id')}
    event.update(id='opening.one',sequence=1,kind='obligation.opened',occurred_at=opening,recorded_at=opening,
                 evidence_id='submitted.outside.streams',activation=opening,deadline=None,source_bundle_hash=digest(compiled))
    request={'header':header,'events':[event],'valid_at':later,'known_at':later,'completeness':None}
    performed=deepcopy(request)
    success={k:v for k,v in event.items() if k not in ('activation','deadline','source_bundle_hash')}
    success.update(id='performance.one',sequence=2,kind='obligation.performed',occurred_at=later,recorded_at=later,evidence_id='stream2.resubmission')
    performed['events'].append(success)
    cases=[{'id':'duty.open.no_invented_deadline','request':request,'expected':{'status':'OPEN'}},
           {'id':'duty.performed','request':performed,'expected':{'status':'SATISFIED_ON_TIME'}}]
    authority=digest(load_case('26ec2')['packet'])
    comparisons=[replay_authority_bound_duty(request,authority,authority),
                 replay_authority_bound_duty(request,authority,'0'*64),
                 replay_authority_bound_duty(request,authority,None)]
    return cases,comparisons

def transfer_references(out, selected, refs):
    """Compare the old denominator with binaries, retaining the other question."""
    path=ROOT/'docs/implementation/interpretation-round12/transfer-reference-packets.json'
    reference=next(r for r in json.loads(path.read_text())['transfer_references'] if r['case_id']=='26ec2')
    source=ROOT/'examples/integrated-assurance/sources/26ec2.json'
    if raw_digest(source.read_bytes())!=reference['source_sha256']:
        raise ValueError('Transfer source changed')
    mapping={'xml':('xml_cert','xml'), 'pdf':('pdf_no_cert','pdf'),
             'web':('web_cert_absent','web'), 'unknown-method':('unknown_method',None)}
    expected={'REQUIRED_BY_FOOTNOTE_3':'TRUE','NOT_REQUIRED_BY_THIS_FOOTNOTE':'FALSE','UNKNOWN':'UNKNOWN'}
    observed={r['id']:r for r in json.loads((out/'str/verification-results.json').read_text())}
    authored={r['id']:r for r in refs['cases']};cases={r['id']:r for r in selected}
    rows=[]
    for original in reference['cases']:
        if original['id'] not in mapping:
            if original['id']!='urgent-blackout':raise ValueError('Unaccounted transfer reference')
            rows.append({'reference':original,'status':'UNALIGNED_OTHER_QUESTION',
                         'reason':'Urgent contact during blackout is not post-launch certificate applicability.'})
            continue
        new_id,method=mapping[original['id']];scenario=authored[new_id];case_id=new_id+'.ecert'
        if not (scenario['method']==method and scenario['licensed'] is True and scenario['after_launch'] is True
                and original['facts']['period']=='after launch' and original['facts']['licensed_firm'] is True):
            raise ValueError('Transfer assumptions do not align')
        row=observed[case_id];target=expected[original['expected']]
        if any(row[engine]['status']!=target for engine in ('java','python')):
            raise ValueError('Compiled result disagrees with transfer reference '+original['id'])
        rows.append({'reference':original,'case_id':case_id,'status':'CONDITIONAL_MATCH',
                     'expected_status':target,'java_status':row['java']['status'],
                     'python_status':row['python']['status'],'snapshot_hash':digest(cases[case_id]['snapshot']),
                     'extra_facts':{'streams':scenario['streams'],'certificate':scenario['cert']},
                     'extra_fact_role':'Stipulated and irrelevant to the applicability expression, not inferred legal facts.'})
    return {'denominator':len(rows),'ecert_question_aligned':sum(r['status']=='CONDITIONAL_MATCH' for r in rows),
            'urgent_contact_other_question':sum(r['status']=='UNALIGNED_OTHER_QUESTION' for r in rows),
            'reference_file_sha256':raw_digest(path.read_bytes()),'rows':rows,
            'basis':'Authored post-generation alignment, original expected answers unchanged',
            'independent_legal_reference':False}


def run(out):
    out=Path(out);refs=json.loads((DOC/'str-reference-cases.json').read_text())
    compiled,bindings,readings=build_str();cases=str_cases(compiled,bindings,refs['cases'])
    event_cases,event_report=events(compiled)
    eip,ecases,ereading=eip_cases()
    builds=[];comparisons=[]
    for label,b,selected in [('str',compiled,cases),('eip',eip,ecases)]:
        built=build_candidate(b,out/label,JDK)
        verified=verify_candidate(built,selected,JDK,event_cases=event_cases if label=='str' else None)
        save(out/label/'bundle.json',b);save(out/label/'reference-cases.json',selected)
        for c in selected:
            actual=evaluate(b,c['snapshot'],c['rule_id'],AT,AT)
            if actual['status']!=c['expected']['status']:raise ValueError('Reference failed '+c['id'])
            comparisons.append({**c,'jar':built['jar'],'class_name':built['class_name']})
        builds.append({'label':label,'build':built,'verification':verified})
    save(out/'formal-input.json',{'cases':comparisons,'jdk':str(JDK)})
    argv=[str(ROOT/'.localresources/assurance-tools/venv/bin/python'),'-m','legalmath.interpretation.assurance.sidecar',
          'formal-cases','--input',str(out/'formal-input.json'),'--output',str(out/'formal-result.json')]
    subprocess.run(argv,cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'CUDA_VISIBLE_DEVICES':'-1'},check=True,timeout=180)
    independent=json.loads((out/'formal-result.json').read_text())
    if independent['status']!='PASS':raise ValueError('Independent formal disagreement')
    catala=build_candidate(compiled,out/'str-catala',JDK,backend='catala',catala_toolchain={
        'compiler':ROOT/'.localresources/catala-toolchain/opam-root/catala-clean-1.2.1/bin/catala',
        'upstream':ROOT/'.localresources/catala-toolchain/catala-0f895e048d19dbe72f24cdd6d5f3398bfe1335fa',
        'lock':ROOT/'docs/implementation/catala/toolchain-lock.json'})
    catala_verified=verify_candidate(catala,cases,JDK)
    monitor=Monitor(out/'monitor');control=[{'control_id':'str.resubmission','source':'circular','dependencies':['interpretation']}]
    versions={'circular':digest(load_case('26ec2')['packet']),'interpretation':digest(readings)}
    def callback(c,s):return {'status':'REASSESSED','source_binding':s,'release_eligible':False}
    ticks=[monitor.tick(control,versions,'typed-str.v1','str',0,callback),
           monitor.tick(control,versions,'typed-str.v1','str',1,callback),
           monitor.tick(control,{**versions,'circular':'0'*64},'typed-str.v1','str',2,callback)]
    if ticks[1]['results'][0]['status']!='UNCHANGED' or ticks[2]['results'][0]['status']!='COMPLETED':raise ValueError('Amendment did not reinvestigate')
    result={'status':'JAVA_SOURCE_EXAMPLE_CONFORMANCE','compiled_cases':len(comparisons),'builds':builds,
            'catala':catala,'catala_verification':catala_verified,'event_cases':event_cases,'authority_bound_duties':event_report,
            'amendment_ticks':ticks,'independent_comparisons':len(independent['comparisons']),
            'readings':readings,'eip_reading':ereading,'reference_basis':'Frozen authored source-explicit development cases',
            'expected_answers_sent_to_models':False,'independent_legal_reference':False,
            'original_STR_transfer_cases':transfer_references(out,cases,refs),
            'release_eligible':False}
    save(out/'result.json',result);return result
