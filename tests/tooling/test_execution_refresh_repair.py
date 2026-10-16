from copy import deepcopy

import pytest
from jsonschema import ValidationError

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.bounded_product import NOTE
from legalmath.interpretation.assurance.bounded_references import prepare, resolve
from tests.assurance.test_remaining_integration_repairs import indexed_product


def answer_wire():
    return {'conclusion': 'Conditional.', 'support': [{'span_id': 's0'}],
        'contrary': [], 'assumptions': [], 'unresolved': [], 'alternatives': [],
        'considered': [], 'source_gaps': [], 'assertion_bindings': []}


def test_unindexed_request_cannot_offer_invented_assertion_bindings():
    record = {'id': 'source.r', 'kind': 'source', 'normative': True,
              'locator': 'synthetic', 'text': 'A court order exempts this transfer.'}
    prepared = prepare({'records': [record], 'available_source_indexes': [],
                        'verified_locator_bindings': []}, NOTE)
    value = answer_wire()
    assert resolve(value, prepared, maximum_bytes=24000)['support'][0]['quote'] == record['text']
    value['assertion_bindings'] = [{'path': '/conclusion', 'index_hash': digest('invented'),
                                   'citation': {'span_id': 's0'}}]
    with pytest.raises(ValidationError):
        resolve(value, prepared, maximum_bytes=24000)


def test_indexed_binding_preserves_source_and_still_checks_foreign_document_and_path(tmp_path):
    product, indexes = indexed_product(tmp_path)
    records = [r for r in product.route.records.values() if r['kind'] == 'source']
    request = product.request('ANSWER_ORIGINAL_QUESTION', 'Question', records)
    prepared = prepare(request, NOTE)
    value = answer_wire()
    value['conclusion'] = 'Paragraph 10 conditions the duty on a request.'
    value['assertion_bindings'] = [{'path': '/conclusion', 'index_hash': indexes[0]['index_hash'],
                                   'citation': {'span_id': 's0'}}]
    expanded = resolve(value, prepared, maximum_bytes=24000)
    product.citations(expanded, records)
    wrong = deepcopy(value)
    wrong['assertion_bindings'][0]['index_hash'] = digest('foreign')
    with pytest.raises(ValidationError):
        resolve(wrong, prepared, maximum_bytes=24000)
    wrong = deepcopy(expanded)
    wrong['assertion_bindings'][0]['path'] = '/missing'
    with pytest.raises(LegalMathError):
        product.citations(wrong, records)
    wrong = deepcopy(expanded)
    wrong['assertion_bindings'][0]['index_hash'] = indexes[1]['index_hash']
    with pytest.raises(LegalMathError):
        product.citations(wrong, records)


def test_index_metadata_without_delivered_locator_does_not_offer_assertions():
    record = {'id': 'source.r', 'kind': 'source', 'normative': True,
              'locator': 'unverified', 'text': 'Retained exact source.'}
    prepared = prepare({'records': [record],
        'available_source_indexes': [{'index_hash': digest('index'), 'source': {}}],
        'verified_locator_bindings': []}, NOTE)
    assert prepared['schema']['properties']['assertion_bindings']['maxItems'] == 0


def test_observation_choices_exclude_nonstring_values_and_preserve_exact_field():
    from legalmath.interpretation.assurance.bounded_context import observation_schema
    request={'records':[{'id':'metadata.r','kind':'metadata',
                        'value':{'name':'exact string','items':[], 'flag':True, 'number':3}}]}
    prepared=prepare(request,observation_schema(['metadata.r']))
    assert len(prepared['observations'])==1
    value={'records':[{'id':'r0','status':'UNRESOLVED','findings':[], 'open_dependencies':[],
        'observations':[{'observation_id':'m0','statement':'The supplied name is recorded.'}]}]}
    expanded=resolve(value,prepared,maximum_bytes=24000)
    assert expanded['records'][0]['observations'][0]=={
        'record_id':'metadata.r','path':['name'],'quote':'exact string','statement':'The supplied name is recorded.'}
    value['records'][0]['observations'][0]['observation_id']='m1'
    with pytest.raises(ValidationError):resolve(value,prepared,maximum_bytes=24000)


