from copy import deepcopy
import pytest

from legalmath.prospectus.successor import explanations, service
from scripts.prospectus_explanation_oracle import check, check_row
from test_calendar_facts import world as calendar_world, NOW, LATER
from test_ratio_facts import world as ratio_world


@pytest.mark.parametrize('expression,observations,expected', [
    ({'any':['a',{'all':['b','c']}]},{'a':True,'b':True,'c':True},{'b':True,'c':True}),
    ({'all':['a','b']},{'a':False,'b':False},{'b':False}),
    ({'any':['a',{'not':'a'}]},{'a':True},{}),
    ({'all':['a',{'not':'a'}]},{'a':False},{}),
    (True,{},{}),(False,{},{}),
    ({'any':['a','b']},{'a':True,'b':None},{'a':True}),
])
def test_subset_minimal_is_not_smallest(expression,observations,expected):
    result=explanations.explain(expression,observations)
    assert result['literals']==expected
    assert check(expression,observations,result)['status']=='VERIFIED'


@pytest.mark.parametrize('observations,engine,active,reason',[
    ({'a':None},'finite',True,'UNKNOWN'),
    ({'a':'conflict'},'finite',True,'CONFLICT'),
    ({'a':True},'z3',True,'UNSUPPORTED_ENGINE'),
    ({'a':True},'finite',False,'INACTIVE_AUTHORITY'),
])
def test_typed_nonexplanation(observations,engine,active,reason):
    r=explanations.explain('a',observations,engine=engine,authority_active=active)
    assert r['reason']==reason
    assert check('a',observations,r,engine=engine,active=active)['status']=='NOT_AVAILABLE'


def test_limits_and_relevant_conflict():
    for size in (12,13):
        e={'all':['f'+str(i) for i in range(size)]};o={n:True for n in e['all']}
        r=explanations.explain(e,o)
        assert check(e,o,r)['status']==('VERIFIED' if size==12 else 'NOT_AVAILABLE')
    e={'any':['a',{'not':'a'}]}
    assert explanations.explain(e,{'a':'conflict'})['reason']=='CONFLICT'
    assert explanations.explain('a',{'a':True,'irrelevant':'conflict'})['literals']=={'a':True}
    deep='a'
    for _ in range(25): deep={'not':deep}
    with pytest.raises(ValueError,match='resource limit'): explanations.explain(deep,{})
    wide={'all':[{'all':['a']*128}]*128}
    with pytest.raises(ValueError,match='resource limit'): explanations.explain(wide,{})


@pytest.mark.parametrize('attack',['insufficient','nonminimal','missing_witness','wrong_witness',
    'invented','wrong_status','wrong_identity','extra'])
def test_independent_checker_rejects_forgery(attack):
    e={'any':['a',{'all':['b','c']}]};o={'a':True,'b':True,'c':True}
    r=explanations.explain(e,o)
    if attack=='insufficient': r['literals'].pop('b');r['deletion_counterexamples'].pop('b')
    if attack=='nonminimal': r['literals']['a']=True;r['deletion_counterexamples']['a']={'a':False,'b':False,'c':False}
    if attack=='missing_witness': r['deletion_counterexamples'].pop('b')
    if attack=='wrong_witness': r['deletion_counterexamples']['b']={'a':True,'b':True,'c':True}
    if attack=='invented': r['literals']['b']=False
    if attack=='wrong_status': r['conclusion']='NO'
    if attack=='wrong_identity': r['expression_sha256']='0'*64
    if attack=='extra': r['verified_legal_truth']=True
    with pytest.raises(ValueError): check(e,o,r)


@pytest.mark.parametrize('route',['request','overlay'])
@pytest.mark.parametrize('kind',['calendar','ratio','boolean','unknown','conflict','inactive'])
@pytest.mark.parametrize('mode',['current','frozen'])
def test_actual_consumer(tmp_path,route,kind,mode):
    ps,data,_=ratio_world(tmp_path) if kind=='ratio' else calendar_world(tmp_path)
    if kind in {'boolean','unknown','conflict'}:
        c=data.pop('calendar_facts')[0]
        fact={k:c[k] for k in ('name','basis_id','instrument_id','jurisdiction','source','valid_from','known_from','observed_at')}
        data['facts']=[] if kind=='unknown' else [{**fact,'value':True}]
        if kind=='conflict':data['facts'].append({**fact,'value':False})
    if kind=='inactive':data['law_bases'][0]['known_from']=LATER
    data['law_explanation']='subset-minimal.v1'
    if route=='request':
        request={**ps['P1']['payload']['request'],**data}
        p1=service.source_product(request,tmp_path);p2=service.construction_product(p1,tmp_path)
        p3=service.interpretation_product(p1,p2)
        ps={'P1':p1,'P2':p2,'P3':p3,'P5':service.financial_product(p1,p2,p3)}
        p4=service.law_product(p1,p3)
    else:p4=service.law_product(ps['P1'],ps['P3'],law_input=data)
    answer=service.consume({**ps,'P4':p4},tmp_path,mode=mode)
    row=answer['questions']['Q4']['value'][0]
    checked=check_row(row,data,ps['P1']['payload']['request']['bundle'],ps['P1']['payload']['graph'])
    assert checked['status']==('NOT_AVAILABLE' if kind in {'unknown','conflict','inactive'} else 'VERIFIED')
    assert answer['mode']=='ASSISTED' and not answer['may_execute_transaction']
    assert answer['questions']['Q4']==p4['payload']['question']


@pytest.mark.parametrize('option',[None,False,True,0,1,{},[],'','minimum-cardinality.v1'])
@pytest.mark.parametrize('route',['request','overlay'])
def test_malformed_option_refused(tmp_path,option,route):
    ps,data,_=calendar_world(tmp_path);data['law_explanation']=option
    with pytest.raises(ValueError,match='Unsupported law explanation'):
        if route=='request': service.source_product({**ps['P1']['payload']['request'],**data},tmp_path)
        else: service.law_product(ps['P1'],ps['P3'],law_input=data)


def test_inactive_duplicate_source_and_current_forgery(tmp_path):
    ps,data,_=calendar_world(tmp_path)
    c=data.pop('calendar_facts')[0]
    f={k:c[k] for k in ('name','basis_id','instrument_id','jurisdiction','source','valid_from','known_from','observed_at')}
    data['facts']=[{**f,'value':True},{**f,'value':False,'observed_at':LATER}]
    data['law_explanation']='subset-minimal.v1'
    p4=service.law_product(ps['P1'],ps['P3'],law_input=data)
    row=p4['payload']['question']['value'][0]
    assert len(row['explanation']['premise_support']['timely'])==1
    check_row(row,data,ps['P1']['payload']['request']['bundle'],ps['P1']['payload']['graph'])
    bad=deepcopy(p4)
    bad['payload']['question']['value'][0]['explanation']['premise_support']['timely'][0]['source']['quote']='forged'
    bad['sha256']=service.digest({k:v for k,v in bad.items() if k!='sha256'})
    with pytest.raises(ValueError,match='differs; reassessment'):service.consume({**ps,'P4':bad},tmp_path,mode='current')
    with pytest.raises(ValueError,match='premise sources'):
        check_row(bad['payload']['question']['value'][0],data,ps['P1']['payload']['request']['bundle'],ps['P1']['payload']['graph'])
