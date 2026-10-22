"""Question-level issue conservation and exact occurrence identity."""
from copy import deepcopy
import pytest
from legalmath.prospectus.successor import definition_dependencies as module
from legalmath.prospectus.successor.contracts import digest

def fixture():
    intervals=[{'start':0,'end':4,'quote':'Call'}, {'start':0,'end':9,'quote':'Call date'}]
    source={'records':[{'id':'U04-call','uses':[{'interval':0},{'interval':1}]}],'intervals':intervals}
    review={'uses':[{'record':'U04-call','origin':'ORIGINAL','interval':i,**v,
        'disposition':'TABLE_COLUMN','remaining':['SCOPE_OPEN','FACT_OPEN'] if i==0 else ['SCOPE_OPEN']}
        for i,v in enumerate(intervals)]}
    record={'id':'U04-call','original_record_sha256':digest(source['records'][0]),
        'use_indices':[0,1],'original_uses':2,'supplemental_uses':0}
    return record,review,source

def questions():
    q={'status':'UNKNOWN','value':None,'witnesses':['retained-witness'],'reasoning':['retained-reason'],
        'unresolved':['other:before','definition-source:U04-call','other:after']}
    result={'Q1':deepcopy(q),'Q2':deepcopy(q),'Q3':{'status':'PARTIAL','value':7}}
    result['Q2']['subquestions']={k:deepcopy(q) for k in ('compulsory_common','possible_common','common_only')}
    return result

def test_shared_start_keeps_both_ends_and_every_reason():
    args=fixture();before=deepcopy(args);r=module._record(*args)
    assert args==before
    assert [u['end'] for u in r['occurrences']]==[4,9]
    assert [(i['reason'],i['use_indices']) for i in r['remaining_premises']]==[('FACT_OPEN',[0]),('SCOPE_OPEN',[0,1])]

def test_projection_reaches_every_question_without_changing_answers():
    r=module._record(*fixture());old=questions();before=deepcopy(old)
    new,links=module._question_projection(old,[r]);assert old==before
    for path in module.PATHS:
        a,b=old,new
        for key in path:a,b=a[key],b[key]
        assert b['unresolved']==['other:before','definition-premise:U04-call:0',
            'definition-premise:U04-call:1','other:after',module.DISCOVERY]
        assert {k:v for k,v in a.items() if k not in ('unresolved','subquestions')}=={k:v for k,v in b.items() if k not in ('unresolved','subquestions')}
    assert len(links)==5 and new['Q3']==old['Q3']

@pytest.mark.parametrize('kind',['missing','duplicate','wrong-end','wrong-interval','wrong-record',
    'unreviewed','empty-reason','wrong-source','wrong-origin','wrong-count'])
def test_occurrence_corruption_refused(kind):
    r,v,s=fixture()
    if kind=='missing':r['use_indices']=[0]
    elif kind=='duplicate':r['use_indices']=[0,0]
    elif kind=='wrong-end':v['uses'][1]['end']=4
    elif kind=='wrong-interval':v['uses'][1]['interval']=0
    elif kind=='wrong-record':v['uses'][0]['record']='other'
    elif kind=='unreviewed':v['uses'][0]['disposition']='UNRECONCILED'
    elif kind=='empty-reason':v['uses'][0]['remaining']=['']
    elif kind=='wrong-source':r['original_record_sha256']='0'*64
    elif kind=='wrong-origin':v['uses'][0]['origin']='invented'
    else:r['original_uses']=3
    with pytest.raises(ValueError):module._record(r,v,s)

@pytest.mark.parametrize('kind',['missing','duplicate','unknown','existing-new','false-status','false-value'])
def test_false_question_projection_refused(kind):
    r=module._record(*fixture());q=questions();target=q['Q2']['subquestions']['common_only']
    if kind=='missing':target['unresolved'].remove('definition-source:U04-call')
    elif kind=='duplicate':target['unresolved'].append('definition-source:U04-call')
    elif kind=='unknown':target['unresolved'].append('definition-source:unknown')
    elif kind=='existing-new':target['unresolved'].append(module.DISCOVERY)
    elif kind=='false-status':target['status']='YES'
    else:target['value']=True
    with pytest.raises(ValueError):module._question_projection(q,[r])
