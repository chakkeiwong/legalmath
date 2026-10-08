from copy import deepcopy
import pytest
from legalmath.errors import LegalMathError
from legalmath.translation.policy import prepare
from legalmath.translation.native_compat import snapshot as native_snapshot
from .support import AT,model,snapshot,rich_model
from legalmath.catala.native.boundary import make_snapshot
from legalmath.translation.catala import lower


@pytest.mark.parametrize('problem,reason',[
    ('missing','INCOMPLETE_INPUTS'),('conflict','CONFLICTING_INPUTS'),('stale','INCOMPLETE_INPUTS'),
    ('future','INCOMPLETE_INPUTS'),('incomplete','INCOMPLETE_INPUTS'),('bound','OUTSIDE_DECLARED_DOMAIN'),
    ('time','SOURCE_VERSION_TIME')])
def test_complete_policy(problem,reason):
    m=model();m['profile']='complete.v1';s=snapshot(m,{'months':'6'});f=s['facts']['months'];at=AT
    if problem=='missing':s['facts']['months']={'type':'integer','status':'unknown','reason':'MISSING'}
    if problem=='conflict':s['facts']['months']={'type':'integer','status':'conflict','evidence_ids':[]}
    if problem=='stale':f.update(valid_from='2020-01-01T00:00:00.000000Z',valid_until=AT)
    if problem=='future':f['recorded_at']='2027-01-01T00:00:00.000000Z'
    if problem=='incomplete':f['complete']=False
    if problem=='time':at='2020-01-01T00:00:00.000000Z'
    if problem=='bound':m['bounds']=[{'input':'months','minimum':None,'maximum':'5','unit_id':'p1','quote':'six months'}]
    assert prepare(m,s,at,AT)['reason']==reason


def test_rich_evidence_is_per_field_and_preserved():
    m=rich_model();s=snapshot(m,{'entries':[{'amount':{'numerator':'1','denominator':'3'},'active':True}],
                             'rate':None,'choice':{'case':'Empty','value':None}})
    assert prepare(m,s,AT,AT)['evidence']==s['evidence']
    del s['evidence']['/entries/0/amount']
    with pytest.raises(LegalMathError):prepare(m,s,AT,AT)


def test_native_adapter_rejects_missing_field_evidence():
    m=rich_model();native=lower(m)['task']
    # Restore original fact names for the compatibility input format.
    for original,f in zip(m['facts'],native['inputs']):f['name']=original['name']
    s=make_snapshot(native,{'entries':[{'amount':{'numerator':'1','denominator':'3'},'active':True}],
                            'rate':None,'choice':{'case':'Empty','value':None}})
    adapted=native_snapshot(s,m)
    assert adapted['evidence']==s['evidence']
    del s['evidence']['/entries/0/amount']
    with pytest.raises(LegalMathError):native_snapshot(s,m)
