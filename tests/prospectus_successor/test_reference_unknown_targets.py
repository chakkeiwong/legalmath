from copy import deepcopy

import pytest
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor.occurrences import anchor
from legalmath.prospectus.successor.reviewed_references import admit, verify_consumed


def fixture(version='reviewed-references.v3',role='UNKNOWN'):
    raw=[{'id':'source','document':'example','source_sha256':'a'*64,'raw':'see clause B',
          'language':'en','visible':True,'page':1},
         {'id':'target','document':'example','source_sha256':'a'*64,'raw':'ambiguous condition',
          'language':'en','visible':True,'page':2}]
    graph={'units':raw,'references':[]}
    assembly={'units':[{'unit':u['id'],'text':u['raw'],'role':'OPERATIVE' if i==0 else role,
                       'questions':['Q1','Q2']} for i,u in enumerate(raw)]}
    source,target=map(anchor,raw)
    row={'id':'link','form':'relative','source':source,'from_use':'source','language':'en',
         'targets':[{'source':target,'use':'target','language':'en'}],'authority':source,
         'questions':['Q1','Q2'],'reason':'Exact citation with unresolved meaning'}
    if version!='reviewed-references.v1':row['discovery_ids']=[]
    packet={'version':version,'assembly_sha256':digest(assembly),
            'review':{'reviewer':'test','kind':'DEVELOPMENT','reason':'test unknown target'},
            'references':[row]}
    return graph,assembly,packet


def test_v3_binds_unknown_target_without_resolving_meaning():
    g,a,p=fixture()
    deps,edges=admit(g,a,p)
    assert deps[0]['status']=='UNRESOLVED'
    assert deps[0]['source_binding']=='RESOLVED'
    assert deps[0]['unknown_target_uses']==['target']
    assert all(not e['resolved'] for e in edges)


@pytest.mark.parametrize('version',['reviewed-references.v1','reviewed-references.v2'])
def test_old_versions_keep_unknown_target_refusal(version):
    with pytest.raises(ValueError,match='not operative'):admit(*fixture(version))


@pytest.mark.parametrize('role',['EXCLUDED','HEADER','INSTRUCTION'])
def test_v3_cannot_admit_nonselected_target(role):
    with pytest.raises(ValueError):admit(*fixture(role=role))


def test_operative_behavior_is_unchanged_between_v2_and_v3():
    assert admit(*fixture('reviewed-references.v2','OPERATIVE'))==admit(*fixture(role='OPERATIVE'))


@pytest.mark.parametrize('mutation',['resolve','hide-question','hide-closure','duplicate','alter-source'])
def test_generic_consumer_refuses_unknown_meaning_forgery(mutation):
    g,a,p=fixture()
    deps,_=admit(g,a,p)
    for q in ('Q1','Q2'):
        deps.append({'id':'reference-closure:'+q,'questions':[q],'status':'UNRESOLVED',
                     'unresolved':['Unresolved reference: reviewed-reference:link']})
    semantic={'dependencies':deps,'questions':{q:{'unresolved':['reviewed-reference:link','reference-closure:'+q]} for q in ('Q1','Q2')}}
    verify_consumed(g,a,{'reference_admission':p},semantic)
    if mutation=='resolve':deps[0]['status']='RESOLVED'
    elif mutation=='hide-question':semantic['questions']['Q2']['unresolved'].remove('reviewed-reference:link')
    elif mutation=='hide-closure':deps[1]['unresolved']=[]
    elif mutation=='duplicate':deps.append(deepcopy(deps[0]))
    else:p['references'][0]['targets'][0]['source']['quote']='wrong'
    with pytest.raises(ValueError):verify_consumed(g,a,{'reference_admission':p},semantic)
