#!/usr/bin/env python3
"""Matched RuleIR/Catala review materials; synthetic collection is never human evidence."""
from copy import deepcopy
from pathlib import Path
import json
import subprocess
import sys
import time
from legalmath.canonical import canonical,digest,loads,raw_digest
from legalmath.catala.native.runtime import build,verify_cases
from legalmath.interpretation.search.formal import RULE
from legalmath.java.manifest import build_candidate,verify_candidate
from scripts.catala_semantic_conformance import irbundle,ircase,candidate
from tests.catala.backend_support import JDK,TOOLCHAIN

ROOT=Path(__file__).resolve().parents[1]
STUDY='catala.review.matched.v5'
# Handwritten experimental controls, not model-generated conversion successes.
FORMULAS={
 'netassets':('assets - liabilities - residence','assets - liabilities',
             '(- (- assets liabilities) residence)','(- assets liabilities)',lambda v:str(int(v['assets'])-int(v['liabilities'])), 'residence deduction'),
 'gifts':('gift and not discount and (specific or producttype)','gift and not discount and specific',
          '(and gift (not discount) (or specific producttype))','(and gift (not discount) specific)',lambda v:v['gift'] and not v['discount'] and v['specific'], 'product-type route'),
 'network':('publicnetwork and not (controls and proper)','publicnetwork and not controls',
            '(and publicnetwork (not (and controls proper)))','(and publicnetwork (not controls))',lambda v:v['publicnetwork'] and not v['controls'],'proper-controls qualifier'),
 'consultation':('(newproduct and seeksauthorisation) or existingtokenisation or materialchange','newproduct and seeksauthorisation',
                 '(or (and newproduct seeksauthorisation) existingtokenisation materialchange)','(and newproduct seeksauthorisation)',lambda v:v['newproduct'] and v['seeksauthorisation'], 'existing-product and material-change routes')}


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical(value))


def materials(row,out):
    t=row['task'];name=t['task_id'].split('.')[-1];ns,nd,irs,ird,mutant,defect=FORMULAS[name];catalog={}
    for variant,source,expr in [('original',ns,irs),('mutated',nd,ird)]:
        d=out/name/variant;d.mkdir(parents=True)
        c=candidate(t,'  definition result equals '+source);b=irbundle(t,expr)
        cases=deepcopy(row['cases'])
        if variant=='mutated':
            for case in cases:
                v={k:x['value'] for k,x in case['snapshot']['facts'].items()}
                case['expected']['value']['result']=mutant(v)
        native=d/'catala';build(t,c,native,JDK,**TOOLCHAIN);nr=verify_cases(native,cases,JDK,compiler=TOOLCHAIN['compiler'])
        ic=[]
        for case in cases:
            v=case['expected']['value']['result'];expected={'status':('TRUE' if v else 'FALSE') if type(v)is bool else 'VALUE','value':v}
            ic.append(ircase(t,b,case['snapshot'],case['id'],expected))
        ib=build_candidate(b,d/'ruleir',JDK);iv=verify_candidate(ib,ic,JDK)
        write(d/'native-cases.json',cases);write(d/'native-verification.json',nr);write(d/'ruleir-cases.json',ic)
        write(d/'ruleir-verification.json',iv)
        changed=[a['id'] for a,z in zip(cases,row['cases']) if a['expected']!=z['expected']]
        assert bool(changed)==(variant=='mutated')
        for language in ('catala','ruleir'):
            program=c['source'] if language=='catala' else json.dumps({'facts':b['facts'],'rule':b['rules'][0]},ensure_ascii=False,indent=2)
            catalog[(language,variant)]={'program':program,'program_hash':raw_digest(program.encode()),'build_hash':nr['build_hash'] if language=='catala' else ib['manifest_hash'],
                                        'verification_hash':digest(nr if language=='catala' else iv),'defect':defect if changed else None,
                                        'changed_reference_cases':changed}
    return catalog


def seal_assignment(body):
    return {**body,'assignment_hash':digest(body)}


