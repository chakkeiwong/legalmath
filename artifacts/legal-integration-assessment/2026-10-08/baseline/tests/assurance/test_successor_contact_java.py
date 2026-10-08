from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.java import contact_boundary
from legalmath.interpretation.search.formal import bundle
from .test_successor_duties import fixture
from .support import reading


def inputs():
    p,policy,c,cover,kw=fixture()
    def r(names,result):
        value=reading();value['citations']=policy['source_evidence']
        value['formalization']={'facts':[{'name':n,'type':'bool','meaning':n,'unit':'truth value',
            'source_unit_ids':['p1'],'requires_judgment':True} for n in names],'scope':'true','result':result,'result_type':'bool'}
        return value
    trigger=bundle(r(['licensed','urgent','in_window'],'(and licensed urgent in_window)'),p,policy['from_inclusive'])
    performance=bundle(r(['contact_observed'],'contact_observed'),p,policy['from_inclusive'])
    request={'profile':contact_boundary.PROFILE,**kw,'licensed':'TRUE','urgent':'TRUE','contacts':[c],'coverage':[cover]}
    return trigger,performance,policy,request


@pytest.fixture(scope='module')
def built(tmp_path_factory):
    root=Path(__file__).resolve().parents[2]
    t,p,policy,request=inputs();jdk=root/'.localresources/java-toolchain/jdk-17.0.20.1+1'
    return contact_boundary.build(t,p,policy,tmp_path_factory.mktemp('contact-host'),jdk),jdk,request


def test_real_java_ingests_histories_and_distinguishes_performance(built):
    build,jdk,base=built;requests=[]
    for label in ('observed','none','unknown','other_actor','other_report','other_recipient','other_channel','late','known_late','disputed','partial_history'):
        r=deepcopy(base)
        if label=='none':r['contacts']=[]
        elif label=='unknown':r['contacts']=[];r['coverage']=[]
        elif label=='other_actor':r['contacts'][0]['actor_id']='firm.b'
        elif label=='other_report':r['contacts'][0]['event']['str_id']='str.b'
        elif label=='other_recipient':r['contacts'][0]['counterparty_id']='other'
        elif label=='other_channel':r['contacts'][0]['channel']='OTHER'
        elif label=='late':r['contacts'][0]['event'].update(occurred_at='2026-01-29T05:00:00.000000Z',recorded_at='2026-01-29T05:00:00.000000Z')
        elif label=='known_late':r['contacts'][0]['event']['recorded_at']='2026-01-29T05:00:00.000000Z'
        elif label=='disputed':r['contacts'][0]['event']['status']='DISPUTED'
        elif label=='partial_history':r['contacts']=[];r['coverage'][0]['channels']=['EMAIL']
        requests.append(r)
    results=contact_boundary.run(build,requests,jdk)
    assert [r['projected_status'] for r in results]==['TRUE','FALSE','UNKNOWN','FALSE','FALSE','FALSE','FALSE','FALSE','FALSE','CONFLICT','UNKNOWN']
    assert all(r['trigger']['status']=='TRUE' and not r['deadline_violation_established'] for r in results)


@pytest.mark.parametrize('kind',['policy_override','actor_collision','malformed_date','channel','extra','untyped','empty_evidence'])
def test_host_rejects_malformed_or_bypassed_history(built,kind):
    build,jdk,base=built;r=deepcopy(base)
    if kind=='policy_override':r['policy']={}
    elif kind=='actor_collision':other=deepcopy(r['contacts'][0]);other['actor_id']='firm.b';r['contacts'].append(other)
    elif kind=='malformed_date':r['contacts'][0]['event']['recorded_at']='yesterday'
    elif kind=='channel':r['contacts'][0]['channel']='TELEPATHY'
    elif kind=='extra':r['contacts'][0]['event']['approved']=True
    elif kind=='untyped':r['licensed']=True
    else:r['contacts'][0]['event']['evidence_ids']=[]
    assert contact_boundary.run(build,[r],jdk)[0]['boundary_status']=='REJECTED'
