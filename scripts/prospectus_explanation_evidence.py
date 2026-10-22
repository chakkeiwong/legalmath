"""Bounded full-answer evidence for original and calendar source cases."""
from copy import deepcopy
from itertools import product
from legalmath.prospectus.successor import explanations, service
from scripts.prospectus_calendar_evidence import load, save, require
from scripts.prospectus_explanation_oracle import check, check_row

REL='docs/implementation/prospectus-execution-authority'
ORIGINAL=REL+'/attempts/law-applicability/attempt-006'
CALENDAR=REL+'/attempts/law-applicability/attempt-008'
CORRECTED=REL+'/attempts/law-applicability/attempt-009'


def corpus(root,attempt):
    expressions=[True,False,'a',{'not':'a'},
        {'all':['a','b','c','d']},{'any':['a','b','c','d']},
        {'any':['a',{'all':['b','c']}]},
        {'all':['a',{'any':['b','c']}]},
        {'any':[{'all':['a','b']},{'all':['c','d']}]},
        {'all':[{'any':['a','b']},{'any':['c','d']}]},
        {'any':['a',{'not':'a'}]},{'all':['a',{'not':'a'}]},
        {'not':{'all':['a','b','c','d']}},
        {'any':[{'all':['a',{'not':'b'}]},{'all':[{'not':'a'},'b']}]},
        {'all':[{'any':['a','b']},{'any':[{'not':'a'},'c']},'d']},
        {'any':[{'all':['a','b']},{'all':['a','c']},{'all':['a','d']}]}]
    cases=[];counts={}
    for i,e in enumerate(expressions):
        for values in product((False,True,None,'conflict'),repeat=4):
            observations=dict(zip(('a','b','c','d'),values))
            result=explanations.explain(e,observations)
            verified=check(e,observations,result)
            key=verified.get('reason',verified['status'])
            counts[key]=counts.get(key,0)+1
            cases.append({'expression':i,'observations':observations,'explanation':result,'verification':verified})
    require(len(cases)==4096,'Wrong exhaustive corpus denominator')
    save(attempt/'corpus.json.gz',{'expressions':expressions,'cases':cases})
    return {'cases':len(cases),'expressions':len(expressions),'statuses':counts,'independent_bitset':True}


def projected(p4,answer,baseline_p4,baseline_answer):
    p=deepcopy(p4);a=deepcopy(answer)
    for row in p['payload']['question'].get('value') or []:row.pop('explanation')
    p['payload']['law_input'].pop('law_explanation')
    p['sha256']=service.digest({k:v for k,v in p.items() if k!='sha256'})
    require(p==baseline_p4,'P4 differs beyond optional explanation')
    for row in a['questions']['Q4'].get('value') or []:row.pop('explanation')
    a['consumed_products']['P4']=p['sha256']
    a['report_sha256']=service.digest({k:v for k,v in a.items() if k!='report_sha256'})
    require(a==baseline_answer,'Whole answer differs beyond optional explanation and exact P4/report digests')


def consumers(root,attempt,cohort):
    require(cohort in {'calendar','original'},'Wrong cohort')
    base=CALENDAR if cohort=='calendar' else ORIGINAL
    ps=load(root/base/'common-products.json.gz')
    selected=load(root/base/('calendar-evidence.json' if cohort=='calendar' else 'cases-result.json'))['cases']
    cases=None if cohort=='calendar' else load(root/ORIGINAL/'favorable-deposit-P4.json.gz')['payload']['cases']
    records=[];refused=0;verified=0;unavailable=0
    for item in selected:
        name=item['case']
        data=(load(root/base/'cases'/(name+'.json.gz'))['input'] if cohort=='calendar' else
              load(root/base/(name+'-input.json.gz')))
        if item.get('status')=='REJECTED':
            for optional in (False,True):
                try:service.law_product(ps['P1'],ps['P3'],cases=cases,law_input={**data,**({'law_explanation':'subset-minimal.v1'} if optional else {})})
                except ValueError as error:require(str(error)==item['reason'],'Original refusal reason changed')
                else:raise ValueError('Original adverse case accepted')
            refused+=1;records.append({'case':name,'original_refusal_preserved':True});continue
        baseline=load(root/CORRECTED/cohort/(name+'.json.gz'))
        old_p4=service.law_product(ps['P1'],ps['P3'],cases=cases,law_input=data)
        old_answer=service.consume({**ps,'P4':old_p4},root,mode='current')
        require(old_p4==baseline['P4'] and old_answer==baseline['answer'],'Legacy full answer changed')
        enabled={**data,'law_explanation':'subset-minimal.v1'}
        p4=service.law_product(ps['P1'],ps['P3'],cases=cases,law_input=enabled)
        proof=[check_row(row,enabled,ps['P1']['payload']['request']['bundle'],ps['P1']['payload']['graph'])
               for row in p4['payload']['question']['value']]
        verified+=sum(p['status']=='VERIFIED' for p in proof)
        unavailable+=sum(p['status']=='NOT_AVAILABLE' for p in proof)
        answers={}
        for mode in ('current','frozen'):
            answer=service.consume({**ps,'P4':p4},root,mode=mode)
            original=deepcopy(old_answer);original['assessment_mode']=mode
            original['report_sha256']=service.digest({k:v for k,v in original.items() if k!='report_sha256'})
            require(answer['questions']['Q4']==p4['payload']['question'],'Explanation lost by consumer')
            projected(p4,answer,old_p4,original)
            answers[mode]=answer
        save(attempt/cohort/(name+'.json.gz'),{'input':enabled,'P4':p4,'answers':answers,'verification':proof})
        records.append({'case':name,'legacy_equal':True,'current_and_frozen_projection_equal':True,'verification':proof})
    require(len(records)==(19 if cohort=='calendar' else 23),'Incomplete source cohort')
    require(refused==(0 if cohort=='calendar' else 2),'Wrong refusal denominator')
    save(attempt/(cohort+'-evidence.json'),records)
    return {'cases':len(records),'legacy_full_answers':len(records)-refused,'original_refusals':refused,
            'current_and_frozen_answers':2*(len(records)-refused),'explained_bases':verified,'unavailable_bases':unavailable}