def validate_response(r,assignment,seen):
    required={'study_id','assignment_hash','reviewer_slot','item_id','position','has_defect','seconds','assistance','explanation','response_hash'}
    if set(r)!=required or r['study_id']!=STUDY or r['assignment_hash']!=assignment['assignment_hash'] or r['reviewer_slot']!=assignment['reviewer_slot']:
        raise ValueError('Wrong assignment')
    if assignment['assignment_hash']!=digest({k:v for k,v in assignment.items() if k!='assignment_hash'}):raise ValueError('Changed assignment')
    item=next((x for x in assignment['items'] if x['item_id']==r['item_id']),None)
    if item is None or item['position']!=r['position']:raise ValueError('Wrong task/order')
    if type(r['has_defect']) is not bool or type(r['seconds']) is not int or not 0<r['seconds']<=86400:raise ValueError('Invalid response/time')
    if r['assistance'] not in ('none','documentation','colleague','AI') or type(r['explanation'])is not str or not 1<=len(r['explanation'])<=10000:raise ValueError('Invalid assistance/explanation')
    if r['response_hash']!=digest({k:v for k,v in r.items() if k!='response_hash'}):raise ValueError('Changed response')
    key=(r['reviewer_slot'],r['item_id'])
    if key in seen:raise ValueError('Duplicate response')
    seen.add(key)
    return r


def analyze(responses,assignments,owner,registry,*,collection_kind):
    if collection_kind not in ('synthetic','human'):raise ValueError('Trusted collector must declare collection kind')
    seen=set();scored=[]
    for r in responses:
        a=assignments[r['reviewer_slot']];validate_response(r,a,seen)
        key=owner[r['item_id']]
        if collection_kind=='human':
            att=registry.get(r['reviewer_slot'],{})
            if not att.get('named_identity') or not att.get('independent_human') or att.get('assignment_hash')!=a['assignment_hash']:
                raise ValueError('No trusted independent human enrollment')
        scored.append({'reviewer_slot':r['reviewer_slot'],'item_id':r['item_id'],'language':key['language'],
                       'correct':r['has_defect']==key['has_defect'],'omission':key['has_defect'] and not r['has_defect'],
                       'false_alarm':not key['has_defect'] and r['has_defect'],'seconds':r['seconds'],'assistance':r['assistance']})
    return {'responses':len(scored),'synthetic_excluded':len(scored) if collection_kind=='synthetic' else 0,
            'human_responses':len(scored) if collection_kind=='human' else 0,
            'diagnostic_scoring':{'correct':sum(r['correct'] for r in scored),'omissions':sum(r['omission'] for r in scored),'false_alarms':sum(r['false_alarm'] for r in scored)},
            'collection_kind':collection_kind,'ranking':'UNSUPPORTED; convenience sources and no preregistered adequately powered human inference',
            'human_readability_evidence':'NONE' if collection_kind=='synthetic' else 'DESCRIPTIVE_ONLY',
            'scores':scored}


