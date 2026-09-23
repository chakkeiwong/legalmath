from copy import deepcopy
import pytest
from legalmath.errors import LegalMathError
from legalmath.interpretation.search.formal import bundle, Comparisons, reconstruction_request, expression
from legalmath.ir.evaluate import evaluate
from tests.search.support import packet,generation

AT='2026-09-23T00:00:00.000000Z'


@pytest.mark.parametrize('text',['(>= x)','(eval python)','true false','('*40+'x'+')'*40,'(integer 1.5)'])
def test_invalid_expression_cannot_become_executable(text):
    reading=generation()['readings'][0];reading['formalization']['result']=text
    with pytest.raises(LegalMathError):bundle(reading,packet(),AT)


def test_roundtrip_request_does_not_leak_original_formula():
    r=generation()['readings'][0];b=bundle(r,packet(),AT);request=reconstruction_request(r,b)
    assert 'result' not in request and 'parent' not in request and 'source_packet' not in request
    assert 'greater than or equal to' in request['result_text']
    assert '(>= months' not in str(request)


def test_smt_witness_is_replayed_in_both_generated_java_classes(root,tmp_path):
    checker=Comparisons(tmp_path,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,
        {'months':{'min':'0','max':'12','allow_unknown':True}})
    a=generation()['readings'][0];b=generation('>')['readings'][0]
    result=checker.compare(a,b,packet())
    assert result['status']=='DIFFERENT'
    assert result['snapshot']['facts']['months']['value']=='6'
    assert result['replays'][0]['java']['status']=='TRUE' and result['replays'][1]['java']['status']=='FALSE'
    assert not result['legal_source_commitment_resolved']
    equal=checker.compare(a,deepcopy(a),packet())
    assert equal['status']=='EQUIVALENT_WITHIN_DOMAIN'


def test_unknown_domain_and_fact_changes_never_count_as_equivalence(root,tmp_path):
    checker=Comparisons(tmp_path,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT)
    a=generation()['readings'][0];b=deepcopy(a)
    assert checker.compare(a,b,packet())['status']=='NO_DIFFERENCE_IN_FINITE_PROBES'
    b['formalization']['facts'][0]['meaning']='Thirty-day periods'
    assert checker.compare(a,b,packet())['status']=='INCOMPARABLE_FACT_BINDINGS'


def test_small_probe_budget_still_exercises_known_scope():
    from legalmath.interpretation.search.formal import snapshots
    reading=generation()['readings'][0]
    reading['formalization']['facts'] += [{'name':'b'+str(i),'type':'bool','meaning':'Condition '+str(i),
        'unit':'Boolean','source_unit_ids':['p1'],'requires_judgment':False} for i in range(8)]
    reading['formalization']['scope']='(and '+' '.join('b'+str(i) for i in range(8))+')'
    compiled=bundle(reading,packet(),AT)
    results=[evaluate(compiled,s,'selected.control',AT,AT) for s in snapshots([compiled],AT,maximum=12)]
    assert any(r['status']=='TRUE' for r in results)


def linkage_pair():
    a=generation()['readings'][0]
    a['formalization']={'facts':[{'name':name,'type':'bool','meaning':meaning,'unit':'truth value',
        'source_unit_ids':['p1'],'requires_judgment':True} for name,meaning in (
            ('scope_fact','Distributor in selected scope'),('gift','Gift offered'),
            ('discount','Gift is solely a fee discount'),('direct','Direct product link'),
            ('contextual','Contextual product link'))],
        'scope':'scope_fact','result':'(and gift (not discount) direct)','result_type':'bool'}
    b=deepcopy(a);b['formalization']['result']='(and gift (not discount) (or direct contextual))'
    return a,b


def test_complete_boolean_domain_finds_live_interaction_missed_by_probes(root,tmp_path):
    from legalmath.interpretation.search.formal import snapshots,project
    a,b=linkage_pair();bundles=[bundle(r,packet(),AT) for r in (a,b)]
    # Reproduce the observed weakness instead of testing an easier unrelated pair.
    probes=list(snapshots(bundles,AT))
    assert len(probes)==128
    assert all(project(evaluate(bundles[0],s,'selected.control',AT,AT))==
               project(evaluate(bundles[1],s,'selected.control',AT,AT)) for s in probes)
    checker=Comparisons(tmp_path,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT)
    result=checker.compare(a,b,packet())
    assert result['status']=='DIFFERENT'
    assert result['domain_origin']=='COMPLETE_DECLARED_BOOLEAN_STATE_SPACE'
    assert all(d['states']==['T','F','U'] for d in result['domain'].values())
    assert result['solver']['status']=='COUNTEREXAMPLE'
    assert project(result['replays'][0]['java'])!=project(result['replays'][1]['java'])
    equivalent=checker.compare(a,deepcopy(a),packet())
    assert equivalent['status']=='EQUIVALENT_WITHIN_DOMAIN'
    assert not equivalent['legal_source_commitment_resolved']


def test_declared_boolean_domain_is_not_silently_replaced(root,tmp_path):
    a,b=linkage_pair();domain={f['name']:{'states':['T','F']} for f in a['formalization']['facts']}
    domain['contextual']={'states':[]}
    checker=Comparisons(tmp_path,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,domain)
    result=checker.compare(a,b,packet())
    assert result['status']=='INCONSISTENT_DOMAIN' and result['domain_origin']=='CALLER_DECLARED'


def test_boolean_solver_unknown_is_visible_and_cannot_mean_equivalence(root,tmp_path,monkeypatch):
    from legalmath.interpretation.search import formal
    a,_=linkage_pair()
    monkeypatch.setattr(formal,'smt_compare',lambda *args,**kwargs:{'status':'UNKNOWN','reason':'TIME_BUDGET'})
    result=Comparisons(tmp_path,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT).compare(a,a,packet())
    assert result['status']=='NO_DIFFERENCE_IN_FINITE_PROBES'
    assert result['solver']['status']=='UNKNOWN' and not result['equivalence_established']


@pytest.mark.parametrize('solver_status,kind', [('UNKNOWN','integer'), ('UNSUPPORTED','integer'), ('UNKNOWN','bool')])
def test_unresolved_declared_domain_never_uses_out_of_domain_witness(root,tmp_path,monkeypatch,solver_status,kind):
    from legalmath.interpretation.search import formal
    a=generation()['readings'][0];b=generation('>')['readings'][0]
    domain={'months':{'min':'7','max':'12','allow_unknown':False}}
    if kind=='bool':
        a,_=linkage_pair()
        a['formalization']['facts']=a['formalization']['facts'][:1]
        a['formalization']['scope']='true';a['formalization']['result']='scope_fact'
        b=deepcopy(a);b['formalization']['result']='false'
        domain={'scope_fact':{'states':['F']}}
    monkeypatch.setattr(formal,'smt_compare',lambda *args,**kwargs:{'status':solver_status,'reason':'TEST_UNRESOLVED'})
    result=Comparisons(tmp_path,root/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT,domain).compare(a,b,packet())
    assert result['status']==solver_status
    assert result['domain']==domain and result['domain_origin']=='CALLER_DECLARED'
    assert 'snapshot' not in result and result['probes']==0
    assert not result['equivalence_established']
