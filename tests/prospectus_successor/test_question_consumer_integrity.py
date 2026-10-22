"""Real consumer checks with resealed, internally consistent phase hashes."""
from copy import deepcopy
import pytest
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import digest
from scripts.prospectus_closure_fixtures import request, PREFIX, LOSS


def products(tmp_path):
    req=request(tmp_path,[PREFIX+LOSS+' An unresolved contract sentence.'])
    req['scope']['Q1']['complete']=False
    p1=service.source_product(req,tmp_path)
    p2=service.construction_product(p1,tmp_path)
    p3=service.interpretation_product(p1,p2)
    return {'P1':p1,'P2':p2,'P3':p3,'P4':service.law_product(p1,p3),
            'P5':service.financial_product(p1,p2,p3)}


def reseal(p,payload):
    p=deepcopy(p)
    bundle=p['P1']['payload']['request']['bundle']
    p['P3']=service.seal('P3',bundle,p['P3']['inputs'],payload)
    for key in ('P4','P5'):
        p[key]=service.seal(key,bundle,{**p[key]['inputs'],'P3':p['P3']['sha256']},p[key]['payload'])
    return p


CASES=('drop-unknown','invent-unknown','duplicate-unknown','status','value','evidence',
       'quantifier','reasoning','premise-applicability','subquestion','drop-subquestion',
       'conversion-alternatives','statutory-disclosures','creditor-amendments',
       'q3-status','q3-value','q3-extra','parent-extra','scope-and-questions')


@pytest.mark.parametrize('case',CASES)
def test_resealed_question_forgery_refused(tmp_path,case):
    p=products(tmp_path)
    value=deepcopy(p['P3']['payload'])
    q=value['questions']; a=q['Q1']
    if case=='drop-unknown': a['unresolved'].pop()
    elif case=='invent-unknown': a['unresolved'].append('invented');a['unresolved'].sort()
    elif case=='duplicate-unknown': a['unresolved'].append(a['unresolved'][0]);a['unresolved'].sort()
    elif case=='status': a['status']='YES'
    elif case=='value': a['value']=True
    elif case=='evidence': a['evidence']=['invented']
    elif case=='quantifier': a['quantifier']='ALL_WORLD_EVENTS'
    elif case=='reasoning': a['reasoning']=[]
    elif case=='premise-applicability': a['premise_applicability']={'invented':True}
    elif case=='subquestion': q['Q2']['subquestions']['common_only']['unresolved'].pop()
    elif case=='drop-subquestion': q['Q2']['subquestions'].pop('possible_common')
    elif case=='conversion-alternatives': q['Q2']['conversion_alternatives']=[{'invented':True}]
    elif case=='statutory-disclosures': a['statutory_disclosures']=['invented']
    elif case=='creditor-amendments': a['creditor_amendments']=['invented']
    elif case=='q3-status': q['Q3']['status']='COMPLETE'
    elif case=='q3-value': q['Q3']['value']['Q1']['complete']=True
    elif case=='q3-extra': q['Q3']['approved']=True
    elif case=='parent-extra': a['approved']=True
    elif case=='scope-and-questions':
        value['scope']['Q1']['complete']=True
        a['unresolved'].remove('Question scope not complete: Q1')
    if case not in ('q3-status','q3-value'):
        q['Q3']['value']['Q1']['unresolved']=deepcopy(a['unresolved'])
    forged=reseal(p,value)
    assert digest(forged)!=digest(p)
    for key,product in forged.items(): service.verify(product,key)
    with pytest.raises(ValueError,match='Consumed (question results|question scope) differ'):
        service.consume(forged,tmp_path,mode='frozen')


@pytest.mark.parametrize('role',('OPERATIVE','UNKNOWN'))
def test_valid_unknown_and_complete_question_fields_preserved(tmp_path,role):
    req=request(tmp_path,[PREFIX+LOSS])
    req['assembly']['operations'][0]['role']=role
    p1=service.source_product(req,tmp_path);p2=service.construction_product(p1,tmp_path)
    p3=service.interpretation_product(p1,p2)
    p={'P1':p1,'P2':p2,'P3':p3,'P4':service.law_product(p1,p3),
       'P5':service.financial_product(p1,p2,p3)}
    observed=service.consume(p,tmp_path,mode='frozen')
    for q in ('Q1','Q2'):
        assert observed['questions'][q]==p3['payload']['questions'][q]
    assert observed['questions']['Q1']['status']==('YES' if role=='OPERATIVE' else 'UNKNOWN')
