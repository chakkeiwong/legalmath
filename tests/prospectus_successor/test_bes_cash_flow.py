"""Finite original reading and consumer glue; no fresh extraction claim."""
from copy import deepcopy
from pathlib import Path
import pytest
from legalmath.prospectus.successor import bes_cash_flow as cash, service
from legalmath.prospectus.successor.contracts import digest, validate_request
from scripts.prospectus_bes_cash_flow import (ROOT, FIXTURE, load, PROFILE_CONTROLS,
    OUTPUT_CONTROLS, profile_mutation, output_mutation, reject_altered_outputs)
from scripts.prospectus_bes_cash_flow_oracle import verify_review, signed_integer
from test_successor import request

@pytest.fixture
def f():
    return load(ROOT / FIXTURE)

def oracle(f, actual):
    return verify_review(actual, f['profile'], f['graph'], f['original_reading'], f['original_units'])

def product_set(tmp_path, f, configured=True):
    # These are explicitly supplied source occurrences. The admitted package
    # separately checks the original full P1 and its complete saved answer.
    req = request(tmp_path, ['Consumer-glue diagnostic'])
    req.pop('assembly'); req.pop('scope')
    req['bundle']['dependencies'] = [{'id': 'original-unresolved', 'questions': ['Q1','Q2'], 'status': 'UNRESOLVED'}]
    graph = deepcopy(service.source_product(req, tmp_path)['payload']['graph'])
    graph.update(units=deepcopy(f['graph']['units']), references=[], unresolved=[])
    p1 = service.seal('P1', req['bundle'], {'request': digest(req)}, {'request': req, 'graph': graph})
    p2 = service.construction_product(p1, tmp_path)
    profile = deepcopy(f['profile']); profile['graph_sha256'] = digest(graph)
    # Byte-identity tests use local copies of the actually inspected images.
    for e in profile['editions']:
        name = e['language'] + '.png'
        (tmp_path / name).write_bytes((ROOT / e['image']['path']).read_bytes())
        e['image']['path'] = name
    p3 = service.interpretation_product(p1, p2, {'source_cash_flow': profile} if configured else None)
    ps = {'P1':p1,'P2':p2,'P3':p3,'P4':service.law_product(p1,p3),'P5':service.financial_product(p1,p2,p3)}
    return ps, profile

def reseal(ps, changed):
    ps['P3'] = {**changed, 'sha256':digest({k:v for k,v in changed.items() if k!='sha256'})}
    ps['P4'] = service.law_product(ps['P1'],ps['P3'])
    ps['P5'] = service.financial_product(ps['P1'],ps['P2'],ps['P3'])

def test_original_reading_checks_complete_and_incomplete_relations(f):
    actual = cash.admit(f['graph'], f['profile'])
    checked = oracle(f, actual)
    assert checked['relations'] == 8 and checked['incomplete_relations'] == 4
    en, pt = actual['editions']
    assert en['relations'][0]['residual'] == 40 and pt['relations'][0]['residual'] == 0
    assert en['relations'][1]['residual'] is None and en['relations'][1]['known_residual_part'] == -40
    assert en['capital_increase']['cells']['2008']['value'] is None
    assert pt['capital_increase']['cells'] is None
    assert actual['controlling_edition'] is None and not actual['may_execute_transaction']

@pytest.mark.parametrize('name', PROFILE_CONTROLS)
def test_malformed_semantic_profile_rejected(f, name):
    with pytest.raises(ValueError):
        cash.admit(f['graph'], profile_mutation(f['profile'], name))

@pytest.mark.parametrize('name', OUTPUT_CONTROLS)
def test_separate_verifier_rejects_wrong_semantic_output(f, name):
    actual = cash.admit(f['graph'], f['profile'])
    with pytest.raises(ValueError):
        oracle(f, output_mutation(actual, name))

def test_actual_adverse_loop_detects_permissive_checker(f):
    actual = cash.admit(f['graph'], f['profile'])
    with pytest.raises(ValueError, match='Incorrect output accepted'):
        reject_altered_outputs(actual, lambda _: True)
    assert len(reject_altered_outputs(actual, lambda a: oracle(f,a))) == len(OUTPUT_CONTROLS)

@pytest.mark.parametrize('lang,literal,value', [('en','(4,041,798)',-4041798),('pt','(4 041 798)',-4041798),
    ('en','0',0),('pt','-',None),('en','187',187)])
def test_independent_parsers_on_original_integer_forms(lang,literal,value):
    assert cash.number(literal,lang) == value and signed_integer(literal,lang) == value

@pytest.mark.parametrize('lang,literal', [('en','4,04,1798'),('pt','4,041,798'),('en','4 041 798'),
    ('en','4.0'),('pt','01'),('en',''),('en','+40'),('en','-40'),('pt','１'),('en','(40')])