def main():
    began=time.monotonic();source=ROOT/'artifacts/catala/gap-closure/source-review/packet.json';packet=loads(source.read_bytes())
    base=ROOT/'artifacts/catala/gap-closure/reviewer-study';out=base/('matched-'+raw_digest(Path(__file__).read_bytes())[:12]);out.mkdir(parents=True,exist_ok=False)
    corpus=packet['corpus'];catalog=[materials(row,out/'owner-builds') for row in corpus]
    assignments={};key={};balance={};position_balance={}
    for i in range(8):
        slot='reviewer-slot-'+str(i+1);items=[]
        for pos in range(4):
            j=(i+pos)%4;row=corpus[j];language='catala' if (pos+i//4)%2 else 'ruleir';variant='mutated' if (i//2+j//2)%2 else 'original'
            control=catalog[j][(language,variant)]
            ident='item-'+digest({'slot':slot,'task':row['task']['task_id']})[:16]
            items.append({'item_id':ident,'position':pos,'source':row['task']['packet'],'question':row['task']['question'],
                          'inputs':row['task']['inputs'],'outputs':row['task']['outputs'],'program':control['program'],'program_hash':control['program_hash']})
            key[ident]={'reviewer_slot':slot,'task_id':row['task']['task_id'],'language':language,'has_defect':variant=='mutated',
                        **control}
            b=row['task']['task_id']+'/'+language+'/'+variant;balance[b]=balance.get(b,0)+1
            p=str(pos)+'/'+language;position_balance[p]=position_balance.get(p,0)+1
        a=seal_assignment({'study_id':STUDY,'reviewer_slot':slot,'items':items,
            'instructions':'Assess each program against the supplied question, interface and retained source. Report whether it has a defect, explain the issue and record time/assistance. Source references can require further legal review.'})
        assignments[slot]=a;write(out/'participants'/(slot+'.json'),a)
    assert set(balance.values())=={2}
    assert set(position_balance.values())=={4}
    responses=[]
    for a in assignments.values():
        for x in a['items']:
            expected=key[x['item_id']]['has_defect']
            body={'study_id':STUDY,'assignment_hash':a['assignment_hash'],'reviewer_slot':a['reviewer_slot'],
                  'item_id':x['item_id'],'position':x['position'],'has_defect':expected if x['position']%2 else not expected,
                  'seconds':10+x['position'],'assistance':'none','explanation':'Synthetic diagnostic; not a human judgment.'}
            responses.append({**body,'response_hash':digest(body)})
    report=analyze(responses,assignments,key,{},collection_kind='synthetic')
    # Diagnostics must reject unauthenticated human claims, duplicate records,
    # changed assignment hashes, negative time and altered answers.
    rejections=[]
    for label,alter in [('duplicate',responses+[responses[0]]),('time',deepcopy(responses)),('assignment',deepcopy(responses))]:
        if label=='time':alter[0]['seconds']=-1;alter[0]['response_hash']=digest({k:v for k,v in alter[0].items() if k!='response_hash'})
        if label=='assignment':alter[0]['assignment_hash']='0'*64
        try:analyze(alter,assignments,key,{},collection_kind='synthetic')
        except ValueError:rejections.append(label)
        else:raise AssertionError(label+' accepted')
    try:analyze(responses,assignments,key,{},collection_kind='human')
    except ValueError:rejections.append('unenrolled-human')
    else:raise AssertionError('Synthetic identity admitted as human')
    protocol={'study_id':STUDY,'source_packet_hash':digest(packet),'tasks':4,'families':3,'slots':8,'planned_responses':32,
        'materials_origin':'Handwritten matched executable controls, not outputs from the conversion experiment.',
        'design':'Each reviewer sees four different tasks once, two in each language; task order rotates. Each task/language/defect cell occurs twice across eight slots. Each position has four assignments in each language.',
        'blinding':'Defect status and owner key withheld; language syntax remains visible. Do not distribute owner-builds or owner-key.json.',
        'collection':'Separate participant files only. Real names, independent-reviewer eligibility and assignment hashes are attested by a trusted collector. These slots are unfilled.',
        'analysis':'Omissions and false alarms are scored from the private key, not self-reported accuracy. Descriptive within-reviewer differences require equal task allocation; no ranking or timing advantage without a prospectively powered study and uncertainty analysis.',
        'legal_status':'Source references pending independent adjudication; verify them before recruiting humans.',
        'balance':balance,'position_balance':position_balance,'rejection_checks':rejections,'default_ready':False}
    write(out/'owner-key.json',key);write(out/'synthetic-responses.json',responses);write(out/'analysis.json',report);write(out/'protocol.json',protocol)
    write(base/'current.json',{'run_directory':out.name,'protocol_hash':digest(protocol),'analysis_hash':digest(report),'human_responses':0})
    write(out/'run-manifest.json',{'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'command':sys.argv,
         'python':sys.executable,'jdk':str(JDK),'CPU_GPU':'CPU, no GPU imports','seed':'N/A deterministic Latin rotation',
         'wall_ms':int((time.monotonic()-began)*1000),'data_version':digest(packet),'plan':'docs/plans/catala-gap-closure.md',
         'script_sha256':raw_digest(Path(__file__).read_bytes()),'result':'analysis.json','result_hash':digest(report)})
    print('Matched controls pass; 32 synthetic responses excluded; rejection checks:',rejections)

if __name__=='__main__':main()
