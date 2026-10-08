from copy import deepcopy
import pytest
from legalmath.canonical import loads
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.authorities import AuthorityCatalog
from legalmath.interpretation.assurance.examples import ExampleRegistry
from .test_authorities import catalog_data
from .support import packet,inventory

SCOPE={'issuer':'Securities and Futures Commission','jurisdiction':'Hong Kong','issue_ids':['gift']}
AT='2023-11-30T00:00:00.000000Z'


def fixture():
    value,docs=catalog_data();value['authorities'][0]['kind']='FAQ'
    catalog=AuthorityCatalog(value,docs);anchor=value['provisions'][0]['regions'][0]['anchor']
    case={'example_id':'fixture.gift','kind':'OFFICIAL_EXAMPLE','provision_id':'code.3.11','issue_id':'gift',
        'issue_description':'Controlled gift example','factors':[{'factor_id':'gift','description':'Gift offered','evidence':[anchor]}],
        'outcome':{'atom':'prohibited','negative':False},'outcome_description':'Fixture prohibition',
        'outcome_evidence':[anchor],'derivation':'Explicit synthetic registry fixture; not an actual SFC case.'}
    registry={'version':'example-registry.v1','authority_catalog_hash':catalog.hash,'examples':[case]}
    return registry,catalog


def query(negative=False):
    return {'queries':[{'candidate_id':'candidate','issue_id':'gift','factors':['gift'],
        'outcome':{'atom':'prohibited','negative':negative},'evidence':inventory()['claims'][0]['evidence']}], 'questions':[]}


def test_catalog_bound_example_reaches_real_case_constructors():
    registry=ExampleRegistry(*fixture());selected=registry.retrieve(SCOPE,AT)
    result=registry.reason(selected,query(True),packet(),['candidate'])
    assert {m['operator'] for m in result['moves']}=={'ANALOGISE','COUNTERCASE'}
    assert result['questions'] and all(not m['legal_priority_established'] for m in result['moves'])
    assert all(m['temporal_status']=='PUBLISHER_INTERVAL_MATCH' for m in result['moves'])
    assert not result['candidate_pruning_authorized']


@pytest.mark.parametrize('field,value',[('issuer','Other issuer'),('jurisdiction','Other jurisdiction'),('issue_ids',['other'])])
def test_scope_mismatch_excludes_examples(field,value):
    registry=ExampleRegistry(*fixture());result=registry.retrieve({**SCOPE,field:value},AT)
    assert not result['examples'] and result['excluded']


def test_wrong_unknown_missing_and_hypothetical_sources_are_explicit():
    data,catalog=fixture();registry=ExampleRegistry(data,catalog)
    assert registry.retrieve(SCOPE,'2026-01-01')['excluded'][0]['reason']=='WRONG_EDITION'
    assert registry.retrieve(SCOPE,AT,maximum=0)['excluded'][0]['reason']=='EXAMPLE_LIMIT'
    data['examples'][0]['kind']='HYPOTHETICAL';registry=ExampleRegistry(data,catalog)
    assert registry.retrieve(SCOPE,AT)['excluded'][0]['reason']=='HYPOTHETICAL_NOT_AUTHORITY'
    data,catalog=fixture();v=deepcopy(catalog.value);v['editions'][0]['temporal_status']='UNKNOWN'
    catalog=AuthorityCatalog(v,catalog.documents);data['authority_catalog_hash']=catalog.hash
    registry=ExampleRegistry(data,catalog);result=registry.reason(registry.retrieve(SCOPE,AT),query(),packet(),['candidate'])
    assert result['moves'][0]['temporal_status']=='UNKNOWN_VERSION'
    assert any('edition' in q for q in result['questions'])
    catalog=AuthorityCatalog(v,{});data['authority_catalog_hash']=catalog.hash
    assert ExampleRegistry(data,catalog).retrieve(SCOPE,AT)['excluded'][0]['reason']=='MISSING_SOURCE'


@pytest.mark.parametrize('change',['court','quote','provision','catalog','factor'])
def test_invented_authority_or_factorization_rejected(change):
    data,catalog=fixture();example=data['examples'][0]
    if change=='court':example['kind']='CASE_LAW'
    if change=='quote':example['outcome_evidence'][0]={**example['outcome_evidence'][0],'quote':'A made-up outcome'}
    if change=='provision':example['provision_id']='unknown'
    if change=='catalog':data['authority_catalog_hash']='0'*64
    if change=='factor':example['factors'].append(deepcopy(example['factors'][0]))
    with pytest.raises(LegalMathError):ExampleRegistry(data,catalog)


