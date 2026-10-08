from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation import Interpretations
from legalmath.interpretation.search.engine import Search,create_search,select_node,backpropagate
from legalmath.interpretation.search.formal import Comparisons
from legalmath.interpretation.search.models import Settings
from legalmath.review.lifecycle import Lifecycle
from legalmath.interpretation.review import guard
from tests.search.support import packet,generation,FunctionProvider

AT='2026-09-23T00:00:00.000000Z'


def setup(db,root,tmp_path,provider,settings=None,p=None):
    Lifecycle(db).register({'author':{'token':'author','roles':['author']},'meaning':{'token':'meaning','roles':['meaning']}})
    service=Interpretations(db);settings=settings or Settings(max_model_calls=6,max_rounds=2)
    run=create_search(service,'author','search',p or packet(),settings)
    checker=Comparisons(tmp_path/'java',root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,
        {'months':{'min':'0','max':'12','allow_unknown':True}})
    return Search(service,'author',run['run_id'],provider,checker)


def answers(request):
    if request['task']=='GENERATE':
        return generation('>' if request['role']=='alternatives' else '>=')
    if request['task']=='REFINE':
        v=generation();v['readings'][0]['assumptions']=['Calendar-month definition needs bank approval']
        v['readings'][0]['distinction']='Expose previously implicit calendar convention'
        return v
    return {'formalization':generation()['readings'][0]['formalization'],'uncertainty':[]}


@pytest.mark.parametrize('scheduler',['bfs','uct'])
def test_actual_generation_expansion_roundtrip_and_release_block(db,root,tmp_path,scheduler):
    provider=FunctionProvider(answers)
    search=setup(db,root,tmp_path,provider,Settings(scheduler=scheduler,max_model_calls=6,max_rounds=2))
    report=search.drive()
    assert report['status']=='BLOCKED_UNRESOLVED',search.state['failures']
    assert not report['release_eligible'] and report['probability_of_legal_correctness'] is None
    assert len(search.state['nodes'])==3 and any(n['parent'] for n in search.state['nodes'])
    assert search.state['roundtrips'] and search.state['comparisons'][0]['result']['status']=='DIFFERENT'
    assert any(n['visits'] for n in search.state['nodes'])
    assert [r['task'] for r in provider.requests[:3]]==['GENERATE']*3
    assert all(r['parent'] is None and not r['diagnostics'] for r in provider.requests[:3])
    assert search.verify_report()==report
    for node in search.state['nodes']:
        with search.db.connect() as con:
            with pytest.raises(LegalMathError,match='Release'):guard(search.db,con,node['bundle_hash'])
    calls=len(provider.requests);assert search.drive()==report and len(provider.requests)==calls


def test_unanimous_omission_and_invalid_encoding_are_preserved(db,root,tmp_path):
    p=packet();p['units'].append({'unit_id':'footnote','locator':'footnote','text':'Consult the Code for exceptions.','normative':True,'span':None})
    def respond(request):
        v=generation();v['coverage'].append({'unit_id':'footnote','status':'CONTEXT','reason':'All members mistakenly ignore obligation'})
        v['readings'][0]['formalization']['result']='(invented months)'
        return v
    search=setup(db,root,tmp_path,FunctionProvider(respond),Settings(max_model_calls=3),p)
    report=search.drive()
    assert report['status']=='BLOCKED_UNRESOLVED'
    assert search.state['nodes'][0]['encoding_error'] and search.state['nodes'][0]['disposition']=='UNREVIEWED'
    records=search.s.read('author',search.rid)['records']
    assert any(i['kind']=='SOURCE_COVERAGE' and i['source_unit_ids']==['footnote'] for i in records['issue'])
    assert report['material']['unexpanded_nodes'] and report['material']['material_unresolved_issue_ids']


def test_model_failure_consumes_calls_and_cannot_disappear(db,root,tmp_path):
    provider=FunctionProvider(lambda request:{'release_eligible':True})
    search=setup(db,root,tmp_path,provider,Settings(max_model_calls=3))
    report=search.drive()
    assert report['model_calls']==3 and len(search.state['failures'])==3
    assert report['material']['unconsidered_dimensions'] and not report['release_eligible']


def test_interruption_is_terminal_without_redispatch(db,root,tmp_path):
    provider=FunctionProvider(answers);search=setup(db,root,tmp_path,provider)
    search.state['model_calls']=1;search.state['pending']='unknown-dispatch';search.save()
    recovered=setup_existing(search,provider).drive()
    assert recovered['stop']=='INTERRUPTED_REVIEW_REQUIRED' and provider.requests==[]
    assert recovered['model_calls']==1


def setup_existing(search,provider):
    return Search(search.s,'author',search.rid,provider,search.checker)


def test_report_material_cannot_hide_uncertainty(db,root,tmp_path):
    search=setup(db,root,tmp_path,FunctionProvider(answers),Settings(max_model_calls=3))
    report=search.drive();report['material']['material_unresolved_issue_ids']=[]
    with db.transaction() as con:search.s._save(con,'search-report',report,'report')
    with pytest.raises(LegalMathError):search.verify_report()


def test_uct_explores_unvisited_roots_and_backpropagates_actual_reward():
    nodes=[{'node_id':n,'root':n,'parent':None,'order':i,'depth':0,'visits':0,'reward':0,'expanded':False,'issued_calls':0} for i,n in enumerate(['a','b'])]
    settings=Settings(scheduler='uct')
    assert select_node(nodes,settings)['node_id']=='a'
    backpropagate(nodes,'a',1)
    assert select_node(nodes,settings)['node_id']=='b'
    nodes.append({'node_id':'c','root':'a','parent':'a','order':2,'depth':1,'visits':0,'reward':0,'expanded':False,'issued_calls':0})
    backpropagate(nodes,'c',2)
    assert nodes[0]['reward']==3 and nodes[0]['visits']==2