def test_both_parsers_refuse_ambiguous_numerals(lang,literal):
    for parser in (cash.number,signed_integer):
        with pytest.raises(ValueError): parser(literal,lang)

def test_frozen_consumer_on_off_preserves_complete_diagnostic_answer(tmp_path,f):
    ps, profile = product_set(tmp_path,f,False)
    before = service.consume(ps,tmp_path,include_artifacts=True)
    p3 = service.interpretation_product(ps['P1'],ps['P2'],{'source_cash_flow':profile})
    reseal(ps,p3)
    after = service.consume(ps,tmp_path,include_artifacts=True)
    assert after['mode']=='ASSISTED' and cash.ADDED in after and cash.ADDED not in before
    for key in before:
        if key not in {'mode','report_sha256','consumed_products'}: assert digest(after[key])==digest(before[key])
    assert after['questions']['Q3']['status']=='PARTIAL' and not after['may_execute_transaction']
    req = deepcopy(ps['P1']['payload']['request']); req['source_cash_flow']=profile
    validate_request(req)

@pytest.mark.parametrize('name', [*OUTPUT_CONTROLS,'missing-output','missing-input','integer-boolean-equality'])
def test_normal_consumer_recomputes_resealed_cash_flow(tmp_path,f,name):
    ps,_ = product_set(tmp_path,f)
    p3 = deepcopy(ps['P3'])
    if name=='missing-output': del p3['payload']['source_cash_flow']
    elif name=='missing-input': p3['payload']['interpretation_input']=None
    elif name=='integer-boolean-equality': p3['payload']['source_cash_flow']['editions'][1]['relations'][0]['residual']=False
    else: p3['payload']['source_cash_flow']=output_mutation(p3['payload']['source_cash_flow'],name)
    reseal(ps,p3)
    with pytest.raises(ValueError,match='Cash-flow'): service.consume(ps,tmp_path)

def test_normal_consumer_rejects_changed_image(tmp_path,f):
    ps,_=product_set(tmp_path,f)
    (tmp_path/'en.png').write_bytes(b'changed')
    with pytest.raises(ValueError,match='image bytes'): service.consume(ps,tmp_path)

def test_repinned_changed_graph_cannot_pass_original_reading_oracle(f):
    altered=deepcopy(f)
    u=next(u for u in altered['graph']['units'] if u['id']=='bes-2008-en:p170:l67')
    u['raw']='-'
    a=altered['profile']['editions'][0]['rows']['buy_investments']['cells'][0]
    a.update(quote='-',end=1)
    altered['profile']['graph_sha256']=digest(altered['graph'])
    result=cash.admit(altered['graph'],altered['profile'])
    assert 'None' not in result['explanation'] and 'unknown' in result['explanation']
    with pytest.raises(ValueError,match='Original row mapping changed'): oracle(altered,result)

def test_historical_composition_uses_authority_hash_not_product_hash(tmp_path):
    from legalmath.prospectus.execution_authority import digest as historical_digest, write, file_hash
    from scripts.prospectus_bes_cash_flow import compressed, reconstruct
    baseline={'original':{'amount':40,'known':False}};overlay={'later':{'dash':None}}
    assert digest(baseline)!=historical_digest(baseline)
    refs={}
    for name,value in [('baseline',baseline),('overlay',overlay)]:
        path=tmp_path/(name+'.json.gz');compressed(path,value)
        refs[name]={'path':path.name,'file_sha256':file_hash(path),'content_sha256':historical_digest(value)}
    write(tmp_path/'composition.json',{**refs,'complete_composed_answer_sha256':historical_digest({**baseline,**overlay})})
    assert reconstruct(tmp_path,'composition.json')=={**baseline,**overlay}

def test_saved_selected_request_parent_is_reconstructed_without_changing_children(tmp_path):
    from scripts.prospectus_bes_cash_flow import NORMAL, products, compressed
    from legalmath.prospectus.execution_authority import write
    req=request(tmp_path,['Original raw request'])
    raw=service.source_product(req,tmp_path)
    selected=deepcopy(req);selected['source_report_readings']={'diagnostic':'retained selection'}
    p1=service.seal('P1',req['bundle'],{'request':digest(selected)},{'request':selected,'graph':raw['payload']['graph']})
    ps={'P1':p1}
    for phase,parents in [('P2',['P1']),('P3',['P1','P2']),('P4',['P1','P3']),('P5',['P2','P3'])]:
        ps[phase]=service.seal(phase,req['bundle'],{k:ps[k]['sha256'] for k in parents},{'diagnostic':phase})
    folder=tmp_path/NORMAL
    compressed(folder/'original-P1.json.gz',raw)
    compressed(folder/'candidate-P2-P5.json.gz',{k:v for k,v in ps.items() if k!='P1'})
    write(folder/'reading-input.json',selected['source_report_readings'])
    recovered=products(tmp_path)
    assert recovered==ps and recovered['P1']['sha256']!=raw['sha256']