def test_unsupported_source_finding_cannot_be_marked_proposed():
    from legalmath.interpretation.assurance.bounded_context import response_schema
    record={'id':'source.r','kind':'source','normative':True,'locator':'synthetic','text':'A rule applies.'}
    prepared=prepare({'records':[record]},response_schema(['source.r']))
    value={'records':[{'id':'r0','status':'PROPOSED','open_dependencies':[],
        'findings':[{'statement':'Missing evidence.','support':[],'contrary':[]}]}]}
    with pytest.raises(ValidationError):resolve(value,prepared,maximum_bytes=24000)
    value['records'][0]['status']='UNRESOLVED'
    assert resolve(value,prepared,maximum_bytes=24000)['records'][0]['status']=='UNRESOLVED'


def test_campaign_passes_same_explicit_correction_setting_to_probe_and_product(tmp_path, monkeypatch):
    from scripts import legal_integration_campaign as campaign
    from tests.assurance.test_bounded_product import envelope
    captured = []
    monkeypatch.setattr(campaign, 'ROOT', tmp_path)
    monkeypatch.setattr(campaign, 'read', lambda path: {'deadline_utc': 'unused'}
        if path.name == 'live-grant.json' else envelope())
    monkeypatch.setattr(campaign, 'tokenizer', lambda path: list)
    monkeypatch.setattr(campaign, 'MAXIMUM_CORRECTIONS', 1)
    monkeypatch.setattr(campaign, 'run_product', lambda *a, **kw: captured.append(kw))
    monkeypatch.setattr(campaign, 'BoundedProduct', lambda *a, **kw: captured.append(kw))
    campaign.session(tmp_path/'probe', None, maximum=100)
    campaign.product(tmp_path/'product', None, maximum=100)
    assert captured[0]['maximum_corrections'] == captured[1]['required']['maximum_corrections'] == 1
    assert captured[0]['maximum_calls'] == captured[1]['required']['maximum_calls'] == 100


def test_arm_budget_includes_dependency_reviews_and_full_correction():
    from scripts.legal_integration_campaign import arm_call_budget
    ordinary = arm_call_budget(4, 9, 7, maximum_corrections=0)
    corrected = arm_call_budget(4, 9, 7, maximum_corrections=1)
    assert ordinary['review_calls'] == 20
    assert corrected['account_correction_reserve'] == 4
    assert corrected['warrant_assessment_reserve'] == 20
    assert corrected['correction_reserve'] == ordinary['maximum_calls'] + 4 + 20
    assert corrected['maximum_calls'] == 2 * ordinary['maximum_calls'] + 4 + 20
    assert arm_call_budget(4, 9, 8, maximum_corrections=1)['maximum_calls'] == corrected['maximum_calls'] + 3
    observed = arm_call_budget(4, 9, 7, maximum_corrections=1, observed_construction_calls=30)
    assert observed['construction_allowance']==60
    assert observed['maximum_calls']==2*(20+60)+4+20


def repair_program(root):
    from scripts.legal_mission_execution import save, ref
    from scripts.legal_integration_execution_repair import expected_program, REOPEN
    from scripts.legal_integration_acceptance_revision import historical_projection
    from tests.tooling.test_execution_refresh import revision, NEW, PLAN
    old, state = revision(root)
    for tid in NEW:
        state['tasks'][tid] = {'status': 'PENDING', 'attempts': []}
    state['tasks']['semantic-preflight'].update(status='BLOCKED', attempts=[{'number': 1}])
    state['program_hash'] = digest(old)
    save(root/'repair-old.json', old);save(root/'repair-state.json', state)
    save(root/'binding.json', {});save(root/'ledger.json', {'calls': []})
    (root/'repair-review.md').write_text('One bounded repair, original global grant unchanged.')
    old_plan = ref(root, PLAN)
    (root/'archived-plan.md').write_bytes((root/PLAN).read_bytes())
    archives = [{'previous':old_plan, 'archive':ref(root,'archived-plan.md')}]
    save(root/'repair-baseline.json', {'archived':archives})
    (root/PLAN).write_text('Repaired current master with original scope and limits.')
    correction = {'profile':'legal-execution-refresh-repair.v1','prior_detours':25,
        'additional_consolidated_revision':1,'live_calls_added':0,'attempts_reset':False,
        'semantic_stage_maximum':516,'reopened_nodes':list(REOPEN),
        'review':ref(root,'repair-review.md'),'baseline':ref(root,'repair-baseline.json'),
        'prior_program':ref(root,'repair-old.json'),'prior_state':ref(root,'repair-state.json'),
        'prior_binding':ref(root,'binding.json'),'prior_ledger':ref(root,'ledger.json')}
    projected=historical_projection(old,{(old_plan['path'],old_plan['sha256']):ref(root,'archived-plan.md')})
    return expected_program(projected,state,correction,root)