def test_invalid_live_style_unit_reference_triggers_counted_output_repair(db,root,tmp_path):
    def respond(request):
        if request['task']=='REFINE':
            value=answers(request);value['dimensions'][0]['source_unit_ids'].append('invented-unit')
            return value
        if request['task']=='REPAIR_OUTPUT':
            assert 'invented-unit' in str(request['invalid_response'])
            assert request['allowed_source_unit_ids']==['p1']
            return answers({'task':'REFINE'})
        return answers(request)
    provider=FunctionProvider(respond)
    search=setup(db,root,tmp_path,provider,Settings(max_model_calls=6,max_rounds=1))
    report=search.drive()
    assert any(n['parent'] for n in search.state['nodes']),search.state['failures']
    assert 'REPAIR_OUTPUT' in [r['task'] for r in provider.requests]
    assert search.state['failures'][0]['repair']=='VALIDATED_OUTPUT_ONLY_MEANING_UNRESOLVED'
    assert report['model_calls']==6 and not report['release_eligible']
    with db.connect() as con:
        failed=search.s._get(con,search.rid,'action',search.state['failures'][0]['action_id'])
        raw=search.s._get(con,search.rid,'search-response',failed['action_id'])
    assert failed['state']=='FAILED' and 'invented-unit' in str(raw['response'])
    from scripts.interpretation_search_pilot import pilot_measurements
    counts,accepted=pilot_measurements(search,report)
    assert accepted and counts['failures'] and not counts['unrepaired_failures']


@pytest.mark.parametrize('change',[{'release_eligible':True},{'probability_of_legal_correctness':'0.99'},
                                  {'status':'READY_FOR_REVIEW'},{'model_calls':0}])
def test_report_verifier_rejects_forged_authority_or_accounting(db,root,tmp_path,change):
    search=setup(db,root,tmp_path,FunctionProvider(lambda r:{'invalid':'output'}),Settings(max_model_calls=3))
    report=search.drive();report.update(change)
    with db.transaction() as con:search.s._save(con,'search-report',report,'report')
    with pytest.raises(LegalMathError,match='integrity'):search.verify_report()


def test_idempotent_create_binds_scheduler_and_all_search_settings(db,root,tmp_path):
    search=setup(db,root,tmp_path,FunctionProvider(answers))
    changed=search.settings.model_copy(update={'scheduler':'uct'})
    with pytest.raises(LegalMathError):create_search(search.s,'author','search',packet(),changed)


def test_repeated_invalid_repair_has_distinct_counted_actions(db,root,tmp_path):
    provider=FunctionProvider(lambda r:{'invalid':'output'})
    search=setup(db,root,tmp_path,provider,Settings(max_model_calls=3,max_output_repairs=2))
    report=search.drive()
    assert report['model_calls']==3 and len(provider.requests)==3
    assert len({f['action_id'] for f in search.state['failures']})==3
    assert report['stop']=='CALL_LIMIT'


@pytest.mark.parametrize('scheduler',['bfs','uct'])
def test_bounded_search_descends_to_a_grandchild_and_keeps_frontier(db,root,tmp_path,scheduler):
    """Multiple rounds must exercise lineage, not only create first-level children."""
    refinement = {'count': 0}

    def respond(request):
        if request['task'] == 'GENERATE':
            comparator = {'normative': '>=', 'controlled-language': '>', 'alternatives': '='}[request['role']]
            value = generation(comparator)
            value['readings'][0]['local_id'] = request['role'] + '-root'
            value['readings'][0]['statement'] = 'Initial root ' + request['role']
            value['readings'][0]['distinction'] = 'Initial distinction ' + request['role']
            return value
        if request['task'] == 'REFINE':
            refinement['count'] += 1
            index = refinement['count']
            value = generation('>' if index % 2 else '>=')
            value['readings'][0]['local_id'] = 'refinement-' + str(index)
            value['readings'][0]['statement'] = 'Refined reading ' + str(index)
            value['readings'][0]['distinction'] = 'Refined distinction ' + str(index)
            value['readings'][0]['assumptions'] = ['fixture refinement ' + str(index)]
            return value
        if request['task'] == 'RECONSTRUCT':
            # This fixture deliberately returns a valid formalization without
            # granting a semantic oracle. Any drift is retained by the engine.
            return {'formalization': generation('>=')['readings'][0]['formalization'], 'uncertainty': []}
        raise AssertionError('Unexpected request task: ' + request['task'])

    provider = FunctionProvider(respond)
    settings = Settings(scheduler=scheduler, max_model_calls=12, max_rounds=4,
                        max_actions_per_root=3, max_output_repairs=0)
    search = setup(db,root,tmp_path,provider,settings)
    report = search.drive()

    assert report['status'] == 'BLOCKED_UNRESOLVED'
    assert report['release_eligible'] is False
    assert search.state['rounds'] == 4
    assert search.state['model_calls'] == len(provider.requests) == 10
    grandchild = [n for n in search.state['nodes'] if n['depth'] == 2]
    assert grandchild, [(n['node_id'], n['depth'], n['parent']) for n in search.state['nodes']]
    for node in grandchild:
        parent = next(n for n in search.state['nodes'] if n['node_id'] == node['parent'])
        assert parent['depth'] == 1
        assert parent['root'] == node['root']
        assert node['node_id'] in report['material']['unexpanded_nodes']
    assert len(search.state['java_checks']) == len(search.state['nodes'])
    assert search.verify_report() == report
