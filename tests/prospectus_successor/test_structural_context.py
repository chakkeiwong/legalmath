from copy import deepcopy

import pytest
from legalmath.prospectus.successor import structural_roles as roles
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor, target
from legalmath.prospectus.successor.reviewed_references import admit, verify_consumed


def fixture(monkeypatch,body='OPERATIVE',heading_only=False):
    raw=[{'id':k,'document':'finite-example','source_sha256':'a'*64,'raw':v,
          'language':'en','visible':True,'page':1} for k,v in
         [('s','See payment terms.'),('h','PAYMENTS'),('b','Pay principal on maturity.'),('x','OTHER HEADING')]]
    g={'units':raw,'references':[]}
    old={'units':[{'unit':u['id'],'text':u['raw'],'role':r,'questions':['Q1','Q2']}
                  for u,r in zip(raw,['OPERATIVE','UNKNOWN',body,'HEADER'])],
         'unresolved':['h']+(['b'] if body=='UNKNOWN' else [])}
    source=anchor(raw[0]);targets=[{'source':anchor(u),'use':u['id'],'language':'en'} for u in raw[1:3]]
    row={'id':'link','form':'relative','source':source,'from_use':'s','language':'en',
         'targets':targets[:1] if heading_only else targets,'authority':source,
         'questions':['Q1','Q2'],'reason':'Exact reviewed context and substantive target','discovery_ids':[]}
    a=deepcopy(old);a['units'][1].update(role='HEADER',reason='Source-reviewed title');a['unresolved']=[u for u in old['unresolved'] if u!='h']
    spec={'profile':'finite-structural.v1','graph_sha256':digest(g),'baseline_assembly_sha256':digest(old),
          'migrated_body_sha256':digest(a),'decisions':[{'unit':'h','before':deepcopy(old['units'][1]),'reason':'Source-reviewed title'}],
          'affected_references':[deepcopy(row)]}
    monkeypatch.setattr(roles,'specification',lambda:deepcopy(spec))
    a['structural_role_review']=roles.packet();monkeypatch.setattr(roles,'ASSEMBLY_SHA256',digest(a))
    packet={'version':'reviewed-references.v4','assembly_sha256':digest(a),'structural_role_review':roles.packet(),
            'review':{'reviewer':'test','kind':'DEVELOPMENT','reason':'Finite exact source review'},'references':[row]}
    return g,old,a,packet


@pytest.mark.parametrize('body',['OPERATIVE','UNKNOWN'])
def test_exact_context_is_retained_without_becoming_operative(monkeypatch,body):
    g,old,a,p=fixture(monkeypatch,body)
    assert roles.apply(g,old,roles.packet())==a
    assert roles.legacy_view(g,a)==old
    deps,edges=admit(g,a,p)
    assert [t['unit'] for t in deps[0]['structural_targets']]==['h']
    assert [t['unit'] for t in deps[0]['targets']]==['b']
    assert [e['to'] for e in edges]==['b']
    assert deps[0]['status']==('UNRESOLVED' if body=='UNKNOWN' else 'RESOLVED')
    with pytest.raises(ValueError):target(g,a,{'source':p['references'][0]['targets'][0]['source'],'use':'h'})


@pytest.mark.parametrize('mutation',['duplicate','omit-body','omit-heading','arbitrary-header','wrong-source','wrong-profile','renamed'])
def test_invalid_context_contract_refused(monkeypatch,mutation):
    g,old,a,p=fixture(monkeypatch);row=p['references'][0]
    if mutation=='duplicate':row['targets'].append(deepcopy(row['targets'][1]))
    elif mutation=='omit-body':row['targets'].pop()
    elif mutation=='omit-heading':row['targets'].pop(0)
    elif mutation=='arbitrary-header':row['targets'][0]={'source':anchor(g['units'][3]),'use':'x','language':'en'}
    elif mutation=='wrong-source':row['targets'][0]['source']['quote']='ALTERED'
    elif mutation=='wrong-profile':p['structural_role_review']['profile_sha256']='0'*64
    else:row['id']='unregistered'
    with pytest.raises(ValueError):admit(g,a,p)


def test_heading_only_registered_reference_still_refused(monkeypatch):
    g,old,a,p=fixture(monkeypatch,heading_only=True)
    with pytest.raises(ValueError,match='substantive target'):admit(g,a,p)


@pytest.mark.parametrize('mutation',['text','role','extra-header','unresolved','graph','marker','missing-request'])
def test_complete_assembly_identity_cannot_be_resealed(monkeypatch,mutation):
    g,old,a,p=fixture(monkeypatch);request=roles.packet()
    if mutation=='text':a['units'][2]['text']='No payment.'
    elif mutation=='role':a['units'][2]['role']='HEADER'
    elif mutation=='extra-header':a['units'][0]['role']='HEADER'
    elif mutation=='unresolved':a['unresolved']=['invented']
    elif mutation=='graph':g['units'][2]['raw']='No payment.'
    elif mutation=='marker':a['structural_role_review']['profile']='changed'
    else:request=None
    with pytest.raises(ValueError):roles.verify(g,a,request)


def test_consumed_context_must_be_preserved(monkeypatch):
    g,old,a,p=fixture(monkeypatch);deps,_=admit(g,a,p)
    semantic={'dependencies':deps,'questions':{q:{'unresolved':[]} for q in ('Q1','Q2')}}
    verify_consumed(g,a,{'reference_admission':p},semantic)
    deps[0]['structural_targets']=[]
    with pytest.raises(ValueError,match='differ'):verify_consumed(g,a,{'reference_admission':p},semantic)