def test_changed_retrieval_invented_factor_and_missing_candidate_are_not_clean():
    registry=ExampleRegistry(*fixture());retrieval=registry.retrieve(SCOPE,AT)
    changed=deepcopy(retrieval);changed['examples'][0]['temporal_status']='CERTAIN'
    with pytest.raises(LegalMathError):registry.reason(changed,query(),packet(),['candidate'])
    q=query();q['queries'][0]['factors']=['invented']
    with pytest.raises(LegalMathError):registry.reason(retrieval,q,packet(),['candidate'])
    result=registry.reason(retrieval,{'queries':[],'questions':[]},packet(),['candidate'])
    assert result['status']=='UNRESOLVED' and result['questions']


def test_opposed_examples_are_retained_as_countercases():
    data,catalog=fixture();opposed=deepcopy(data['examples'][0]);opposed['example_id']='fixture.opposed'
    opposed['outcome']['negative']=True;opposed['derivation']='Explicitly opposed synthetic interpretation of same fixture'
    data['examples'].append(opposed);registry=ExampleRegistry(data,catalog)
    result=registry.reason(registry.retrieve(SCOPE,AT),query(),packet(),['candidate'])
    assert 'DISTINGUISH_WITH_CASE' in {m['operator'] for m in result['moves']}
    assert not result['candidate_pruning_authorized']


def test_registry_change_invalidates_only_relevant_example_scope():
    data,catalog=fixture();a=ExampleRegistry(data,catalog).dependencies(SCOPE,AT)
    unrelated=deepcopy(data['examples'][0]);unrelated.update(example_id='other',issue_id='other')
    data['examples'].append(unrelated)
    assert ExampleRegistry(data,catalog).dependencies(SCOPE,AT)==a
    data['examples'][0]['outcome']['negative']=True
    assert ExampleRegistry(data,catalog).dependencies(SCOPE,AT)!=a


def test_assurance_uses_registry_queries_and_preserves_unknown_applicability(root,tmp_path):
    from legalmath.interpretation.assurance.engine import Assurance
    from tests.search.support import FunctionProvider
    from .test_integration import responder,settings,source
    registry=ExampleRegistry(*fixture());normal=responder()
    def respond(request):
        if request['task']=='REGISTERED_EXAMPLE_QUERIES':
            p=request['source_packet'];cid=next(iter(request['candidates']))
            q=query();q['queries'][0].update(candidate_id=cid,evidence=[{'unit_id':p['units'][0]['unit_id'],'quote':p['units'][0]['text']}])
            return q
        return normal(request)
    directory=tmp_path/'run'
    run=Assurance(directory,FunctionProvider(respond),root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,settings())
    result=run.drive([source()],'Gift',example_registry=registry,example_scope=SCOPE)
    assert result['execution_complete'],result
    assert result['case_moves'] and any(f['kind']=='EXAMPLE_APPLICABILITY_QUESTION' for f in result['findings'])
    assert (directory/'example-registry.json').is_file() and list((directory/'example-sources').glob('*.bin'))
    assert run.verify()==result


def test_unavailable_requested_example_check_is_incomplete_and_monitor_retries(root,tmp_path):
    from legalmath.interpretation.assurance.engine import Assurance
    from legalmath.interpretation.assurance.monitor import Monitor
    from tests.search.support import FunctionProvider
    from .test_integration import responder,settings,source
    registry=ExampleRegistry(*fixture());normal=responder()
    def respond(request):
        if request['task']=='REGISTERED_EXAMPLE_QUERIES':raise LegalMathError('E_RESOURCE_LIMIT')
        return normal(request)
    directory=tmp_path/'run'
    r=Assurance(directory,FunctionProvider(respond),root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,settings()).drive(
        [source()],'Gift',example_registry=registry,example_scope=SCOPE)
    assert not r['execution_complete'] and any(f['kind']=='EXAMPLE_QUERY_UNAVAILABLE' for f in r['findings'])
    monitor=Monitor(tmp_path/'monitor');control=[{'control_id':'gift','source':'s','dependencies':[]}]
    for t in (0,1):assert monitor.tick(control,{'s':'v'},'m','f',t,lambda c,s:r)['results'][0]['status']=='FAILED'
    assert monitor.tick(control,{'s':'v'},'m','f',2,lambda c,s:r)['results'][0]['status']=='REVISION_RETRY_LIMIT'


def test_cyclic_argument_analysis_cannot_be_cached_as_completed(root,tmp_path):
    from legalmath.interpretation.assurance.engine import Assurance
    from tests.search.support import FunctionProvider
    from .test_integration import responder,settings,source
    normal=responder()
    def respond(request):
        value=normal(request)
        if request['task']=='STRUCTURED_CRITICISM':
            value['arguments'][0]['parents']=[value['arguments'][0]['argument_id']]
        return value
    r=Assurance(tmp_path/'run',FunctionProvider(respond),root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,settings()).drive([source()],'Gift')
    assert r['argumentation']['status']=='CYCLIC_SUPPORT_UNRESOLVED' and not r['execution_complete']