def test_repair_preserves_old_plan_and_acquisition_ceiling(tmp_path):
    from scripts.legal_mission_execution import validate_program
    program=repair_program(tmp_path)
    validate_program(program,tmp_path)
    semantic=next(t for t in program['tasks'] if t['id']=='semantic-preflight')
    acquire=next(t for t in program['tasks'] if t['id']=='acquire-p10')
    assert semantic['maximum_attempts']==2
    assert acquire['maximum_attempts']==1  # this fixture's existing ceiling


@pytest.mark.parametrize('fault',['deadline','acquisition','semantic','unrelated'])
def test_repair_refuses_unreviewed_extension(tmp_path,fault):
    from scripts.legal_mission_execution import validate_program,Refused
    program=repair_program(tmp_path)
    if fault=='deadline':program['deadline_utc']='2100-01-01T00:00:00+00:00'
    elif fault=='acquisition':next(t for t in program['tasks'] if t['id']=='acquire-p10')['maximum_attempts']+=1
    elif fault=='semantic':next(t for t in program['tasks'] if t['id']=='semantic-preflight')['maximum_attempts']+=1
    else:next(t for t in program['tasks'] if t['id']=='unrelated')['acceptance']='Changed'
    with pytest.raises(Refused):validate_program(program,tmp_path)


def test_current_live_entry_uses_reviewed_scope_without_dispatch_arity_failure(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from scripts import legal_integration_current_live as live
    from scripts import legal_integration_reopening_live as controls
    captured=[]
    completed=[]
    class Execution:
        def __init__(self,*args):pass
        def run(self):
            captured.append('local-frontier-drained')
        def summary(self):
            return {'ready':[] if completed else ['semantic-preflight'],'running':[],
                    'tasks':{'semantic-preflight':{'status':'BLOCKED' if completed else 'READY'}}}
    def complete(execution,tid,function):
        completed.append((tid,function()))
    monkeypatch.setattr(live,'ROOT',tmp_path)
    monkeypatch.setattr(live,'MasterExecution',Execution)
    monkeypatch.setattr(live,'activate',lambda:SimpleNamespace(
        provider=lambda:SimpleNamespace(check=lambda:None),complete_node=complete))
    monkeypatch.setattr(live,'current_scope',lambda:(live.LIVE,'review',256,516,1))
    monkeypatch.setattr(live,'admit_stage',lambda name,maximum:captured.append((name,maximum)))
    monkeypatch.setattr(live,'read',lambda path:{})
    monkeypatch.setattr(live,'ref',lambda root,path:{'path':str(path),'sha256':'test'})
    def semantic(service,**kwargs):
        captured.append(kwargs)
        return {'qualified':False}
    monkeypatch.setattr(controls,'semantic_control',semantic)
    result=live.live()
    assert result['tasks']['semantic-preflight']['status']=='BLOCKED'
    assert captured[0]==('semantic-preflight',516)
    assert captured[1]['per_case_calls']==256 and captured[1]['maximum_corrections']==1
    assert completed[0][1]['_node_status']=='BLOCKED'
    assert captured[-1]=='local-frontier-drained'

