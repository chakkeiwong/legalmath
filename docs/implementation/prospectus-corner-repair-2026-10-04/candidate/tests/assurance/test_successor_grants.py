from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import pytest
from legalmath.canonical import canonical, raw_digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.grants import GrantedAllowance


def grant(tmp_path, maximum=2):
    prior=tmp_path/'prior.json';prior.write_bytes(canonical({'maximum':1,'calls':[
        {'request_hash':'a'*64,'issued_at_ns':'1'}]}))
    p=tmp_path/'grant.json';p.write_text(json.dumps({'schema':'legalmath.additional-grant.v1',
        'grant_id':'test.explicit','authorized_calls':maximum,'authorization':'Explicit test allowance',
        'predecessor':{'path':'prior.json','sha256':raw_digest(prior.read_bytes())},'ledger':'new.json'}))
    return GrantedAllowance(p),prior


def test_additional_grant_never_rewrites_prior_or_refunds(tmp_path):
    allowance,old=grant(tmp_path);before=old.read_bytes()
    assert allowance.reserve('b'*64)==1
    assert allowance.reserve('b'*64)==2
    with pytest.raises(LegalMathError):allowance.reserve('c'*64)
    assert old.read_bytes()==before
    assert GrantedAllowance(allowance.grant_path).verify()['used']==2


def test_concurrent_last_reservation_is_not_overspent(tmp_path):
    allowance,_=grant(tmp_path,1)
    def reserve(_):
        try:return allowance.reserve('b'*64)
        except LegalMathError as e:return e.code
    with ThreadPoolExecutor(max_workers=4) as pool:values=list(pool.map(reserve,range(8)))
    assert values.count(1)==1 and values.count('E_RESOURCE_LIMIT')==7


@pytest.mark.parametrize('target',['prior','grant','ledger'])
def test_changed_authorization_or_history_rejected(tmp_path,target):
    allowance,old=grant(tmp_path);allowance.reserve('b'*64)
    p={'prior':old,'grant':allowance.grant_path,'ledger':allowance.path}[target]
    v=json.loads(p.read_text())
    if target=='prior':v['calls'][0]['request_hash']='c'*64
    elif target=='grant':v['authorized_calls']=3
    else:v['calls'][0]['request_hash']='not a hash'
    p.write_text(json.dumps(v))
    with pytest.raises(LegalMathError):allowance.reserve('b'*64)


def test_scoped_live_requires_grant_before_provider_dispatch(tmp_path):
    from legalmath.interpretation.assurance.scoped_investigation import investigate
    class Untrusted:
        live=True
        def complete(self,*a):raise AssertionError('must not dispatch')
    with pytest.raises(LegalMathError) as caught:
        investigate({},[],{},{},Untrusted(),tmp_path/'scope')
    assert caught.value.code=='E_AUTHORITY'


def test_parallel_arm_ceilings_share_one_global_grant(tmp_path):
    from legalmath.interpretation.assurance.grants import GrantSlice
    allowance,_=grant(tmp_path,3)
    a=GrantSlice(allowance.grant_path,tmp_path/'a.json',2)
    b=GrantSlice(allowance.grant_path,tmp_path/'b.json',2)
    assert a.reserve('a'*64)==1 and b.reserve('b'*64)==2 and a.reserve('c'*64)==3
    with pytest.raises(LegalMathError):a.reserve('d'*64)
    with pytest.raises(LegalMathError):b.reserve('e'*64)
    assert allowance.verify()['used']==3
    assert len(json.loads(b.slice_path.read_text())['reservations'])==2
    with pytest.raises(LegalMathError):GrantSlice(allowance.grant_path,tmp_path/'a.json',3).reserve('f'*64)


@pytest.mark.parametrize('maximum',[1,4])
def test_granted_scoped_route_reserves_before_dispatch_and_resumes(tmp_path,maximum):
    from copy import deepcopy
    from .test_round16 import scoped_fixture
    from legalmath.canonical import digest
    from legalmath.interpretation.search.providers import CodexProvider, Completion
    from legalmath.interpretation.assurance.scoped_investigation import investigate
    allowance,old=grant(tmp_path,maximum);before=old.read_bytes()
    p,c,r,q,answer=scoped_fixture()
    class Counted(CodexProvider):
        provider_id='counted.local.transport.fixture'
        def __init__(self):self.allowance=allowance;self.routing={'fixture':True};self.calls=0
        def complete(self,request,schema,settings):
            slot=self.allowance.reserve(digest(request));self.calls+=1
            return Completion(deepcopy(answer),{'allowance_slot':slot,'request_hash':digest(request),
                                               'synthetic_transport':True})
    provider=Counted();directory=tmp_path/'scoped'
    result=investigate(p,c,r,q,provider,directory,maximum_rounds=1)
    issued=provider.calls
    resumed=investigate(p,c,r,q,provider,directory,maximum_rounds=1)
    assert provider.calls==issued and old.read_bytes()==before
    assert allowance.verify()['used']==issued
    assert not result['release_eligible'] and not resumed['release_eligible']
    if maximum==1:assert result['status']=='DISPATCH_BLOCKED' and result['pending_pairs']
    else:assert issued==2 and result['pairs_with_two_validated_proposals']==1
